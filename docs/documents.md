<style>
    .md-typeset h1{
        display: none;
    }
    .md-sidebar--primary {
        display: none;
    }
</style>

## Documents

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

By default, Mongotoy pluralizes the lowercase class name to determine the collection name. So, in this 
case, the collection name will be `persons`. 

Additionally, you can specify a custom collection name by defining the `__collection_name__` property within the class:

````python
from mongotoy import Document


class Person(Document):
    __collection_name__ = 'users'
````

/// warning | Attention
When defining class attributes, it's crucial to specify their **types**. Mongotoy utilizes these _type annotations_ 
to generate **fields** accordingly. Attributes _without type annotations_ will be ignored and treated as regular
class fields.
///


### The id field

In Mongotoy, the `id` field is essential in every document, acting as the primary key to ensure unique identification. 
You can define the id field using the `mongotoy.field()` function, as explained in the 
[fields chapter](https://gurcuff91.github.io/mongotoy/fields/). If you create a new document without explicitly
specifying an `id` field, Mongotoy automatically generates one and assigns a `bson.ObjectId` type to it. 
This unique identifier simplifies document management and facilitates efficient querying within MongoDB collections.

/// note
All classes derived from `mongotoy.Document` come with an `id` property, which provides access to the document's ID 
field. To retrieve the ID field of a `Person` document, simply access it using `Person.id`. Similarly, to access the ID
field value of a `Person` instance, use `person.id`.
///


## Embedded Documents

Mongotoy supports the creation of embedded documents by inheriting from `mongotoy.EmbeddedDocument` and defining your 
class attributes in a manner similar to how you would define a Python dataclass. Here's a quick example:

````python
from mongotoy import EmbeddedDocument


class Address(EmbeddedDocument):
    street: str
    city: str
    zipcode: int
    country: str
````

An embedded document in Mongotoy serves as a container for defining complex object types that are nested within other 
documents. Unlike standalone documents, embedded documents do not represent individual collections in the database. 
Instead, they are used to encapsulate related data fields within a parent document, allowing for more structured and 
organized data models.

## Supported Data Types

Mongotoy supports a wide range of data types, encompassing both common built-in Python types and custom types 
tailored to specific use cases. 

#### Supported built-in Python types

- `str`
- `bool`
- `bytes`
- `int`
- `float`
- `decimal.Decimal`
- `datetime.datetime`
- `datetime.date`
- `datetime.time`
- `uuid.UUID`

#### Supported bson types

- `bson.ObjectId`

#### Supported sequence types

- `list`
- `tuple`
- `set`

#### Supported custom types

- `mogotoy.types.IpV4`: Represents an IPv4 address.
- `mogotoy.types.IpV6`: Represents an IPv6 address.
- `mogotoy.types.Port`: Represents a port number.
- `mogotoy.types.Mac`: Represents a MAC address.
- `mogotoy.types.Phone`: Represents a phone number.
- `mogotoy.types.Email`: Represents an email address.
- `mogotoy.types.Card`: Represents a credit card number.
- `mogotoy.types.Ssn`: Represents a Social Security Number (SSN).
- `mogotoy.types.Hashtag`: Represents a hashtag.
- `mogotoy.types.Doi`: Represents a Digital Object Identifier (DOI).
- `mogotoy.types.Url`: Represents a URL.
- `mogotoy.types.Version`: Represents a Semantic Version Number.
- `mogotoy.types.Point`: Represents a GEO-JSON Point.
- `mogotoy.types.MultiPoint`: Represents a GEO-JSON MultiPoint.
- `mogotoy.types.LineString`: Represents a GEO-JSON LineString.
- `mogotoy.types.MultiLineString`: Represents a GEO-JSON MultiLineString.
- `mogotoy.types.Polygon`: Represents a GEO-JSON Polygon.
- `mogotoy.types.MultiPolygon`: Represents a GEO-JSON MultiPolygon.
- `mogotoy.types.Json`: Represents a valid json data.
- `mogotoy.types.Bson`: Represents a valid bson data.
- `mogotoy.types.File`: Represents a Grid-FS object.

You can effortlessly utilize these data types within your documents, and Mongotoy will take care of automatic 
field creation and validation.

### Nullable types
By default, Mongotoy does not permit `null` data. However, you can specify nullability using `typing.Optional`. 
Below is an example of a Person document that allows `null` data:

````python
import datetime
from typing import Optional
from mongotoy import Document


class Person(Document):
    name: Optional[str]
    age: Optional[int]
    dob: Optional[datetime.datetime]
````

### Using Documents types

Mongotoy facilitates the integration of other documents as types within documents, offering a flexible approach 
to defining complex data structures. This means you can use instances of other Mongotoy document classes as 
attribute types within your own document classes. By incorporating related documents as types, you can establish 
meaningful relationships between different data entities, enhancing the organization and clarity of your data model. 
This feature enables you to design more comprehensive and interconnected schemas, reflecting the real-world 
relationships between entities in your application domain.

/// note
There are two types of documents: `mongotoy.Document` and `mongotoy.EmbeddedDocument`. 
While you can use both types seamlessly in your application, it's essential to understand that Mongotoy employs 
different approaches under the hood to handle them.
///

When you specify a document field with a `mongotoy.EmbeddedDocument`, Mongotoy treats it as embedded data, meaning that
the document is stored directly within the parent document. On the other hand, when you use a `mongotoy.Document`, 
Mongotoy treats it as a [reference](https://gurcuff91.github.io/mongotoy/references/) to another collection.

Here's an example of embedding an address within a person document:

````python
import datetime
from mongotoy import Document, EmbeddedDocument

class Address(EmbeddedDocument):
    street: str
    city: str
    zipcode: int
    country: str


class Person(Document):
    name: str
    age: int
    dob: datetime.datetime
    address: Address
````


Here's an example of referencing an address within a person document:

````python
import datetime
from mongotoy import Document

class Address(Document):
    street: str
    city: str
    zipcode: int
    country: str


class Person(Document):
    name: str
    age: int
    dob: datetime.datetime
    address: Address
````

Mongotoy simplifies the definition of document structures by leveraging familiar Python syntax and type annotations. 
With Mongotoy, you can effortlessly specify field types and establish relationships between documents, 
streamlining the process of designing complex data models.
