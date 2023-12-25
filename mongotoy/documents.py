
import abc
from collections import OrderedDict
from typing import TYPE_CHECKING, Any

import bson
import pymongo
from mongotoy import fields, mappers
from mongotoy.errors import DocumentError, DocumentValidationError, ValidationError
from mongotoy.fields import EmptyValue, FieldInfo


_REGISTERED_DOCS = OrderedDict()


class BaseDocMeta(abc.ABCMeta):
    """
    Metaclass for defining the behavior of classes derived from `BaseDoc`.
    This metaclass is responsible for combining fields from base classes and the current class,
    registering the document class, and ensuring unique document names.

    Args:
        name (str): Name of the class.
        bases (tuple): Tuple of base classes.
        namespace (dict): Dictionary containing the class attributes.
        **kwargs: Additional keyword arguments.

    Raises:
        DocumentError: If a document with the same name is already registered.
    """
        
    def __new__(mcls, name, bases, namespace, **kwargs):
        _cls = super().__new__(mcls, name, bases, namespace)
        
        # add base classes fields
        _fields = OrderedDict()
        for base in bases:
            _fields.update(getattr(base, '__fields__', {}))

        # add class namespace declared fields
        _fields.update({
            field.name: field
            for field in namespace.values()
            if isinstance(field, FieldInfo)
        })

        # set cls fields
        _cls.__fields__ = _fields
        
        # register document cls
        if name in _REGISTERED_DOCS:
            raise DocumentError(f'Document {name} already defined, please use a different name')
        _REGISTERED_DOCS[name] = _cls
        
        return _cls
    
    
class DocMeta(BaseDocMeta):
    """
    Metaclass for defining the behavior of classes derived from `Document` with additional document-specific features.

    Args:
        name (str): Name of the class.
        bases (tuple): Tuple of base classes.
        namespace (dict): Dictionary containing the class attributes.
        **kwargs: Additional keyword arguments.

    Raises:
        DocumentError: If no id field is declared or if multiple id fields are declared.
    """
    
    def __new__(mcls, name, bases, namespace, **kwargs):
        _cls = super().__new__(mcls, name, bases, namespace)
        
        # TODO prep config
        
        # check id field
        _id_fields = [field.name for field in _cls.__fields__.values() if field.id_field]
        if len(_id_fields) == 0:
            raise DocumentError(f'No id field declared into document {_cls}')
        if len(_id_fields) > 1:
            raise DocumentError(f'Too many id fields declared into document {_cls}.{_id_fields}') 
        
        return _cls
        
        
class BaseDoc(abc.ABC, metaclass=BaseDocMeta):
    """
    Base class for defining documents with fields in a structured manner.

    Attributes:
        __fields__ (dict): A dictionary to store field information.
        __data__ (dict): A dictionary to store document data.

    Methods:
        __init_instance__: Initializes an instance of the document with the given data.
        empty: Creates an empty instance of the document.
        parse: Parses a dictionary into a document instance.
        get_indexes: Retrieves a list of MongoDB index models based on document fields.
        dump_bson: Dumps the document data into a BSON format.

    Args:
        **data: Keyword arguments for initializing document data.

    Raises:
        DocumentValidationError: If there are validation errors during document initialization.
    """
    if TYPE_CHECKING:
        __fields__: dict[str, FieldInfo]
        __data__: dict[str, Any]

    def __init__(self, **data): 
        self.__init_instance__(self, data)
        
    @classmethod
    def __init_instance__(
        cls,
        instance,
        data,
        use_defaults: bool = True,
        strict: bool = True,
        parse_bson: bool = False,
        **options
    ):
        """
        Initializes an instance of the document with the given data.

        Args:        
            instance: The document instance to initialize.
            data: Data to parse into the document.
            use_defaults: If True, uses default values for missing fields.
            strict: If True, raises errors for unknown data types.
            parse_bson: If True, parses BSON data.

        Raises:
            DocumentValidationError: If there are validation errors during document initialization.
        """
        instance.__data__ = {}
        errors = []
        for field in cls.__fields__.values():
            try:
                value = data.get(field.alias, data.get(field.name, EmptyValue))
                field.__set__(
                    instance,
                    value=value,
                    use_defaults=use_defaults,
                    strict=strict,
                    parse_bson=parse_bson,
                    **options
                )
            except ValidationError as err:
                errors.append(err)

        if errors:
            raise DocumentValidationError(
                errors=errors,
                document_cls=cls,
            )

    @classmethod
    def empty(cls, use_defaults: bool = False) -> 'BaseDoc':
        """
        Creates an empty instance of the document.

        Args:
            use_defaults: If True, uses default values for fields.

        Returns:
            BaseDoc: An empty instance of the document.
        """
        instance = cls.__new__(cls)
        cls.__init_instance__(instance, data={}, use_defaults=use_defaults)
        return instance
    
    @classmethod
    def parse(
        cls,
        data: dict,
        use_defaults: bool = True,
        strict: bool = True,
        parse_bson: bool = False,
        **options
    ) -> 'BaseDoc':
        """
        Parses data into a document instance.

        Args:
            data: Data to parse into the document.
            use_defaults: If True, uses default values for missing fields.
            strict: If True, raises errors for unknown data types.
            parse_bson: If True, parses BSON data.

        Returns:
            BaseDoc: A document instance.
        """
        instance = cls.__new__(cls)
        cls.__init_instance__(
            instance,
            data=data,
            use_defaults=use_defaults,
            strict=strict,
            parse_bson=parse_bson,
            **options
        )
        return instance 
    
    @classmethod
    def get_indexes(cls) -> list[pymongo.IndexModel]:
        """
        Retrieves a list of MongoDB index models based on document fields.

        Returns:
            list: A list of pymongo.IndexModel instances.
        """
        indexes = []

        # add field indexes
        for field in cls.__fields__.values():
            field_index = field.get_index()
            if field_index:
                indexes.append(field_index)

            # unwrap list mapper
            field_mapper = field.mapper
            if isinstance(field_mapper, mappers.ListMapper):
                field_mapper = field_mapper.inner_mapper

            # add EmbeddedDocumentMapper indexes
            if isinstance(field_mapper, mappers.EmbeddedDocumentMapper):
                embedded_doc_cls = field_mapper.document_cls
                for index in embedded_doc_cls.get_indexes():
                    index_doc = index.document
                    index_keys = index_doc.pop('key')
                    index_new_keys = []
                    for index_key, index_type in index_keys.items():
                        index_new_keys.append((f'{field.alias}.{index_key}', index_type))
                    indexes.append(pymongo.IndexModel(index_new_keys, **index_doc))

            # TODO add Geo indexes
            # if isinstance(field_mapper, mappers.GeoDataMapper):
            #     geo_type = field_mapper.geo_type
            #     if geo_type in (
            #             GeoDataType.MULTI_POINT,
            #             GeoDataType.MULTI_LINESTRING,
            #             GeoDataType.MULTI_POLYGON,
            #             GeoDataType.GEOMETRY_COLLECTION
            #     ):
            #         indexes.append(
            #             pymongo.IndexModel([(field.alias, pymongo.GEOSPHERE)])
            #         )

        return indexes
    
    def __getitem__(self, key):
        """
        Gets the value of a field by key.

        Args:
            key: The key (field name or alias) to retrieve.

        Returns:
            Any: The value of the field.

        Raises:
            DocumentError: If the field is not found or not declared.
        """
        field = self.__fields__.get(key)
        if not field:
            raise DocumentError(f'Field {key} not found or not declared yet')
        return field.__get__(self, self.__class__)
    
    def __setitem__(self, key, item):
        """
        Sets the value of a field by key.

        Args:
            key: The key (field name or alias) to set.
            item: The value to set.

        Raises:
            DocumentError: If the field is not found or not declared.
        """
        field = self.__fields__.get(key)
        if not field:
            raise DocumentError(f'Field {key} not found or not declared yet')
        field.__set__(self, item)
    
    def __delitem__(self, key):
        """
        Deletes the value of a field by key.

        Args:
            key: The key (field name or alias) to delete.

        Raises:
            DocumentError: If the field is not found or not declared.
        """
        field = self.__fields__.get(key)
        if not field:
            raise DocumentError(f'Field {key} not found or not declared yet')
        field.__delete__(self)
    
    def dump_bson(self, by_alias: bool = True) -> bson.SON:
        """
        Dumps the document data into a BSON format.

        Args:
            by_alias: If True, uses field aliases as keys.

        Returns:
            bson.SON: A BSON document.
        """
        data = {}
        for field in self.__fields__.values():
            key = field.alias if by_alias else field.name
            value = self.__data__.get(field.name, EmptyValue)
            if value not in (EmptyValue, None):
                data[key] = field.mapper.dump_bson(value, by_alias=by_alias) if value is not None else value
            
        return bson.SON(data)        
    
    
class EmbeddedDocument(BaseDoc):
    """
    Base class for defining embedded documents within other documents.

    Example:
        ```python
        class Address(EmbeddedDocument):
            street = StringField()
            city = StringField()
            zip_code = StringField()
        ```

    Inherited Attributes:
        __fields__ (dict): A dictionary to store field information.
        __data__ (dict): A dictionary to store document data.
    """
    pass

class Document(BaseDoc, metaclass=DocMeta):
    """
    Base class for defining top-level documents with MongoDB-specific configuration.

    Example:
        ```python
        class MyDocument(Document):
            field1 = StringField()
            field2 = IntField()
        ```

    Inherited Attributes:
        __fields__ (dict): A dictionary to store field information.
        __data__ (dict): A dictionary to store document data.

    Metaclass Attributes:
        document_config (dict): MongoDB-specific configuration for the document.

    Attributes:
        id (ObjectId): An ObjectId field for the document ID with default settings.
    """
    if TYPE_CHECKING:
        document_config: dict

    id = fields.ObjectIdField(id_field=True, default_factory=lambda: bson.ObjectId())
        
