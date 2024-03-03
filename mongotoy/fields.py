import types
import typing

import pymongo

from mongotoy import expressions, cache, mappers
from mongotoy.errors import ValidationError, ErrorWrapper

if typing.TYPE_CHECKING:
    from mongotoy import documents


# Expose specific symbols for external use
__all__ = (
    'field',
    'reference',
)


def field(
        alias: str = None,
        id_field: bool = False,
        default: typing.Any = expressions.EmptyValue,
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
        mapper: mappers.Mapper,
        alias: str = None,
        id_field: bool = False,
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
            index (IndexType, optional): Type of index for the field. Defaults to None.
            sparse (bool, optional): Whether the index should be sparse. Defaults to False.
            unique (bool, optional): Whether the index should be unique. Defaults to False.

        """
        # If it's an ID field, enforce specific settings
        if id_field:
            alias = '_id'

        # Initialize field attributes
        self._owner = None
        self._name = None
        self._mapper = mapper
        self._alias = alias
        self._id_field = id_field
        self._index = index
        self._sparse = sparse
        self._unique = unique

    # Method for building a mapper based on annotations
    @classmethod
    def _build_mapper(cls, mapper_bind: typing.Type, **options) -> 'mappers.Mapper':
        """
        Build a data mapper based on annotations.

        Args:
            mapper_bind (Type): Type annotation for the mapper.
            **options: Additional options.

        Returns:
            Mapper: The constructed data mapper.

        Raises:
            TypeError: If the mapper type is not recognized.
        """
        from mongotoy import documents

        # Simple type annotation
        if not typing.get_args(mapper_bind):
            # Set up mapper parameters
            mapper_params = {
                'nullable': options.pop('nullable', False),
                'default': options.pop('default', expressions.EmptyValue),
                'default_factory': options.pop('default_factory', None),
            }

            # Check if it's a document type
            if isinstance(mapper_bind, (typing.ForwardRef, str)) or issubclass(mapper_bind, documents.BaseDocument):

                # Get from ForwardRef
                if isinstance(mapper_bind, typing.ForwardRef):
                    mapper_bind = getattr(mapper_bind, '__forward_arg__')

                # Set up parameters for document mapping
                mapper_params['document_cls'] = mapper_bind
                mapper_bind = mappers.EmbeddedDocumentMapper

                # If it's a document reference
                if options.get('type') == 'reference':
                    mapper_params['ref_field'] = options.pop('ref_field')
                    mapper_params['key_name'] = options.pop('key_name')
                    mapper_bind = mappers.ReferencedDocumentMapper

            # Check if mapper_bind is suitable for reference
            if options.get('type') == 'reference' and mapper_bind is not mappers.ReferencedDocumentMapper:
                # noinspection SpellCheckingInspection
                raise Exception(f'Type {mapper_bind} cannot be used with mongotoy.reference() descriptor')

            # Create the mapper
            mapper_cls = cache.mappers.get_type(mapper_bind)
            if not mapper_cls:
                raise TypeError(f'Data mapper not found for type {mapper_bind}')

            return mapper_cls(**mapper_params)

        # Get type origin and arguments
        type_origin = typing.get_origin(mapper_bind)
        type_args = typing.get_args(mapper_bind)
        mapper_bind = type_args[0]

        # Check for nullable type
        if type_origin in (typing.Union, types.UnionType) and len(type_args) > 1 and type_args[1] is types.NoneType:
            options['nullable'] = True
            return cls._build_mapper(mapper_bind, **options)

        # Create mapper for list type
        if type_origin is list:
            return mappers.ListMapper(
                nullable=options.pop('nullable', False),
                default=options.pop('default', expressions.EmptyValue),
                default_factory=options.pop('default_factory', expressions.EmptyValue),
                mapper=cls._build_mapper(mapper_bind, **options)
            )

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
                **info
            ),
            alias=info.get('alias'),
            id_field=info.get('id_field', False),
            index=info.get('index'),
            sparse=info.get('sparse', False),
            unique=info.get('unique', False)
        )

    @property
    def mapper(self) -> 'mappers.Mapper':
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
        return instance.__data__.get(self.name, expressions.EmptyValue)

    def __set__(self, instance, value):
        """
        Set the value of the field.

        Args:
            instance: The instance of the owner class.
            value: The value to be set.

        """
        value = self.validate(value)
        if value is not expressions.EmptyValue:
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

    def validate(self, value) -> typing.Any:
        """
        Validate the value of the field.

        Args:
            value: The value to be validated.

        Returns:
            Any: The validated value.

        Raises:
            ValidationError: If validation fails.

        """
        try:
            value = self.mapper.validate(value)
        except ValidationError as e:
            raise ValidationError(
                errors=[ErrorWrapper(loc=(self.name,), error=i) for i in e.errors]
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
        if isinstance(mapper, mappers.ListMapper):
            mapper = mapper.mapper
        # Unwrap EmbeddedDocumentMapper or ReferencedDocumentMapper
        if isinstance(mapper, (mappers.EmbeddedDocumentMapper, mappers.ReferencedDocumentMapper)):
            mapper = mapper.document_cls

        # Check item on mapper
        try:
            getattr(mapper.__bind__ if isinstance(mapper, mappers.Mapper) else mapper, item)
        except AttributeError as e:
            # noinspection PyProtectedMember
            raise AttributeError(f'[{self._field._owner.__name__}.{self._alias}] {str(e)}') from None

        return FieldProxy(
            field=mapper.__fields__[item],
            parent=self
        )
