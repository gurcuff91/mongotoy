import collections
import datetime
import os
import re
import typing

import bson

from mongotoy import geodata

if typing.TYPE_CHECKING:
    from mongotoy import db


class IpV4(collections.UserString):
    """
    Represents an IPv4 address.

    Args:
        value (str): The IPv4 address value.

    Raises:
        ValueError: If the value is not a valid IPv4 address.
    """

    _regex = re.compile(
        r'(\b25[0-5]|\b2[0-4][0-9]|\b[01]?[0-9][0-9]?)(\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}'
    )

    def __init__(self, value):
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid IPv4 address')
        super().__init__(value)


class IpV6(collections.UserString):
    """
    Represents an IPv6 address.

    Args:
        value (str): The IPv6 address value.

    Raises:
        ValueError: If the value is not a valid IPv6 address.
    """

    # noinspection RegExpSimplifiable
    _regex = re.compile(
        r'(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:)'
        r'{1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:)'
        r'{1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]'
        r'{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]'
        r'{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}'
        r'((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|'
        r'([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|'
        r'1{0,1}[0-9]){0,1}[0-9]))'
    )

    def __init__(self, value):
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid IPv6 address')
        super().__init__(value)


class Port(collections.UserString):
    """
    Represents a port number.

    Args:
        value (str): The port number value.

    Raises:
        ValueError: If the value is not a valid port number.
    """

    _regex = re.compile(
        r'^((6553[0-5])|(655[0-2][0-9])|(65[0-4][0-9]{2})|(6[0-4][0-9]{3})|([1-5][0-9]{4})|([0-5]{0,5})|'
        r'([0-9]{1,4}))$'
    )

    def __init__(self, value):
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid port number')
        super().__init__(value)


class Mac(collections.UserString):
    """
    Represents a MAC address.

    Args:
        value (str): The MAC address value.

    Raises:
        ValueError: If the value is not a valid MAC address.
    """

    _regex = re.compile(
        r'^[a-fA-F0-9]{2}(:[a-fA-F0-9]{2}){5}$'
    )

    def __init__(self, value):
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid MAC address')
        super().__init__(value)


class Phone(collections.UserString):
    """
    Represents a phone number.

    Args:
        value (str): The phone number value.

    Raises:
        ValueError: If the value is not a valid phone number.
    """

    # noinspection RegExpRedundantEscape,RegExpSimplifiable
    _regex = re.compile(
        r'^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$'
    )

    def __init__(self, value):
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid phone number')
        super().__init__(value)


class Email(collections.UserString):
    """
    Represents an email address.

    Args:
        value (str): The email address value.

    Raises:
        ValueError: If the value is not a valid email address.
    """

    _regex = re.compile(
        r'(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|'
        r'(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]'
        r'{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))'
    )

    def __init__(self, value):
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid email address')
        super().__init__(value)


class Card(collections.UserString):
    """
    Represents a credit card number.

    Args:
        value (str): The credit card number value.

    Raises:
        ValueError: If the value is not a valid credit card number.
    """

    _regex = re.compile(
        r'(^4[0-9]{12}(?:[0-9]{3})?$)|(^(?:5[1-5][0-9]{2}|222[1-9]|22'
        r'[3-9][0-9]|2[3-6][0-9]{2}|27[01][0-9]|2720)[0-9]{12}$)|(3[47][0-9]'
        r'{13})|(^3(?:0[0-5]|[68][0-9])[0-9]{11}$)|(^6(?:011|5[0-9]{2})[0-9]'
        r'{12}$)|(^(?:2131|1800|35\d{3})\d{11}$)'
    )

    def __init__(self, value):
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid credit card number')
        super().__init__(value)


class Ssn(collections.UserString):
    """
    Represents a Social Security Number (SSN).

    Args:
        value (str): The SSN value.

    Raises:
        ValueError: If the value is not a valid SSN.
    """

    _regex = re.compile(
        r'^(?!0{3})(?!6{3})[0-8]\d{2}-(?!0{2})\d{2}-(?!0{4})\d{4}$'
    )

    def __init__(self, value):
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid SSN')
        super().__init__(value)


class Hashtag(collections.UserString):
    """
    Represents a hashtag.

    Args:
        value (str): The hashtag value.

    Raises:
        ValueError: If the value is not a valid hashtag.
    """

    _regex = re.compile(
        r'^#[^ !@#$%^&*(),.?":{}|<>]*$'
    )

    def __init__(self, value):
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid hashtag')
        super().__init__(value)


class Doi(collections.UserString):
    """
    Represents a Digital Object Identifier (DOI).

    Args:
        value (str): The DOI value.

    Raises:
        ValueError: If the value is not a valid DOI.
    """

    # noinspection RegExpRedundantEscape,RegExpSimplifiable
    _regex = re.compile(
        r'^(10\.\d{4,5}\/[\S]+[^;,.\s])$'
    )

    def __init__(self, value):
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid DOI')
        super().__init__(value)


class Url(collections.UserString):
    """
    Represents a URL.

    Args:
        value (str): The URL value.

    Raises:
        ValueError: If the value is not a valid URL.
    """

    # noinspection RegExpDuplicateCharacterInClass,RegExpRedundantEscape
    _regex = re.compile(
        r'https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b'
        r'([-a-zA-Z0-9()!@:%_\+.~#?&\/\/=]*)'
    )

    def __init__(self, value):
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid URL')
        super().__init__(value)


class Version(collections.UserString):
    """
    Represents a Semantic Version Number.

    Args:
        value (str): The version number value.

    Raises:
        ValueError: If the value is not a valid Semantic Version Number.
    """

    _regex = re.compile(
        r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-]'
        r'[0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+'
        r'([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
    )

    def __init__(self, value):
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid Semantic Version Number')
        super().__init__(value)


class Point(geodata.Position, geodata.Geometry):
    """
    For type "Point", the "coordinates" member is a single position.

    https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.2
    """

    def __init__(self, *coordinates: int | float):
        if len(coordinates) != 2:
            raise TypeError(f'The Point must represent single position, i.e. [lat, long]')
        super().__init__(*coordinates)


class MultiPoint(list[Point], geodata.Geometry):
    """
    For type "MultiPoint", the "coordinates" member is an array of
    positions.

    https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.3
    """

    def __init__(self, *points: Point):
        super().__init__([Point(*i) for i in points])


class LineString(list[Point], geodata.Geometry):
    """
    For type "LineString", the "coordinates" member is an array of two or
    more positions.

    https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.4
    """

    def __init__(self, *points: Point):
        if not len(points) >= 2:
            raise TypeError('The LineString must be an array of two or more Points')
        super().__init__([Point(*i) for i in points])


class MultiLineString(list[LineString], geodata.Geometry):
    """
    For type "MultiLineString", the "coordinates" member is an array of
    LineString coordinate arrays.

    https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.5
    """

    def __init__(self, *lines: LineString):
        super().__init__([LineString(*i) for i in lines])


class Polygon(list[LineString], geodata.Geometry):
    """
    https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.6
    """

    def __init__(self, *rings: LineString):
        super().__init__([geodata.LinearRing(*i) for i in rings])


class MultiPolygon(list[Polygon], geodata.Geometry):
    """
     For type "MultiPolygon", the "coordinates" member is an array of
     Polygon coordinate arrays.

     https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.7
    """

    def __init__(self, *polygons: Polygon):
        super().__init__([Polygon(*i) for i in polygons])


class Json(dict):
    """
    Represents a valid json data.
    """


class Bson(bson.SON):
    """
    Represents a valid bson data.
    """


class File(typing.Protocol):
    # noinspection SpellCheckingInspection
    """
    This is a facade for type mogotoy.db.FsObject
    """
    id: bson.ObjectId
    filename: str
    metadata: Json
    chunk_size: int
    length: int
    upload_date: datetime.datetime
    content_type: str
    chunks: int

    def create_revision(
        self,
        fs: 'db.FsBucket',
        src: typing.IO | bytes,
        metadata: dict = None
    ) -> typing.Union[typing.Coroutine[typing.Any, typing.Any, 'File'], 'File']:
        pass

    # noinspection SpellCheckingInspection
    def download_to(
        self,
        fs: 'db.FsBucket',
        dest: typing.IO,
        revision: int = None
    ) -> typing.Coroutine[typing.Any, typing.Any, None] | None:
        pass

    def stream(
        self,
        fs: 'db.FsBucket',
        revision: int = None
    ) -> typing.Union[typing.Coroutine[typing.Any, typing.Any, 'FileStream'], 'FileStream']:
        pass

    def delete(self, fs: 'db.FsBucket') -> typing.Coroutine[typing.Any, typing.Any, None] | None:
        pass


class FileStream(typing.Protocol):
    # noinspection SpellCheckingInspection
    """
    This is a facade for type mogotoy.db.FsObjectStream
    """

    def seek(self, pos: int, whence: int = os.SEEK_SET) -> int:
        pass

    def seekable(self) -> bool:
        pass

    def tell(self) -> int:
        pass

    def close(self):
        pass

    def read(self, size: int = -1) -> typing.Coroutine[typing.Any, typing.Any, bytes] | bytes:
        pass

    # noinspection SpellCheckingInspection
    def readchunk(self) -> typing.Coroutine[typing.Any, typing.Any, bytes] | bytes:
        pass

    def readline(self, size: int = -1) -> typing.Coroutine[typing.Any, typing.Any, bytes] | bytes:
        pass
