<style>
    .md-typeset h1{
        display: none;
    }
    .md-sidebar--primary {
        width: 8rem;
    }
</style>

## Defining documents

Defining documents in Mongotoy is straightforward. Simply inherit from `mongotoy.Document` class and define your class
attributes similarly to how you would define a [Python dataclass](https://docs.python.org/3/library/dataclasses.html). 
In this example, each class attribute represents a field in the database, and the class itself corresponds 
to a collection:

````python
import datetime
from mongotoy import Document


class Person(Document):
    name: str
    age: int
    dob: datetime.datetime
````

/// warning | Attention
When defining class attributes, it's crucial to specify their **types**. Mongotoy utilizes these _type annotations_ 
to generate **fields** accordingly. Attributes _without type annotations_ will be ignored and treated as regular
class fields.
///

/// note
By default, Mongotoy does **not require** any field values to be specified during document creation, aligning with
MongoDB's schemaless nature. Unspecified field values are set to `mongotoy.expressions.EmptyValue`, and Mongotoy 
only validates the values of fields that have been explicitly specified. The exception to this rule is the `id` field,
which must have at least one default value defined either through the `default` or `default_factory` properties.
///

### The collection name

By default, Mongotoy pluralizes the lowercase class name to determine the collection name. So, in this 
case, the collection name will be `persons`. 

Additionally, you can specify a custom collection name by defining the `__collection_name__` property within the class:

````python
from mongotoy import Document


class Person(Document):
    __collection_name__ = 'users'
````

### The id field

In Mongotoy, the `id` field is essential in every document, acting as the primary key to ensure unique identification. 
You can define the id field using the `mongotoy.field(id_field=True)` as explained in the 
[fields section](/gurcuff91/mongotoy/docs/fields). If you create a new document without explicitly specifying an `id` field, Mongotoy automatically 
generates one and assigns a `bson.ObjectId` type to it. This unique identifier simplifies document management and 
facilitates efficient querying within MongoDB collections.

/// note
All classes derived from `mongotoy.Document` come with an `id` property, which provides access to the document's ID 
field. To retrieve the ID field of a `Person` document, simply access it using `Person.id`. Similarly, to access the ID
field value of a `Person` instance, use `person.id`.
///

### Configuration

Mongotoy offers document-level configuration for various settings, including indexes, capped collection options, 
timeseries collection options, codec options, read preference, read concern, write concern, and additional 
MongoDB collection options.

Configuration params:

- **indexes**: List of indexes for the document.
- **capped**: Indicates if the collection is capped (default is False).
- **capped_size**: The maximum size of the capped collection in bytes (default is 16 MB).
- **capped_max**: The maximum number of documents allowed in a capped collection (default is None).
- **timeseries_field**: The field name to use as the time field for timeseries collections (default is None).
- **timeseries_meta_field**: The field name for metadata in timeseries collections (default is None).
- **timeseries_granularity**: The granularity of time intervals.
- **timeseries_expire_after_seconds**: The expiration time for documents in a timeseries collection, in seconds.
- **codec_options**: The BSON codec options (default is None).
- **read_preference**: The read preference for the document (default is None).
- **read_concern**: The read concern for the document (default is None).
- **write_concern**: The write concern for the document (default is None).
- **extra_options**: Extra options for the collection creation (default is an empty dictionary).

These configurations exclusively pertain to the document collection level and do not extend to other collections within 
the database. To specify settings, you use the `document_config` class attribute in your document definition.

````python
from mongotoy import Document
from mongotoy.documents import DocumentConfig


class Person(Document):
    document_config = DocumentConfig(capped_collection=True)
````


### Embedded documents

An _embedded document_ serves as a container for defining complex object types that are nested within other 
documents. Unlike _documents_, _embedded documents_ do not represent individual collections in the database. 
Instead, they are used to encapsulate related data fields within a parent document, allowing for more structured and 
organized data models.

Mongotoy supports the creation of embedded documents by inheriting from `mongotoy.EmbeddedDocument` and defining your 
class attributes in a manner similar to how you would define a [Document](#documents). Here's a quick example:

````python
from mongotoy import EmbeddedDocument


class Address(EmbeddedDocument):
    street: str
    city: str
    zipcode: int
    country: str
````

## Dumping documents

Mongotoy simplifies the process of exporting document data by offering three distinct methods: 
`dump_dict`, `dump_json`, and `dump_bson`. These three methods offer flexibility, allowing you to choose the
appropriate format based on needs and integration requirements.

/// note
The `dump_json` and `dump_bson` methods only prepares data for compatibility with JSON and BSON formats respectively. 
However, they don't perform serialization themselves, to fully serialize the data you'll need to use an 
appropriate third-party library.
///

### Dict
The `dump_dict` method converts document data into a Python dictionary format, facilitating integration with
Python-based workflows and applications. It supports the following customization parameters to tailor the output 
according to specific requirements.

- **by_alias**: Dumping by fields aliases. (default is False)
- **exclude_empty**: Exclude fields with empty values from the output. (default is False)
- **exclude_null**: Exclude fields with null values from the output. (default is False)

### Json
The `dump_json` method export the document data in a format compatible with JSON, facilitating
interoperability with various systems and services supporting JSON data exchange. It supports the following
customization parameters to tailor the output according to specific requirements.

- **by_alias**: Dumping by fields aliases. (default is False)
- **exclude_null**: Exclude fields with null values from the output. (default is False)

### Bson
The `dump_bson` method export the document data in a format compatible with BSON for seamless interaction 
with MongoDB database. It supports the following customization parameters to tailor the output 
according to specific requirements.

- **by_alias**: Dumping by fields aliases. (default is True)
- **exclude_null**: Exclude fields with null values from the output. (default is False)

/// note
The `dump_json` and `dump_bson` methods exclude empty values from the output, unlike `dump_dict`, which includes 
them optionally.
///

Through these versatile dumping methods, Mongotoy empowers you to work with document data in various formats,
catering to diverse data processing and integration requirements. Whether it's within Python environments, 
interoperating with JSON-compatible systems, or interacting with MongoDB databases, Mongotoy provides the 
flexibility and compatibility needed for efficient data management and integration.
