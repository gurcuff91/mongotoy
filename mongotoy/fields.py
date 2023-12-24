
import inspect
import re
from typing import Any, Callable, Literal, Type, TYPE_CHECKING
import bson
import pymongo
from mongotoy import mappers
from mongotoy.errors import ErrorWrapper, ValidationError
from mongotoy.mappers import Mapper

if TYPE_CHECKING:
    from mongotoy.documents import EmbeddedDocument


EmptyValue = type('Empty', (), {'__repr__': lambda _: 'Empty()'})()
IndexType = Literal[-1, 1, '2d', '2dsphere', 'hashed', 'text']


class FieldInfo:
    
    def __init__(
        self,
        mapper: Mapper,
        alias: str = None,
        id_field: bool = False,
        nullable: bool = True,
        default: Any = EmptyValue,
        default_factory: Callable[[], Any] = None,        
        index: IndexType = None,
        unique: bool = False,
        unique_with: str | list[str] = None,
        sparse: bool = False,
        timeseries_field: bool = False,
        timeseries_meta_field: bool = False,
    ):
        # change props when is id_field
        if id_field:
            alias = '_id'
            nullable = False
            
        # ensure default_factory is not null
        if not default_factory:
            def default_factory():
                return default
            
        # ensure unique_with as list and enable unique index
        if unique_with:
            unique = True
            unique_with = unique_with if isinstance(unique_with, list) else [unique_with]
            
        self._owner = None
        self._name = None
        self._mapper = mapper
        self._alias = alias
        self._id_field = id_field
        self._nullable = nullable
        self._default_factory = default_factory
        self._index = index
        self._unique = unique
        self._unique_with = unique_with
        self._sparse = sparse
        self.timeseries_field = timeseries_field
        self.timeseries_meta_field = timeseries_meta_field
        
    @property
    def mapper(self) -> Mapper:
        return self._mapper    
        
    @property
    def name(self) -> str:
        return self._name    
    
    @property
    def alias(self) -> str:
        return self._alias or self._name  
    
    @property
    def id_field(self) -> bool:
        return self._id_field    
    
    def __set_name__(self, owner, name):
        self._owner = owner
        self._name = name
    
    def __get__(self, instance, owner):
        if not instance:
            pass  # TODO impl FieldProxy
        value = instance.__data__.get(self.name, EmptyValue)
        if value is not EmptyValue:
            return self.mapper.dump(value)
        return EmptyValue        
    
    def __set__(self, instance, value, **options):
        value = self.parse(value, instance=instance, **options)
        if value is not EmptyValue:
            instance.__data__[self.name] = value
    
    def __delete__(self, instance):
         instance.__data__.pop(self.name, None)  
    
    def get_index(self) -> pymongo.IndexModel | None:
        index = {}
        if self._unique or self._sparse:
            index[self.alias] = pymongo.ASCENDING
        if self._index is not None:
            index[self.alias] = self._index
        if self._unique_with:
            for key in self._unique_with:
                index[key] = pymongo.ASCENDING
        if index:
            return pymongo.IndexModel(
                [(field, idx) for field, idx in index.items()],
                unique=self._unique,
                sparse=self._sparse
            )
    
    def parse(self, value, **options):
        use_defaults = options['use_defaults']

        # use default if value is empty
        if value is EmptyValue and use_defaults:
            value = self._default_factory()

        # return an empty value
        if value is EmptyValue:
            return value

        # check nullability
        if value is None:
            if not self._nullable:
                raise ValueError('Null value not allowed')
            else:
                return value
        
        # add field level options
        options['owner'] = self._owner            
        options['field_info'] = self          
        
        try:
            # mapper parsing
            value = self.mapper.parse(value, **options)
            
            # owner instance validator
            validator = getattr(options['instance'], f'validate_{self.name}', None)
            if validator and inspect.ismethod(validator):
                validator(value)
            
        except  ValidationError as e:
            raise ValidationError(
                errors=[ErrorWrapper(loc=self.name, error=err) for err in e.errors]
            ) from None
        except Exception as e:
            raise ValidationError(
                errors=[ErrorWrapper(loc=self.name, error=e)]
            ) from None
            
        return value 
    
    
def ListField(
    inner_field: FieldInfo,    
    alias: str = None,
    nullable: bool = True,
    default: Any = None,
    default_factory: Callable[[], Any] = None,  
    index: IndexType = None,     
    unique: bool = False,         
    unique_with: str | list[str] = None,
    sparse: bool = False,
    min_len: int = None,
    max_len: int = None
) -> FieldInfo:
    return FieldInfo(
        mapper=mappers.ListMapper(
            inner_mapper=inner_field.mapper,
            min_len=min_len,
            max_len=max_len
        ),
        alias=alias,
        nullable=nullable,
        default=default,
        default_factory=default_factory,
        index=index,
        unique=unique,
        unique_with=unique_with,
        sparse=sparse
    )        
 
def EmbeddedDocumentField(
    document_cls: Type['EmbeddedDocument'] | str,    
    alias: str = None,
    nullable: bool = True,
    default: Any = None,
    default_factory: Callable[[], Any] = None,  
    index: IndexType = None,     
    unique: bool = False,         
    unique_with: str | list[str] = None,
    sparse: bool = False,
    timeseries_meta_field: bool = False
) -> FieldInfo:
    return FieldInfo(
        mapper=mappers.EmbeddedDocumentMapper(
            document_cls=document_cls
        ),
        alias=alias,
        nullable=nullable,
        default=default,
        default_factory=default_factory,
        index=index,
        unique=unique,
        unique_with=unique_with,
        sparse=sparse,
        timeseries_meta_field=timeseries_meta_field
    ) 
    
def ObjectIdField(    
    alias: str = None,
    id_field: bool = False,
    nullable: bool = True,
    default: Any = None,
    default_factory: Callable[[], Any] = None,        
    index: IndexType = None,
    unique: bool = False,
    unique_with: str | list[str] = None,
    sparse: bool = False,
    dump_str: bool = False
) -> FieldInfo:
    return FieldInfo(
        mapper=mappers.ObjectIdMapper(
            dump_str==dump_str
        ),
        alias=alias,
        id_field=id_field,
        nullable=nullable,
        default=default,
        default_factory=default_factory,
        index=index,
        unique=unique,
        unique_with=unique_with,
        sparse=sparse
    )
    
def UUIDField(    
    alias: str = None,
    id_field: bool = False,
    nullable: bool = True,
    default: Any = None,
    default_factory: Callable[[], Any] = None,        
    index: IndexType = None,
    unique: bool = False,
    unique_with: str | list[str] = None,
    sparse: bool = False,
    uuid_version: int = None,
    uuid_repr: int = bson.STANDARD,
    parse_str: bool = False,
    dump_str: bool = False,
    dump_bson_binary: bool = False,
) -> FieldInfo:
    return FieldInfo(
        mapper=mappers.UUIDMapper(
            uuid_version=uuid_version,
            uuid_repr=uuid_repr,
            parse_str=parse_str,
            dump_str=dump_str,
            dump_bson_binary=dump_bson_binary
        ),
        alias=alias,
        id_field=id_field,
        nullable=nullable,
        default=default,
        default_factory=default_factory,
        index=index,
        unique=unique,
        unique_with=unique_with,
        sparse=sparse
    )    
    
def StrField(    
    alias: str = None,
    id_field: bool = False,
    nullable: bool = True,
    default: Any = None,
    default_factory: Callable[[], Any] = None,        
    index: IndexType = None,
    unique: bool = False,
    unique_with: str | list[str] = None,
    sparse: bool = False,
    min_len: int = None,
    max_len: int = None,
    choices: list[str] = None,
    regex: re.Pattern = None
) -> FieldInfo:
    return FieldInfo(
        mapper=mappers.StrMapper(
            min_len=min_len,
            max_len=max_len,
            choices=choices,
            regex=regex
        ),
        alias=alias,
        id_field=id_field,
        nullable=nullable,
        default=default,
        default_factory=default_factory,
        index=index,
        unique=unique,
        unique_with=unique_with,
        sparse=sparse
    )
    
def BinaryField(    
    alias: str = None,
    id_field: bool = False,
    nullable: bool = True,
    default: Any = None,
    default_factory: Callable[[], Any] = None,        
    index: IndexType = None,
    unique: bool = False,
    unique_with: str | list[str] = None,
    sparse: bool = False,
    parse_base64: bool = False,
    dump_base64: bool = False
) -> FieldInfo:
    return FieldInfo(
        mapper=mappers.BinaryMapper(
            parse_base64=parse_base64,
            dump_base64=dump_base64
        ),
        alias=alias,
        id_field=id_field,
        nullable=nullable,
        default=default,
        default_factory=default_factory,
        index=index,
        unique=unique,
        unique_with=unique_with,
        sparse=sparse
    )
            