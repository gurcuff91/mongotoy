
import base64
import re
from typing import TYPE_CHECKING, Type
import uuid
import bson
from mongotoy.errors import DocumentError, ErrorWrapper, MapperError, ValidationError

if TYPE_CHECKING:
    from mongotoy.documents import EmbeddedDocument


class Mapper:
    """
    Base class to define a data mapper.

    Data mappers provide three methods:
      - parse: parse and validate a value
      - dump: transform a value to dump it
      - dump_bson: transform a value to dump it as valid bson value
    """
    
    def parse(self, value, **options):
        return value
    
    def dump(self, value):
        return value    
    
    def dump_bson(self, value, **options):
        return value
    
    
class ListMapper(Mapper):
    
    def __init__(
        self,
        inner_mapper: Mapper,
        min_len: int = None,
        max_len: int = None
    ):
        if isinstance(inner_mapper, ListMapper):
            raise MapperError('ListMapper not support other ListMapper as inner_mapper')
        
        self._inner_mapper = inner_mapper
        self._min_len = min_len
        self._max_len = max_len
        
    @property
    def inner_mapper(self)-> Mapper:
        return self._inner_mapper
        
    def parse(self, value, **options):
        if not isinstance(value, list):
            raise TypeError(f'Invalid type {type(value)} required is {list}')

        value_len = len(value)
        if self._min_len is not None and value_len < self._min_len:
            raise ValueError(f'Invalid length {value_len}, min allowed is {self._min_len}')
        if self._max_len is not None and value_len > self._max_len:
            raise ValueError(f'Invalid length {value_len}, max allowed is {self._max_len}')
        
        # get validated values
        new_value = []
        for i, val in enumerate(value):
            try:
                new_value.append(
                    self.inner_mapper.parse(val, **options)
                )
            except ValidationError as e:
                raise ValidationError(
                    errors=[ErrorWrapper(loc=str(i), error=err) for err in e.errors]
                ) from None
            except Exception as e:
                raise ValidationError(
                    errors=[ErrorWrapper(loc=str(i), error=e)]
                ) from None

        return new_value
    
    def dump(self, value):
        return [self.inner_mapper.dump(val) for val in value]
    
    def dump_bson(self, value, **options):
        return [self.inner_mapper.dump_bson(val, **options) for val in value]
    
    
class EmbeddedDocumentMapper(Mapper):
    
    def __init__(self, document_cls: Type['EmbeddedDocument'] | str):
        self._document_cls = document_cls

    @property
    def document_cls(self) -> Type['EmbeddedDocument']:
        if isinstance(self._document_cls, str):
            from mongotoy.documents import _REGISTERED_DOCS
            doc_cls = _REGISTERED_DOCS.get(self._document_cls)
            if not doc_cls:
                raise DocumentError(f'Document {self._document_cls} not found or not declared yet')
            return doc_cls            
        return self._document_cls
    
    def parse(self, value, **options):
        strict = options['strict']
        
        # parse from dict
        if not strict:
            if isinstance(value, dict):
                value = self.document_cls.parse(value, **options)                
         # validate type
        if not isinstance(value, self.document_cls):
            raise TypeError(f'Invalid type, required {self.document_cls}, got {type(value)}')

        return value
    
    def dump_bson(self, value, **options):
        return value.dump_bson(**options)
    
    
class ObjectIdMapper(Mapper):
    
    def __init__(self, dump_str: bool = False):
        self._dump_str = dump_str
        
    def parse(self, value, **options):
        if not bson.ObjectId.is_valid(value):
            raise ValueError(f'Value {value} is not a valid ObjectId')
        return bson.ObjectId(value)
    
    def dump(self, value):
        if self._dump_str:
            return str(value)
        return value
    

class UUIDMapper(Mapper):
    
    def __init__(
        self,
        uuid_version: int = None,
        uuid_repr: int = bson.STANDARD,
        parse_str: bool = False,
        dump_str: bool = False,
        dump_bson_binary: bool = False,
    ):
        self._uuid_version = uuid_version
        self._uuid_repr = uuid_repr
        self._parse_str = parse_str
        self._dump_str = dump_str
        self._dump_bson_binary = dump_bson_binary
        
    def parse(self, value, **options):
        strict = options['strict']
        parse_bson = options['parse_bson']    
          
        if not strict:
            if isinstance(value, bson.Binary) and parse_bson:
                value = value.as_uuid(uuid_representation=self._uuid_repr)
            if isinstance(value, str) and self._parse_str:
                value = uuid.UUID(value)
                
        if not isinstance(value, uuid.UUID):
            raise TypeError(f'Invalid type {type(value)} required is {uuid.UUID}')
        if self._uuid_version is not None and value.version != self._uuid_version:
            raise ValueError(f'Invalid UUID version {value.version}, required is {self._uuid_version}')
        
        return value
    
    def dump(self, value):
        if self._dump_str:
            return str(value)
        return value
    
    def dump_bson(self, value, **options):
        if self._dump_bson_binary:
            return bson.Binary.from_uuid(value, uuid_representation=self._uuid_repr)
        return value
    
    
class StrMapper(Mapper):
    
    def __init__(
        self,
        min_len: int = None,
        max_len: int = None,
        choices: list[str] = None,
        regex: re.Pattern = None
    ):
        self._min_len = min_len
        self._max_len = max_len
        self._choices = choices
        self._regex = regex
        
    def parse(self, value, **options):
        if not isinstance(value, str):
            raise TypeError(f'Invalid type, required {str}, got {type(value)}')

        value_len = len(value)
        if self._min_len is not None and value_len < self._min_len:
            raise ValueError(f'Invalid length {value_len}, min is {self._min_len}')
        if self._max_len is not None and value_len > self._max_len:
            raise ValueError(f'Invalid length {value_len}, max is {self._max_len}')
        if self._choices and value not in self._choices:
            raise ValueError(f'Value {value} not belong to choices {self._choices}')
        if self._regex and not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} not match with regex {self._regex.pattern}')
        
        return value
    
    
class BinaryMapper(Mapper):
    
    def __init__(
        self,
        parse_base64: bool = False,
        dump_base64: bool = False
    ):
        self._parse_base64 = parse_base64
        self._dump_base64 = dump_base64
        
    def parse(self, value, **options):
        strict = options['strict']
        parse_bson = options['parse_bson']    
          
        if not strict:
            if isinstance(value, bson.Binary) and parse_bson:
                value = bytes(value)
            if isinstance(value, str) and self._parse_base64:
                value = base64.b64decode(value)
                
        if not isinstance(value, bytes):
            raise TypeError(f'Invalid type, required {bytes}, got {type(value)}')
        
        return value
    
    def dump(self, value):
        if self._dump_base64:
            return base64.b64encode(value).decode()
        return value