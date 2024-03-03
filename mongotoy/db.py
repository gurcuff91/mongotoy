import asyncio

import bson
import pymongo
from motor.core import AgnosticClient, AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.read_concern import ReadConcern

from mongotoy.errors import EngineError


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
        self._collections = []
        self._lock = asyncio.Lock()

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
        self._collections = await self._db_client[self._database].list_collection_names()

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


class Session:
    pass


class Transaction:
    pass
