<style>
    .md-typeset h1{
        display: none;
    }
    .md-sidebar--primary {
        display: none;
    }
</style>

<p align="center">
  <a href="https://github.com/gurcuff91/mongotoy">
    <img src="assets/mongotoy.png?raw=true" alt="Mongotoy Logo" width="45%" height="auto">
  </a>
</p>

<p align="center">
  <i>Comprehensive ODM for MongoDB</i>
</p>

<p align="center">
  <a href="https://pypi.org/project/mongotoy/">
    <img src="https://img.shields.io/pypi/v/mongotoy?color=%2334D058&label=version" alt="Version"/>
  </a>
  <a href="https://pypi.org/project/mongotoy/">
    <img src="https://img.shields.io/pypi/pyversions/mongotoy.svg?color=%2334D058" alt="Supported Python Versions"/>
  </a>
</p>

<hr>
<p align="justify">
  Mongotoy is a comprehensive Object-Document Mapper (ODM) that streamlines interactions with MongoDB databases in 
  Python applications. Powered by <a href="https://github.com/mongodb/motor">Motor</a> driver, Mongotoy seamlessly 
  integrates with MongoDB, offering a versatile toolkit for constructing high-performance applications. This integration
  facilitates efficient communication with MongoDB databases, guaranteeing optimal scalability and responsiveness. With 
  Mongotoy, you can unlock the full potential of MongoDB's features.
</p>
<hr>

## Features

- **Asynchronous Power**: Mongotoy leverages the asynchronous paradigm of Python, enabling efficient management of
I/O operations for optimal performance and responsiveness in applications.

- **Based on Motor Driver**: Mongotoy is built on top of the asynchronous [Motor](https://github.com/mongodb/motor)
MongoDB driver, ensuring seamless integration with asynchronous Python applications.

- **Schemaless Flexibility**: With a schemaless design, Mongotoy empowers developers to work with MongoDB databases
without rigid schemas, adapting to evolving data models effortlessly.

- **Intuitive API**: Mongotoy features an elegant and straightforward API facilitating common database operations.

- **Flexible Configuration Options**: Mongotoy offers extensive configuration options at both the database and 
document levels, enabling fine-tuning of MongoDB interactions for optimal performance and reliability.

- **Custom Data Types Support**: Mongotoy simplifies handling of custom data types and allows defining new types
through Data Mapper classes, enhancing data integrity and consistency.

- **Object-Document Mapping**: Simplifying MongoDB document manipulation, Mongotoy maps Python objects to MongoDB 
documents seamlessly, enabling intuitive and object-oriented interactions.

- **Document Serialization**: Mongotoy supports serialization of documents into JSON, BSON, or Python dictionaries, 
enabling seamless integration with different parts of an application stack.

- **Document Inheritance Support**: Mongotoy provides robust support for document inheritance, enabling the creation
of hierarchical data models and promoting code reuse and maintainability.

- **Python Type Hint Support**: Mongotoy allows developers to define document fields using Python type hints, 
enhancing code readability and enabling type checking.

- **Relationship Management**: Simplifying relationship management between documents, Mongotoy offers robust support
for references and embedded documents, automating insertions, deletions, and updates.

- **Automatic Operation Handling**: Mongotoy automates insertion and deletion management, ensuring data integrity 
and consistency across related documents.

- **Query Building**: Mongotoy provides a powerful query building interface for constructing complex queries using 
Pythonic syntax.

- **Index Management**: Mongotoy simplifies the management of database indexes, optimizing query performance for 
efficient data retrieval.

- **Transactions**: Supporting MongoDB transactions, Mongotoy ensures data consistency and atomicity across multiple
operations within a single transactional context.

- **Geospatial Data Support**: Mongotoy offers robust support for geospatial data types, facilitating storage, 
querying, and spatial analysis.

- **Database Seeding Management**: With built-in support for database seeding, Mongotoy streamlines the 
initialization of databases with predefined data sets, enhancing developer productivity.

- **Support for Capped Collections**: Mongotoy natively supports capped collections in MongoDB, ideal for 
scenarios requiring fixed-size, ordered datasets.

- **Time Series Collections Management**: Mongotoy provides robust support for managing time series data in 
MongoDB, optimized for storing and querying time-stamped data points.

- **GridFS File Handling**: Mongotoy seamlessly integrates with MongoDB's GridFS storage system for efficient
handling of large files, offering a high-level interface for file management within MongoDB.

## License
This project is licensed under the terms of the [Apache 2.0 license](https://www.apache.org/licenses/LICENSE-2.0).
