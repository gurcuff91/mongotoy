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


### Customization parameters

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

### Extra configurations

The `mongotoy.field()` function accepts additional parameters for fine-tuning field creation and validation. 
Certain [data types](/gurcuff91/mongotoy/docs/data_types) support specific configuration parameters.

#### Comparable types

Comparable types such as `int`, `float`, `decimal.Decimal`, `datetime.datetime`, `datetime.date` and `datetime.time`
enable comparison operations between values of the same type. These types support various comparison
configuration parameters to fine-tune how comparisons are conducted.

- **lt** (less than)
- **lte** (less than or equal to)
- **gt** (greater than)
- **gte** (greater than or equal to)

#### String type

The `str` type supports these configuration parameters for customization:

- **min_length**: Specifies the minimum length allowed.
- **max_length**: Specifies the maximum length allowed.
- **choices**: Defines a list of valid value choices.
- **regex**: Defines a regular expression to validate.

#### Sequence types

Sequence types such as `list`, `tuple` and `set` supports these configuration parameters for customization:

- **min_items**: Specifies the minimum items allowed.
- **max_items**: Specifies the maximum items allowed.


The following example shows how to use extra configuration parameters:

````python
from mongotoy import Document, field


class Person(Document):
    name: str = field(max_length=128)
    age: int = field(gte=21)
    colors: list[str] = field(choices=['white', 'black', 'green'], max_items=2)
````
