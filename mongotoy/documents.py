
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
            raise DocumentError(f'Document {name} already defined, please user diferent name')
        _REGISTERED_DOCS[name] = _cls
        
        return _cls
    
    
class DocMeta(BaseDocMeta):
    
    def __new__(mcls, name, bases, namespace, **kwargs):
        _cls = super().__new__(mcls, name, bases, namespace)
        
        # TODO prep config
        
        # check id field
        _id_fields = [field.name for field in _cls.__fields__.values() if field.id_field]
        if len(_id_fields) == 0:
            raise DocumentError(f'No id field declared into document {_cls}')
        if len(_id_fields) > 1:
            raise DocumentError(f'To many id fields declared into document {_cls}.{_id_fields}') 
        
        return _cls
        
        
class BaseDoc(abc.ABC, metaclass=BaseDocMeta):
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
    
    def dump_bson(self, by_alias: bool = True) -> bson.SON:
        data = {}
        for field in self.__fields__.values():
            key = field.alias if by_alias else field.name
            value = self.__data__.get(field.name, EmptyValue)
            if value not in (EmptyValue, None):
                data[key] = field.mapper.dump_bson(value, by_alias=by_alias) if value is not None else value
            
        return bson.SON(data)        
    
    
class EmbeddedDocument(BaseDoc):
    pass


class Document(BaseDoc, metaclass=DocMeta):
    if TYPE_CHECKING:
        document_config: dict
        
    id = fields.ObjectIdField(id_field=True, default_factory=lambda: bson.ObjectId())
        
