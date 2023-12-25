
import datetime
import inspect
import re
from typing import Any, Callable, Literal, Type, TYPE_CHECKING
import bson
import pymongo
from mongotoy import mappers
from mongotoy.errors import ErrorWrapper, FieldError, ValidationError
from mongotoy.expressions import Q, Asc, Desc
from mongotoy.mappers import Mapper

if TYPE_CHECKING:
    from mongotoy.documents import EmbeddedDocument


EmptyValue = type('Empty', (), {'__repr__': lambda _: 'Empty()'})()
IndexType = Literal[-1, 1, '2d', '2dsphere', 'hashed', 'text']


class FieldInfo:
    """
    Represents information about a field in a document.

    Args:
        - mapper (Mapper): The mapper responsible for handling the data of the field.
        - alias (str): An optional alias for the field.
        - id_field (bool): Indicates whether the field is an ID field.
        - nullable (bool): Indicates whether the field can be set to None.
        - default (Any): The default value for the field.
        - default_factory (Callable[[], Any]): A callable that returns the default value.
        - index (IndexType): The type of index to be applied to the field.
        - unique (bool): Indicates whether the field should have a unique index.
        - unique_with (str | list[str]): Field or fields that the uniqueness of this field depends on.
        - sparse (bool): Indicates whether the index should be sparse.
        - timeseries_field (bool): Indicates whether the field is a timeseries field.
        - timeseries_meta_field (bool): Indicates whether the field is a timeseries meta field.
    """

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
        # Change props when it is an id_field
        if id_field:
            alias = '_id'
            nullable = False

        # Ensure default_factory is not null
        if not default_factory:
            def default_factory():
                return default

        # Ensure unique_with as list and enable unique index
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
        """
        Get the mapper associated with the field.

        Returns:
            Mapper: The mapper for the field.
        """
        return self._mapper

    @property
    def name(self) -> str:
        """
        Get the name of the field.

        Returns:
            str: The name of the field.
        """
        return self._name

    @property
    def alias(self) -> str:
        """
        Get the alias of the field.

        Returns:
            str: The alias of the field or the name if alias is not set.
        """
        return self._alias or self._name

    @property
    def id_field(self) -> bool:
        """
        Check if the field is an ID field.

        Returns:
            bool: True if the field is an ID field, False otherwise.
        """
        return self._id_field

    def __set_name__(self, owner, name):
        """
        Set the name of the field when it is assigned to a class attribute.

        Args:
            owner: The owner class.
            name: The name of the field.
        """
        self._owner = owner
        self._name = name

    def __get__(self, instance, owner):
        """
        Get the value of the field when accessed through an instance.

        Args:
            instance: The instance of the owner class.
            owner: The owner class.

        Returns:
            Any: The value of the field or EmptyValue if not set.
        """
        if not instance:
            pass  # TODO impl FieldProxy
        value = instance.__data__.get(self.name, EmptyValue)
        if value is not EmptyValue:
            return self.mapper.dump(value)
        return EmptyValue

    def __set__(self, instance, value, **options):
        """
        Set the value of the field when assigned through an instance.

        Args:
            instance: The instance of the owner class.
            value: The value to be set.
            **options: Additional options for setting the value.
        """
        value = self.parse(value, instance=instance, **options)
        if value is not EmptyValue:
            instance.__data__[self.name] = value

    def __delete__(self, instance):
        """
        Delete the value of the field when deleted through an instance.

        Args:
            instance: The instance of the owner class.
        """
        instance.__data__.pop(self.name, None)

    def get_index(self) -> pymongo.IndexModel | None:
        """
        Get the MongoDB index model for the field.

        Returns:
            pymongo.IndexModel or None: The index model or None if no index is specified.
        """
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
        return None

    def parse(self, value, **options):
        """
        Parse and validate the given value for the field.

        Args:
            value: The value to be parsed.
            **options: Additional options for parsing.

        Returns:
            Any: The parsed and validated value for the field.

        Raises:
            ValidationError: If parsing or validation fails.
        """
        use_defaults = options['use_defaults']

        # Use default if value is empty
        if value is EmptyValue and use_defaults:
            value = self._default_factory()

        # Return an empty value
        if value is EmptyValue:
            return value

        # Check nullability
        if value is None:
            if not self._nullable:
                raise ValueError('Null value not allowed')
            else:
                return value

        # Add field level options
        options['owner'] = self._owner
        options['field_info'] = self

        try:
            # Mapper parsing
            value = self.mapper.parse(value, **options)

            # Owner instance validator
            validator = getattr(options['instance'], f'validate_{self.name}', None)
            if validator and inspect.ismethod(validator):
                validator(value)

        except ValidationError as e:
            raise ValidationError(
                errors=[ErrorWrapper(loc=self.name, error=err) for err in e.errors]
            ) from None
        except Exception as e:
            raise ValidationError(
                errors=[ErrorWrapper(loc=self.name, error=e)]
            ) from None

        return value
    
    
class FieldProxy:
    """
    Proxy class for accessing fields within an embedded or referenced document.

    Args:
        - field (FieldInfo): The field information instance.
        - parent (FieldProxy): The parent FieldProxy instance (if any).

    Properties:
        - field (FieldInfo): The field information instance.
        - _alias (str): The alias of the field, considering the parent's alias if present.

    Methods:
        - __str__: Returns the string representation of the field's alias.
        - __pos__: Represents the ascending ordering of the field.
        - __neg__: Represents the descending ordering of the field.
        - __eq__: Represents equality comparison of the field.
        - __ne__: Represents inequality comparison of the field.
        - __gt__: Represents greater-than comparison of the field.
        - __ge__: Represents greater-than-or-equal-to comparison of the field.
        - __lt__: Represents less-than comparison of the field.
        - __le__: Represents less-than-or-equal-to comparison of the field.
        - __getattr__: Allows accessing nested fields using dot notation.

    Example:
        ```python
        class Address(EmbeddedDocument):
            street: str
            city: str

        class Person(EmbeddedDocument):
            name: str
            address: Address

        person_proxy = FieldProxy(field=Person.__fields__['address'])
        street_proxy = person_proxy.address.street  # Accessing nested fields using dot notation
        ```

    """

    def __init__(self, field: FieldInfo, parent: 'FieldProxy' = None):
        self._field = field
        self._parent = parent

    @property
    def field(self) -> FieldInfo:
        """
        Get the field information instance.

        Returns:
            FieldInfo: The field information instance.
        """
        return self._field

    @property
    def _alias(self) -> str:
        """
        Get the alias of the field, considering the parent's alias if present.

        Returns:
            str: The alias of the field.
        """
        if self._parent:
            return f'{self._parent._alias}.{self.field.alias}'
        return self.field.alias

    def __str__(self):
        """
        Returns the string representation of the field's alias.

        Returns:
            str: The string representation of the field's alias.
        """
        return self._alias
    
    def __pos__(self):
        """
        Represents the ascending ordering of the field.

        Returns:
            Q: Query object representing ascending order by the field.
        """
        return Asc(self._alias)

    def __neg__(self):
        """
        Represents the descending ordering of the field.

        Returns:
            Q: Query object representing descending order by the field.
        """
        return Desc(self._alias)

    def __eq__(self, other):
        """
        Represents equality comparison of the field.

        Args:
            other: The value or field to compare.

        Returns:
            Q: Query object representing equality comparison.
        """
        return Q._eq(self._alias, other)

    def __ne__(self, other):
        """
        Represents inequality comparison of the field.

        Args:
            other: The value or field to compare.

        Returns:
            Q: Query object representing inequality comparison.
        """
        return Q._ne(self._alias, other)

    def __gt__(self, other):
        """
        Represents greater-than comparison of the field.

        Args:
            other: The value or field to compare.

        Returns:
            Q: Query object representing greater-than comparison.
        """
        return Q._gt(self._alias, other)

    def __ge__(self, other):
        """
        Represents greater-than-or-equal-to comparison of the field.

        Args:
            other: The value or field to compare.

        Returns:
            Q: Query object representing greater-than-or-equal-to comparison.
        """
        return Q._gte(self._alias, other)

    def __lt__(self, other):
        """
        Represents less-than comparison of the field.

        Args:
            other: The value or field to compare.

        Returns:
            Q: Query object representing less-than comparison.
        """
        return Q._lt(self._alias, other)

    def __le__(self, other):
        """
        Represents less-than-or-equal-to comparison of the field.

        Args:
            other: The value or field to compare.

        Returns:
            Q: Query object representing less-than-or-equal-to comparison.
        """
        return Q._lte(self._alias, other)

    def __getattr__(self, item):
        """
        Allows accessing nested fields using dot notation.

        Args:
            item (str): The name of the nested field.

        Returns:
            FieldProxy: The FieldProxy instance for the nested field.

        Raises:
            FieldError: If the nested field is not found in the document.
        """
        # Unwrap ListMapper
        mapper = self.field.mapper
        if isinstance(mapper, mappers.ListMapper):
            mapper = mapper.inner_mapper

        if not isinstance(mapper, (mappers.EmbeddedDocumentMapper, mappers.ReferencedDocumentMapper)):
            raise FieldError(
                f'FieldProxy for {self.field.name} does not expose field attributes, '
                f'use {self.field.name}.field property instead to access field info instance'
            )

        fields = mapper.document_cls.__fields__
        if item not in fields:
            raise FieldError(f'Field {item} not found in document {mapper.document_cls}')

        return FieldProxy(
            field=fields[item],
            parent=self
        )
    
    
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
    
    
def ReferencedDocumentField(
    key_name: str,
    document_cls: Type['EmbeddedDocument'] | str,    
    alias: str = None,
    nullable: bool = True,  
    index: IndexType = None,     
    unique: bool = False,         
    unique_with: str | list[str] = None,
    sparse: bool = False,
    ref: str = None,
    back_ref: str = None
) -> FieldInfo:
    return FieldInfo(
        mapper=mappers.ReferencedDocumentMapper(
            key_name=key_name,
            document_cls=document_cls,
            ref=ref,
            back_ref=back_ref
        ),
        alias=alias,
        nullable=nullable,
        index=index,
        unique=unique,
        unique_with=unique_with,
        sparse=sparse
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
    
    
def IntField(    
    alias: str = None,
    id_field: bool = False,
    nullable: bool = True,
    default: Any = None,
    default_factory: Callable[[], Any] = None,        
    index: IndexType = None,
    unique: bool = False,
    unique_with: str | list[str] = None,
    sparse: bool = False,        
    gt: int = None,
    gte: int = None,
    lt: int = None,
    lte: int = None,
    mul: int = None,
    parse_hex: bool = False,
    dump_hex: bool = False,
    dump_bson_int64: bool = False
) -> FieldInfo:
    return FieldInfo(
        mapper=mappers.IntMapper(
            gt=gt,
            gte=gte,
            lt=lt,
            lte=lte,
            mul=mul,
            parse_hex=parse_hex,
            dump_hex=dump_hex,
            dump_bson_int64=dump_bson_int64
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
    
    
def FloatField(    
    alias: str = None,
    id_field: bool = False,
    nullable: bool = True,
    default: Any = None,
    default_factory: Callable[[], Any] = None,        
    index: IndexType = None,
    unique: bool = False,
    unique_with: str | list[str] = None,
    sparse: bool = False,        
    gt: float = None,
    gte: float = None,
    lt: float = None,
    lte: float = None
) -> FieldInfo:
    return FieldInfo(
        mapper=mappers.DecimalMapper(
            gt=gt,
            gte=gte,
            lt=lt,
            lte=lte,
            dump_float=True,
            dump_bson_decimal128=False
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
    
    
def DecimalField(    
    alias: str = None,
    id_field: bool = False,
    nullable: bool = True,
    default: Any = None,
    default_factory: Callable[[], Any] = None,        
    index: IndexType = None,
    unique: bool = False,
    unique_with: str | list[str] = None,
    sparse: bool = False,        
    gt: float = None,
    gte: float = None,
    lt: float = None,
    lte: float = None
) -> FieldInfo:
    return FieldInfo(
        mapper=mappers.DecimalMapper(
            gt=gt,
            gte=gte,
            lt=lt,
            lte=lte,
            dump_float=False,
            dump_bson_decimal128=True
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
    
    
def BooleanField(    
    alias: str = None,
    id_field: bool = False,
    nullable: bool = True,
    default: Any = None,
    default_factory: Callable[[], Any] = None,        
    index: IndexType = None,
    unique: bool = False,
    unique_with: str | list[str] = None,
    sparse: bool = False
) -> FieldInfo:
    return FieldInfo(
        mapper=mappers.BoolMapper(),
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
    
    
def DatetimeField(    
    alias: str = None,
    id_field: bool = False,
    nullable: bool = True,
    default: Any = None,
    default_factory: Callable[[], Any] = None,        
    index: IndexType = None,
    unique: bool = False,
    unique_with: str | list[str] = None,
    sparse: bool = False,        
    gt: datetime.datetime = None,
    gte: datetime.datetime = None,
    lt: datetime.datetime = None,
    lte: datetime.datetime = None,
    parse_format: str = None,
    dump_str: bool = False,
    dump_format: str = None
) -> FieldInfo:
    return FieldInfo(
        mapper=mappers.DatetimeMapper(
            gt=gt,
            gte=gte,
            lt=lt,
            lte=lte,
            parse_format=parse_format,
            dump_str=dump_str,
            dump_format=dump_format
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
    
    
def DateField(    
    alias: str = None,
    id_field: bool = False,
    nullable: bool = True,
    default: Any = None,
    default_factory: Callable[[], Any] = None,        
    index: IndexType = None,
    unique: bool = False,
    unique_with: str | list[str] = None,
    sparse: bool = False,        
    gt: datetime.date = None,
    gte: datetime.date = None,
    lt: datetime.date = None,
    lte: datetime.date = None,
    parse_format: str = None,
    dump_str: bool = False,
    dump_format: str = None
) -> FieldInfo:
    return FieldInfo(
        mapper=mappers.DateMapper(
            gt=gt,
            gte=gte,
            lt=lt,
            lte=lte,
            parse_format=parse_format,
            dump_str=dump_str,
            dump_format=dump_format
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
    
    
def TimeField(    
    alias: str = None,
    id_field: bool = False,
    nullable: bool = True,
    default: Any = None,
    default_factory: Callable[[], Any] = None,        
    index: IndexType = None,
    unique: bool = False,
    unique_with: str | list[str] = None,
    sparse: bool = False,        
    gt: datetime.time = None,
    gte: datetime.time = None,
    lt: datetime.time = None,
    lte: datetime.time = None,
    parse_format: str = None,
    dump_str: bool = False,
    dump_format: str = None
) -> FieldInfo:
    return FieldInfo(
        mapper=mappers.TimeMapper(
            gt=gt,
            gte=gte,
            lt=lt,
            lte=lte,
            parse_format=parse_format,
            dump_str=dump_str,
            dump_format=dump_format
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
    
    
def DatetimeMSField(    
    alias: str = None,
    id_field: bool = False,
    nullable: bool = True,
    default: Any = None,
    default_factory: Callable[[], Any] = None,        
    index: IndexType = None,
    unique: bool = False,
    unique_with: str | list[str] = None,
    sparse: bool = False,        
    gt: int = None,
    gte: int = None,
    lt: int = None,
    lte: int = None,
    dump_datetime: bool = False
) -> FieldInfo:
    return FieldInfo(
        mapper=mappers.DatetimeMSMapper(
            gt=gt,
            gte=gte,
            lt=lt,
            lte=lte,
            dump_datetime=dump_datetime
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
            