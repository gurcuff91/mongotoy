<style>
    .md-typeset h1{
        display: none;
    }
    .md-sidebar--primary {
        width: 8rem;
    }
</style>

## Engine

The `Engine` class in Mongotoy serves as a versatile interface for managing MongoDB databases, providing a 
comprehensive set of features to streamline database operations. With asynchronous support built-in, it efficiently 
handles tasks like database connection, sessions, migrations, and seeding, ensuring seamless interactions. 
You can customize database interactions by specifying options such as _codec options_, _read preference_, 
_read concern_, and _write concern_, tailoring the functionality to specific requirements.

The Engine class accepts the following params:

- **database**: The name of the MongoDB database.
- **codec_options**: The BSON codec options.
- **read_preference**: The read preference for the MongoDB client.
- **read_concern**: The read concern for the MongoDB client.
- **write_concern**: The written concern for the MongoDB client.

The following example shows how to initialize the Engine
````python
import bson
import pymongo
from pymongo.read_concern import ReadConcern
from mongotoy import Engine

# Create database engine
engine = Engine(
    database='my-test-db',
    codec_options=bson.CodecOptions(uuid_representation=bson.JAVA_LEGACY),    
    read_preference=pymongo.ReadPreference.PRIMARY,
    read_concern=ReadConcern('majority'),
    write_concern=pymongo.WriteConcern(w=2)
)
````

This example initializes an `Engine` instance with specified configuration. It sets the target database to
`my-test-db` and configures `codec_options` to use the _Java Legacy UUID_ representation. Additionally, it specifies
`read_preference` as _primary_ , a `read_concern` of `majority`, and a `write_concern` with a `w=2`. Overall, 
the setup ensures compatibility and consistency in database interactions.

The `Engine` class offers convenient properties and methods for seamless access to various MongoDB components. 
With properties like `.client`, `.database`, and methods like `.collection()` and `.gridfs()`, you can effortlessly 
interact with the underlying MongoDB client, database collections, and GridFS buckets.

````python
# Access to an underlying client
engine.client

# Access to an underlying database
engine.database

# Get a collection named 'users'
engine.collection('users')

# Get a bucket named 'images'
engine.gridfs('images')
````

### Database connection

The `engine.connect()` function establishes a connection to the MongoDB server asynchronously. It accepts connection 
arguments for [AsyncIOMotorClient](https://motor.readthedocs.io/en/stable/api-asyncio/asyncio_motor_client.html) and 
includes an optional parameter, `ping`, which determines whether to ping the server after establishing the connection.

````python
# Connect to a local db, and send ping command
await engine.connect('mongodb://localhost:27017', ping=True)
````

/// warning | Attention
Before accessing any features of the `Engine` class, ensure it is connected to the database using the `connect()` method.
Failure to do so will result in a `mongotoy.errors.EngineError`.
///

### Open session

To open a new database session, use the `engine.session()` function. The `Session` object supports context handling,
enabling you to use it within a context; this ensures the proper _starting/ending_ of the session. 
See [session](#session)

### Execute migration

Migrations in `Mongotoy` cover a range of tasks essential for seamlessly transitioning your data structures into
MongoDB. These tasks include migrating _indexes_, creating _capped collections_, and defining _time series_ collections.
This comprehensive support ensures that your data migration process is efficient and encompasses all necessary 
configurations for optimal data management in MongoDB.

To migrate a document, use the `engine.migrate()` or `engine.migrate_all()` functions as follows:

````python
# Open database session
async with engine.session() as session:
    
    # Migrate single document
    await engine.migrate(Person, session=session)

    # Migrate many documents
    await engine.migrate_all([Author, Book], session=session)
````

/// note
Migrations are only applied if the associated collection for the document does not already exist in the database.
///

### Execute seeding

Seeding in `Mongotoy` provides a convenient way to populate your database with _initial data_, ensuring that your 
database is preloaded with the necessary information to kickstart your application or project. It allows you to 
define and execute seeding functions that insert predefined data into your MongoDB collections, helping you streamline
the setup process and accelerate development.

To execute a seeding function, use the `engine.seeding()` or `engine.seeding_all()` functions as follows:

````python
from mongotoy.db import Session

async def seeder_01(session: Session):
    # Exec some data insertions here ...

async def seeder_02(session: Session):
    # Exec some data insertions here ...

# Open database session
async with engine.session() as session:

    # Seed one function
    await engine.seeding(seeder_01, session=session)
    
    # Seed many functions
    await engine.seeding_all([seeder_01, seeder_02], session=session)
````

/// note
Seeding functions are applied only once, regardless of how many times they are executed. They are registered in a 
collection named `mongotoy.seeding`, ensuring that they are executed only once to prevent duplicate data seeding.
///

## Session

The `Session` class in Mongotoy provides a context manager for managing MongoDB database operations within a 
transaction-like context. It facilitates starting and ending MongoDB sessions, allowing for efficient handling 
of database transactions. Additionally, it offers methods for managing transactions, accessing object managers for
document classes, interacting with GridFS buckets, saving documents to the database, deleting documents, 
and managing cascading deletes. Through its asynchronous support, it ensures smooth and streamlined database 
operations, enhancing the overall efficiency of MongoDB interactions.

The `Session` class provides properties for managing MongoDB sessions and database interactions. 
These properties include:

- **engine**: Represents the `Engine` associated with the session, enabling direct access to database operations
and configurations.

- **started**: Indicates whether the session has been initialized, offering a boolean value to track session status.

- **driver_session**: Offers access to the underlying MongoDB driver session, facilitating low-level database 
operations and transactions.

### Lifecycle

The `Session` class offers a flexible approach to managing its lifecycle. While it provides a context manager 
interface for automatic lifecycle management, you can also control it manually using the `start()` and `end()` methods.
Sessions must always be instantiated from an `Engine` instance using the `engine.session()` function.

````python
# Open db session with context
async with engine.session() as session:
    # Exec session operations here ...


# Open db session with no context
session = engine.session()
await session.start()
# Exec session operations here ...
await session.end()
````

These examples showcase two methods of opening a database session with Mongotoy's Engine class. The first one uses 
a context manager, ensuring proper session handling and cleanup after execution. The second method directly initializes
a session without context management, requiring explicit invocation of methods for session initiation and termination.

### Open transaction

To open a new database transaction, use the `session.transaction()` function. The `Transaction` object supports 
context handling, enabling you to use it within a context; this ensures the proper _commit/abort_ of the 
transaction. See [transaction](#transaction)

### Objects

The `objects` method in the `Session` class facilitates the creation of an `Objects` instance, which allows for 
querying documents of a specified type within the session context. It provides flexibility in querying documents 
and supports deep dereferencing when needed. See [objects](/gurcuff91/mongotoy/docs/objects)

````python
# Open db session
async with engine.session() as session:
    
    # Get objects for Person document
    persons = session.objects(Person)
    
    # Eexec operations over persons ...
````

### Files

The `fs` method in the `Session` class facilitates seamless interaction with GridFS, a MongoDB feature for storing 
and retrieving large files such as images, videos, and documents. With this method, users can efficiently manage 
file storage directly within the database, ensuring robust and scalable file handling capabilities.
See [files](/gurcuff91/mongotoy/docs/files)

````python
# Open db session
async with engine.session() as session:
    
    # Get fs bucket
    files = session.fs()
    
    # Eexec operations over files ...
````

### Saving documents

The `save` and `save_all` methods in the `Session` class enable the efficient persistence of MongoDB documents 
into the associated database. By invoking these methods, you can seamlessly store individual documents or batches of 
documents while ensuring data integrity and consistency. This functionality streamlines the process of data storage,
enhancing the overall efficiency and reliability of database operations.

````python
# Open db session
async with engine.session() as session:
    
    # Save a single person
    await session.save(person_01)
    
    # Save many persons
    await session.save_all([person_01, person_02])
````

By default, the saving methods do not include saving references. However, you can enable this functionality by 
`setting save_references=True`. This feature allows for the comprehensive storage of documents along with their
associated references, enhancing the integrity and completeness of the data stored in the MongoDB database.

### Deleting documents

The `delete` and `delete_all` methods in the `Session` class facilitate the removal of documents from the MongoDB 
database. These methods provide a convenient way to delete individual documents or multiple documents at once. 
Additionally, they offer support for cascading deletion, allowing for the removal of associated documents as well.
This ensures efficient and streamlined data management within MongoDB, empowering users to maintain data integrity
and cleanliness effectively.

````python
# Open db session
async with engine.session() as session:
    
    # Delete a single person
    await session.delete(person_01)
    
    # Delete many persons
    await session.delete_all([person_01, person_02])
````

By default, the deletion methods do not remove associated references, but you can activate this functionality by 
setting `delete_cascade=True`. This feature allows for the removal of related references along with the specified 
documents, ensuring comprehensive data cleanup and management.

## Transaction

The `Transaction` class encapsulates MongoDB transactions, ensuring the atomicity of operations within a session 
context. It is initialized with a session object, providing access to the associated MongoDB session via the `session` 
property. Upon initialization, the class starts the transaction using the provided session. The `commit()` method is 
responsible for committing changes made during the transaction, while `abort()` discards changes and closes the 
transaction. These methods handle exceptions to ensure proper transaction management. Additionally, the class supports
context management.

````python
# Open db session
async with engine.session() as session:
    
    # Handle transaction in context
    async with session.transaction():
        # Exec session operations inside transaction here ...

    # Handle transaction manually
    tx = session.transaction()
    try:
        # Exec transaction operations here ...
    except:
        await tx.abort()
    else:
        await tx.commit()
````

This example showcases transaction management within a database session. Transactions can be handled either 
automatically within a context, ensuring _commit_ or _abort_ in case of errors, or manually, allowing for customized 
error handling.