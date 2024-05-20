import asyncio
import datetime
import functools
import inspect
import mimetypes
import os
import typing

import bson
import gridfs
import pymongo
from motor.core import AgnosticClient, AgnosticDatabase, AgnosticCollection, AgnosticClientSession
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket, AsyncIOMotorGridOut
from motor.motor_gridfs import AgnosticGridFSBucket
from pymongo.read_concern import ReadConcern

from mongotoy import documents, expressions, references, fields, types, sync
from mongotoy.errors import EngineError, NoResultsError, ManyResultsError, SessionError

__all__ = (
    'Engine',
    'Session',
)

from mongotoy.expressions import Query

T = typing.TypeVar('T', bound=documents.Document)


class Engine:
    # noinspection GrazieInspection
    """
        Represents a MongoDB engine with asynchronous support.

        Args:
            database (str): The name of the MongoDB database.
            codec_options (bson.CodecOptions): The BSON codec options.
            read_preference (pymongo.ReadPreference): The read preference for the MongoDB client.
            read_concern (pymongo.ReadConcern): The read concern for the MongoDB client.
            write_concern (pymongo.WriteConcern): The write concern for the MongoDB client.

        Example:
            # Create an Engine instance
            engine = Engine(
                database='my_database',
                codec_options=bson.CodecOptions(),
                read_preference=pymongo.ReadPreference.PRIMARY,
                read_concern=pymongo.ReadConcern('majority'),
                write_concern=pymongo.WriteConcern(w=2)
            )

            # Connect to the MongoDB server
            await engine.connect('mongodb://localhost:27017/')

            # Access the MongoDB client and database
            client = engine.client
            database = engine.database

            # Create a session and perform operations
            async with engine.session() as session:
                # Insert a document
                my_doc = MyDocument()
                await session.save(my_doc)
        """

    def __init__(
        self,
        database: str,
        codec_options: bson.CodecOptions = None,
        read_preference: pymongo.ReadPreference = None,
        read_concern: ReadConcern = None,
        write_concern: pymongo.WriteConcern = None
    ):
        forbid_chars = {"/", "\\", ".", '"', "$"}
        forbidden = forbid_chars.intersection(set(database))
        if len(forbidden) > 0:
            raise EngineError(f"Database name cannot contain: {' '.join(forbidden)}")

        self._database = database
        self._codec_options = codec_options
        self._read_preference = read_preference
        self._read_concern = read_concern
        self._write_concern = write_concern
        self._db_client = None
        self._migration_lock = asyncio.Lock()

    @property
    def client(self) -> AgnosticClient:
        """
        Returns the MongoDB client.

        Raises:
            EngineError: If the engine is disconnected, the connect method must be called first.
        """
        if not self._db_client:
            raise EngineError('Engine disconnected, call connect(...) method first')
        return self._db_client

    @property
    def database(self) -> AgnosticDatabase:
        """
        Returns the MongoDB database.

        Returns:
            AgnosticDatabase: The MongoDB database with configured options.
        """
        # noinspection PyTypeChecker
        return self.client.get_database(
            name=self._database,
            codec_options=self._codec_options,
            read_preference=self._read_preference,
            read_concern=self._read_concern,
            write_concern=self._write_concern
        )

    def _get_document_indexes(
        self,
        document_cls: typing.Type[documents.BaseDocument],
        parent: str = None
    ) -> list[pymongo.IndexModel]:
        """
        Retrieves document indexes.

        Args:
            document_cls (typing.Type[documents.BaseDocument]): The document class.
            parent (str, optional): The parent document.

        Returns:
            list[pymongo.IndexModel]: List of pymongo IndexModels.
        """
        from mongotoy import mappers

        indexes = []
        for field in document_cls.__fields__.values():
            # Add index field
            index = field.get_index()
            if index:
                i_doc = index.document
                i_keys = i_doc.pop('key')
                i_new_keys = []
                for i_key, i_type in i_keys.items():
                    i_new_keys.append(
                        (f'{parent}.{i_key}' if parent else i_key, i_type)
                    )
                indexes.append(pymongo.IndexModel(i_new_keys, **i_doc))

            # Unwrap ManyMapper
            mapper = field.mapper
            if isinstance(mapper, mappers.SequenceMapper):
                mapper = mapper.unwrap()

            # Add Geo Index
            if isinstance(
                mapper,
                (
                    mappers.MultiPointMapper,
                    mappers.MultiLineStringMapper,
                    mappers.PolygonMapper,
                )
            ):
                indexes.append(
                    pymongo.IndexModel(
                        [(f'{parent}.{field.alias}' if parent else field.alias, pymongo.GEOSPHERE)]
                    )
                )

            # Add EmbeddedDocument indexes
            if isinstance(mapper, mappers.EmbeddedDocumentMapper):
                indexes.extend(self._get_document_indexes(mapper.document_cls, parent=field.alias))

        return indexes

    def _get_document_collection(self, document_cls: typing.Type[T]) -> AgnosticCollection:
        """
        Retrieves the document collection.

        Args:
            document_cls (typing.Type[T]): The document class.

        Returns:
            AgnosticCollection: The MongoDB collection.
        """
        config = document_cls.document_config
        # noinspection PyTypeChecker
        return self.database[document_cls.__collection_name__].with_options(
            codec_options=config.codec_options or self._codec_options,
            read_preference=config.read_preference or self._read_preference,
            read_concern=config.read_concern or self._read_concern,
            write_concern=config.write_concern or self._write_concern
        )

    async def _create_document_indexes(
        self,
        document_cls: typing.Type[T],
        driver_session: AgnosticClientSession = None
    ):
        """
        Creates indexes for a document.

        Args:
            document_cls (typing.Type[T]): The document class.
            driver_session (AgnosticClientSession, optional): The database session.
        """
        indexes = self._get_document_indexes(document_cls)
        collection = self._get_document_collection(document_cls)
        if indexes:
            await collection.create_indexes(indexes, session=driver_session)

    async def _create_document_collection(
        self,
        document_cls: typing.Type[T],
        driver_session: AgnosticClientSession = None
    ):
        """
        Creates a document collection.

        Args:
            document_cls (typing.Type[T]): The document class.
            driver_session (AgnosticClientSession, optional): The database session.
        """
        config = document_cls.document_config
        options = {'check_exists': False}

        # Configure options for capped collections
        if config.capped:
            options['capped'] = True
            options['size'] = config.capped_size
            if config.capped_max:
                options['max'] = config.capped_max

        # Configure options for timeseries collections
        if config.timeseries_field:
            timeseries = {
                'timeField': config.timeseries_field,
                'granularity': config.timeseries_granularity
            }
            if config.timeseries_meta_field:
                timeseries['metaField'] = config.timeseries_meta_field

            options['timeseries'] = timeseries
            if config.timeseries_expire_after_seconds:
                options['expireAfterSeconds'] = config.timeseries_expire_after_seconds

        # Create the collection with configured options
        await self.database.create_collection(
            name=document_cls.__collection_name__,
            codec_options=config.codec_options or self._codec_options,
            read_preference=config.read_preference or self._read_preference,
            read_concern=config.read_concern or self._read_concern,
            write_concern=config.write_concern or self._write_concern,
            session=driver_session,
            **options
        )

    async def _exec_migration(
        self,
        document_cls: typing.Type[T],
        skip_exist: bool = True,
        driver_session: AgnosticClientSession = None
    ):
        """
        Executes document migration.

        Args:
            document_cls (typing.Type[T]): The document class.
            skip_exist (bool, optional): Whether to skip if a collection exists.
            driver_session (AgnosticClientSession, optional): The database session.
        """
        do_apply = True

        # Skip if a collection already exists
        if skip_exist:
            collections = await self.database.list_collection_names(session=driver_session)
            if document_cls.__collection_name__ in collections:
                do_apply = False

        # Create collection and indexes
        if do_apply:
            await self._create_document_collection(document_cls, driver_session=driver_session)
            await self._create_document_indexes(document_cls, driver_session=driver_session)

    # noinspection PyMethodMayBeStatic,PyUnresolvedReferences
    async def _exec_seeding(
        self,
        func: typing.Callable[['Session'], typing.Coroutine[typing.Any, typing.Any, None]],
        session: 'Session',
        skip_exist: bool = True
    ):
        """
        Executes seeding.

        Args:
            func (typing.Callable[['Session'], typing.Coroutine[typing.Any, typing.Any, None]]): The seeding function.
            session (Session): The session object.
            skip_exist (bool, optional): Whether to skip if seeding already exists.
        """
        if not inspect.iscoroutinefunction(func):
            raise TypeError('Seeding function must be async')

        func_path = f'{func.__module__}.{func.__name__}'
        do_seeding = True

        # Skip if seeding already applied
        if skip_exist:
            # noinspection PyProtectedMember
            if await session.objects(Seeding).filter(
                Seeding.function == func_path
            )._count():
                do_seeding = False

        if do_seeding:
            await func(session)
            # noinspection PyProtectedMember
            await session._save(Seeding(function=func_path))

    async def _connect(self, *conn, ping: bool = False):
        """
        Connects to the MongoDB server.

        Args:
            *conn: Connection arguments for AsyncIOMotorClient.
            ping (bool): Whether to ping the server after connecting.
        """
        self._db_client = AsyncIOMotorClient(*conn)
        if ping:
            await self._db_client.admin.command({'ping': 1})

    async def _migrate(
        self,
        document_cls: typing.Type[T],
        session: 'Session' = None
    ):
        """
        Migrates a document.

        Args:
            document_cls (typing.Type[T]): The document class.
            session (Session, optional): The session object.
        """
        driver_session = session.driver_session if session else None
        await self._exec_migration(document_cls, driver_session=driver_session)

    async def _migrate_all(
        self,
        documents_cls: list[typing.Type[T]],
        session: 'Session' = None
    ):
        """
        Migrates multiple documents.

        Args:
            documents_cls (list[typing.Type[T]]): List of document classes.
            session (Session, optional): The session object.
        """
        driver_session = session.driver_session if session else None
        collections = await self.database.list_collection_names(session=driver_session)
        await asyncio.gather(*[
            self._exec_migration(
                doc_cls,
                skip_exist=False,
                driver_session=driver_session
            ) for doc_cls in documents_cls if doc_cls.__collection_name__ not in collections
        ])

    async def _seeding(
        self,
        func: typing.Callable[['Session'], typing.Coroutine[typing.Any, typing.Any, None]],
        session: 'Session' = None
    ):
        """
        Executes seeding for a specific function.

        Args:
            func (typing.Callable[['Session'], typing.Coroutine[typing.Any, typing.Any, None]]): The seeding function.
            session (Session, optional): The session object.
        """
        await self._exec_seeding(func, session=session)

    async def _seeding_all(
        self,
        funcs: list[typing.Callable[['Session'], typing.Coroutine[typing.Any, typing.Any, None]]],
        session: 'Session' = None
    ):
        """
        Executes seeding for multiple functions.

        Args:
            funcs (list[Callable[['Session'], Coroutine[Any, Any, None]]]): List of seeding functions.
            session (Session, optional): The session object.
        """
        # noinspection PyProtectedMember
        seeds = await session.objects(Seeding)._fetch()
        seeds = [s.function for s in seeds]
        # noinspection PyUnresolvedReferences
        await asyncio.gather(*[
            self._exec_seeding(
                func,
                session=session,
                skip_exist=False
            ) for func in funcs if f'{func.__module__}.{func.__name__}' not in seeds
        ])

    def session(self) -> 'Session':
        """
        Creates a new MongoDB session.

        Returns:
            Session: A new MongoDB session associated with the engine.
        """
        return Session(engine=self)

    def collection(self, document_cls_or_name: typing.Type[T] | str) -> AgnosticCollection:
        """
        Retrieves the MongoDB collection.

        Args:
            document_cls_or_name (typing.Type[T] | str): The document class or collection name.

        Returns:
            AgnosticCollection: The MongoDB collection.
        """
        if not isinstance(document_cls_or_name, str):
            return self._get_document_collection(document_cls_or_name)

        # noinspection PyTypeChecker
        return self.database[document_cls_or_name].with_options(
            codec_options=self._codec_options,
            read_preference=self._read_preference,
            read_concern=self._read_concern,
            write_concern=self._write_concern
        )

    # noinspection SpellCheckingInspection
    def gridfs(
        self,
        bucket_name: str = 'fs',
        chunk_size_bytes: int = gridfs.DEFAULT_CHUNK_SIZE
    ) -> AgnosticGridFSBucket:
        """
        Retrieves the GridFS bucket.

        Args:
            bucket_name (str): The name of the GridFS bucket.
            chunk_size_bytes (int): The chunk size in bytes.

        Returns:
            AgnosticGridFSBucket: The GridFS bucket.
        """
        return AsyncIOMotorGridFSBucket(
            database=self.database,
            bucket_name=bucket_name,
            chunk_size_bytes=chunk_size_bytes,
            write_concern=self.database.write_concern,
            read_preference=self.database.read_preference
        )

    @sync.proxy
    def connect(
        self,
        *conn,
        ping: bool = False
    ) -> typing.Coroutine[typing.Any, typing.Any, None] | None:
        return self._connect(*conn, ping)

    @sync.proxy
    def migrate(
        self,
        document_cls: typing.Type[T],
        session: 'Session' = None
    ) -> typing.Coroutine[typing.Any, typing.Any, None] | None:
        return self._migrate(document_cls, session)

    @sync.proxy
    def migrate_all(
        self,
        documents_cls: list[typing.Type[T]],
        session: 'Session' = None
    ) -> typing.Coroutine[typing.Any, typing.Any, None] | None:
        return self._migrate_all(documents_cls, session)

    @sync.proxy
    def seeding(
        self,
        func: typing.Callable[['Session'], typing.Coroutine[typing.Any, typing.Any, None]],
        session: 'Session' = None
    ) -> typing.Coroutine[typing.Any, typing.Any, None] | None:
        return self._seeding(func, session)

    @sync.proxy
    def seeding_all(
        self,
        funcs: list[typing.Callable[['Session'], typing.Coroutine[typing.Any, typing.Any, None]]],
        session: 'Session' = None
    ) -> typing.Coroutine[typing.Any, typing.Any, None] | None:
        return self._seeding_all(funcs, session)


class Session(typing.AsyncContextManager, typing.ContextManager):
    """
    Represents a MongoDB session for performing database operations within a transaction-like context.

    Args:
        engine (Engine): The MongoDB engine associated with the session.
    """

    def __init__(self, engine: Engine):
        # MongoDB engine associated with the session
        self._engine = engine
        # MongoDB driver session
        self._driver_session = None

    @property
    def engine(self) -> Engine:
        """
        Returns the MongoDB engine associated with the session.
        """
        return self._engine

    @property
    def started(self) -> bool:
        """
        Returns a boolean indicating whether the session has been started.
        """
        return self._driver_session is not None

    @property
    def driver_session(self) -> AgnosticClientSession:
        """
        Returns the MongoDB driver session.

        Raises:
            EngineError: If the session is not started.
        """
        if not self.started:
            raise SessionError('Session not started')
        return self._driver_session

    async def __aenter__(self) -> 'Session':
        """
        Enables the use of the 'async with' statement.
        """
        await self._start()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """
        Enables the use of the 'async with' statement. Ends the session upon exiting the context.
        """
        await self._end()

    def __enter__(self) -> 'Session':
        return sync.run_sync(self.__aenter__)()

    def __exit__(self, exc_type, exc_value, traceback):
        sync.run_sync(self.__aexit__)(exc_type, exc_value, traceback)

    async def _start(self):
        """
        Starts the MongoDB session.

        Raises:
            EngineError: If the session is already started.
        """
        if not self._driver_session:
            self._driver_session = await self.engine.client.start_session()

    async def _end(self):
        """
        Ends the MongoDB session.

        Raises:
            EngineError: If the session is not started.
        """
        if self.driver_session:
            await self.driver_session.end_session()
            self._driver_session = None

    async def _save_references(self, doc: T):
        """
        Saves referenced documents.

        Args:
            doc (T): The document object.
        """
        operations = []
        for field, reference in doc.__references__.items():
            obj = getattr(doc, field)
            if obj in (expressions.EmptyValue, None):
                continue
            if not reference.is_many:
                obj = [obj]
            operations.append(
                self._save_all(obj, save_references=True)
            )

        await asyncio.gather(*operations)

    async def _save(self, doc: T, save_references: bool = False):
        """
        Saves a document to the database.

        Args:
            doc (T): The document object to save.
            save_references (bool): Whether to save referenced documents.
        """
        operations = []
        if save_references:
            operations.append(self._save_references(doc))

        son = doc.dump_bson()
        await asyncio.gather(*operations)
        await self.engine.collection(doc.__collection_name__).update_one(
            filter=Query.Eq('_id', son.pop('_id')),
            update={'$set': son},
            upsert=True,
            session=self.driver_session
        )

    async def _save_all(self, docs: list[T], save_references: bool = False):
        """
        Saves a list of documents to the database.

        Args:
            docs (list[T]): The list of document objects to save.
            save_references (bool): Whether to save referenced documents.
        """
        await asyncio.gather(*[self._save(i, save_references) for i in docs if i is not None])

    async def _delete_cascade(self, doc: T):
        """
        Deletes documents that reference the given document.

        Args:
            doc (T): The document object to delete.
        """
        doc_cls = type(doc)
        rev_references = references.get_reverse_references(document_cls=doc_cls)
        operations = []

        # Get reverse references
        for ref_doc_cls, refs in rev_references.items():
            ref_doc_objects = self.objects(ref_doc_cls, dereference_deep=1)
            query = functools.reduce(
                lambda x, y: x | Query.Eq(y.key_name, getattr(doc, y.ref_field.name)),
                refs.values(),
                Query()
            )
            # Get referenced docs
            async for ref_doc in ref_doc_objects.filter(query):
                do_delete = False
                # Scan all references
                for field_name, reference in refs.items():
                    if not reference.is_many:
                        do_delete = True
                        break

                    # Get reference value
                    value = getattr(ref_doc, field_name)
                    if value:
                        # Wipe doc from value
                        value = [
                            i for i in value
                            if getattr(i, reference.ref_field.name) != getattr(doc, reference.ref_field.name)
                        ]
                        if not value:
                            do_delete = True
                            break
                        setattr(ref_doc, field_name, value)
                        # Apply update
                        operations.append(self._save(ref_doc))

                # Apply delete
                if do_delete:
                    operations.append(self._delete(ref_doc, delete_cascade=True))

        await asyncio.gather(*operations)

    async def _delete(self, doc: T, delete_cascade: bool = False):
        """
        Deletes a document from the database.

        Args:
            doc (T): The document object to delete.
            delete_cascade (bool): Whether to delete referenced documents.
        """
        operations = []
        if delete_cascade:
            operations.append(self._delete_cascade(doc))

        await asyncio.gather(*operations)
        await self.engine.collection(doc.__collection_name__).delete_one(
            filter=Query.Eq('_id', doc.id),
            session=self.driver_session
        )

    async def _delete_all(self, docs: list[T], delete_cascade: bool = False):
        """
        Deletes a list of documents from the database.

        Args:
            docs (list[T]): The list of document objects to delete.
            delete_cascade (bool): Whether to delete referenced documents.
        """
        await asyncio.gather(*[self._delete(i, delete_cascade) for i in docs if i is not None])

    def transaction(self) -> 'Transaction':
        """
        Creates a new MongoDB transaction.

        Returns:
            Transaction: A new MongoDB transaction associated with the engine
        """
        return Transaction(session=self)

    def objects(self, document_cls: typing.Type[T], dereference_deep: int = 0) -> 'Objects[T]':
        """
        Returns an object manager for the specified document class.

        Args:
            document_cls (typing.Type[T]): The document class.
            dereference_deep (int): Depth of dereferencing.

        Returns:
            Objects[T]: An object manager.
        """
        return Objects(document_cls, session=self, dereference_deep=dereference_deep)

    def fs(self, chunk_size_bytes: int = gridfs.DEFAULT_CHUNK_SIZE) -> 'FsBucket':
        """
        Returns a GridFS bucket manager.

        Args:
            chunk_size_bytes (int): The chunk size in bytes.

        Returns:
            FsBucket: A GridFS bucket manager.
        """
        return FsBucket(self, chunk_size_bytes=chunk_size_bytes)

    @sync.proxy
    def start(self) -> typing.Coroutine[typing.Any, typing.Any, None] | None:
        return self._start()

    @sync.proxy
    def end(self) -> typing.Coroutine[typing.Any, typing.Any, None] | None:
        return self._end()

    @sync.proxy
    def save(
        self,
        doc: T,
        save_references: bool = False
    ) -> typing.Coroutine[typing.Any, typing.Any, None] | None:
        return self._save(doc, save_references)

    @sync.proxy
    def save_all(
        self,
        docs: list[T],
        save_references: bool = False
    ) -> typing.Coroutine[typing.Any, typing.Any, None] | None:
        return self._save_all(docs, save_references)

    @sync.proxy
    def delete(
        self,
        doc: T,
        delete_cascade: bool = False
    ) -> typing.Coroutine[typing.Any, typing.Any, None] | None:
        return self._delete(doc, delete_cascade)

    @sync.proxy
    def delete_all(
        self,
        docs: list[T],
        delete_cascade: bool = False
    ) -> typing.Coroutine[typing.Any, typing.Any, None] | None:
        return self._delete_all(docs, delete_cascade)


class Transaction(typing.AsyncContextManager, typing.ContextManager):
    """
        Represents a MongoDB transaction for performing atomic operations within a session or engine context.

        Args:
            session (Session): The session related with transaction.
    """

    # noinspection PyProtectedMember
    def __init__(self, session: Session):
        self._session = session

        # Start transaction
        self._session.driver_session.start_transaction(
            read_concern=self._session.engine._read_concern,
            read_preference=self._session.engine._read_preference,
            write_concern=self._session.engine._write_concern
        )

    @property
    def session(self) -> 'Session':
        """
        Returns the associated MongoDB session for the transaction.

        Returns:
            Session: The associated MongoDB session.
        """
        return self._session

    async def __aenter__(self) -> 'Transaction':
        """
        Enables the use of the 'async with' statement.

        Returns:
            Transaction: The transaction instance.
        """
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """
        Enables the use of the 'async with' statement. Ends the transaction upon exiting the context.

        Args:
            exc_type: The type of the exception.
            exc_value: The exception value.
            traceback: The exception traceback.
        """
        if exc_value:
            await self._abort()
        else:
            await self._commit()

    def __enter__(self) -> 'Transaction':
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        sync.run_sync(self.__aexit__)(exc_type, exc_value, traceback)

    async def _commit(self):
        """
        Commits changes and closes the MongoDB transaction.

        Raises:
            EngineError: If the transaction is not started.
        """
        await self._session.driver_session.commit_transaction()

    async def _abort(self):
        """
        Discards changes and closes the MongoDB transaction.

        Raises:
            EngineError: If the transaction is not started.
        """
        await self._session.driver_session.abort_transaction()

    @sync.proxy
    def commit(self) -> typing.Coroutine[typing.Any, typing.Any, None] | None:
        return self._commit()

    @sync.proxy
    def abort(self) -> typing.Coroutine[typing.Any, typing.Any, None] | None:
        return self._abort()


class Objects(typing.Generic[T]):
    # noinspection SpellCheckingInspection
    """
        Represents a query set for retrieving documents from the database.
        This class provides methods for filtering, sorting, limiting, and executing queries asynchronously.

        Args:
            document_cls (typing.Type[T]): The document class associated with the query set.
            session (Session): The session object used for database operations.
            dereference_deep (int, optional): The depth of dereferencing for referenced documents.
        """

    def __init__(self, document_cls: typing.Type[T], session: Session, dereference_deep: int = 0):
        self._document_cls = document_cls
        self._session = session
        self._dereference_deep = dereference_deep
        self._collection = session.engine.collection(document_cls)
        self._filter = expressions.Query()
        self._sort = expressions.Sort()
        self._skip = 0
        self._limit = 0

    def __copy__(self, **options) -> 'Objects[T]':
        """
        Creates a shallow copy of the query set with specified options.

        Args:
            **options: Additional options to be applied to the copy.

        Returns:
            Objects[T]: A shallow copy of the query set with specified options.
        """
        objs = Objects(
            document_cls=self._document_cls,
            session=self._session,
            dereference_deep=self._dereference_deep
        )
        setattr(objs, '_collection', self._collection)
        setattr(objs, '_filter', options.get('_filter', self._filter))
        setattr(objs, '_sort', options.get('_sort', self._sort))
        setattr(objs, '_skip', options.get('_skip', self._skip))
        setattr(objs, '_limit', options.get('_limit', self._limit))

        return objs

    async def __aiter__(self) -> typing.AsyncGenerator[T, None]:
        """
        Asynchronously iterates over the result set, executing the query.

        Yields:
            T: The parsed document instances.

        Raises:
            NoResultsError: If no results are found.
            ManyResultsError: If more than one result is found.
        """
        # noinspection PyTypeChecker
        pipeline = references.build_dereference_pipeline(
            references=self._document_cls.__references__.values(),
            deep=self._dereference_deep
        )

        if self._filter:
            pipeline.append({'$match': self._filter})
        if self._sort:
            pipeline.append({'$sort': self._sort})
        if self._skip > 0:
            pipeline.append({'$skip': self._skip})
        if self._limit > 0:
            pipeline.append({'$limit': self._limit})

        cursor = self._collection.aggregate(pipeline, session=self._session.driver_session)
        async for data in cursor:
            yield self._document_cls(**data)

    def __iter__(self) -> typing.Generator[T, None, None]:
        for doc in sync.as_sync_gen(self.__aiter__()):
            yield doc

    async def _create(self, **data) -> T:
        """
        Creates a new document in the database.

        Args:
            **data: Keyword arguments representing the document data.

        Returns:
            T: The newly created document instance.
        """
        doc = self._document_cls(**data)
        # noinspection PyProtectedMember
        await self._session._save(doc, save_references=True)
        return doc

    async def _fetch(self) -> list[T]:
        """
        Retrieves all documents in the result set.

        Returns:
            list[T]: The list of parsed document instances.
        """
        return [doc async for doc in self]

    async def _fetch_one(self) -> T:
        """
        Retrieves a specific document in the result set.

        Returns:
            T: The parsed document instance.

        Raises:
            NoResultsError: If no results are found.
            ManyResultsError: If more than one result is found.
        """
        docs = await self.limit(2)._fetch()
        if not docs:
            raise NoResultsError()
        if len(docs) > 1:
            raise ManyResultsError()
        return docs[0]

    # noinspection PyShadowingBuiltins
    async def _fetch_by_id(self, value: typing.Any) -> T:
        """
        Retrieves a document by its identifier.

        Args:
            value (typing.Any): The identifier value.

        Returns:
            T: The parsed document instance.
        """
        # noinspection PyProtectedMember
        return await self.filter(
            self._document_cls.id == self._document_cls.id._field.mapper.__validate_value__(value)
        )._fetch_one()

    async def _count(self) -> int:
        """
        Counts the number of documents in the result set.

        Returns:
            int: The count of documents.
        """
        return await self._collection.count_documents(
            filter=self._filter,
            session=self._session.driver_session
        )

    def filter(self, *queries: expressions.Query | bool, **filters) -> 'Objects[T]':
        """
        Adds filter conditions to the query set.

        Args:
            *queries (expressions.Query | bool): Variable number of filter expressions.
            **filters: Keyword arguments representing additional filter conditions.

        Returns:
            Objects[T]: The updated query set with added filter conditions.
        """
        _filter = self._filter
        for q in queries:
            _filter = _filter & q
        if filters:
            _filter = _filter & expressions.Q(**filters)
        return self.__copy__(_filter=_filter)

    def sort(self, *sorts: expressions.Sort) -> 'Objects[T]':
        """
        Adds sort conditions to the query set.

        Args:
            *sorts (expressions.Sort): Variable number of sort expressions.

        Returns:
            Objects[T]: The updated query set with added sort conditions.
        """
        _sort = self._sort
        for sort in sorts:
            _sort = _sort | expressions.Sort(sort)
        return self.__copy__(_sort=_sort)

    def skip(self, skip: int) -> 'Objects[T]':
        """
        Sets the number of documents to skip in the result set.

        Args:
            skip (int): The number of documents to skip.

        Returns:
            Objects[T]: The updated query set with the skip value set.
        """
        return self.__copy__(_skip=skip)

    def limit(self, limit: int) -> 'Objects[T]':
        """
        Sets the maximum number of documents to return.

        Args:
            limit (int): The maximum number of documents to return.

        Returns:
            Objects[T]: The updated query set with the limit value set.
        """
        return self.__copy__(_limit=limit)

    @sync.proxy
    def create(self, **data) -> typing.Coroutine[typing.Any, typing.Any, T] | T:
        return self._create(**data)

    @sync.proxy
    def fetch(self) -> typing.Coroutine[typing.Any, typing.Any, list[T]] | list[T]:
        return self._fetch()

    @sync.proxy
    def fetch_one(self) -> typing.Coroutine[typing.Any, typing.Any, T] | T:
        return self._fetch_one()

    @sync.proxy
    def fetch_by_id(self, value: typing.Any) -> typing.Coroutine[typing.Any, typing.Any, T] | T:
        return self._fetch_by_id(value)

    @sync.proxy
    def count(self) -> typing.Coroutine[typing.Any, typing.Any, int] | int:
        return self._count()


# noinspection PyProtectedMember
class FsBucket(Objects['FsObject']):
    # noinspection SpellCheckingInspection
    """
        Represents a file system bucket for storing and managing file objects.
        This class inherits from Objects and provides methods for file upload,
        existence check, and accessing file revisions.

        Args:
            session (Session): The session object used for database operations.
            chunk_size_bytes (int): The size of chunks in bytes for file storage (default gridfs.DEFAULT_CHUNK_SIZE).
        """

    def __init__(
        self,
        session: Session,
        chunk_size_bytes: int = gridfs.DEFAULT_CHUNK_SIZE
    ):
        super().__init__(
            document_cls=FsObject,
            session=session
        )
        self._bucket = session.engine.gridfs('fs', chunk_size_bytes)
        self._chunk_size_bytes = chunk_size_bytes

    # noinspection PyMethodMayBeStatic
    async def _create(
        self,
        filename: str,
        src: typing.IO | bytes,
        metadata: dict = None,
        chunk_size_bytes: int = None
    ) -> 'FsObject':
        """
        Uploads a file to the file system bucket.

        Args:
            filename (str): The name of the file.
            src (typing.IO | bytes): The source file object or bytes to be uploaded.
            metadata (dict, optional): Additional metadata for the file.
            chunk_size_bytes (int, optional): The size of chunks in bytes for file storage.

        Returns:
            FsObject: The uploaded file object.
        """
        # Create metadata
        metadata = metadata or {}
        content_type = mimetypes.guess_type(filename, strict=False)[0]
        if content_type:
            metadata['contentType'] = content_type

        # Create object
        obj = FsObject(
            filename=filename,
            metadata=metadata
        )
        # Upload contents
        await self._bucket.upload_from_stream_with_id(
            file_id=obj.id,
            filename=filename,
            source=src,
            metadata=metadata,
            chunk_size_bytes=chunk_size_bytes or self._chunk_size_bytes,
            session=self._session.driver_session
        )
        # Update obj info
        obj = await self._fetch_by_id(obj.id)

        return obj

    async def _exist(self, filename: str) -> bool:
        """
        Checks if a file exists in the file system bucket.

        Args:
            filename (str): The name of the file.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        count = await self.filter(Query.Eq('filename', filename))._count()
        return count > 0

    async def _revisions(self, filename: str) -> list['FsObject']:
        """
        Retrieves all revisions of a file from the file system bucket.

        Args:
            filename (str): The name of the file.

        Returns:
            list[FsObject]: A list of file objects representing revisions.
        """
        return await self.filter(Query.Eq('filename', filename))._fetch()

    @sync.proxy
    def create(
        self,
        filename: str,
        src: typing.IO | bytes,
        metadata: dict = None,
        chunk_size_bytes: int = None
    ) -> typing.Coroutine[typing.Any, typing.Any, 'FsObject'] | 'FsObject':
        return self._create(filename, src, metadata, chunk_size_bytes)

    @sync.proxy
    def exist(
        self,
        filename: str
    ) -> typing.Coroutine[typing.Any, typing.Any, bool] | bool:
        return self._exist(filename)

    @sync.proxy
    def revisions(
        self,
        filename: str
    ) -> typing.Coroutine[typing.Any, typing.Any, list['FsObject']] | list['FsObject']:
        return self._revisions(filename)


# noinspection PyProtectedMember
class FsObject(documents.Document):
    """
    Represents a file object stored in the file system.
    This class inherits from Document and provides methods for creating revisions, downloading, and streaming files.

    Attributes:
        filename (str): The name of the file.
        metadata (types.Json): Metadata associated with the file.
        chunk_size (int): The size of chunks in bytes for file storage.
        length (int): The length of the file.
        upload_date (datetime.datetime): The date and time when the file was uploaded.

    """

    filename: str
    metadata: types.Json
    chunk_size: int = fields.field(alias='chunkSize')
    length: int
    upload_date: datetime.datetime = fields.field(alias='uploadDate')

    __collection_name__ = 'fs.files'

    @property
    def content_type(self) -> str:
        return self.metadata.get('contentType')

    @property
    def chunks(self) -> int:
        import math
        return math.ceil(self.length / self.chunk_size)

    async def _create_revision(
        self,
        fs: FsBucket,
        src: typing.IO | bytes,
        metadata: dict = None
    ) -> 'FsObject':
        """
        Creates a revision of the file.

        Args:
            fs (FsBucket): The file system bucket where the revision will be created.
            src (typing.IO | bytes): The source file object or bytes for the new revision.
            metadata (dict, optional): Additional metadata for the new revision.

        """
        return await fs._create(
            self.filename,
            src=src,
            metadata=metadata,
            chunk_size_bytes=self.chunk_size
        )

    # noinspection SpellCheckingInspection
    async def _download_to(self, fs: FsBucket, dest: typing.IO, revision: int = 0):
        """
        Downloads a file revision.

        Revision numbers are defined as follows:

            0 = the original stored file
            1 = the first revision
            2 = the second revision
            ...
            -2 = the second most recent revision
            -1 = the most recent revision

        Args:
            fs (FsBucket): The file system bucket from where the file will be downloaded.
            dest (typing.IO): The destination file object to write the downloaded file contents.
            revision (int): The revision number of the file to download.

        """
        await fs._bucket.download_to_stream_by_name(
            filename=self.filename,
            destination=dest,
            revision=revision,
            session=fs._session.driver_session
        )

    async def _stream(self, fs: FsBucket, revision: int = 0) -> 'FsObjectStream':
        """
        Streams the file from the file system.

        Revision numbers are defined as follows:

            0 = the original stored file
            1 = the first revision
            2 = the second revision
            ...
            -2 = the second most recent revision
            -1 = the most recent revision

        Args:
            fs (FsBucket): The file system bucket from where the file will be streamed.
            revision (int, optional): The revision number of the file to stream.

        Returns:
            FsObjectStream: An asynchronous file streamer.

        """
        grid_out = await fs._bucket.open_download_stream_by_name(
            filename=self.filename,
            revision=revision,
            session=fs._session.driver_session
        )

        return FsObjectStream(grid_out)

    async def _delete(self, fs: FsBucket):
        await fs._bucket.delete(
            file_id=self.id,
            session=fs._session.driver_session
        )

    @sync.proxy
    def create_revision(
        self,
        fs: FsBucket,
        src: typing.IO | bytes,
        metadata: dict = None
    ) -> typing.Union[typing.Coroutine[typing.Any, typing.Any, 'FsObject'], 'FsObject']:
        return self._create_revision(fs, src, metadata)

    @sync.proxy
    def download_to(
        self,
        fs: FsBucket,
        dest: typing.IO,
        revision: int = 0
    ) -> typing.Coroutine[typing.Any, typing.Any, None] | None:
        return self._download_to(fs, dest, revision)

    @sync.proxy
    def stream(
        self,
        fs: FsBucket,
        revision: int = 0
    ) -> typing.Union[typing.Coroutine[typing.Any, typing.Any, 'FsObjectStream'], 'FsObjectStream']:
        return self._stream(fs, revision)

    @sync.proxy
    def delete(self, fs: FsBucket) -> typing.Coroutine[typing.Any, typing.Any, None] | None:
        return self._delete(fs)


class FsObjectStream:
    """
    Represents the contents of file stored in MongoDB GridFS.

    Args:
        grid_out (AsyncIOMotorGridOut): The underlying GridFS file object.

    """

    def __init__(self, grid_out: AsyncIOMotorGridOut):
        self._driver_grid_out = grid_out

    async def _read(self, size: int = -1) -> bytes:
        """
        Reads data from the file asynchronously.

        Args:
            size (int, optional): The number of bytes to read. If not specified or negative, reads until EOF.

        Returns:
            bytes: The data read from the file.
        """
        return await self._driver_grid_out.read(size)

    # noinspection SpellCheckingInspection
    async def _readchunk(self) -> bytes:
        """
        Reads a chunk of data from the file asynchronously.

        Returns:
            bytes: The data chunk read from the file.
        """
        return await self._driver_grid_out.readchunk()

    async def _readline(self, size: int = -1) -> bytes:
        """
        Reads a line from the file asynchronously.

        Args:
            size (int, optional): The maximum number of bytes to read. If not specified or negative, reads until EOF.

        Returns:
            bytes: The line read from the file.
        """
        return await self._driver_grid_out.readline(size)

    def seek(self, pos: int, whence: int = os.SEEK_SET) -> int:
        """
        Moves the file pointer to a specified position.

        Args:
            pos (int): The position to seek to.
            whence (int, optional): The reference point for the seek operation.

        Returns:
            int: The new position of the file pointer.
        """
        return self._driver_grid_out.seek(pos, whence)

    def seekable(self) -> bool:
        """
        Checks if the file is seekable.

        Returns:
            bool: True if the file is seekable, False otherwise.
        """
        return self._driver_grid_out.seekable()

    def tell(self) -> int:
        """
        Returns the current position of the file pointer.

        Returns:
            int: The current position of the file pointer.
        """
        return self._driver_grid_out.tell()

    def close(self):
        """Closes the file."""
        self._driver_grid_out.close()

    @sync.proxy
    def read(
        self,
        size: int = -1
    ) -> typing.Coroutine[typing.Any, typing.Any, bytes] | bytes:
        return self._read(size)

    # noinspection SpellCheckingInspection
    @sync.proxy
    def readchunk(self) -> typing.Coroutine[typing.Any, typing.Any, bytes] | bytes:
        return self._readchunk()

    @sync.proxy
    def readline(
        self,
        size: int = -1
    ) -> typing.Coroutine[typing.Any, typing.Any, bytes] | bytes:
        return self._readline(size)


class Seeding(documents.Document):
    """
    Represents a seeding operation in the database.
    This class inherits from Document and tracks seeding functions applied to the database.

    Attributes:
        function (str): The name or identifier of the seeding function.
        applied_at (datetime.datetime): The timestamp when the seeding was applied.

    """

    function: str = fields.field(id_field=True)
    applied_at: datetime.datetime = fields.field(default_factory=datetime.datetime.utcnow)

    __collection_name__ = 'mongotoy.seeding'
