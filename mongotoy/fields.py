import dataclasses
import re
import typing

import pymongo

from mongotoy import expressions, mappers
from mongotoy.errors import ValidationError, ErrorWrapper


__all__ = (
    'FieldOptions',
    'field',
    'reference',
)


@dataclasses.dataclass
class FieldOptions(mappers.MapperOptions):
    """
    Represents the options for configuring a field in a document.
    Inherits from MapperOptions and adds additional attributes for field customization.
    Attributes:
        alias (str): Alias name for the field. Defaults to None.
        id_field (bool): Flag indicating whether the field is the primary key. Defaults to False.
        index (expressions.IndexType): Type of index to apply to the field. Defaults to None.
        sparse (bool): Flag indicating whether the index should be sparse. Defaults to False.
        unique (bool): Flag indicating whether the field value must be unique. Defaults to False.
    """
    alias: str = dataclasses.field(default=None)
    id_field: bool = dataclasses.field(default=False)
    index: expressions.IndexType = dataclasses.field(default=None)
    sparse: bool = dataclasses.field(default=False)
    unique: bool = dataclasses.field(default=False)


def field(
        alias: str = None,
        id_field: bool = False,
        default: typing.Any = expressions.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None,
        index: expressions.IndexType = None,
        sparse: bool = False,
        unique: bool = False,
        lt: typing.Any = None,
        lte: typing.Any = None,
        gt: typing.Any = None,
        gte: typing.Any = None,
        min_items: typing.Optional[int] = None,
        max_items: typing.Optional[int] = None,
        min_length: typing.Optional[int] = None,
        max_length: typing.Optional[int] = None,
        choices: typing.Optional[list[str]] = None,
        regex: re.Pattern = None,
        **extra
) -> FieldOptions:
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
        lt (Any): Upper bound for the field value.
        lte (Any): Upper bound (inclusive) for the field value.
        gt (Any): Lower bound for the field value.
        gte (Any): Lower bound (inclusive) for the field value.
        min_items (int, optional): Minimum number of items for sequence fields.
        max_items (int, optional): Maximum number of items for sequence fields.
        min_length (int, optional): Minimum length for string fields.
        max_length (int, optional): Maximum length for string fields.
        choices (list[str], optional): List of allowed choices for string fields.
        regex (re.Pattern): Regular expression for string fields.
        extra: Extra options for customization. Defaults to empty dict.

    Returns:
        FieldOptions: Field descriptor.

    """
    return FieldOptions(
        alias=alias,
        id_field=id_field,
        default=default,
        default_factory=default_factory,
        index=index,
        sparse=sparse,
        unique=unique,
        lt=lt,
        lte=lte,
        gt=gt,
        gte=gte,
        min_items=min_items,
        max_items=max_items,
        min_length=min_length,
        max_length=max_length,
        choices=choices,
        regex=regex,
        extra=extra
    )


def reference(ref_field: str = 'id', key_name: str = None) -> FieldOptions:
    """
    Create a reference field descriptor for a document.

    Args:
        ref_field (str): Name of the referenced field.
        key_name (str, optional): Key name for the reference. Defaults to None.

    Returns:
        RefFieldOptions: Reference field descriptor.

    """
    return FieldOptions(ref_field=ref_field, key_name=key_name)


class Field:
    """
    Class for defining document fields.

    This class represents a field in a document schema. It allows specifying various attributes such as the field
    mapper, alias, index type, and uniqueness.

    Args:
        mapper (Mapper): The mapper object for the field.
        options (FieldOptions): File configuration params.
    """

    def __init__(
        self,
        mapper: mappers.Mapper,
        options: FieldOptions
    ):
        # If it's an ID field, enforce specific settings
        if options.id_field:
            options.alias = '_id'

        # Initialize field attributes
        self._owner = None
        self._name = None
        self._mapper = mapper
        self._options = options

    @property
    def mapper(self) -> mappers.Mapper:
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
        return self._options.alias or self._name

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
        if self._options.unique or self._options.sparse:
            index = pymongo.ASCENDING
        if self._options.index is not None:
            index = self._options.index
        if index:
            return pymongo.IndexModel(
                keys=[(self.alias, index)],
                unique=self._options.unique,
                sparse=self._options.sparse
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
            # Validate value
            value = self.mapper(value)

            # Check id value
            if self.alias == '_id' and value is expressions.EmptyValue:
                raise ValidationError([
                    ErrorWrapper(loc=tuple(), error=ValueError('Id field value required'))
                ])
        except ValidationError as e:
            raise ValidationError(
                errors=[ErrorWrapper(loc=(self.name,), error=i) for i in e.errors]
            ) from None

        return value


class FieldProxy:
    """
    Proxy class for fields.

    This class provides a proxy interface for accessing fields in a document schema. It allows for convenient field
    access and query construction using dot notation.

    Args:
        field (Field): The field object to proxy.
        parent (FieldProxy, optional): The parent proxy if the field is nested within another field. Defaults to None.

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
            return f'{self._parent._alias}.{self._field.alias}'
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

    def __pos__(self):
        """
        Represents ascending sort expression of the field.

        Returns:
            Sort: Sort object representing ascending sort expression.
        """
        return expressions.Sort.Asc(self)

    def __neg__(self):
        """
        Represents descending sort expression of the field.

        Returns:
            Sort: Sort object representing descending sort expression.
        """
        return expressions.Sort.Desc(self)

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
        # Unwrap ManyMapper
        mapper = self._field.mapper
        if isinstance(mapper, mappers.SequenceMapper):
            mapper = mapper.unwrap()

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
