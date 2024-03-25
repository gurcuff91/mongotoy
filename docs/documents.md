<style>
    .md-typeset h1{
        display: none;
    }
    .md-sidebar--primary {
        display: none;
    }
</style>

## Embedded Documents

An _embedded document_ serves as a container for defining complex object types that are nested within other 
documents. Unlike _standalone documents_, _embedded documents_ do not represent individual collections in the database. 
Instead, they are used to encapsulate related data fields within a parent document, allowing for more structured and 
organized data models.

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
[fields section](#fields). If you create a new document without explicitly
specifying an `id` field, Mongotoy automatically generates one and assigns a `bson.ObjectId` type to it. 
This unique identifier simplifies document management and facilitates efficient querying within MongoDB collections.

/// note
All classes derived from `mongotoy.Document` come with an `id` property, which provides access to the document's ID 
field. To retrieve the ID field of a `Person` document, simply access it using `Person.id`. Similarly, to access the ID
field value of a `Person` instance, use `person.id`.
///

### Configuration

Mongotoy offers document-level configuration for various settings, including indexes, capped collection options, 
timeseries collection options, codec options, read preference, read concern, write concern, and additional 
MongoDB document options.

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
- **extra_options**: Extra options for the document configuration (default is an empty dictionary).

All of these configurations apply only at the document collection level and do not affect the rest of the 
database collections.


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

### Using Nullable types
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

When you specify a document field with a `mongotoy.EmbeddedDocument`, Mongotoy treats it as _embedded data_, 
meaning that the document is stored directly within the parent document. On the other hand, when you
use a `mongotoy.Document`, Mongotoy treats it as a _reference_ to another collection.
See [references section](#references)

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

/// note
The only difference is the base class of the `Address` document.
///

#### Forwarding Types

Mongotoy facilitates the utilization of document types as [forward dependencies](https://peps.python.org/pep-0563/#forward-references), 
enabling the use of document types that may not have been created yet or are defined in different modules.
This feature supports self-referential document type as well.

Here's an example demonstrating the use of a self-referential document type:

````python
import datetime
from typing import Optional
from mongotoy import Document, reference


class Person(Document):
    name: str
    age: int
    dob: datetime.datetime
    parent: Optional['Person'] = reference()
````

In this example, the `Person` document references its own type in the `parent` field, allowing for self-referential 
relationships within the document.

/// warning
Using `mongotoy.reference(`) is essential for specifying the `parent` field as a reference, especially when dealing 
with _Forwarding Types_. Mongotoy doesn't evaluate _Forwarding Types_ during document creation to determine their type. 
By default, it assumes they are embedded documents. Therefore, `mongotoy.reference()` ensures proper handling of the 
field as a reference. See [references section](#references).
///

## Fields

Mongotoy not only generates fields based on types but also provides options for customization such as 
aliases, indexing, uniqueness, and default values using the `mongotoy.field()` function. This enables you to define
fields with specific properties tailored to the application needs, offering enhanced control and flexibility
in document definition.


### Customization Parameters

The `mongotoy.field()` function accepts the following parameters:

- **alias**: Alias for the field. Defaults to None.
- **id_field**: Indicates if the field is an ID field. Defaults to False.
- **default**: Default value for the field. Defaults to `mongotoy.expresions.EmptyValue`.
- **default_factory**: Factory function for generating default values. Defaults to None.
- **index**: Type of index for the field. Defaults to None.
- **sparse**: Whether the index should be sparse. Defaults to False.
- **unique**: Whether the index should be unique. Defaults to False.

Here's an example that showcases the customization of fields in Mongotoy documents. 
Each field in the `Person` class utilizes the `mongotoy.field()` function for customization.

````python
import pymongo
import datetime
from mongotoy import Document, field


class Person(Document):
    code: str = field(id_field=True)
    name: str = field(index=pymongo.TEXT, unique=True)
    age: int = field(index=pymongo.DESCENDING)
    dob: datetime.datetime = field(default_factory=datetime.date.today)
````

The `code` field is specified with `id_field=True`, indicating it serves as the _primary key_. 
Additionally, the `name` field is configured for _full-text search indexing_ (`index=pymongo.TEXT`) and _uniqueness_
(`unique=True`). The `age` field is indexed in _descending order_ (`index=pymongo.DESCENDING`), facilitating 
efficient sorting based on age. Lastly, the `dob` field is assigned a _default value_ using 
`default_factory=datetime.date.today`, ensuring it defaults to the current date if not explicitly provided.

## References

Mongotoy simplifies the handling of references by automatically generating them when you use a `mongotoy.Document` 
type as a field in another document. This means that you don't need to manually manage references between documents. 
Additionally, Mongotoy provides flexibility in configuring reference behavior through the `mongotoy.reference()` 
function. With this function, you can customize how references are handled.

### Customization Parameters

The `mongotoy.reference()` function accepts the following parameters:

- **ref_field**: Name of the referenced field. Defaults to `id`
- **key_name**: Key name for the reference. Defaults to None.

/// note
If `key_name` isn't specified, Mongotoy automatically generates it by concatenating the name of the field that holds
the reference value with the name of the referenced field.
///

Here's an example that showcases the customization of references in Mongotoy documents. 

````python
import datetime
from typing import Optional
from mongotoy import Document, reference


class Person(Document):
    code: str
    name: str
    age: int
    dob: datetime.datetime
    parent: Optional['Person'] = reference(ref_field='code', key_name='p_code')
````

The `parent` field in the `Person` document class serves as a reference to another `Person` document, 
denoting the individual's parent. This field is optional, enabling it to either reference another `Person` 
document or set as **null**. Through the `mongotoy.reference()` function, the reference behavior is established
based on the `code` field of the referenced document. In the database, the reference key is labeled as `p_code`. 
This setup ensures that when a `Person` document is saved, the `code` value of the referenced `Person` document 
stored in the `parent` field is also stored in the current document under the `p_code` key.

/// danger
Utilizing `mongotoy.reference()` in a class that isn't derived from `mongotoy.Document`, or 
omitting `mongotoy.reference()` when using a `mongotoy.Document` based class as a [forwarded type](#forwarding-types),
will result in a `mongotoy.errors.DocumentValidation` error during document instantiation.
///

Mongotoy streamlines the definition of MongoDB document structures by offering a user-friendly interface that
leverages Python syntax and type annotations. This approach allows you to easily define field types and establish
relationships between documents, facilitating the creation of data models. With Mongotoy, you can seamlessly 
navigate the complexities of MongoDB schema design, ensuring a more intuitive and efficient development process.
