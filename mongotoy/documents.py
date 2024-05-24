import abc
import dataclasses
import typing
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Literal

import bson
import pymongo
from pymongo.collation import Collation
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
        val_errors = []

        for field in self.__fields__.values():
            value = data.get(field.alias, data.get(field.name, expressions.EmptyValue))
            try:
                field.__set__(self, value=value)
            except ValidationError as e:
                val_errors.extend(e.errors)

        if val_errors:
            raise DocumentValidationError(self.__class__, errors=val_errors)

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


@dataclasses.dataclass
class DocumentConfig:
    """
    Represents configuration options for a document in MongoDB.

    This data class defines various settings such as indexes, capped collection options, timeseries collection options,
    codec options, read preference, read concern, write concern, and extra options for a MongoDB document.

    Attributes:
        indexes (list[pymongo.IndexModel]): List of index models for the document.
        timeseries_field (str): The field name to use as the time field for timeseries collections (default is None).
        timeseries_meta_field (str): The field name for metadata in timeseries collections (default is None).
        timeseries_granularity (Literal['seconds', 'minutes', 'hours']): The granularity of time intervals.
        timeseries_expire_after_seconds (int): The expiration time for documents in a timeseries collection, in seconds
        capped_collection (bool): Indicates if the collection is capped (default is False).
        capped_collection_size (int): The maximum size of the capped collection in bytes (default is 16 MB).
        capped_collection_max (int): The maximum number of documents allowed in a capped collection (default is None).
        collation (Collation): The collation to use in a document collection (default is None).
        extra_collection_options (dict): Extra options for the document collection (default is an empty dictionary).
        codec_options (bson.CodecOptions): The BSON codec options (default is None).
        read_preference (pymongo.ReadPreference): The read preference for the document (default is None).
        read_concern (ReadConcern): The read concern for the document (default is None).
        write_concern (pymongo.WriteConcern): The written concern for the document (default is None).

    """

    indexes: list[pymongo.IndexModel] = dataclasses.field(default_factory=list)
    timeseries_field: str = dataclasses.field(default=None)
    timeseries_meta_field: str = dataclasses.field(default=None)
    timeseries_granularity: Literal['seconds', 'minutes', 'hours'] = dataclasses.field(default=None)
    timeseries_expire_after_seconds: int = dataclasses.field(default=None)
    capped_collection: bool = dataclasses.field(default=False)
    capped_collection_size: int = dataclasses.field(default=16 * (2 ** 20))  # 16 Mb
    capped_collection_max: int = dataclasses.field(default=None)
    collation: Collation = dataclasses.field(default=None)
    extra_collection_options: dict = dataclasses.field(default_factory=dict)
    codec_options: bson.CodecOptions = dataclasses.field(default=None)
    read_preference: pymongo.ReadPreference = dataclasses.field(default=None)
    read_concern: ReadConcern = dataclasses.field(default=None)
    write_concern: pymongo.WriteConcern = dataclasses.field(default=None)

    def merge(self, new_config: 'DocumentConfig'):
        """
        Merge the current document configuration with a new configuration.

        This function updates the current configuration with values from the new configuration,
        prioritizing the values from the current configuration if they are defined.

        Args:
            new_config (DocumentConfig): The new configuration to merge.

        """
        # Merge indexes
        self.indexes.extend(new_config.indexes)

        # Merge timeseries fields
        self.timeseries_field = self.timeseries_field or new_config.timeseries_field
        self.timeseries_meta_field = self.timeseries_meta_field or new_config.timeseries_meta_field

        # Merge timeseries settings
        self.timeseries_granularity = self.timeseries_granularity or new_config.timeseries_granularity
        self.timeseries_expire_after_seconds = (
            self.timeseries_expire_after_seconds or new_config.timeseries_expire_after_seconds
        )


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

        # Process document fields
        _id_field = None
        _references = OrderedDict()
        for field in _cls.__fields__.values():
            # Check id field
            if field.options.id_field:
                _id_field = field

            # Unwrap SequenceMapper
            _mapper = field.mapper
            _is_many = False
            if isinstance(_mapper, mappers.SequenceMapper):
                _mapper = _mapper.unwrap()
                _is_many = True

            # Add references
            if isinstance(_mapper, mappers.ReferencedDocumentMapper):
                _references[field.name] = references.Reference(
                    document_cls=getattr(_mapper, '_document_cls'),
                    ref_field=_mapper.options.ref_field,
                    key_name=_mapper.options.key_name or f'{field.alias}_{_mapper.options.ref_field}',
                    is_many=_is_many,
                    name=field.alias
                )

        # Create id field if not exist
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

        # Merge base configs
        _base_config = DocumentConfig()
        for base in bases:
            _config = getattr(base, 'document_config', None)
            if _config:
                _base_config.merge(_config)

        # Get Document config from namespace and merge with base config
        _doc_config = namespace.get('document_config', DocumentConfig())
        _doc_config.merge(_base_config)

        # Set Document class properties
        _cls.id = _id_field
        _cls.document_config = _doc_config
        _cls.__collection_name__ = namespace.get('__collection_name__', f'{name.lower()}s')
        _cls.__fields__['id'] = _id_field
        _cls.__references__ = _references

        return _cls


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


# noinspection SpellCheckingInspection
def get_embedded_document_cls(doc_type: typing.Type | str) -> typing.Type[EmbeddedDocument]:
    """
    Get the embedded document class based on its type or name.

    Args:
        doc_type (Type | str): The type or name of the embedded document.

    Returns:
        Type['documents.EmbeddedDocument']: The embedded document class.

    Raises:
        TypeError: If the provided type is not a subclass of mongotoy.EmbeddedDocument.
    """
    doc_cls = cache.documents.get_type(doc_type, do_raise=True)
    if not issubclass(doc_cls, EmbeddedDocument):
        raise TypeError(f'Type {doc_cls} is not a mongotoy.EmbeddedDocument subclass')

    return doc_cls


# noinspection SpellCheckingInspection
def get_document_cls(doc_type: typing.Type | str) -> typing.Type[Document]:
    """
    Get the document class based on its type or name.

    Args:
        doc_type (Type | str): The type or name of the document.

    Returns:
        Type['documents.Document']: The document class.

    Raises:
        TypeError: If the provided type is not a subclass of mongotoy.Document.
    """
    doc_cls = cache.documents.get_type(doc_type, do_raise=True)
    if not issubclass(doc_cls, Document):
        raise TypeError(f'Type {doc_cls} is not a mongotoy.Document subclass')

    return doc_cls


def get_document_field(document_cls: typing.Type[BaseDocument], field_name: str) -> fields.Field:
    """
    Get the field from a document class based on the field's name.

    Args:
        document_cls (Type['documents.BaseDocument']): The document class containing the field.
        field_name (str): The name of the field.

    Returns:
        'fields.Field': The field object.

    Raises:
        TypeError: If the field does not exist in the document class.
    """
    field = document_cls.__fields__.get(field_name)
    if not field:
        raise TypeError(f'Field `{document_cls.__name__}.{field}` does not exist')

    return field
