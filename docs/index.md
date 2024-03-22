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