import abc
import dataclasses
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Literal

import bson
import pymongo
from pymongo.read_concern import ReadConcern

from mongotoy import cache, expressions, references, fields, mappers
from mongotoy.errors import DocumentError, ValidationError, DocumentValidationError

__all__ = (
    'EmbeddedDocument',
    'DocumentConfig',
    'Document',
)


class BaseDocumentMeta(abc.ABCMeta):
    """
    Metaclass for base document class.
    """

    def __new__(mcls, name, bases, namespace, **kwargs):
        """
        Creates a new instance of the base document class.

        Args:
            name (str): The name of the class.
            bases (tuple): The base classes of the class.
            namespace (dict): The namespace of the class.
            **kwargs: Additional keyword arguments.

        Returns:
            type: The new class instance.

        Raises:
            DocumentError: If an error occurs during class creation.

        """
        # Add base classes fields
        _fields = OrderedDict()
        for base in bases:
            _fields.update(getattr(base, '__fields__', {}))

        # Add class namespace declared fields
        for field_name, anno_type in namespace.get('__annotations__', {}).items():
            options = namespace.get(field_name, fields.FieldOptions())
            if not isinstance(options, fields.FieldOptions):
                # noinspection PyTypeChecker,SpellCheckingInspection
                raise DocumentError(
                    loc=(name, field_name),
                    msg=f'Invalid field descriptor {type(options)}. '
                        f'Use mongotoy.field() or mongotoy.reference() descriptors'
                )
            try:
                _fields[field_name] = fields.Field(
                    mapper=mappers.build_mapper(anno_type, options=options),
                    options=options
                )
            except TypeError as e:
                # noinspection PyTypeChecker
                raise DocumentError(
                    loc=(name, field_name),
                    msg=f'Invalid field annotation {anno_type}. {str(e)}'
                ) from None
            except Exception as e:
                # noinspection PyTypeChecker
                raise DocumentError(
                    loc=(name, field_name),
                    msg=str(e)
                )

        # Update namespace with fields
        namespace.update(_fields)
        # Build class
        _cls = super().__new__(mcls, name, bases, namespace)
        # Set cls fields
        _cls.__fields__ = _fields
        # Register class
        cache.documents.add_type(name, _cls)

        return _cls


# noinspection PyUnresolvedReferences
class BaseDocument(abc.ABC, metaclass=BaseDocumentMeta):
    """
    Base class representing a document.

    This class serves as the foundation for defining documents. It provides methods for dumping document data in
    various formats.

    Attributes:
        __fields__ (dict[str, fields.Field]): Dictionary mapping field names to Field objects.
        __data__ (dict[str, Any]): Dictionary storing document data.

    """

    if TYPE_CHECKING:
        __fields__: dict[str, fields.Field]
        __data__: dict[str, Any]

    def __init__(self, **data):
        self.__data__ = {}
        errors = []
        for field in self.__fields__.values():
            value = data.get(field.alias, data.get(field.name, expressions.EmptyValue))
            try:
                field.__set__(self, value=value)
            except ValidationError as e:
                errors.extend(e.errors)
        if errors:
            raise DocumentValidationError(self.__class__, errors=errors)

    def _dump(
        self,
        mode: Literal['dict', 'json', 'bson'] | None,
        by_alias: bool = False,
        exclude_empty: bool = False,
        exclude_null: bool = False
    ) -> dict:
        """
        Dumps the document data.

        Args:
            mode (Literal['dict', 'json', 'bson'] | None): The dump mode.
            by_alias (bool): Flag to dump by alias.
            exclude_empty (bool): Flag to exclude empty fields.
            exclude_null (bool): Flag to exclude null fields.

        Returns:
            dict: The dumped data.

        """
        data = {}
        for field in self.__fields__.values():
            value = field.__get__(self, owner=self.__class__)
            if exclude_empty and value is expressions.EmptyValue:
                continue
            if exclude_null and value is None:
                continue

            if mode:
                dumper_fn = getattr(field.mapper, f'dump_{mode}')
                value = dumper_fn(
                    value,
                    by_alias=by_alias,
                    exclude_empty=exclude_empty,
                    exclude_null=exclude_null,
                ) if value not in (expressions.EmptyValue, None) else value

            data[field.alias if by_alias else field.name] = value

        return data

    def dump_dict(
        self,
        by_alias: bool = False,
        exclude_empty: bool = False,
        exclude_null: bool = False
    ) -> dict:
        """
        Dumps the document data to a dictionary.

        Args:
            by_alias (bool): Flag to dump by alias.
            exclude_empty (bool): Flag to exclude empty fields.
            exclude_null (bool): Flag to exclude null fields.

        Returns:
            dict: The dumped data.

        """
        return self._dump(
            mode='dict',
            by_alias=by_alias,
            exclude_empty=exclude_empty,
            exclude_null=exclude_null
        )

    # noinspection PyUnusedLocal
    def dump_json(
        self,
        by_alias: bool = False,
        exclude_null: bool = False,
        **_
    ) -> dict:
        """
        Dumps the document data to JSON format.

        Args:
            by_alias (bool): Flag to dump by alias.
            exclude_null (bool): Flag to exclude null fields.

        Returns:
            dict: The dumped data.

        """
        return self._dump(
            mode='json',
            by_alias=by_alias,
            exclude_empty=True,
            exclude_null=exclude_null
        )

    # noinspection PyUnusedLocal
    def dump_bson(
        self,
        by_alias: bool = True,
        exclude_null: bool = False,
        **_
    ) -> bson.SON:
        """
        Dumps the document data to BSON format.

        Args:
            by_alias (bool): Flag to dump by alias.
            exclude_null (bool): Flag to exclude null fields.

        Returns:
            bson.SON: The dumped data.

        """
        return bson.SON(
            self._dump(
                mode='bson',
                by_alias=by_alias,
                exclude_empty=True,
                exclude_null=exclude_null
            )
        )


class EmbeddedDocument(BaseDocument):
    """
    Class representing an embedded document.

    This class serves as a base for defining embedded documents within other documents. It inherits functionality
    from the BaseDocument class.
    """


class DocumentMeta(BaseDocumentMeta):
    """
    Metaclass for document class.
    """

    # noinspection PyUnresolvedReferences
    def __new__(mcls, name, bases, namespace, **kwargs):
        """
        Creates a new instance of the document class.

        Args:
            name (str): The name of the class.
            bases (tuple): The base classes of the class.
            namespace (dict): The namespace of the class.
            **kwargs: Additional keyword arguments.

        Returns:
            type: The new class instance.

        Raises:
            DocumentError: If an error occurs during class creation.

        """
        _cls = super().__new__(mcls, name, bases, namespace)

        _id_field = None
        _references = OrderedDict()
        for field in _cls.__fields__.values():
            # Check id field
            # noinspection PyProtectedMember
            if field._options.id_field:
                _id_field = field

            # Unwrap ManyMapper
            _mapper = field.mapper
            _is_many = False
            if isinstance(_mapper, mappers.SequenceMapper):
                _mapper = _mapper.unwrap()
                _is_many = True

            # Add references
            if isinstance(_mapper, mappers.ReferencedDocumentMapper):
                # noinspection PyProtectedMember,PyUnresolvedReferences
                _references[field.name] = references.Reference(
                    document_cls=_mapper._document_cls,
                    ref_field=_mapper._options.ref_field,
                    key_name=_mapper._options.key_name or f'{field.alias}_{_mapper._options.ref_field}',
                    is_many=_is_many,
                    name=field.alias
                )

        if not _id_field:
            _options = fields.FieldOptions(
                id_field=True,
                default_factory=bson.ObjectId
            )
            _id_field = fields.Field(
                mapper=mappers.ObjectIdMapper(options=_options),
                options=_options
            )
            _id_field.__set_name__(_cls, 'id')

        # Set class props
        _cls.__fields__['id'] = _id_field
        _cls.__references__ = _references
        _cls.__collection_name__ = namespace.get('__collection_name__', f'{name.lower()}s')
        _cls.id = _id_field
        _cls.document_config = namespace.get('document_config', DocumentConfig())

        return _cls


@dataclasses.dataclass
class DocumentConfig:
    """
    Represents configuration options for a document in MongoDB.

    This data class defines various settings such as indexes, capped collection options, timeseries collection options,
    codec options, read preference, read concern, write concern, and extra options for a MongoDB document.

    Attributes:
        indexes (list[pymongo.IndexModel]): List of index models for the document.
        capped (bool): Indicates if the collection is capped (default is False).
        capped_size (int): The maximum size of the capped collection in bytes (default is 16 MB).
        capped_max (int): The maximum number of documents allowed in a capped collection (default is None).
        timeseries_field (str): The field name to use as the time field for timeseries collections (default is None).
        timeseries_meta_field (str): The field name for metadata in timeseries collections (default is None).
        timeseries_granularity (Literal['seconds', 'minutes', 'hours']): The granularity of time intervals.
        timeseries_expire_after_seconds (int): The expiration time for documents in a timeseries collection, in seconds.
        codec_options (bson.CodecOptions): The BSON codec options (default is None).
        read_preference (pymongo.ReadPreference): The read preference for the document (default is None).
        read_concern (ReadConcern): The read concern for the document (default is None).
        write_concern (pymongo.WriteConcern): The write concern for the document (default is None).
        extra_options (dict): Extra options for the document configuration (default is an empty dictionary).

    """

    indexes: list[pymongo.IndexModel] = dataclasses.field(default_factory=lambda: list())
    capped: bool = dataclasses.field(default=False)
    capped_size: int = dataclasses.field(default=16 * (2 ** 20))  # 16 Mb
    capped_max: int = dataclasses.field(default=None)
    timeseries_field: str = dataclasses.field(default=None)
    timeseries_meta_field: str = dataclasses.field(default=None)
    timeseries_granularity: Literal['seconds', 'minutes', 'hours'] = dataclasses.field(default='seconds')
    timeseries_expire_after_seconds: int = dataclasses.field(default=None)
    codec_options: bson.CodecOptions = dataclasses.field(default=None)
    read_preference: pymongo.ReadPreference = dataclasses.field(default=None)
    read_concern: ReadConcern = dataclasses.field(default=None)
    write_concern: pymongo.WriteConcern = dataclasses.field(default=None)
    extra_options: dict = dataclasses.field(default_factory=lambda: dict())


class Document(BaseDocument, metaclass=DocumentMeta):
    """
    Represents a document in MongoDB.

    This class inherits from BaseDocument and implements the DocumentMeta metaclass. It provides functionality
    for dumping BSON data.

    Attributes:
        __collection_name__ (str): The name of the collection where documents of this class are stored.
        document_config (DocumentConfig): Configuration options for the document.

    """

    if TYPE_CHECKING:
        __collection_name__: str
        __references__: dict[str, references.Reference]
        document_config: DocumentConfig

    __collection_name__ = None
    document_config = DocumentConfig()

    def dump_bson(
        self,
        by_alias: bool = True,
        exclude_null: bool = False,
        **options
    ) -> bson.SON:
        """
        Dump the document to BSON format.

        Args:
            by_alias (bool): Whether to use field aliases in the BSON output.
            exclude_null (bool): Whether to exclude fields with null values from the BSON output.
            **options: Additional options for BSON dumping.

        Returns:
            bson.SON: The BSON representation of the document.

        """
        son = super().dump_bson(by_alias, exclude_null, **options)

        for field, reference in self.__references__.items():
            field = self.__fields__[field]
            key = field.alias if by_alias else field.name
            value = son.pop(key, expressions.EmptyValue)
            if value is expressions.EmptyValue:
                continue
            son[reference.key_name] = value

        return son
