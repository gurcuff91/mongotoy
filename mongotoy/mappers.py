
import base64
import datetime
import decimal
import re
from typing import TYPE_CHECKING, Type
import uuid
import bson
from mongotoy.documents import EmbeddedDocument
from mongotoy.errors import DocumentError, ErrorWrapper, MapperError, ValidationError

if TYPE_CHECKING:
    from mongotoy.documents import EmbeddedDocument, Document
    from mongotoy.fields import FieldInfo


class Mapper:
    """
    Base class for defining a data mapper.

    Data mappers perform three main functions:
        - parse: Parses and validates a given value.
        - dump: Transforms a value for display purposes.
        - dump_bson: Transforms a value for storage as a valid BSON value.

    These functions can be overridden in derived classes for custom behavior.
    """
    
    def parse(self, value, **options):
        """
        Parse and validate the given value.

        Args:
            value: The value to be parsed.
            **options: Additional options for parsing.

        Returns:
            The parsed and validated value.
        """
        return value
    
    def dump(self, value):
        """
        Transform the given value for display purposes.

        Args:
            value: The value to be transformed.

        Returns:
            The transformed value for display.
        """
        return value    
    
    def dump_bson(self, value, **options):
        """
        Transform the given value for storage as a valid BSON value.

        Args:
            value: The value to be transformed.
            **options: Additional options for dumping as BSON.

        Returns:
            The transformed value suitable for BSON serialization and storage.
        """
        return value    
    
    
class ListMapper(Mapper):
    """
    Mapper for handling lists of elements with a specific type.

    ListMapper provides functionality for parsing, transforming, and storing lists of elements.

    Args:
        - inner_mapper (Mapper):
            The inner mapper responsible for mapping individual elements in the list.
        - min_len (int, optional):
            Minimum length: The minimum length constraint for the mapped list.
        - max_len (int, optional):
            Maximum length: The maximum length constraint for the mapped list.

    Example:
        ```python
        inner_mapper = IntMapper(gt=0, lt=10)
        list_mapper = ListMapper(inner_mapper=inner_mapper, min_len=2, max_len=5)
        ```

        In this example, `list_mapper` is configured to handle a list of integers where each element
        should be greater than 0 and less than 10. The list length should be between 2 and 5.
        ```
    """
    
    def __init__(
        self,
        inner_mapper: Mapper,
        min_len=None,
        max_len=None
    ):
        if isinstance(inner_mapper, ListMapper):
            raise MapperError('ListMapper does not support another ListMapper as inner_mapper')
        
        self._inner_mapper = inner_mapper
        self._min_len = min_len
        self._max_len = max_len
        
    @property
    def inner_mapper(self):
        """
        Get the inner mapper responsible for mapping individual elements.

        Returns:
            Mapper: The inner mapper.
        """
        return self._inner_mapper
        
    def parse(self, value, **options):
        """
        Parse and validate the given list of elements.

        Returns:
            List: The parsed and validated list of elements.

        Raises:
            TypeError: If the input is not a list.
            ValueError: If the length of the list violates constraints.
            ValidationError: If there are parsing errors within the list elements.
        """
        if not isinstance(value, list):
            raise TypeError(f'Invalid type {type(value)}, required type is {list}')

        value_len = len(value)
        if self._min_len is not None and value_len < self._min_len:
            raise ValueError(f'Invalid length {value_len}, min allowed is {self._min_len}')
        if self._max_len is not None and value_len > self._max_len:
            raise ValueError(f'Invalid length {value_len}, max allowed is {self._max_len}')
        
        # Get validated values
        new_value = []
        for i, val in enumerate(value):
            try:
                new_value.append(self.inner_mapper.parse(val, **options))
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
        """
        Transform the given list of elements for display purposes.

        Returns:
            List: The transformed list of elements for display.
        """
        return [self.inner_mapper.dump(val) for val in value]
    
    def dump_bson(self, value, **options):
        """
        Transform the given list of elements for storage as a valid BSON value.

        Returns:
            List: The transformed list of elements suitable for BSON serialization and storage.
        """
        return [self.inner_mapper.dump_bson(val, **options) for val in value]
    
    
class EmbeddedDocumentMapper(Mapper):
    """
    Mapper for handling data associated with embedded documents.

    Args:
        - document_cls (Type['EmbeddedDocument']):
            The type of embedded document or the name of the embedded document class.
            
    Example:
        ```python
        class Address(EmbeddedDocument):
            street: str
            city: str
            zip_code: str

        # Creating an EmbeddedDocumentMapper for the Address class
        address_mapper = EmbeddedDocumentMapper(document_cls=Address)
        
        # Creating an EmbeddedDocumentMapper using the class name
        address_mapper = EmbeddedDocumentMapper(document_cls="Address")
        ```
    """
    
    def __init__(self, document_cls: Type['EmbeddedDocument'] | str):
        self._document_cls = document_cls

    @property
    def document_cls(self) -> Type['EmbeddedDocument']:
        """
        Get the embedded document class associated with the mapper.

        Returns:
            Type['EmbeddedDocument']: The embedded document class.
        
        Raises:
            DocumentError: If the document class is not found or not declared.
        """
        if isinstance(self._document_cls, str):
            from mongotoy.documents import _REGISTERED_DOCS
            doc_cls = _REGISTERED_DOCS.get(self._document_cls)
            if not doc_cls:
                raise MapperError(f'Document {self._document_cls} not found or not declared yet')
            return doc_cls            
        return self._document_cls
    
    def parse(self, value, **options):
        """
        Parse and validate the given value, ensuring it matches the embedded document type.

        Args:
            value: The value to be parsed.
            **options: Additional options for parsing.

        Returns:
            Type['EmbeddedDocument']: The parsed and validated embedded document.

        Raises:
            TypeError: If the value is not an instance of the expected embedded document type.
        """
        strict = options['strict']
        
        # Parse from dict if not in strict mode
        if not strict and isinstance(value, dict):
            value = self.document_cls.parse(value, **options)

        # Validate type
        if not isinstance(value, self.document_cls):
            raise TypeError(f'Invalid type, required {self.document_cls}, got {type(value)}')

        return value
    
    def dump_bson(self, value, **options):
        """
        Transform the given embedded document for storage as a valid BSON value.

        Args:
            value: The embedded document to be transformed.
            **options: Additional options for dumping as BSON.

        Returns:
            bson.Document: The transformed BSON document.
        """
        return value.dump_bson(**options)
    
    
class ReferencedDocumentMapper(EmbeddedDocumentMapper):
    """
    Mapper for handling references to documents stored in other collections.

    Args:
        - key_name (str): The name of the field storing the reference value in the collection that holds relation.
        - document_cls (type['Document'] | str): The type of the referenced document or the name of the document class.
        - ref (str): The name of the field in the referenced document containing the reference value.
        - back_ref (str): The name of the field in the referenced document containing the back reference.

    Raises:
        MapperError: If both ref and back_ref are not defined, or if both are defined.

    Example:
        ```python
        class User(Document):
            id: ObjectId
            name: str

        class Book(Document):
            title: str
            author_id: ObjectId  # Here, 'author_id' is the key_name for referencing the User document

        class AuthorReferenceMapper(DocumentReferenceMapper):
            def __init__(self):
                super().__init__(key_name='author_id', document_cls=User, ref='id')

        # Creating a DocumentReferenceMapper for referencing authors in the Book document
        author_ref_mapper = AuthorReferenceMapper()
        ```

    Properties:
        - is_back_ref (bool): Indicates whether the mapper represents a back reference.
        - ref (FieldInfo): The field information for the reference field.
        - back_ref (FieldInfo): The field information for the back reference field.
    """

    def __init__(
        self,
        key_name: str,
        document_cls: type['Document'] | str,
        ref: str = None,
        back_ref: str = None
    ):
        # Ensure that either ref or back_ref is defined, but not both
        if (not ref and not back_ref) or (ref and back_ref):
            raise MapperError('DocumentReferenceMapper must define either ref or back_ref')

        # Call the constructor of the parent class (EmbeddedDocumentMapper)
        super().__init__(document_cls=document_cls)

        # Initialize attributes specific to DocumentReferenceMapper
        self._key_name = key_name
        self._ref = ref
        self._back_ref = back_ref

    @property
    def is_back_ref(self) -> bool:
        """
        Check if the mapper represents a back reference.

        Returns:
            bool: True if the mapper represents a back reference, False otherwise.
        """
        return bool(self._back_ref)

    @property
    def ref(self) -> 'FieldInfo':
        """
        Get the field information for the reference field.

        Returns:
            FieldInfo: The field information for the reference field.

        Raises:
            MapperError: If ref is not defined or the field is not found in the referenced document.
        """
        if not self._ref:
            raise MapperError('DocumentReferenceMapper does not define ref')

        ref_field = self.document_cls.__fields__.get(self._ref)
        if not ref_field:
            raise MapperError(
                f'Field {self._document_cls.__class__.__name__}.{self._ref} not found or not declared yet'
            )

        return ref_field

    @property
    def back_ref(self) -> 'FieldInfo':
        """
        Get the field information for the back reference field.

        Returns:
            FieldInfo: The field information for the back reference field.

        Raises:
            MapperError: If back_ref is not defined or the reference field is not found in the referenced document.
        """
        if not self._back_ref:
            raise MapperError('DocumentReferenceMapper does not define back_ref')

        back_ref_field = self.document_cls.__fields__.get(self._back_ref)
        if not back_ref_field:
            raise MapperError(
                f'Reference field {self._document_cls.__class__.__name__}.{self._back_ref} not found or not declared yet'
            )

        return back_ref_field

    def dump_bson(self, value, **options):
        """
        Transform the given reference document for storage as a valid BSON value.

        Args:
            value: The reference document to be transformed.
            **options: Additional options for dumping as BSON.

        Returns:
            bson.Document or mongotoy.fields.EmptyValue: The transformed BSON document or EmptyValue.
        """
        from mongotoy.fields import EmptyValue

        if not self.is_back_ref:
            return value[self.ref.name]

        return EmptyValue
    
    
class ObjectIdMapper(Mapper):
    """
    Mapper for handling ObjectId data.

    Args:
        - dump_str (bool): Flag to indicate whether the value should be dumped to a string.

    Example:
        ```python
        # Creating an ObjectIdMapper that dumps ObjectId as strings
        string_id_mapper = ObjectIdMapper(dump_str=True)

        # Parsing a string value into ObjectId
        parsed_object_id = string_id_mapper.parse("615fc7a5b27d692db1bb9437")

        # Dumping ObjectId as a string
        dumped_value = string_id_mapper.dump(parsed_object_id)
        ```
    """
    
    def __init__(self, dump_str: bool = False):
        self._dump_str = dump_str
        
    def parse(self, value, **options):
        """
        Parse and validate the given value as an ObjectId.

        Args:
            value: The value to be parsed.
            **options: Additional options for parsing.

        Returns:
            bson.ObjectId: The parsed and validated ObjectId.

        Raises:
            ValueError: If the value is not a valid ObjectId.
        """
        if not bson.ObjectId.is_valid(value):
            raise ValueError(f'Value {value} is not a valid ObjectId')
        return bson.ObjectId(value)
    
    def dump(self, value):
        """
        Transform the given ObjectId value for display purposes.

        Args:
            value: The ObjectId value to be transformed.

        Returns:
            str or bson.ObjectId: The transformed value based on the dump_str flag.
        """
        if self._dump_str:
            return str(value)
        return value
    

class UUIDMapper(Mapper):
    """
    Mapper for handling UUID data.

    Args:
        - uuid_version (int): UUID version. The version of the UUID, if applicable.
        - uuid_repr (int): UUID representation. The representation format for UUID.
        - parse_str (bool): Flag to indicate whether the value should be parsed from a string.
        - dump_str (bool): Flag to indicate whether the value should be dumped to a string.
        - dump_bson_binary (bool): Flag to indicate whether the value should be dumped to BSON binary.

    Example:
        ```python
        # Creating a UUIDMapper with specific options
        uuid_mapper = UUIDMapper(uuid_version=4, uuid_repr=bson.STANDARD, parse_str=True, dump_str=True)

        # Parsing a UUID from a string
        parsed_uuid = uuid_mapper.parse('550e8400-e29b-41d4-a716-446655440000')

        # Dumping the parsed UUID for display as a string
        dumped_value = uuid_mapper.dump(parsed_uuid)
        ```
    """
    
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
        """
        Parse and validate the given value as a UUID.

        Args:
            value: The value to be parsed.
            **options: Additional options for parsing.

        Returns:
            uuid.UUID: The parsed and validated UUID.

        Raises:
            TypeError: If the value is not an instance of the expected UUID type.
            ValueError: If the UUID version is invalid.
        """
        strict = options['strict']
        parse_bson = options['parse_bson']    
          
        # Parse from BSON binary if not in strict mode
        if not strict:
            if isinstance(value, bson.Binary) and parse_bson:
                value = value.as_uuid(uuid_representation=self._uuid_repr)
            # Parse from string if not in strict mode
            if isinstance(value, str) and self._parse_str:
                value = uuid.UUID(value)
                
        # Validate type
        if not isinstance(value, uuid.UUID):
            raise TypeError(f'Invalid type {type(value)}, required is {uuid.UUID}')
        # Validate UUID version
        if self._uuid_version is not None and value.version != self._uuid_version:
            raise ValueError(f'Invalid UUID version {value.version}, required is {self._uuid_version}')
        
        return value
    
    def dump(self, value):
        """
        Transform the given UUID value for display purposes.

        Args:
            value: The UUID value to be transformed.

        Returns:
            str or uuid.UUID: The transformed value based on the dump_str flag.
        """
        if self._dump_str:
            return str(value)
        return value
    
    def dump_bson(self, value, **options):
        """
        Transform the given UUID value for storage as BSON binary or uuid.

        Args:
            value: The UUID value to be transformed.
            **options: Additional options for dumping.

        Returns:
            bson.Binary or uuid.UUID: The transformed value based on the dump_bson_binary flag.
        """
        if self._dump_bson_binary:
            return bson.Binary.from_uuid(value, uuid_representation=self._uuid_repr)
        return value
    
    
class BinaryMapper(Mapper):
    """
    Mapper for handling binary data.

    Args:
        - parse_base64 (bool): Flag to indicate whether the value should be parsed from base64 data.
        - dump_base64 (bool): Flag to indicate whether the value should be dumped to base64 data.

    Example:
        ```python
        # Creating a BinaryMapper with specific options
        binary_mapper = BinaryMapper(parse_base64=True, dump_base64=True)

        # Parsing binary data from a base64-encoded string
        parsed_binary = binary_mapper.parse('SGVsbG8gd29ybGQh')

        # Dumping the parsed binary data for display as a base64-encoded string
        dumped_value = binary_mapper.dump(parsed_binary)
        ```
    """
    
    def __init__(
        self,
        parse_base64: bool = False,
        dump_base64: bool = False
    ):
        self._parse_base64 = parse_base64
        self._dump_base64 = dump_base64
        
    def parse(self, value, **options):
        """
        Parse and validate the given value as binary data.

        Args:
            value: The value to be parsed.
            **options: Additional options for parsing.

        Returns:
            bytes: The parsed and validated binary data.

        Raises:
            TypeError: If the value is not an instance of the expected bytes type.
        """
        strict = options['strict']
        parse_bson = options['parse_bson']    
          
        # Parse from BSON binary if not in strict mode
        if not strict:
            if isinstance(value, bson.Binary) and parse_bson:
                value = bytes(value)
            # Parse from base64 string if not in strict mode
            if isinstance(value, str) and self._parse_base64:
                value = base64.b64decode(value)
                
        # Validate type
        if not isinstance(value, bytes):
            raise TypeError(f'Invalid type, required {bytes}, got {type(value)}')
        
        return value
    
    def dump(self, value):
        """
        Transform the given binary data for display purposes.

        Args:
            value: The binary data to be transformed.

        Returns:
            str or bytes: The transformed value based on the dump_base64 flag.
        """
        if self._dump_base64:
            return base64.b64encode(value).decode()
        return value
    
    
class StrMapper(Mapper):
    """
    Mapper for handling string data.

    Args:
        - min_len (int): Minimum length. The minimum length of the value.
        - max_len (int): Maximum length. The maximum length of the value.
        - choices (list[str]): Choices. A list of valid choices for the value.
        - regex (re.Pattern): Regular expression. A regular expression pattern for validation.

    Example:
        ```python
        # Creating a StrMapper with specific options
        str_mapper = StrMapper(min_len=3, max_len=10, choices=['apple', 'banana'], regex=re.compile(r'^[a-zA-Z]+$'))

        # Parsing and validating a string value
        parsed_value = str_mapper.parse('apple')

        # Example of raising ValueError due to length constraint violation
        try:
            invalid_value = str_mapper.parse('kiwi')
        except ValueError as ve:
            print(ve)
        ```
    """
    
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
        """
        Parse and validate the given value as a string.

        Args:
            value: The value to be parsed.
            **options: Additional options for parsing.

        Returns:
            str: The parsed and validated string value.

        Raises:
            TypeError: If the value is not an instance of the expected str type.
            ValueError: If the length is invalid, the value is not in choices, or it does not match the regex pattern.
        """
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
       
    
class IntMapper(Mapper):
    """
    Mapper for handling integer data.

    Args:
        - gt (int): Greater than. The value should be greater than this.
        - gte (int): Greater than or equal to. The value should be greater than or equal to this.
        - lt (int): Less than. The value should be less than this.
        - lte (int): Less than or equal to. The value should be less than or equal to this.
        - mul (int): Multiple of. The value should be a multiple of this.
        - parse_hex (bool): Flag to indicate whether the value should be parsed from hexadecimal data.
        - dump_hex (bool): Flag to indicate whether the value should be dumped to hexadecimal data.
        - dump_bson_int64 (bool): Flag to indicate whether the value should be dumped to BSON int64.

    Example:
        ```python
        # Creating an IntMapper with specific options
        int_mapper = IntMapper(gt=0, lt=100, mul=5, parse_hex=True, dump_hex=True, dump_bson_int64=True)

        # Parsing and validating an integer value
        parsed_value = int_mapper.parse('0x1A', strict=False)

        # Example of raising ValueError due to value being less than the specified minimum
        try:
            invalid_value = int_mapper.parse(-5)
        except ValueError as ve:
            print(ve)
        ```
    """
    
    def __init__(
        self,        
        gt: int = None,
        gte: int = None,
        lt: int = None,
        lte: int = None,
        mul: int = None,
        parse_hex: bool = False,
        dump_hex: bool = False,
        dump_bson_int64: bool = False
    ):
        self._gt = gt
        self._gte = gte
        self._lt = lt
        self._lte = lte
        self._mul = mul
        self._parse_hex = parse_hex
        self._dump_hex = dump_hex
        self._dump_bson_int64 = dump_bson_int64
        
    def parse(self, value, **options):
        """
        Parse and validate the given value as an integer.

        Args:
            value: The value to be parsed.
            **options: Additional options for parsing.

        Returns:
            int: The parsed and validated integer value.

        Raises:
            TypeError: If the value is not an instance of the expected int type.
            ValueError: If the value violates the specified constraints.
        """
        strict = options['strict']
        parse_bson = options['parse_bson']    
          
        # Parse from BSON int64 if not in strict mode
        if not strict:
            if isinstance(value, bson.Int64) and parse_bson:
                value = int(value)
            # Parse from hexadecimal if not in strict mode
            if isinstance(value, str) and self._parse_hex:
                value = int(value, 16)
            # Parse from string if not in strict mode
            elif isinstance(value, str):
                value = int(value)
                
        # Validate type
        if not isinstance(value, int):
            raise TypeError(f'Invalid type, required {int}, got {type(value)}')
        
        # Validate constraints
        if self._gt is not None and value <= self._gt:
            raise ValueError(f'Value {value} is not greater than {self._gt}')
        if self._gte is not None and value < self._gte:
            raise ValueError(f'Value {value} is not greater than or equal to {self._gte}')
        if self._lt is not None and value >= self._lt:
            raise ValueError(f'Value {value} is not less than {self._lt}')
        if self._lte is not None and value > self._lte:
            raise ValueError(f'Value {value} is not less than or equal to {self._lte}')        
        if self._mul is not None and value % self._mul != 0:
            raise ValueError(f'Value {value} is not a multiple of {self._mul}')
        
        return value
    
    def dump(self, value):
        """
        Transform the given integer value for display purposes.

        Args:
            value: The integer value to be transformed.

        Returns:
            str or int: The transformed value based on the dump_hex flag.
        """
        if self._dump_hex:
            return f'{value:x}'
        return value
    
    def dump_bson(self, value, **options):
        """
        Transform the given integer value for storage as BSON int32 or int64.

        Args:
            value: The integer value to be transformed.
            **options: Additional options for dumping.

        Returns:
            bson.Int64 or int: The transformed value based on the dump_bson_int64 flag.
        """
        if self._dump_bson_int64:
            return bson.Int64(value)
        return value
    

class DecimalMapper(Mapper):
    """
    Mapper for handling decimal data.

    Args:
        - gt (float): Greater than. The value should be greater than this.
        - gte (float): Greater than or equal to. The value should be greater than or equal to this.
        - lt (float): Less than. The value should be less than this.
        - lte (float): Less than or equal to. The value should be less than or equal to this.
        - dump_float (bool): Flag to indicate whether the value should be dumped to float data.
        - dump_bson_decimal128 (bool): Flag to indicate whether the value should be dumped to BSON decimal128.

    Example:
        ```python
        # Creating a DecimalMapper with specific options
        decimal_mapper = DecimalMapper(gt=0, lt=100, dump_float=True, dump_bson_decimal128=True)

        # Parsing and validating a decimal value
        parsed_value = decimal_mapper.parse('25.5', strict=False)

        # Example of raising ValueError due to value being less than the specified minimum
        try:
            invalid_value = decimal_mapper.parse(-5.5)
        except ValueError as ve:
            print(ve)
        ```
    """
    
    def __init__(
        self,        
        gt: float = None,
        gte: float = None,
        lt: float = None,
        lte: float = None,
        dump_float: bool = False,
        dump_bson_decimal128: bool = False
    ):
        self._gt = gt
        self._gte = gte
        self._lt = lt
        self._lte = lte
        self._dump_float = dump_float
        self._dump_bson_decimal128 = dump_bson_decimal128
        
    def parse(self, value, **options):
        """
        Parse and validate the given value as a decimal.

        Args:
            value: The value to be parsed.
            **options: Additional options for parsing.

        Returns:
            decimal.Decimal: The parsed and validated decimal value.

        Raises:
            TypeError: If the value is not an instance of the expected decimal.Decimal type.
            ValueError: If the value violates the specified constraints.
        """
        strict = options['strict']
        parse_bson = options['parse_bson']
        
         # Parse from float value
        if isinstance(value, float):
            value = decimal.Decimal(value)
        
        # Parse from BSON decimal128 if not in strict mode
        if not strict:
            if isinstance(value, bson.Decimal128) and parse_bson:
                value = value.to_decimal()
            # Parse from string if not in strict mode
            if isinstance(value, str):
                value = decimal.Decimal(value)
                
        # Validate type
        if not isinstance(value, decimal.Decimal):
            raise TypeError(f'Invalid type, required {decimal.Decimal}, got {type(value)}')
        
        # Validate constraints
        if self._gt is not None and value <= self._gt:
            raise ValueError(f'Value {value} is not greater than {self._gt}')
        if self._gte is not None and value < self._gte:
            raise ValueError(f'Value {value} is not greater than or equal to {self._gte}')
        if self._lt is not None and value >= self._lt:
            raise ValueError(f'Value {value} is not less than {self._lt}')
        if self._lte is not None and value > self._lte:
            raise ValueError(f'Value {value} is not less than or equal to {self._lte}')  
        
        return value
    
    def dump(self, value):
        """
        Transform the given decimal value for display purposes.

        Args:
            value: The decimal value to be transformed.

        Returns:
            float or decimal.Decimal: The transformed value based on the dump_float flag.
        """
        if self._dump_float:
            return float(value)
        return value
    
    def dump_bson(self, value, **options):
        """
        Transform the given decimal value for storage as BSON decimal128.

        Args:
            value: The decimal value to be transformed.
            **options: Additional options for dumping.

        Returns:
            bson.Decimal128 or float: The transformed value based on the dump_bson_decimal128 flag.
        """
        if self._dump_bson_decimal128:
            return bson.Decimal128(value)
        return float(value)
    
    
class BoolMapper(Mapper):
    """
    Mapper for handling boolean data.

    Provides functionality to parse various representations of boolean values.

    Args:
        None

    Example:
        ```python
        # Creating a BoolMapper instance
        bool_mapper = BoolMapper()

        # Parsing and validating boolean values
        parsed_true = bool_mapper.parse(1, strict=False)
        parsed_false = bool_mapper.parse('false', strict=False)
        
        # Example of raising TypeError due to invalid boolean representation
        try:
            invalid_value = bool_mapper.parse('invalid', strict=False)
        except TypeError as te:
            print(te)
        ```
    """
    
    def parse(self, value, **options):
        """
        Parse and validate the given value as a boolean.

        Args:
            value: The value to be parsed.
            **options: Additional options for parsing.

        Returns:
            bool: The parsed and validated boolean value.

        Raises:
            TypeError: If the value cannot be decoded into a boolean or is not of type bool.
        """
        strict = options['strict']
        
        # Parse from int if not in strict mode
        if not strict:
            if isinstance(value, int):
                if value == 0:
                    value = False
                elif value == 1:
                    value = True
            # Parse from string if not in strict mode
            if isinstance(value, str):
                if value in ('false', '0', 'no', 'off'):
                    value = False
                elif value in ('true', '1', 'yes', 'on'):
                    value = True
                else:
                    raise TypeError(f'Unable to decode boolean from string {value}')
        
        # Validate type   
        if not isinstance(value, bool):
            raise TypeError(f'Invalid type, required {bool}, got {type(value)}')

        return value
    
    
class DatetimeMapper(Mapper):
    """
    Mapper for handling datetime data.

    DatetimeMapper provides functionality to parse and dump datetime values based on specified constraints
    and formats.

    Args:
        gt (datetime): Greater than. The datetime value should be greater than this.
        gte (ddatetime): Greater than or equal to. The datetime value should be greater than or equal to this.
        lt (ddatetime): Less than. The datetime value should be less than this.
        lte (datetimel): Less than or equal to. The datetime value should be less than or equal to this.
        parse_format (str): Format string for parsing datetime values.
        dump_str (bool): Flag to indicate whether the value should be dumped to a string.
        dump_format (str): Format string for dumping datetime values.
        
    Example:
    ```python
    # Create a DatetimeMapper with constraints and formatting options
    datetime_mapper = DatetimeMapper(
        gt=datetime.datetime(2022, 1, 1),
        parse_format="%Y-%m-%d %H:%M:%S",
        dump_str=True,
        dump_format="%Y-%m-%d %H:%M:%S"
    )
    
    # Parse a datetime value
    parsed_datetime = datetime_mapper.parse("2023-02-15 14:30:00")
    
    # Dump a datetime value for display
    dumped_value = datetime_mapper.dump(parsed_datetime)
    ```

    Note:
    - If parse_format or dump_format is not provided, default parsing and dumping methods are used.
    - If dump_str is True, the datetime value is dumped as a string using the specified or default format.
    - If dump_str is False, the datetime value is dumped as a datetime object.

    Raises:
        ValueError: If the provided datetime constraints are invalid.
        TypeError: If the provided formats are not valid strings or if the parsed value is not a datetime object.
    """
    
    def __init__(
        self,        
        gt: datetime.datetime = None,
        gte: datetime.datetime = None,
        lt: datetime.datetime = None,
        lte: datetime.datetime = None,
        parse_format: str = None,
        dump_str: bool = False,
        dump_format: str = None
    ):
        self._gt = gt
        self._gte = gte
        self._lt = lt
        self._lte = lte
        self._parse_format = parse_format
        self._dump_str = dump_str
        self._dump_format = dump_format
        
    def parse(self, value, **options):
        """
        Parse and validate the given value as a datetime.

        Args:
            value: The value to be parsed.
            **options: Additional options for parsing.

        Returns:
            datetime.datetime: The parsed and validated datetime value.

        Raises:
            ValueError: If the provided datetime constraints are invalid.
            TypeError: If the provided formats are not valid strings or if the parsed value is not a datetime object.
        """
        strict = options['strict']
        
        # Parse from string if not in strict mode
        if not strict:
            if isinstance(value, str):
                if self._parse_format:
                    value = datetime.datetime.strptime(value, self._parse_format)
                else:
                    value = datetime.datetime.fromisoformat(value)
            # Parse from timestamp if not in strict mode
            if isinstance(value, (int, float)):
                value = datetime.datetime.fromtimestamp(value)
        
        # Convert from date
        if isinstance(value, datetime.date):
            value = datetime.datetime.combine(value, datetime.time.min)
        # Convert from time
        if isinstance(value, datetime.time):
            value = datetime.datetime.combine(datetime.date.min, value)
                
        # Validate type
        if not isinstance(value, datetime.datetime):
            raise TypeError(f'Invalid type, required {datetime.datetime}, got {type(value)}')
        
        # Validate constraints
        if self._gt is not None and value <= self._gt:
            raise ValueError(f'Value {value} is not greater than {self._gt}')
        if self._gte is not None and value < self._gte:
            raise ValueError(f'Value {value} is not greater than or equal to {self._gte}')
        if self._lt is not None and value >= self._lt:
            raise ValueError(f'Value {value} is not less than {self._lt}')
        if self._lte is not None and value > self._lte:
            raise ValueError(f'Value {value} is not less than or equal to {self._lte}') 
        
        return value
    
    def dump(self, value):
        """
        Transform the given datetime value for display purposes.

        Args:
            value: The datetime value to be transformed.

        Returns:
            datetime.datetime or str: The transformed value based on the dump_str and dump_format flags.
        """
        if self._dump_str:
            if self._dump_format:
                return value.strftime(self._dump_format)
            return value.isoformat()
        return value
    
    
class DateMapper(DatetimeMapper):
    """
    Mapper for handling date data.

    DateMapper is a subclass of DatetimeMapper, providing functionality to parse and dump date values.

    Args:
        gt (date): Greater than. The date value should be greater than this.
        gte (date): Greater than or equal to. The date value should be greater than or equal to this.
        lt (date): Less than. The date value should be less than this.
        lte (date): Less than or equal to. The date value should be less than or equal to this.
        parse_format (str): Format string for parsing date values.
        dump_str (bool): Flag to indicate whether the value should be dumped to a string.
        dump_format (str): Format string for dumping date values.   
        
    Example:
    ```python
    # Create a DateMapper with constraints and formatting options
    date_mapper = DateMapper(
        gt=datetime.date(2022, 1, 1),
        parse_format="%Y-%m-%d",
        dump_str=True,
        dump_format="%m/%d/%Y"
    )
    
    # Parse a date value
    parsed_date = date_mapper.parse("2023-02-15")
    
    # Dump a date value for display
    dumped_value = date_mapper.dump(parsed_date)
    ``` 

    Note:
    - Inherits parsing and dumping methods from DatetimeMapper.
    - The provided datetime constraints and formats apply to date values.

    Raises:
        Same as DatetimeMapper.
    """

    def __init__(
        self,
        gt: datetime.date = None,
        gte: datetime.date = None,
        lt: datetime.date = None,
        lte: datetime.date = None,
        parse_format: str = None,
        dump_str: bool = False,
        dump_format: str = None,
    ):
        # Convert date constraints to datetime constraints if they are not None
        gt_datetime = datetime.datetime.combine(gt, datetime.time.min) if gt is not None else None
        gte_datetime = datetime.datetime.combine(gte, datetime.time.min) if gte is not None else None
        lt_datetime = datetime.datetime.combine(lt, datetime.time.max) if lt is not None else None
        lte_datetime = datetime.datetime.combine(lte, datetime.time.max) if lte is not None else None

        # Call the super constructor with datetime constraints
        super().__init__(
            gt=gt_datetime,
            gte=gte_datetime,
            lt=lt_datetime,
            lte=lte_datetime,
            parse_format=parse_format,
            dump_str=dump_str,
            dump_format=dump_format,
        )

    def parse(self, value, **options):
        """
        Parse and validate the given value as a date.

        Args:
            value: The value to be parsed.
            **options: Additional options for parsing.

        Returns:
            datetime.date: The parsed and validated date value.

        Raises:
            Same as DatetimeMapper.
        """
        value = super().parse(value, **options)
        return value.date()
    
    def dump_bson(self, value, **options):
        """
        Transform the given date value for BSON storage purposes.

        Args:
            value: The date value to be transformed.

        Returns:
            datetime.datetime: The transformed value with time set to the minimum for BSON storage.
        """
        return datetime.datetime.combine(value, datetime.time.min)
    
    
class TimeMapper(DatetimeMapper):
    """
    Mapper for handling time data.

    TimeMapper is a subclass of DatetimeMapper, providing functionality to parse and dump time values.

    Args:
        gt (time): Greater than. The time value should be greater than this.
        gte (time): Greater than or equal to. The time value should be greater than or equal to this.
        lt (time): Less than. The time value should be less than this.
        lte (time): Less than or equal to. The time value should be less than or equal to this.
        parse_format (str): Format string for parsing time values.
        dump_str (bool): Flag to indicate whether the value should be dumped to a string.
        dump_format (str): Format string for dumping time values.    

    Example:
    ```python
    # Create a TimeMapper with constraints and formatting options
    time_mapper = TimeMapper(
        gte=datetime.time(8, 0),
        lt=datetime.time(17, 0),
        parse_format="%H:%M:%S",
        dump_str=True,
        dump_format="%I:%M %p"
    )
    
    # Parse a time value
    parsed_time = time_mapper.parse("12:30:45")
    
    # Dump a time value for display
    dumped_value = time_mapper.dump(parsed_time)
    ```

    Note:
    - Inherits parsing and dumping methods from DatetimeMapper.
    - The provided datetime constraints and formats apply to time values.

    Raises:
        Same as DatetimeMapper.
    """

    def __init__(
        self,
        gt: datetime.time = None,
        gte: datetime.time = None,
        lt: datetime.time = None,
        lte: datetime.time = None,
        parse_format: str = None,
        dump_str: bool = False,
        dump_format: str = None,
    ):
        # Convert time constraints to datetime constraints if they are not None
        gt_datetime = datetime.datetime.combine(datetime.date.min, gt) if gt is not None else None
        gte_datetime = datetime.datetime.combine(datetime.date.min, gte) if gte is not None else None
        lt_datetime = datetime.datetime.combine(datetime.date.min, lt) if lt is not None else None
        lte_datetime = datetime.datetime.combine(datetime.date.min, lte) if lte is not None else None

        # Call the super constructor with datetime constraints
        super().__init__(
            gt=gt_datetime,
            gte=gte_datetime,
            lt=lt_datetime,
            lte=lte_datetime,
            parse_format=parse_format,
            dump_str=dump_str,
            dump_format=dump_format,
        )

    def parse(self, value, **options):
        """
        Parse and validate the given value as a time.

        Args:
            value: The value to be parsed.
            **options: Additional options for parsing.

        Returns:
            datetime.time: The parsed and validated time value.

        Raises:
            Same as DatetimeMapper.
        """
        value = super().parse(value, **options)
        return value.time()
    
    def dump_bson(self, value, **options):
        """
        Transform the given time value for BSON storage purposes.

        Args:
            value: The time value to be transformed.

        Returns:
            datetime.datetime: The transformed value with date set to the minimum for BSON storage.
        """
        return datetime.datetime.combine(datetime.date.min, value)
    
    
class DatetimeMSMapper(Mapper):
    """
    Mapper for handling datetime with milliseconds data.

    DatetimeMSMapper provides functionality to parse and dump datetime values with milliseconds based on specified constraints.

    Args:
        gt (int): Greater than. The datetime value in milliseconds should be greater than this.
        gte (int): Greater than or equal to. The datetime value in milliseconds should be greater than or equal to this.
        lt (int): Less than. The datetime value in milliseconds should be less than this.
        lte (int): Less than or equal to. The datetime value in milliseconds should be less than or equal to this.
        dump_datetime (bool): Flag to indicate whether the value should be dumped as a datetime object.

    Example:
    ```python
    # Create a DatetimeMSMapper with constraints and settings
    datetime_ms_mapper = DatetimeMSMapper(
        gt=1649048400000,  # Greater than 2022-03-04T15:00:00
        lt=1649134799999,  # Less than 2022-03-05T15:00:00
        dump_datetime=True,  # Dump the value as a datetime object
    )

    # Parse a datetime with milliseconds value
    parsed_value = datetime_ms_mapper.parse(1649077200000)

    # Dump the parsed value for display
    dumped_value = datetime_ms_mapper.dump(parsed_value)
    ```

    Raises:
        ValueError: If the provided datetime constraints are invalid.
        TypeError: If the parsed value is not a datetime object or an integer.
    """
    
    def __init__(
        self,
        gt: int = None,
        gte: int = None,
        lt: int = None,
        lte: int = None,
        dump_datetime: bool = False
    ):
        self._gt = gt
        self._gte = gte
        self._lt = lt
        self._lte = lte
        self._dump_datetime = dump_datetime
        
    def parse(self, value, **options):
        """
        Parse and validate the given value as a datetime with milliseconds.

        Args:
            value: The value to be parsed.
            **options: Additional options for parsing.

        Returns:
            datetime.datetime: The parsed and validated datetime value with milliseconds.

        Raises:
            ValueError: If the provided datetime constraints are invalid.
            TypeError: If the parsed value is not a datetime object or an integer.
        """
        # Convert from int and datetime
        if isinstance(value, (int, datetime.datetime)):
            value = bson.DatetimeMS(value)
            
        # Validate type
        if not isinstance(value, datetime.datetime):
            raise TypeError(f'Invalid type, required {datetime.datetime}, got {type(value)}')
        
        # Validate constraints
        if self._gt is not None and value <= self._gt:
            raise ValueError(f'Value {value} is not greater than {self._gt}')
        if self._gte is not None and value < self._gte:
            raise ValueError(f'Value {value} is not greater than or equal to {self._gte}')
        if self._lt is not None and value >= self._lt:
            raise ValueError(f'Value {value} is not less than {self._lt}')
        if self._lte is not None and value > self._lte:
            raise ValueError(f'Value {value} is not less than or equal to {self._lte}') 
        
        return value
    
    def dump(self, value):
        """
        Transform the given datetime with milliseconds value for display purposes.

        Args:
            value: The datetime value with milliseconds to be transformed.

        Returns:
            datetime.datetime or bson.DatetimeMS: The transformed value based on the dump_datetime flag.
        """
        if self._dump_datetime:
            return value.as_datetime()
        return value

            
                    

