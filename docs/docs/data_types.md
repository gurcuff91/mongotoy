<style>
    .md-typeset h1{
        display: none;
    }
    .md-sidebar--primary {
        width: 8rem;
    }
</style>

## Supported Data Types

Mongotoy supports a wide range of data types, encompassing both common built-in Python types and custom types 
tailored to specific use cases. 

#### Supported built-in types

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

#### Supported sequence types

- `list`
- `tuple`
- `set`

#### Supported bson types

- `bson.ObjectId`

#### Custom types

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

You can effortlessly use these data types within your documents, and Mongotoy will take care of automatic field creation
and validation.

### Using nullable types
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

### Using documents types

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

When you specify a document field with a `mongotoy.EmbeddedDocument` base type, Mongotoy treats it as _embedded data_, 
meaning that the document is stored directly within the parent document. On the other hand, when you
use a `mongotoy.Document` base type, Mongotoy treats it as a _reference_ to another collection.
See [references](/gurcuff91/mongotoy/docs/references)

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

#### Forwarding types

Mongotoy facilitates the utilization of document types as [forward dependencies](https://peps.python.org/pep-0563/#forward-references), 
enabling the use of document types that may not have been created yet or are defined in different modules.
This feature supports a self-referential document type as well.

Here's an example demonstrating the use of a self-referential document type:

````python
import datetime
from mongotoy import Document, reference


class Person(Document):
    name: str
    age: int
    dob: datetime.datetime
    parent: 'Person' = reference()
````

In this example, the `Person` document references its own type in the `parent` field, allowing for self-referential 
relationships within the document.

/// warning | Attention
Using `mongotoy.reference(`) is **essential** for specifying the `parent` field as a reference, especially when dealing 
with _Forwarding Types_. Mongotoy doesn't evaluate _Forwarding Types_ during document creation to determine their type. 
By default, it assumes they are embedded documents. Therefore, `mongotoy.reference()` ensures proper handling of the 
field as a reference. See [references](/gurcuff91/mongotoy/docs/references).
///