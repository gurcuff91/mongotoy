import asyncio
import datetime
import functools
import mimetypes
import typing

import bson
import gridfs
import pymongo
from motor.core import AgnosticClient, AgnosticDatabase, AgnosticCollection, AgnosticClientSession
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket, AsyncIOMotorGridOut
from motor.motor_gridfs import AgnosticGridFSBucket
from pymongo.read_concern import ReadConcern

from mongotoy import documents, expressions, references, fields, types
from mongotoy.errors import EngineError, NoResultsError, ManyResultsError

__all__ = (
    'Engine',
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
                # Get or create a collection for a document class
                collection = await engine.get_collection(MyDocument, session=session)
                # Perform operations on the collection
                await collection.insert_one({'key': 'value'})
        """

    def __init__(
        self,
        database: str,
        codec_options: bson.CodecOptions = None,
        read_preference: pymongo.ReadPreference = None,
        read_concern: ReadConcern = None,
        write_concern: pymongo.WriteConcern = None
    ):
        # Check for forbidden characters in the database name
        forbid_chars = {"/", "\\", ".", '"', "$"}
        forbidden = forbid_chars.intersection(set(database))
        if len(forbidden) > 0:
            raise EngineError(f"Database name cannot contain: {' '.join(forbidden)}")

        # Initialize instance variables
        self._database = database
        self._codec_options = codec_options
        self._read_preference = read_preference
        self._read_concern = read_concern
        self._write_concern = write_concern
        self._db_client = None
        self._migration_lock = asyncio.Lock()

    async def connect(self, *conn, ping: bool = False):
        """
        Connects to the MongoDB server.

        Args:
            *conn: Connection arguments for AsyncIOMotorClient.
            ping (bool): Whether to ping the server after connecting.
        """
        self._db_client = AsyncIOMotorClient(*conn)
        if ping:
            await self._db_client.admin.command({'ping': 1})

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

    def session(self) -> 'Session':
        """
        Creates a new MongoDB session.

        Returns:
            Session: A new MongoDB session associated with the engine.
        """
        return Session(engine=self)

    def transaction(self) -> 'Transaction':
        """
        Creates a new MongoDB transaction.

        Returns:
            Transaction: A new MongoDB transaction associated with the engine
        """
        return Transaction(provider=self)

    def collection(self, document_cls_or_name: typing.Type[T] | str) -> AgnosticCollection:
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
        return AsyncIOMotorGridFSBucket(
            database=self.database,
            bucket_name=bucket_name,
            chunk_size_bytes=chunk_size_bytes,
            write_concern=self.database.write_concern,
            read_preference=self.database.read_preference
        )

    def _get_document_indexes(
        self,
        document_cls: typing.Type[documents.BaseDocument],
        parent: str = None
    ) -> list[pymongo.IndexModel]:
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
            if isinstance(mapper, mappers.ManyMapper):
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
        session: AgnosticClientSession = None
    ):
        indexes = self._get_document_indexes(document_cls)
        collection = self._get_document_collection(document_cls)
        if indexes:
            await collection.create_indexes(indexes, session=session)

    async def _create_document_collection(
        self,
        document_cls: typing.Type[T],
        session: AgnosticClientSession = None
    ):
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
            session=session,
            **options
        )

    async def migrate(
        self,
        document_cls: typing.Type[T],
        check_exist: bool = True,
        with_lock: bool = True,
        session: 'Session' = None
    ):
        # Lock
        if with_lock:
            await self._migration_lock.acquire()

        driver_session = session.driver_session if session else None
        do_apply = True

        # Check if collection already exist
        if check_exist:
            collections = await self.database.list_collection_names(session=driver_session)
            if document_cls.__collection_name__ in collections:
                do_apply = False

        # Create collection and indexes
        if do_apply:
            await self._create_document_collection(document_cls, session=driver_session)
            await self._create_document_indexes(document_cls, session=driver_session)

        # Unlock
        if with_lock:
            self._migration_lock.release()

    async def migrate_all(
        self,
        documents_cls: list[typing.Type[T]],
        session: 'Session' = None
    ):
        driver_session = session.driver_session if session else None
        async with self._migration_lock:
            collections = await self.database.list_collection_names(session=driver_session)
            await asyncio.gather(*[
                self.migrate(i, check_exist=False, with_lock=False)
                for i in documents_cls
                if i.__collection_name__ not in collections
            ])


class Session(typing.AsyncContextManager):
    """
        Represents a MongoDB session for performing database operations within a transaction-like context.

        Args:
            engine (Engine): The MongoDB engine associated with the session.

        Example:
            # Create a Session instance
            session = Session(engine=my_engine)

            # Start the session
            await session.start()

            # Perform operations within the session context
            async with session:
                # Access the driver session and perform database operations
                collection = await session.get_collection(MyDocument)
                await collection.insert_one({'key': 'value'})

            # End the session
            await session.end()
    """
    def __init__(self, engine: Engine):
        self._engine = engine
        self._driver_session = None

    @property
    def engine(self) -> Engine:
        """
        Returns the MongoDB engine associated with the session.

        Returns:
            Engine: The MongoDB engine.
        """
        return self._engine

    @property
    def started(self) -> bool:
        """
        Returns a boolean indicating whether the session has been started.

        Returns:
            bool: True if the session has been started, False otherwise.
        """
        return self._driver_session is not None

    @property
    def driver_session(self) -> AgnosticClientSession:
        """
        Returns the MongoDB driver session.

        Raises:
            EngineError: If the session is not started.

        Returns:
            AgnosticClientSession: The MongoDB driver session.
        """
        if not self.started:
            raise EngineError('Session not started')
        return self._driver_session

    async def start(self):
        """
        Starts the MongoDB session.

        Raises:
            EngineError: If the session is already started.
        """
        if self.started:
            raise EngineError('Session already started')
        self._driver_session = await self.engine.client.start_session()

    async def end(self):
        """
        Ends the MongoDB session.

        Raises:
            EngineError: If the session is not started.
        """
        if not self.started:
            raise EngineError('Session not started')
        await self.driver_session.end_session()
        self._driver_session = None

    async def __aenter__(self) -> 'Session':
        """
        Enables the use of the 'async with' statement.

        Returns:
            Session: The session instance.
        """
        await self.start()
        return self

    async def __aexit__(self, __exc_type, __exc_value, __traceback) -> None:
        """
        Enables the use of the 'async with' statement. Ends the session upon exiting the context.

        Args:
            __exc_type: The type of the exception.
            __exc_value: The exception value.
            __traceback: The exception traceback.
        """
        await self.end()

    def transaction(self) -> 'Transaction':
        """
        Creates a new MongoDB transaction.

        Returns:
            Transaction: A new MongoDB transaction associated with the engine
        """
        return Transaction(provider=self)

    def objects(self, document_cls: typing.Type[T], dereference_deep: int = 0) -> 'Objects[T]':
        return Objects(document_cls, session=self, dereference_deep=dereference_deep)

    def fs(self, chunk_size_bytes: int = gridfs.DEFAULT_CHUNK_SIZE) -> 'FsBucket':
        return FsBucket(self, chunk_size_bytes=chunk_size_bytes)

    async def _save_references(self, doc: T):
        operations = []
        for field, reference in doc.__references__.items():
            obj = getattr(doc, field)
            if obj in (expressions.EmptyValue, None):
                continue
            if not reference.is_many:
                obj = [obj]
            operations.append(
                self.save_all(obj, save_references=True)
            )

        await asyncio.gather(*operations)

    async def save(self, doc: T, save_references: bool = False):
        operations = []
        if save_references:
            operations.append(self._save_references(doc))

        son = doc.dump_bson()
        operations.append(
            self.engine.collection(doc.__collection_name__).update_one(
                filter=Query.Eq('_id', son.pop('_id')),
                update={'$set': son},
                upsert=True,
                session=self.driver_session
            )
        )
        await asyncio.gather(*operations)

    async def save_all(self, docs: list[T], save_references: bool = False):
        await asyncio.gather(*[self.save(i, save_references) for i in docs if i is not None])

    async def _delete_cascade(self, doc: T):
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
                        operations.append(self.save(ref_doc))

                # Apply delete
                if do_delete:
                    operations.append(self.delete(ref_doc, delete_cascade=True))

        await asyncio.gather(*operations)

    async def delete(self, doc: T, delete_cascade: bool = False):
        operations = []
        if delete_cascade:
            operations.append(self._delete_cascade(doc))

        await asyncio.gather(*operations)
        await self.engine.collection(doc.__collection_name__).delete_one(
            filter=Query.Eq('_id', doc.id),
            session=self.driver_session
        )

    async def delete_all(self, docs: list[T], delete_cascade: bool = False):
        await asyncio.gather(*[self.delete(i, delete_cascade) for i in docs if i is not None])


class Transaction(typing.AsyncContextManager):
    # noinspection GrazieInspection
    """
        Represents a MongoDB transaction for performing atomic operations within a session or engine context.

        Args:
            provider (Session or Engine): The provider of the transaction, either a Session or an Engine.

        Attributes:
            _is_session_provided (bool): Indicates whether the transaction is provided with a Session.
            _session (Session): The associated MongoDB session for the transaction.
            _tx_started (bool): Indicates whether the transaction has been started.
            _tx_context: The context manager for the transaction.

        Example:
            # Create a Transaction instance using a Session
            session = Session(engine=my_engine)
            transaction = Transaction(provider=session)

            # Or create a Transaction instance using an Engine
            engine = Engine(database='my_database')
            transaction = Transaction(provider=engine)

            # Start and commit the transaction
            async with transaction:
                # Perform atomic operations within the transaction context
                await session.get_collection(MyDocument)
                await session.save(my_document_instance)

            # Alternatively, use the commit and abort methods
            await transaction.start()
            try:
                # Perform atomic operations
                await session.save(my_document_instance)
                await transaction.commit()
            except Exception as e:
                await transaction.abort()
                raise e
    """

    def __init__(self, provider: Session | Engine):
        self._is_session_provided = isinstance(provider, Session)
        self._tx_started = False
        self._tx_context = None

        # Get session instance according provider type
        if self._is_session_provided:
            if not provider.started:
                raise EngineError('Session not started')
            self._session = provider
        else:
            self._session = provider.session()

    @property
    def session(self) -> 'Session':
        """
        Returns the associated MongoDB session for the transaction.

        Returns:
            Session: The associated MongoDB session.
        """
        return self._session

    @property
    def started(self) -> bool:
        """
        Returns a boolean indicating whether the transaction has been started.

        Returns:
            bool: True if the transaction has been started, False otherwise.
        """
        return self._tx_started

    async def start(self):
        """
        Starts the MongoDB transaction.

        Raises:
            EngineError: If the transaction is already started.
        """
        if self._tx_started:
            raise EngineError('Transaction already started')
        if not self._is_session_provided:
            await self._session.start()
        self._tx_context = await self._session.driver_session.start_transaction().__aenter__()
        self._tx_started = True

    async def commit(self):
        """
        Commits changes and closes the MongoDB transaction.

        Raises:
            EngineError: If the transaction is not started.
        """
        if not self._tx_started:
            raise EngineError('Transaction not started')
        await self._session.driver_session.commit_transaction()
        if not self._is_session_provided:
            await self._session.end()
        self._tx_started = False

    async def abort(self):
        """
        Discards changes and closes the MongoDB transaction.

        Raises:
            EngineError: If the transaction is not started.
        """
        if not self._tx_started:
            raise EngineError('Transaction not started')
        await self._session.driver_session.abort_transaction()
        if not self._is_session_provided:
            await self._session.end()
        self._tx_started = False

    async def __aenter__(self) -> 'Transaction':
        """
        Enables the use of the 'async with' statement.

        Returns:
            Transaction: The transaction instance.
        """
        await self.start()
        return self

    async def __aexit__(self, __exc_type, __exc_value, __traceback) -> None:
        """
        Enables the use of the 'async with' statement. Ends the transaction upon exiting the context.

        Args:
            __exc_type: The type of the exception.
            __exc_value: The exception value.
            __traceback: The exception traceback.
        """
        await self._tx_context.__aexit__(__exc_type, __exc_value, __traceback)
        self._tx_started = False


class Objects(typing.Generic[T]):

    def __init__(self, document_cls: typing.Type[T], session: Session, dereference_deep: int = 0):
        self._document_cls = document_cls
        self._session = session
        self._dereference_deep = dereference_deep
        self._collection = session.engine.collection(document_cls)
        self._filter = expressions.Query()
        self._sort = expressions.Sort()
        self._skip = 0
        self._limit = 0

    def __copy_with__(self, **options) -> 'Objects[T]':
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

    async def create(self, **data) -> T:
        doc = self._document_cls(**data)
        await self._session.save(doc, save_references=True)
        return doc

    def filter(self, *queries: expressions.Query, **filters) -> 'Objects[T]':
        """
        Adds filter conditions to the query set.

        Args:
            *filters: Variable number of filters.

        Returns:
            QuerySet: The updated query set.
        """
        _filter = self._filter
        for q in queries:
            _filter = _filter & q
        if filters:
            _filter = _filter & expressions.Q(**filters)
        return self.__copy_with__(_filter=_filter)

    def sort(self, *sorts: expressions.Sort) -> 'Objects[T]':
        """
        Adds sort conditions to the query set.

        Args:
            *sorts (dict): Variable number of sort dictionaries.

        Returns:
            QuerySet: The updated query set.
        """
        _sort = self._sort
        for sort in sorts:
            _sort = _sort | expressions.Sort(sort)
        return self.__copy_with__(_sort=_sort)

    def skip(self, skip: int) -> 'Objects[T]':
        """
        Sets the number of documents to skip in the result set.

        Args:
            skip (int): The number of documents to skip.

        Returns:
            QuerySet: The updated query set.
        """
        return self.__copy_with__(_skip=skip)

    def limit(self, limit: int) -> 'Objects[T]':
        """
        Sets the maximum number of documents to return.

        Args:
            limit (int): The maximum number of documents to return.

        Returns:
            QuerySet: The updated query set.
        """
        return self.__copy_with__(_limit=limit)

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

    async def fetch(self, dereference_deep: int = 0) -> list[T]:
        """
        Retrieves all documents in the result set.

        Args:
            dereference_deep (int): The depth of dereference documents.

        Returns:
            list[T]: The list of parsed document instances.
        """
        self._dereference_deep = dereference_deep
        return [doc async for doc in self]

    async def fetch_one(self, dereference_deep: int = 0) -> T:
        """
        Retrieves a specific document in the result set.

        Args:
            dereference_deep (int): The depth of dereference documents.

        Returns:
            T: The parsed document instance.

        Raises:
            NoResultsError: If no results are found.
            ManyResultsError: If more than one result is found.
        """
        docs = await self.limit(2).fetch(dereference_deep)
        if not docs:
            raise NoResultsError()
        if len(docs) > 1:
            raise ManyResultsError()
        return docs[0]

    # noinspection PyShadowingBuiltins
    async def fetch_by_id(self, value: typing.Any, dereference_deep: int = 0) -> T:
        id_mapper = self._document_cls.__fields__['id'].mapper
        return await self.filter(
            Query.Eq('_id', id_mapper.validate(value))
        ).fetch_one(dereference_deep)

    async def count(self) -> int:
        """
        Counts the number of documents in the result set.

        Returns:
            int: The count of documents.
        """
        return await self._collection.count_documents(
            filter=self._filter,
            session=self._session.driver_session
        )


# noinspection PyProtectedMember
class FsBucket(Objects['FsObject']):

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

    # noinspection PyMethodMayBeStatic
    async def create(
        self,
        filename: str,
        src: typing.IO | bytes,
        metadata: dict = None
    ) -> 'FsObject':
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
            session=self._session.driver_session
        )
        # Update obj info
        obj = await self.fetch_by_id(obj.id)

        return obj

    async def exist(self, filename: str) -> bool:
        count = await self.filter(Query.Eq('filename', filename)).count()
        return count > 0

    async def revisions(self, filename: str) -> list['FsObject']:
        return await self.filter(Query.Eq('filename', filename)).fetch()


# noinspection PyProtectedMember
class FsObject(documents.Document):
    filename: str
    metadata: types.Json
    chunk_size: int = fields.field(alias='chunkSize')
    length: int
    upload_date: datetime.datetime = fields.field(alias='uploadDate')

    # noinspection SpellCheckingInspection
    __collection_name__ = 'fs.files'

    async def create_revision(self, fs: FsBucket, src: typing.IO | bytes, metadata: dict = None):
        await fs.create(self.filename, src=src, metadata=metadata)

    # noinspection SpellCheckingInspection
    async def download(self, fs: FsBucket, dest: typing.IO, revision: int = None):
        if revision is None:
            await fs._bucket.download_to_stream(
                file_id=self.id,
                destination=dest,
                session=fs._session.driver_session
            )
        else:
            await fs._bucket.download_to_stream_by_name(
                filename=self.filename,
                destination=dest,
                revision=revision,
                session=fs._session.driver_session
            )

    async def stream(self, fs: FsBucket, revision: int = None) -> AsyncIOMotorGridOut:
        if revision is None:
            return await fs._bucket.open_download_stream(
                file_id=self.id,
                session=fs._session.driver_session
            )
        return await fs._bucket.open_download_stream_by_name(
            filename=self.filename,
            revision=revision,
            session=fs._session.driver_session
        )
