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
