<style>
    .md-typeset h1{
        display: none;
    }
    .md-sidebar--primary {
        width: 8rem;
    }
</style>

## References

Mongotoy simplifies the handling of references by automatically generating them when you use a `mongotoy.Document` 
base type as a field in another document. This means that you don't need to manually manage references between documents. 
Additionally, Mongotoy provides flexibility in configuring reference behavior through the `mongotoy.reference()` 
function. With this function, you can customize how references are handled.

### Customization Parameters

The `mongotoy.reference()` function accepts the following parameters:

- **ref_field**: Name of the referenced field. Defaults to `id`
- **key_name**: Key name for the reference. Defaults to None.

/// note
If `key_name` isn't specified, Mongotoy automatically generates it by concatenating the name of the field that holds
the reference value with the name of the referenced field. In the example below, if `key_name` is not specified
explicitly, it will default to `parent_code`.
///

Here's an example that showcases the customization of references in Mongotoy documents. 

````python
import datetime
from mongotoy import Document, reference


class Person(Document):
    code: str
    name: str
    age: int
    dob: datetime.datetime
    parent: 'Person' = reference(ref_field='code', key_name='p_code')
````

The `parent` field in the `Person` document class serves as a reference to another `Person` document, 
denoting the individual's parent. Through the `mongotoy.reference()` function, the reference behavior is established
based on the `code` field of the referenced document. In the database, the reference key is labeled as `p_code`. 
This setup ensures that when a `Person` document is saved, the `code` value of the referenced `Person` document 
stored in the `parent` field is also stored in the current document under the `p_code` key.

/// danger
Utilizing `mongotoy.reference()` in a class that isn't derived from `mongotoy.Document`, or 
omitting `mongotoy.reference()` when using a `mongotoy.Document` based class as a 
[forwarded type](/gurcuff91/mongotoy/docs/data_types/#forwarding-types), will result in a
`mongotoy.errors.DocumentValidation` error during document instantiation.
///