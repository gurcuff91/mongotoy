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

    Args:
        nullable (bool, optional): Whether the value can be None. Defaults to False.
        default (Any, optional): Default value for the mapper. Defaults to expressions.EmptyValue.
        default_factory (Callable[[], Any], optional): A callable that returns the default value.
            Defaults to None.
    """

    if typing.TYPE_CHECKING:
        __bind__: typing.Type

    def __init__(
        self,
        nullable: bool = False,
        default: typing.Any = expressions.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None
    ):
        self._nullable = nullable
        self._default_factory = default_factory if default_factory else lambda: default

    def __call__(self, value) -> typing.Any:
        """
        Validate the value against the mapper.

        Args:
            value (Any): The value to be validated.

        Raises:
            ValueError: If the value is invalid.

        Returns:
            Any: The validated value.
        """
        if value is expressions.EmptyValue:
            value = self._default_factory()
            if value is expressions.EmptyValue:
                return value

        if value is None:
            if not self._nullable:
                raise ValueError('Null value not allowed')
            return value

        try:
            value = self.validate(value)
        except (TypeError, ValueError) as e:
            raise ValidationError(errors=[ErrorWrapper(loc=tuple(), error=e)]) from None

        return value

    @abc.abstractmethod
    def validate(self, value) -> typing.Any:
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
        Dump the value to be in a dictionary.

        Args:
            value: The value to be dumped.
            **options: Additional options.

        Returns:
            Any: The dumped value.

        """
        return value

    def dump_json(self, value, **options) -> typing.Any:
        """
        Dump the value to valid JSON.

        Args:
            value: The value to be dumped.
            **options: Additional options.

        Returns:
            Any: The dumped value.

        """
        return value

    def dump_bson(self, value, **options) -> typing.Any:
        """
        Dump the value to valid BSON.

        Args:
            value: The value to be dumped.
            **options: Additional options.

        Returns:
            Any: The dumped value.

        """
        return value


class ManyMapper(Mapper):
    """
    Mapper for handling lists of elements.
    """

    def __init__(
        self,
        mapper: Mapper,
        nullable: bool = False,
        default: typing.Any = expressions.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None,
    ):
        """
        Initialize the ManyMapper.

        Args:
            mapper (Mapper): The mapper for the list items.

        """
        self._mapper = mapper
        # ManyMapper must be at least empty list not an EmptyValue for ReferencedDocumentMapper
        if default is expressions.EmptyValue and isinstance(self.unwrap(), ReferencedDocumentMapper):
            default = []
        super().__init__(nullable, default, default_factory)

    @property
    def mapper(self) -> Mapper:
        """
        Get the mapper for the list items.

        Returns:
            Mapper: The mapper for the list items.

        """
        return self._mapper

    def unwrap(self) -> Mapper:
        """Get the innermost mapper that isn't a ManyMapper"""
        mapper_ = self.mapper
        while isinstance(mapper_, ManyMapper):
            mapper_ = mapper_.mapper
        return mapper_

    def validate(self, value) -> typing.Any:
        """
        Validate the list value.

        Args:
            value: The list value to be validated.

        Returns:
            Any: The validated list value.

        Raises:
            ValidationError: If validation fails.

        """
        if not isinstance(value, self.__bind__):
            raise TypeError(f'Invalid data type {type(value)}, required is {self.__bind__}')

        new_value = []
        errors = []
        # noinspection PyTypeChecker
        for i, val in enumerate(value):
            try:
                new_value.append(self.mapper(val))
            except ValidationError as e:
                errors.extend([ErrorWrapper(loc=(str(i),), error=j) for j in e.errors])
        if errors:
            raise ValidationError(errors=errors)

        return self.__bind__(new_value)

    def dump_dict(self, value, **options) -> typing.Any:
        """
        Dump the list value to a dictionary.

        Args:
            value: The list value to be dumped.
            **options: Additional options.

        Returns:
            Any: The dumped list value.

        """
        return self.__bind__([self.mapper.dump_dict(i, **options) for i in value])

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


class ListMapper(ManyMapper, bind=list):
    """
    Mapper for handling lists.
    """


class TupleMapper(ManyMapper, bind=tuple):
    """
    Mapper for handling tuples.
    """


class SetMapper(ManyMapper, bind=set):
    """
    Mapper for handling sets.
    """


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
    def document_cls(self) -> typing.Type['documents.EmbeddedDocument']:
        """
        Get the class of the embedded document.

        Returns:
            Type['documents.BaseDocument']: The class of the embedded document.

        """
        return references.get_embedded_document_cls(self._document_cls)

    def validate(self, value) -> typing.Any:
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
        key_name: str = None,
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

    def validate(self, value) -> typing.Any:
        value = super().validate(value)
        if getattr(value, self.ref_field.name) is expressions.EmptyValue:
            raise ValueError(
                f'Referenced field {self.document_cls.__name__}.{self.ref_field.name} value required'
            )
        return value

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

    def validate(self, value) -> typing.Any:
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

    def validate(self, value) -> typing.Any:
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

    def validate(self, value) -> typing.Any:
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


class BinaryMapper(Mapper, bind=bytes):
    """
    Mapper for handling binary values.
    """

    def validate(self, value) -> typing.Any:
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

    def validate(self, value) -> typing.Any:
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

    def validate(self, value) -> typing.Any:
        """
        Validate the ObjectId value.

        Args:
            value: The value to be validated.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if not bson.ObjectId.is_valid(value):
            raise TypeError(f'Invalid data type {type(value)}, required is {bson.ObjectId}')
        return bson.ObjectId(value)

    def dump_json(self, value, **options) -> typing.Any:
        return str(value)


class DecimalMapper(Mapper, bind=decimal.Decimal):
    """
    Mapper for handling decimal values.
    """

    def validate(self, value) -> typing.Any:
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

    def validate(self, value) -> typing.Any:
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

    def validate(self, value) -> typing.Any:
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

    def validate(self, value) -> typing.Any:
        """
        Validate the date value.

        Args:
            value: The value to be validated.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if isinstance(value, datetime.datetime):
            value = value.date()
        if not isinstance(value, datetime.date):
            raise TypeError(f'Invalid data type {type(value)}, required is {datetime.date}')
        return value

    def dump_json(self, value, **options) -> typing.Any:
        return value.isoformat()

    def dump_bson(self, value, **options) -> typing.Any:
        return datetime.datetime.combine(date=value, time=datetime.time.min)


class TimeMapper(Mapper, bind=datetime.time):
    """
    Mapper for handling timedelta values.
    """

    def validate(self, value) -> typing.Any:
        """
        Validate the timedelta value.

        Args:
            value: The value to be validated.

        Returns:
            Any: The validated value.

        Raises:
            TypeError: If validation fails due to incorrect data type.

        """
        if isinstance(value, datetime.datetime):
            value = value.time()
        if not isinstance(value, datetime.time):
            raise TypeError(f'Invalid data type {type(value)}, required is {datetime.time}')
        return value

    def dump_json(self, value, **options) -> typing.Any:
        return value.isoformat()

    def dump_bson(self, value, **options) -> typing.Any:
        return datetime.datetime.combine(date=datetime.datetime.min, time=value)


class ConstrainedStrMapper(StrMapper):

    def validate(self, value) -> typing.Any:
        return self.__bind__(super().validate(value))

    def dump_json(self, value, **options) -> typing.Any:
        return str(value)

    def dump_bson(self, value, **options) -> typing.Any:
        return str(value)


class IpV4Mapper(ConstrainedStrMapper, bind=types.IpV4):
    pass


class IpV6Mapper(ConstrainedStrMapper, bind=types.IpV6):
    pass


class PortMapper(ConstrainedStrMapper, bind=types.Port):
    pass


class MacMapper(ConstrainedStrMapper, bind=types.Mac):
    pass


class PhoneMapper(ConstrainedStrMapper, bind=types.Phone):
    pass


class EmailMapper(ConstrainedStrMapper, bind=types.Email):
    pass


class CardMapper(ConstrainedStrMapper, bind=types.Card):
    pass


class SsnMapper(ConstrainedStrMapper, bind=types.Ssn):
    pass


class HashtagMapper(ConstrainedStrMapper, bind=types.Hashtag):
    pass


class DoiMapper(ConstrainedStrMapper, bind=types.Doi):
    pass


class UrlMapper(ConstrainedStrMapper, bind=types.Url):
    pass


class VersionMapper(ConstrainedStrMapper, bind=types.Version):
    pass


class GeometryMapper(Mapper):
    """
    Mapper class for geometry data.

    This mapper validates and handles geometry data.
    """

    def validate(self, value) -> typing.Any:
        """
        Validate the value against the mapper.

        Args:
            value (Any): The value to be validated.

        Raises:
            TypeError: If the value is not of the expected type.

        Returns:
            Any: The validated value.
        """
        if isinstance(value, dict):
            value = geodata.parse_geojson(value, parser=self.__bind__)
        if not isinstance(value, self.__bind__):
            raise TypeError(f'Invalid data type {type(value)}, required is {self.__bind__}')
        return value

    def dump_json(self, value, **options) -> typing.Any:
        return {
            'type': self.__bind__.__name__,
            'coordinates': list(value)
        }

    def dump_bson(self, value, **options) -> typing.Any:
        return self.dump_json(value, **options)


class PointMapper(GeometryMapper, bind=types.Point):
    """
    Mapper class for Point geometry data.
    """


class MultiPointMapper(GeometryMapper, bind=types.MultiPoint):
    """
    Mapper class for MultiPoint geometry data.
    """


class LineStringMapper(GeometryMapper, bind=types.LineString):
    """
    Mapper class for LineString geometry data.
    """


class MultiLineStringMapper(GeometryMapper, bind=types.MultiLineString):
    """
    Mapper class for MultiLineString geometry data.
    """


class PolygonMapper(GeometryMapper, bind=types.Polygon):
    """
    Mapper class for Polygon geometry data.
    """


class MultiPolygonMapper(GeometryMapper, bind=types.MultiPolygon):
    """
    Mapper class for MultiPolygon geometry data.
    """


class JsonMapper(Mapper, bind=types.Json):

    def validate(self, value) -> typing.Any:
        if not isinstance(value, dict):
            raise TypeError(f'Invalid data type {type(value)}, required is {types.Json}')

        # Check Json valid data
        import json
        try:
            json.dumps(value)
        except Exception as e:
            raise ValueError(f'Invalid JSON data: {str(e)}') from None

        return types.Json(value)

    def dump_json(self, value, **options) -> typing.Any:
        return dict(value)

    def dump_bson(self, value, **options) -> typing.Any:
        return self.dump_json(value, **options)


class BsonMapper(Mapper, bind=types.Bson):

    def validate(self, value) -> typing.Any:
        if not isinstance(value, dict):
            raise TypeError(f'Invalid data type {type(value)}, required is {types.Bson}')

        # Check Bson valid data
        try:
            bson.encode(value)
        except Exception as e:
            raise ValueError(f'Invalid BSON data: {str(e)}') from None

        return types.Bson(value)

    def dump_json(self, value, **options) -> typing.Any:
        # noinspection SpellCheckingInspection
        raise NotImplementedError(
            'mongotoy.types.Bson does not implement dump_json, use mongotoy.types.Json instead'
        )

    def dump_bson(self, value, **options) -> typing.Any:
        return bson.SON(value)


class FileMapper(ReferencedDocumentMapper, bind=types.File):

    def __init__(
        self,
        nullable: bool = False,
        default: typing.Any = expressions.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None
    ):
        from mongotoy import db
        super().__init__(
            document_cls=db.FsObject,
            ref_field='id',
            nullable=nullable,
            default=default,
            default_factory=default_factory
        )
