<style>
    .md-typeset h1{
        display: none;
    }
    .md-sidebar--primary {
        display: none;
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

These customizations enable you to tailor field behavior in documents, including indexing, uniqueness, 
and default values.
