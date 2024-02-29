import abc
import datetime
import decimal
import types
import typing
import uuid

import bson
import pymongo

from mongotoy import references, expressions
from mongotoy.errors import ValidationError, ErrorWrapper

if typing.TYPE_CHECKING:
    from mongotoy import documents

# A placeholder type for empty values
EmptyValue = type('EmptyValue', (), {})()

# Expose specific symbols for external use
__all__ = (
    'field',
    'reference',
)


def field(
        alias: str = None,
        id_field: bool = False,
        default: typing.Any = EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None,
        index: expressions.IndexType = None,
        sparse: bool = False,
        unique: bool = False
) -> dict:
    """
    Create a field descriptor for a document.

    Args:
        alias (str, optional): Alias for the field. Defaults to None.
        id_field (bool, optional): Indicates if the field is an ID field. Defaults to False.
        default (Any, optional): Default value for the field. Defaults to EmptyValue.
        default_factory (Callable[[], Any], optional): Factory function for generating default values. Defaults to None.
        index (IndexType, optional): Type of index for the field. Defaults to None.
        sparse (bool, optional): Whether the index should be sparse. Defaults to False.
        unique (bool, optional): Whether the index should be unique. Defaults to False.

    Returns:
        dict: Field descriptor.

    """
    return {
        'type': 'field',
        'alias': alias,
        'id_field': id_field,
        'default': default,
        'default_factory': default_factory,
        'index': index,
        'sparse': sparse,
        'unique': unique
    }


def reference(ref_field: str, key_name: str = None) -> dict:
    """
    Create a reference field descriptor for a document.

    Args:
        ref_field (str): Name of the referenced field.
        key_name (str, optional): Key name for the reference. Defaults to None.

    Returns:
        dict: Reference field descriptor.

    """
    return {
        'type': 'reference',
        'ref_field': ref_field,
        'key_name': key_name,
    }


class Field:
    """
    Class for defining document fields.
    """

    def __init__(
        self,
        mapper: 'Mapper',
        alias: str = None,
        id_field: bool = False,
        nullable: bool = False,
        default: typing.Any = EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None,
        index: expressions.IndexType = None,
        sparse: bool = False,
        unique: bool = False
    ):
        """
        Initialize the Field object.

        Args:
            mapper (Mapper): Mapper object for the field.
            alias (str, optional): Alias for the field. Defaults to None.
            id_field (bool, optional): Indicates if the field is an ID field. Defaults to False.
            nullable (bool, optional): Indicates if the field is nullable. Defaults to False.
            default (Any, optional): Default value for the field. Defaults to EmptyValue.
            default_factory (Callable[[], Any], optional): Factory for generating default values. Defaults to None.
            index (IndexType, optional): Type of index for the field. Defaults to None.
            sparse (bool, optional): Whether the index should be sparse. Defaults to False.
            unique (bool, optional): Whether the index should be unique. Defaults to False.

        """
        # If it's an ID field, enforce specific settings
        if id_field:
            alias = '_id'
            nullable = False

        # Initialize field attributes
        self._owner = None
        self._name = None
        self._mapper = mapper
        self._alias = alias
        self._id_field = id_field
        self._nullable = nullable
        self._default_factory = default_factory if default_factory else lambda: default
        self._index = index
        self._sparse = sparse
        self._unique = unique

    # Method for building a mapper based on annotations
    @classmethod
    def _build_mapper(cls, mapper_bind: typing.Type, field_info: dict, mapper_params: dict, **options) -> 'Mapper':
        """
        Build a data mapper based on annotations.

        Args:
            mapper_bind (Type): Type annotation for the mapper.
            field_info (dict): Information about the field.
            mapper_params (dict): Parameters for the mapper.
            **options: Additional options.

        Returns:
            Mapper: The constructed data mapper.

        Raises:
            TypeError: If the mapper type is not recognized.
        """
        # Simple type annotation
        if not typing.get_args(mapper_bind):
            from mongotoy import documents

            # Check if it's a document type
            if isinstance(mapper_bind, (typing.ForwardRef, str)) or issubclass(mapper_bind, documents.BaseDocument):
                if isinstance(mapper_bind, typing.ForwardRef):
                    mapper_bind = getattr(mapper_bind, '__forward_arg__')

                # Set up parameters for document mapping
                mapper_params['document_cls'] = mapper_bind
                mapper_bind = EmbeddedDocumentMapper

                # If it's a document reference
                if field_info.get('type') == 'reference':
                    mapper_params['ref_field'] = field_info.get('ref_field')
                    mapper_params['key_name'] = field_info.get('key_name')
                    mapper_params['is_many'] = options.get('is_many', False)
                    mapper_bind = ReferencedDocumentMapper

            # Create the mapper
            mapper_cls = _MAPPERS_REG.get(mapper_bind)
            if not mapper_cls:
                raise TypeError(f'Data mapper not found for type {mapper_bind}')
            mapper = mapper_cls(**mapper_params)

            # If it's many, use ListMapper
            if options.get('is_many', False):
                mapper = ListMapper(mapper)
            return mapper

        # Get type origin and arguments
        type_origin = typing.get_origin(mapper_bind)
        type_args = typing.get_args(mapper_bind)
        mapper_bind = type_args[0]

        # Check for nullable type
        if type_origin in (typing.Union, types.UnionType) and len(type_args) > 1 and type_args[1] is types.NoneType:
            field_info['nullable'] = True
            return cls._build_mapper(mapper_bind, field_info, mapper_params)

        # Check for list type
        if type_origin is list:
            return cls._build_mapper(mapper_bind, field_info, mapper_params, is_many=True)

        raise TypeError(f'Invalid outer annotation {type_origin}, allowed are [{list}, {typing.Optional}]')

    @classmethod
    def from_annotated_type(cls, anno_type: typing.Type, info: dict) -> 'Field':
        """
        Create a Field instance from an annotated type.

        Args:
            anno_type (Type): Annotated type for the field.
            info (dict, optional): Additional information about the field. Defaults to {}.

        Returns:
            Field: The constructed Field instance.

        """
        return Field(
            mapper=cls._build_mapper(
                mapper_bind=anno_type,
                field_info=info,
                mapper_params={}
            ),
            alias=info.get('alias'),
            id_field=info.get('id_field', False),
            nullable=info.get('nullable', False),
            default=info.get('default', EmptyValue),
            default_factory=info.get('default_factory'),
            index=info.get('index'),
            sparse=info.get('sparse'),
            unique=info.get('unique')
        )

    @property
    def mapper(self) -> 'Mapper':
        """
        Get the mapper associated with the field.

        Returns:
            Mapper: The mapper object.

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
            str: The alias of the field, or its name if no alias is set.

        """
        return self._alias or self._name

    @property
    def id_field(self) -> bool:
        """
        Check if the field is an ID field.

        Returns:
            bool: True if it's an ID field, False otherwise.

        """
        return self._id_field

    def __set_name__(self, owner, name):
        """
        Set the name of the field.

        Args:
            owner: The owner class of the field.
            name (str): The name of the field.

        """
        self._owner = owner
        self._name = name

    def __get__(self, instance, owner):
        """
        Get the value of the field.

        Args:
            instance: The instance of the owner class.
            owner: The owner class.

        Returns:
            Any: The value of the field.

        """
        if not instance:
            return FieldProxy(self)
        return instance.__data__.get(self.name, EmptyValue)

    def __set__(self, instance, value):
        """
        Set the value of the field.

        Args:
            instance: The instance of the owner class.
            value: The value to be set.

        """
        value = self.validate(value)
        if value is not EmptyValue:
            instance.__data__[self.name] = value

    def get_index(self) -> pymongo.IndexModel | None:
        """
        Get the index definition for the field.

        Returns:
            pymongo.IndexModel | None: The index definition, or None if no index is defined.

        """
        index = None
        if self._unique or self._sparse:
            index = pymongo.ASCENDING
        if self._index is not None:
            index = self._index
        if index:
            return pymongo.IndexModel(
                keys=[(self.alias, index)],
                unique=self._unique,
                sparse=self._sparse
            )

    def validate(self, value, **options) -> typing.Any:
        """
        Validate the value of the field.

        Args:
            value: The value to be validated.
            **options: Additional options.

        Returns:
            Any: The validated value.

        Raises:
            ValidationError: If validation fails.

        """
        if value is EmptyValue:
            value = self._default_factory()
            if value is EmptyValue:
                return value

        if value is None:
            if not self._nullable:
                raise ValidationError(
                    errors=[ErrorWrapper(loc=(self.name,), error=ValueError('Null valued not allowed'))]
                )
            return value

        try:
            value = self.mapper.validate(value, **options)
        except (TypeError, ValueError) as e:
            raise ValidationError(
                errors=[ErrorWrapper(loc=(self.name,), error=e)]
            ) from None
        except ValidationError as e:
            raise ValidationError(
                errors=[ErrorWrapper(loc=(self.name,) if self._owner else (), error=i) for i in e.errors]
            ) from None

        return value


class FieldProxy:
    """
    Proxy class for fields.
    """

    # noinspection PyShadowingNames
    def __init__(self, field: Field, parent: 'FieldProxy' = None):
        self._field = field
        self._parent = parent

    @property
    def _alias(self) -> str:
        """
        Get the alias of the field, considering the parent's alias if present.

        Returns:
            str: The alias of the field.
        """
        if self._parent:
            return f'{self._parent._alias}.{self.field.alias}'
        return self._field.alias

    def __str__(self):
        """
        Returns the string representation of the field's alias.

        Returns:
            str: The string representation of the field's alias.
        """
        return self._alias

    def __eq__(self, other):
        """
        Represents equality comparison of the field.

        Args:
            other: The value or field to compare.

        Returns:
            Query: Query object representing equality comparison.
        """
        return expressions.Query.Eq(self, other)

    def __ne__(self, other):
        """
        Represents inequality comparison of the field.

        Args:
            other: The value or field to compare.

        Returns:
            Query: Query object representing inequality comparison.
        """
        return expressions.Query.Ne(self._alias, other)

    def __gt__(self, other):
        """
        Represents greater-than comparison of the field.

        Args:
            other: The value or field to compare.

        Returns:
            Query: Query object representing greater-than comparison.
        """
        return expressions.Query.Gt(self._alias, other)

    def __ge__(self, other):
        """
        Represents greater-than-or-equal-to comparison of the field.

        Args:
            other: The value or field to compare.

        Returns:
            Query: Query object representing greater-than-or-equal-to comparison.
        """
        return expressions.Query.Gte(self._alias, other)

    def __lt__(self, other):
        """
        Represents less-than comparison of the field.

        Args:
            other: The value or field to compare.

        Returns:
            Query: Query object representing less-than comparison.
        """
        return expressions.Query.Lt(self._alias, other)

    def __le__(self, other):
        """
        Represents less-than-or-equal-to comparison of the field.

        Args:
            other: The value or field to compare.

        Returns:
            Query: Query object representing less-than-or-equal-to comparison.
        """
        return expressions.Query.Lte(self._alias, other)

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
        mapper = self._field.mapper
        if isinstance(mapper, ListMapper):
            mapper = mapper.mapper
        # Unwrap EmbeddedDocumentMapper or ReferencedDocumentMapper
        if isinstance(mapper, (EmbeddedDocumentMapper, ReferencedDocumentMapper)):
            mapper = mapper.document_cls

        # Check item on mapper
        try:
            getattr(mapper.__bind__ if isinstance(mapper, Mapper) else mapper, item)
        except AttributeError as e:
            # noinspection PyProtectedMember
            raise AttributeError(f'[{self._field._owner.__name__}.{self._alias}] {str(e)}') from None

        return FieldProxy(
            field=mapper.__fields__[item],
            parent=self
        )


_MAPPERS_REG = {}


class MapperMeta(abc.ABCMeta):
    """
    Metaclass for Mapper classes.
    """

    def __new__(mcls, name, bases, namespace, **kwargs):
        """
        Create a new Mapper class.

        Args:
            name (str): Name of the class.
            bases: Base classes.
            namespace: Namespace dictionary.
            **kwargs: Additional keyword arguments.

        Returns:
            Mapper: The newly created Mapper class.

        """
        _cls = super().__new__(mcls, name, bases, namespace)
        _cls.__bind__ = kwargs.get('bind', _cls)
        _MAPPERS_REG[_cls.__bind__] = _cls

        return _cls


class Mapper(abc.ABC, metaclass=MapperMeta):
    """
    Abstract base class for data mappers.
    """

    @abc.abstractmethod
    def validate(self, value, **options) -> typing.Any:
        """
        Validate the value.

        Args:
            value: The value to be validated.
            **options: Additional options.

        Returns:
            Any: The validated value.

        """
        raise NotImplementedError

    def dump_dict(self, value, **options) -> typing.Any:
        """
        Dump the value to a dictionary.

        Args:
            value: The value to be dumped.
            **options: Additional options.

        Returns:
            Any: The dumped value.

        """
        return value

    def dump_json(self, value, **options) -> typing.Any:
        """
        Dump the value to JSON.

        Args:
            value: The value to be dumped.
            **options: Additional options.

        Returns:
            Any: The dumped value.

        """
        return value

    def dump_bson(self, value, **options) -> typing.Any:
        """
        Dump the value to BSON.

        Args:
            value: The value to be dumped.
            **options: Additional options.

        Returns:
            Any: The dumped value.

        """
        return value


class ListMapper(Mapper):
    """
    Mapper for handling lists.
    """

    def __init__(self, mapper: Mapper):
        """
        Initialize the ListMapper.

        Args:
            mapper (Mapper): The mapper for the list items.

        """
        self._mapper = mapper

    @property
    def mapper(self) -> Mapper:
        """
        Get the mapper for the list items.

        Returns:
            Mapper: The mapper for the list items.

        """
        return self._mapper

    def validate(self, value, **options) -> typing.Any:
        """
        Validate the list value.

        Args:
            value: The list value to be validated.
            **options: Additional options.

        Returns:
            Any: The validated list value.

        Raises:
            ValidationError: If validation fails.

        """
        if not isinstance(value, list):
            raise TypeError(f'Invalid data type {type(value)}, required is {list}')

        new_value = []
        errors = []
        for i, val in enumerate(value):
            try:
                new_value.append(self.mapper.validate(val, **options))
            except ValidationError as e:
                errors.extend([ErrorWrapper(loc=(str(i),), error=j) for j in e.errors])
        if errors:
            raise ValidationError(errors=errors)

        return value

    def dump_dict(self, value, **options) -> typing.Any:
        """
        Dump the list value to a dictionary.

        Args:
            value: The list value to be dumped.
            **options: Additional options.

        Returns:
            Any: The dumped list value.

        """
        return [self.mapper.dump_dict(i, **options) for i in value]

    def dump_json(self, value, **options) -> typing.Any:
        """
        Dump the list value to JSON.

        Args:
            value: The list value to be dumped.
            **options: Additional options.

        Returns:
            Any: The dumped list value.

        """
        return [self.mapper.dump_json(i, **options) for i in value]

    def dump_bson(self, value, **options) -> typing.Any:
        """
        Dump the list value to BSON.

        Args:
            value: The list value to be dumped.
            **options: Additional options.

        Returns:
            Any: The dumped list value.

        """
        return [self.mapper.dump_bson(i, **options) for i in value]


class EmbeddedDocumentMapper(Mapper):
    """
    Mapper for embedded documents.
    """

    def __init__(self, document_cls: typing.Type['documents.BaseDocument'] | str):
        """
        Initialize the EmbeddedDocumentMapper.

        Args:
            document_cls (Type['documents.BaseDocument'] | str): The class or name of the embedded document.

        """
        self._document_cls = document_cls

    @property
    def document_cls(self) -> typing.Type['documents.BaseDocument']:
        """
        Get the class of the embedded document.

        Returns:
            Type['documents.BaseDocument']: The class of the embedded document.

        """
        if isinstance(self._document_cls, str):
            return references.get_document_cls(self._document_cls)
        return self._document_cls

    def validate(self, value, **options) -> typing.Any:
        """
        Validate the embedded document value.

        Args:
            value: The value to be validated.
            **options: Additional options.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if isinstance(value, dict):
            value = self.document_cls(**value)
        if not isinstance(value, self.document_cls):
            raise TypeError(f'Invalid data type {type(value)}, required is {self.document_cls}')
        return value

    def dump_dict(self, value, **options) -> typing.Any:
        """
        Dump the embedded document value to a dictionary.

        Args:
            value: The value to be dumped.
            **options: Additional options.

        Returns:
            Any: The dumped value.

        """
        return value.dump_dict(**options)

    def dump_json(self, value, **options) -> typing.Any:
        """
        Dump the embedded document value to JSON.

        Args:
            value: The value to be dumped.
            **options: Additional options.

        Returns:
            Any: The dumped value.

        """
        return value.dump_json(**options)

    def dump_bson(self, value, **options) -> typing.Any:
        """
        Dump the embedded document value to BSON.

        Args:
            value: The value to be dumped.
            **options: Additional options.

        Returns:
            Any: The dumped value.

        """
        return value.dump_bson(**options)


class ReferencedDocumentMapper(EmbeddedDocumentMapper):
    """
    Mapper for referenced documents.
    """

    def __init__(
        self,
        document_cls: typing.Type['documents.BaseDocument'] | str,
        ref_field: str,
        key_name: str,
        is_many: bool
    ):
        """
        Initialize the ReferencedDocumentMapper.

        Args:
            document_cls (Type['documents.BaseDocument'] | str): The class or name of the referenced document.
            ref_field (str): The name of the referenced field.
            key_name (str): The key name for the reference.
            is_many (bool): Indicates if it's a many-to-many relationship.

        """
        super().__init__(document_cls)
        self._reference = references.Reference(
            document_cls=document_cls,
            ref_field=ref_field,
            key_name=key_name,
            is_many=is_many
        )

    @property
    def document_cls(self) -> typing.Type['documents.BaseDocument']:
        """
        Get the class of the referenced document.

        Returns:
            Type['documents.BaseDocument']: The class of the referenced document.

        """
        return self._reference.document_cls

    @property
    def ref_field(self) -> Field:
        """
        Get the reference field.

        Returns:
            Field: The reference field.

        """
        return self._reference.ref_field

    def dump_bson(self, value, **options) -> typing.Any:
        """
        Dump the value to BSON.

        Args:
            value: The value to be dumped.
            **options: Additional options.

        Returns:
            Any: The dumped value.

        """
        return getattr(value, self.ref_field.name)


class StrMapper(Mapper, bind=str):
    """
    Mapper for handling string values.
    """

    def validate(self, value, **options) -> typing.Any:
        """
        Validate the string value.

        Args:
            value: The value to be validated.
            **options: Additional options.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if not isinstance(value, str):
            raise TypeError(f'Invalid data type {type(value)}, required is {str}')
        return value


class IntMapper(Mapper, bind=int):
    """
    Mapper for handling integer values.
    """

    def validate(self, value, **options) -> typing.Any:
        """
        Validate the integer value.

        Args:
            value: The value to be validated.
            **options: Additional options.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if not isinstance(value, int):
            raise TypeError(f'Invalid data type {type(value)}, required is {int}')
        return value


class FloatMapper(Mapper, bind=float):
    """
    Mapper for handling float values.
    """

    def validate(self, value, **options) -> typing.Any:
        """
        Validate the float value.

        Args:
            value: The value to be validated.
            **options: Additional options.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if not isinstance(value, float):
            raise TypeError(f'Invalid data type {type(value)}, required is {float}')
        return value


class ObjectIdMapper(Mapper, bind=bson.ObjectId):
    """
    Mapper for handling BSON ObjectId values.
    """

    def validate(self, value, **options) -> typing.Any:
        """
        Validate the ObjectId value.

        Args:
            value: The value to be validated.
            **options: Additional options.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if not isinstance(value, bson.ObjectId):
            raise TypeError(f'Invalid data type {type(value)}, required is {bson.ObjectId}')
        return value


class DecimalMapper(Mapper, bind=decimal.Decimal):
    """
    Mapper for handling decimal values.
    """

    def validate(self, value, **options) -> typing.Any:
        """
        Validate the decimal value.

        Args:
            value: The value to be validated.
            **options: Additional options.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if not isinstance(value, decimal.Decimal):
            raise TypeError(f'Invalid data type {type(value)}, required is {decimal.Decimal}')
        return value


class UUIDMapper(Mapper, bind=uuid.UUID):
    """
    Mapper for handling UUID values.
    """

    def validate(self, value, **options) -> typing.Any:
        """
        Validate the UUID value.

        Args:
            value: The value to be validated.
            **options: Additional options.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if not isinstance(value, uuid.UUID):
            raise TypeError(f'Invalid data type {type(value)}, required is {uuid.UUID}')
        return value


class DateTimeMapper(Mapper, bind=datetime.datetime):
    """
    Mapper for handling datetime values.
    """

    def validate(self, value, **options) -> typing.Any:
        """
        Validate the datetime value.

        Args:
            value: The value to be validated.
            **options: Additional options.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if not isinstance(value, datetime.datetime):
            raise TypeError(f'Invalid data type {type(value)}, required is {datetime.datetime}')
        return value


class DateMapper(Mapper, bind=datetime.date):
    """
    Mapper for handling date values.
    """

    def validate(self, value, **options) -> typing.Any:
        """
        Validate the date value.

        Args:
            value: The value to be validated.
            **options: Additional options.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if not isinstance(value, datetime.date):
            raise TypeError(f'Invalid data type {type(value)}, required is {datetime.date}')
        return value


class TimeDeltaMapper(Mapper, bind=datetime.timedelta):
    """
    Mapper for handling timedelta values.
    """

    def validate(self, value, **options) -> typing.Any:
        """
        Validate the timedelta value.

        Args:
            value: The value to be validated.
            **options: Additional options.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if not isinstance(value, datetime.timedelta):
            raise TypeError(f'Invalid data type {type(value)}, required is {datetime.timedelta}')
        return value
