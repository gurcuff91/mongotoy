import re
import typing

from mongotoy import fields


class IpV4(fields.StrMapper):

    def __init__(
        self,
        nullable: bool = False,
        default: typing.Any = fields.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None
    ):
        super().__init__(nullable, default, default_factory)
        self._regex = re.compile(
            r'(\b25[0-5]|\b2[0-4][0-9]|\b[01]?[0-9][0-9]?)(\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}'
        )

    def __validate_value__(self, value) -> typing.Any:
        value = super().__validate_value__(value)
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid ip-v4')
        return value


class IpV6(fields.StrMapper):

    def __init__(
        self,
        nullable: bool = False,
        default: typing.Any = fields.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None
    ):
        super().__init__(nullable, default, default_factory)
        # noinspection RegExpSimplifiable
        self._regex = re.compile(
            r'(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:)'
            r'{1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:)'
            r'{1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]'
            r'{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]'
            r'{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}'
            r'((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|'
            r'([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|'
            r'1{0,1}[0-9]){0,1}[0-9]))'
        )

    def __validate_value__(self, value) -> typing.Any:
        value = super().__validate_value__(value)
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid ip-v6')
        return value


class Port(fields.StrMapper):

    def __init__(
        self,
        nullable: bool = False,
        default: typing.Any = fields.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None
    ):
        super().__init__(nullable, default, default_factory)
        self._regex = re.compile(
            r'^((6553[0-5])|(655[0-2][0-9])|(65[0-4][0-9]{2})|(6[0-4][0-9]{3})|([1-5][0-9]{4})|([0-5]{0,5})|'
            r'([0-9]{1,4}))$'
        )

    def __validate_value__(self, value) -> typing.Any:
        value = super().__validate_value__(value)
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid port number')
        return value


class Mac(fields.StrMapper):

    def __init__(
        self,
        nullable: bool = False,
        default: typing.Any = fields.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None
    ):
        super().__init__(nullable, default, default_factory)
        self._regex = re.compile(
            r'^[a-fA-F0-9]{2}(:[a-fA-F0-9]{2}){5}$'
        )

    def __validate_value__(self, value) -> typing.Any:
        value = super().__validate_value__(value)
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid mac address')
        return value


class Phone(fields.StrMapper):

    def __init__(
        self,
        nullable: bool = False,
        default: typing.Any = fields.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None
    ):
        super().__init__(nullable, default, default_factory)
        # noinspection RegExpRedundantEscape,RegExpSimplifiable
        self._regex = re.compile(
            r'^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$'
        )

    def __validate_value__(self, value) -> typing.Any:
        value = super().__validate_value__(value)
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid phone number')
        return value


class Email(fields.StrMapper):

    def __init__(
        self,
        nullable: bool = False,
        default: typing.Any = fields.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None
    ):
        super().__init__(nullable, default, default_factory)
        self._regex = re.compile(
            r'(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|'
            r'(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]'
            r'{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))'
        )

    def __validate_value__(self, value) -> typing.Any:
        value = super().__validate_value__(value)
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid e-mail')
        return value


class Card(fields.StrMapper):

    def __init__(
        self,
        nullable: bool = False,
        default: typing.Any = fields.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None
    ):
        super().__init__(nullable, default, default_factory)
        self._regex = re.compile(
            r'(^4[0-9]{12}(?:[0-9]{3})?$)|(^(?:5[1-5][0-9]{2}|222[1-9]|22'
            r'[3-9][0-9]|2[3-6][0-9]{2}|27[01][0-9]|2720)[0-9]{12}$)|(3[47][0-9]'
            r'{13})|(^3(?:0[0-5]|[68][0-9])[0-9]{11}$)|(^6(?:011|5[0-9]{2})[0-9]'
            r'{12}$)|(^(?:2131|1800|35\d{3})\d{11}$)'
        )

    def __validate_value__(self, value) -> typing.Any:
        value = super().__validate_value__(value)
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid credit card number')
        return value


class Ssn(fields.StrMapper):

    def __init__(
        self,
        nullable: bool = False,
        default: typing.Any = fields.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None
    ):
        super().__init__(nullable, default, default_factory)
        self._regex = re.compile(
            r'^(?!0{3})(?!6{3})[0-8]\d{2}-(?!0{2})\d{2}-(?!0{4})\d{4}$'
        )

    def __validate_value__(self, value) -> typing.Any:
        value = super().__validate_value__(value)
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid SSN')
        return value


class BitcoinAddr(fields.StrMapper):

    def __init__(
        self,
        nullable: bool = False,
        default: typing.Any = fields.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None
    ):
        super().__init__(nullable, default, default_factory)
        self._regex = re.compile(
            r'^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}$'
        )

    def __validate_value__(self, value) -> typing.Any:
        value = super().__validate_value__(value)
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid bitcoin address')
        return value


class Hashtag(fields.StrMapper):

    def __init__(
        self,
        nullable: bool = False,
        default: typing.Any = fields.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None
    ):
        super().__init__(nullable, default, default_factory)
        self._regex = re.compile(
            r'^#[^ !@#$%^&*(),.?":{}|<>]*$'
        )

    def __validate_value__(self, value) -> typing.Any:
        value = super().__validate_value__(value)
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid hashtag')
        return value


class Doi(fields.StrMapper):

    def __init__(
        self,
        nullable: bool = False,
        default: typing.Any = fields.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None
    ):
        super().__init__(nullable, default, default_factory)
        # noinspection RegExpRedundantEscape,RegExpSimplifiable
        self._regex = re.compile(
            r'^(10\.\d{4,5}\/[\S]+[^;,.\s])$'
        )

    def __validate_value__(self, value) -> typing.Any:
        value = super().__validate_value__(value)
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid DOI')
        return value


class Url(fields.StrMapper):

    def __init__(
        self,
        nullable: bool = False,
        default: typing.Any = fields.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None
    ):
        super().__init__(nullable, default, default_factory)
        # noinspection RegExpRedundantEscape,RegExpDuplicateCharacterInClass
        self._regex = re.compile(
            r'https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b'
            r'([-a-zA-Z0-9()!@:%_\+.~#?&\/\/=]*)'
        )

    def __validate_value__(self, value) -> typing.Any:
        value = super().__validate_value__(value)
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid URL')
        return value


class Version(fields.StrMapper):

    def __init__(
        self,
        nullable: bool = False,
        default: typing.Any = fields.EmptyValue,
        default_factory: typing.Callable[[], typing.Any] = None
    ):
        super().__init__(nullable, default, default_factory)
        self._regex = re.compile(
            r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-]'
            r'[0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+'
            r'([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
        )

    def __validate_value__(self, value) -> typing.Any:
        value = super().__validate_value__(value)
        if not self._regex.fullmatch(value):
            raise ValueError(f'Value {value} is not a valid semantic version number')
        return value
