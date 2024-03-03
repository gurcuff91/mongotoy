import abc
import datetime
import decimal
import typing
import uuid

import bson

from mongotoy import cache, expressions, references, types, geodata
from mongotoy.errors import ValidationError, ErrorWrapper

if typing.TYPE_CHECKING:
    from mongotoy import documents, fields


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
        cache.mappers.add_type(_cls.__bind__, _cls)

        return _cls


class Mapper(abc.ABC, metaclass=MapperMeta):
    """
    Abstract base class for data mappers.
    """

    def __init__(
        self,
        nullable: bool = False,
        default: typing.Any = expressions.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None
    ):
        self._nullable = nullable
        self._default_factory = default_factory if default_factory else lambda: default

    def validate(self, value) -> typing.Any:
        if value is expressions.EmptyValue:
            value = self._default_factory()
            if value is expressions.EmptyValue:
                return value

        if value is None:
            if not self._nullable:
                raise ValueError('Null valued not allowed')
            return value

        try:
            value = self.__validate_value__(value)
        except (TypeError, ValueError) as e:
            # noinspection PyTypeChecker
            raise ValidationError(
                errors=[ErrorWrapper(loc=(), error=e)]
            ) from None

        return value

    @abc.abstractmethod
    def __validate_value__(self, value) -> typing.Any:
        """
        Validate the value.

        Args:
            value: The value to be validated.

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

    def __init__(
        self,
        mapper: Mapper,
        nullable: bool = False,
        default: typing.Any = expressions.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None,
    ):
        """
        Initialize the ListMapper.

        Args:
            mapper (Mapper): The mapper for the list items.

        """
        self._mapper = mapper
        super().__init__(nullable, default, default_factory)

    @property
    def mapper(self) -> Mapper:
        """
        Get the mapper for the list items.

        Returns:
            Mapper: The mapper for the list items.

        """
        return self._mapper

    def __validate_value__(self, value) -> typing.Any:
        """
        Validate the list value.

        Args:
            value: The list value to be validated.

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
                new_value.append(self.mapper.validate(val))
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

    def __init__(
        self,
        document_cls: typing.Type['documents.BaseDocument'] | str,
        nullable: bool = False,
        default: typing.Any = expressions.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None,
    ):
        """
        Initialize the EmbeddedDocumentMapper.

        Args:
            document_cls (Type['documents.BaseDocument'] | str): The class or name of the embedded document.

        """
        self._document_cls = document_cls
        super().__init__(nullable, default, default_factory)

    @property
    def document_cls(self) -> typing.Type['documents.BaseDocument']:
        """
        Get the class of the embedded document.

        Returns:
            Type['documents.BaseDocument']: The class of the embedded document.

        """
        return references.get_base_document_cls(self._document_cls)

    def __validate_value__(self, value) -> typing.Any:
        """
        Validate the embedded document value.

        Args:
            value: The value to be validated.

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
        nullable: bool = False,
        default: typing.Any = expressions.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None,
    ):
        """
        Initialize the ReferencedDocumentMapper.

        Args:
            document_cls (Type['documents.BaseDocument'] | str): The class or name of the referenced document.
            ref_field (str): The name of the referenced field.
            key_name (str): The key name for the reference.
        """
        self._ref_field = ref_field
        self._key_name = key_name
        super().__init__(document_cls, nullable, default, default_factory)

    @property
    def document_cls(self) -> typing.Type['documents.Document']:
        """
        Get the class of the referenced document.

        Returns:
            Type['documents.BaseDocument']: The class of the referenced document.

        """
        return references.get_document_cls(self._document_cls)

    @property
    def ref_field(self) -> 'fields.Field':
        """
        Get the reference field.

        Returns:
            Field: The reference field.

        """
        return references.get_field(self._ref_field, document_cls=self.document_cls)

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

    def __validate_value__(self, value) -> typing.Any:
        """
        Validate the string value.

        Args:
            value: The value to be validated.

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

    def __validate_value__(self, value) -> typing.Any:
        """
        Validate the integer value.

        Args:
            value: The value to be validated.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if not isinstance(value, int):
            raise TypeError(f'Invalid data type {type(value)}, required is {int}')
        return value


class BoolMapper(Mapper, bind=bool):
    """
    Mapper for handling integer values.
    """

    def __validate_value__(self, value) -> typing.Any:
        """
        Validate the boolean value.

        Args:
            value: The value to be validated.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if not isinstance(value, bool):
            raise TypeError(f'Invalid data type {type(value)}, required is {bool}')
        return value


class BinMapper(Mapper, bind=bytes):
    """
    Mapper for handling binary values.
    """

    def __validate_value__(self, value) -> typing.Any:
        """
        Validate the boolean value.

        Args:
            value: The value to be validated.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if not isinstance(value, bytes):
            raise TypeError(f'Invalid data type {type(value)}, required is {bytes}')
        return value

    def dump_json(self, value, **options) -> typing.Any:
        import base64
        return (
            f'data:application/octet-stream;base64,'
            f'{base64.b64encode(value).decode()}'
        )


class FloatMapper(Mapper, bind=float):
    """
    Mapper for handling float values.
    """

    def __validate_value__(self, value) -> typing.Any:
        """
        Validate the float value.

        Args:
            value: The value to be validated.

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

    def __validate_value__(self, value) -> typing.Any:
        """
        Validate the ObjectId value.

        Args:
            value: The value to be validated.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if not isinstance(value, bson.ObjectId):
            raise TypeError(f'Invalid data type {type(value)}, required is {bson.ObjectId}')
        return value

    def dump_json(self, value, **options) -> typing.Any:
        return str(value)


class DecimalMapper(Mapper, bind=decimal.Decimal):
    """
    Mapper for handling decimal values.
    """

    def __validate_value__(self, value) -> typing.Any:
        """
        Validate the decimal value.

        Args:
            value: The value to be validated.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if isinstance(value, bson.Decimal128):
            value = value.to_decimal()
        if not isinstance(value, decimal.Decimal):
            raise TypeError(f'Invalid data type {type(value)}, required is {decimal.Decimal}')

        # Ensure decimal limits for mongodb
        # https://www.mongodb.com/docs/upcoming/release-notes/3.4/#decimal-type
        ctx = decimal.Context(prec=34)
        return ctx.create_decimal(value)

    def dump_json(self, value, **options) -> typing.Any:
        return float(value)

    def dump_bson(self, value, **options) -> typing.Any:
        return bson.Decimal128(value)


class UUIDMapper(Mapper, bind=uuid.UUID):
    """
    Mapper for handling UUID values.
    """

    def __validate_value__(self, value) -> typing.Any:
        """
        Validate the UUID value.

        Args:
            value: The value to be validated.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if not isinstance(value, uuid.UUID):
            raise TypeError(f'Invalid data type {type(value)}, required is {uuid.UUID}')
        return value

    def dump_json(self, value, **options) -> typing.Any:
        return str(value)


class DateTimeMapper(Mapper, bind=datetime.datetime):
    """
    Mapper for handling datetime values.
    """

    def __validate_value__(self, value) -> typing.Any:
        """
        Validate the datetime value.

        Args:
            value: The value to be validated.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if not isinstance(value, datetime.datetime):
            raise TypeError(f'Invalid data type {type(value)}, required is {datetime.datetime}')
        return value

    def dump_json(self, value, **options) -> typing.Any:
        return value.isoformat()


class DateMapper(Mapper, bind=datetime.date):
    """
    Mapper for handling date values.
    """

    def __validate_value__(self, value) -> typing.Any:
        """
        Validate the date value.

        Args:
            value: The value to be validated.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if not isinstance(value, datetime.date):
            raise TypeError(f'Invalid data type {type(value)}, required is {datetime.date}')
        return value

    def dump_json(self, value, **options) -> typing.Any:
        return value.isoformat()


class TimeMapper(Mapper, bind=datetime.time):
    """
    Mapper for handling timedelta values.
    """

    def __validate_value__(self, value) -> typing.Any:
        """
        Validate the timedelta value.

        Args:
            value: The value to be validated.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if not isinstance(value, datetime.time):
            raise TypeError(f'Invalid data type {type(value)}, required is {datetime.time}')
        return value

    def dump_json(self, value, **options) -> typing.Any:
        return value.isoformat()


class IpV4Mapper(StrMapper, bind=types.IpV4):

    def __validate_value__(self, value) -> typing.Any:
        return types.IpV4(super().__validate_value__(value))


class IpV6Mapper(StrMapper, bind=types.IpV6):

    def __validate_value__(self, value) -> typing.Any:
        return types.IpV6(super().__validate_value__(value))


class PortMapper(StrMapper, bind=types.Port):

    def __validate_value__(self, value) -> typing.Any:
        return types.Port(super().__validate_value__(value))


class MacMapper(StrMapper, bind=types.Mac):

    def __validate_value__(self, value) -> typing.Any:
        return types.Mac(super().__validate_value__(value))


class PhoneMapper(StrMapper, bind=types.Phone):

    def __validate_value__(self, value) -> typing.Any:
        return types.Phone(super().__validate_value__(value))


class EmailMapper(StrMapper, bind=types.Email):

    def __validate_value__(self, value) -> typing.Any:
        return types.Email(super().__validate_value__(value))


class CardMapper(StrMapper, bind=types.Card):

    def __validate_value__(self, value) -> typing.Any:
        return types.Card(super().__validate_value__(value))


class SsnMapper(StrMapper, bind=types.Ssn):

    def __validate_value__(self, value) -> typing.Any:
        return types.Ssn(super().__validate_value__(value))


class HashtagMapper(StrMapper, bind=types.Hashtag):

    def __validate_value__(self, value) -> typing.Any:
        return types.Hashtag(super().__validate_value__(value))


class DoiMapper(StrMapper, bind=types.Doi):

    def __validate_value__(self, value) -> typing.Any:
        return types.Doi(super().__validate_value__(value))


class UrlMapper(StrMapper, bind=types.Url):

    def __validate_value__(self, value) -> typing.Any:
        return types.Url(super().__validate_value__(value))


class VersionMapper(StrMapper, bind=types.Version):

    def __validate_value__(self, value) -> typing.Any:
        return types.Version(super().__validate_value__(value))


class GeometryMapper(Mapper):

    def __validate_value__(self, value) -> typing.Any:
        if isinstance(value, dict):
            # noinspection PyTypeChecker
            value = geodata.parse_geojson(value, parser=self.__bind__)
        if not isinstance(value, types.Point):
            raise TypeError(f'Invalid data type {type(value)}, required is {self.__bind__}')
        return value

    def dump_json(self, value, **options) -> typing.Any:
        return value.dump_geojson()

    def dump_bson(self, value, **options) -> typing.Any:
        return value.dump_geojson()


class PointMapper(GeometryMapper, bind=types.Point):
    pass


class MultiPointMapper(GeometryMapper, bind=types.MultiPoint):
    pass


class LineStringMapper(GeometryMapper, bind=types.LineString):
    pass


class MultiLineStringMapper(GeometryMapper, bind=types.MultiLineString):
    pass


class PolygonMapper(GeometryMapper, bind=types.Polygon):
    pass


class MultiPolygonMapper(GeometryMapper, bind=types.MultiPolygon):
    pass
