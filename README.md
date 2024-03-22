# Mongotoy: Async ODM for MongoDB

Mongotoy is a comprehensive asynchronous Object-Document Mapper (ODM) designed to simplify interactions with MongoDB databases in Python applications. Leveraging the Motor asynchronous MongoDB driver, Mongotoy seamlessly integrates asynchronous programming with MongoDB, providing developers with a powerful toolset for building high-performance applications. This integration allows for efficient communication with MongoDB databases, ensuring optimal scalability and responsiveness. With Mongotoy, developers can harness the full potential of MongoDB's features while enjoying the benefits of asynchronous programming, making it an ideal choice for modern, data-driven applications.


## Key Features

- **Asynchronous Power**: Mongotoy leverages the asynchronous paradigm of Python, enabling efficient management of I/O operations for optimal performance and responsiveness in applications.


- **Based on Motor Driver**: Mongotoy is built on top of the asynchronous Motor MongoDB driver, ensuring seamless integration with asynchronous Python applications. 


- **Schemaless Flexibility**: With a schemaless design, Mongotoy empowers developers to work with MongoDB databases without rigid schemas, adapting to evolving data models effortlessly.


- **Intuitive API**: Mongotoy features an elegant and straightforward API facilitating common database operations.


- **Flexible Configuration Options**: Mongotoy offers extensive configuration options at both the database and document levels, enabling fine-tuning of MongoDB interactions for optimal performance and reliability.


- **Custom Data Types Support**: Mongotoy simplifies handling of custom data types and allows defining new types through Data Mapper classes, enhancing data integrity and consistency.


- **Object-Document Mapping**: Simplifying MongoDB document manipulation, Mongotoy maps Python objects to MongoDB documents seamlessly, enabling intuitive and object-oriented interactions.


- **Document Serialization**: Mongotoy supports serialization of documents into JSON, BSON, or Python dictionaries, enabling seamless integration with different parts of an application stack.


- **Document Inheritance Support**: Mongotoy provides robust support for document inheritance, enabling the creation of hierarchical data models and promoting code reuse and maintainability.


- **Python Type Hint Support**: Mongotoy allows developers to define document fields using Python type hints, enhancing code readability and enabling type checking.


- **Relationship Management**: Simplifying relationship management between documents, Mongotoy offers robust support for references and embedded documents, automating insertions, deletions, and updates.


- **Automatic Operation Handling**: Mongotoy automates insertion and deletion management, ensuring data integrity and consistency across related documents.


- **Query Building**: Mongotoy provides a powerful query building interface for constructing complex queries using Pythonic syntax.


- **Index Management**: Mongotoy simplifies the management of database indexes, optimizing query performance for efficient data retrieval.


- **Transactions**: Supporting MongoDB transactions, Mongotoy ensures data consistency and atomicity across multiple operations within a single transactional context.


- **Geospatial Data Support**: Mongotoy offers robust support for geospatial data types, facilitating storage, querying, and spatial analysis.


- **Database Seeding Management**: With built-in support for database seeding, Mongotoy streamlines the initialization of databases with predefined data sets, enhancing developer productivity.


- **Support for Capped Collections**: Mongotoy natively supports capped collections in MongoDB, ideal for scenarios requiring fixed-size, ordered datasets.


- **Time Series Collections Management**: Mongotoy provides robust support for managing time series data in MongoDB, optimized for storing and querying time-stamped data points.


- **GridFS File Handling**: Mongotoy seamlessly integrates with MongoDB's GridFS storage system for efficient handling of large files, offering a high-level interface for file management within MongoDB.


## Get Started

### Installation

Mongotoy can be easily installed via pip.

```bash
pip install mongotoy
```

### Define your first Document(s)

To define your first document, you'll create Python classes that represent the structure of your data. Each class corresponds to a collection in MongoDB. For example, let's define two classes: `Address` and `Person`.
In this example, Address is an embedded document containing address information, while Person is a document representing a person. Each field in these classes corresponds to a field in the MongoDB document. You can also specify additional options for each field, such as uniqueness or indexing.

```python
from mongotoy import Document, EmbeddedDocument, field, types
import datetime
import pymongo

class Address(EmbeddedDocument):
    street: str = field(index=pymongo.TEXT)
    city: str
    zip: int
    location: types.Point

class Person(Document):
    name: str = field(unique=True)
    last_name: str
    address: Address
    dob: datetime.date
    ssn: types.Ssn
```

### Interact with DB (CRUD operations)

To interact with the database using Mongotoy, you first need to establish a connection to the database and open a
database session. Then, you can perform CRUDs operations:

```python
from mongotoy import Engine, types
import datetime
import asyncio

# Create the MongoDB database engine
db = Engine(database='test-db')

async def main():
    # Connect to the MongoDB database
    await db.connect('mongodb://localhost:27017')
    
    # Create a new Person instance
    customer = Person(
        name='John',
        last_name='Doe',
        dob=datetime.date(1990, 12, 25),
        ssn='701-76-9732',
        address=Address(
            street='12910 US-90',
            city='Live Oak',
            zip=81100,
            location=types.Point(34.56, 78.98),
        )
    )    
    
    # Open a database session
    async with db.session() as session:
        
        # Save the customer document to the database
        await session.save(customer)
        
        # Fetch all customers from database
        async for c in session.objects(Person):
            print(c.dump_dict())
            
        # Update customer dob
        customer.dob=datetime.date(1995, 10, 25)
        await session.save(customer)
        
        # Open a Transaction
        async with session.transaction():
            # Delete customer
            await session.delete(customer)
        

# Run code 
if __name__ == '__main__':
    asyncio.run(main())
```

Mongotoy provides Python developers with a seamless and intuitive solution for MongoDB database management. With Motor asynchronous driver integration, schemaless flexibility, and an intuitive API, Mongotoy simplifies database tasks from CRUD operations to advanced queries and geospatial data handling. Additional features like document inheritance, transaction support, and document serialization enhance its versatility.

## Extras
See full documentation at: 

**If you like this project buy me a coffe !!**

<a href="https://www.buymeacoffee.com/gurcuff91" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="42" width="175"></a>
