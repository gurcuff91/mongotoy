<style>
    .md-typeset h1{
        display: none;
    }
    .md-sidebar--primary {
        width: 8rem;
    }
</style>

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
import uuid
import pymongo
import datetime
from mongotoy import Document, field


class Person(Document):
    code: str = field(id_field=True, default_factory=lambda: uuid.uuid4().hex)
    name: str = field(index=pymongo.TEXT, unique=True)
    age: int = field(index=pymongo.DESCENDING)
    dob: datetime.datetime = field(default_factory=datetime.date.today)
````

This example illustrates the definition of a `Person` document class with tailored field configurations.
The `code` field serves as the _primary key_, automatically generated with a unique identifier through
`uuid.uuid4().hex`. Additionally, the `name` field is indexed for text search using `pymongo.TEXT` and enforced
as unique. The `age` field is indexed in descending order to optimize sorting operations. Finally, the dob field 
defaults to the current date using `datetime.date.today()`. 


### Using extra configurations

The `mongotoy.field()` function accommodates an arbitrary number of additional parameters for fine-tuning field 
creation and validation. Certain [data types](/gurcuff91/mongotoy/docs/data_types) support specific configuration 
parameters.

#### Comparable types

Comparable types such as `int`, `float`, `decimal.Decimal`, `datetime.datetime`, `datetime.date` and `datetime.time`
enable comparison operations between values of the same type. These types support various comparison
configuration parameters to fine-tune how comparisons are conducted.

- **lt** (less than)
- **lte** (less than or equal to)
- **gt** (greater than)
- **gte** (greater than or equal to)

#### String type

In addition, the `str` type supports several configuration parameters for customization:

- **min_len**: Specifies the minimum length allowed for the string.
- **max_len**: Specifies the maximum length allowed for the string.
- **choices**: Defines a list of valid choices for the string value.

The following example shows how to use extra configuration parameters:

````python
from mongotoy import Document, field


class Person(Document):
    name: str = field(max_len=128)
    age: int = field(gte=21)
    fav_color: str = field(choices=['white', 'black', 'red', 'blue', 'green'])
````

In this example, the `Person` document defines three fields: `name`, `age`, and `fav_color`. The `name` field is of 
type `str` and is configured with a _maximum length_ of 128 characters. For the `age` field, which is of type `int`, a 
_minimum value_ of 21 is specified. Lastly, the `fav_color` field, also of type `str`, is constrained to a predefined 
set of _choices_: `'white', 'black', 'red', 'blue', and 'green'`. Any validation that violates these rules will 
raise a `mongotoy.error.DocumentValidation` error.