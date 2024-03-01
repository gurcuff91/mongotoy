import abc
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Literal

import bson

from mongotoy import fields, references, cache
from mongotoy.errors import DocumentError, ValidationError, DocumentValidationError

__all__ = (
    'EmbeddedDocument',
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
            info = namespace.get(field_name, {})
            if not isinstance(info, dict):
                # noinspection PyTypeChecker,SpellCheckingInspection
                raise DocumentError(
                    loc=(name, field_name),
                    msg=f'Invalid field descriptor. Use mongotoy.field() or mongotoy.reference() descriptors'
                )
            try:
                _fields[field_name] = fields.Field.from_annotated_type(anno_type, info=info)
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


class DocumentMeta(BaseDocumentMeta):
    """
    Metaclass for document class.
    """

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
            if field._id_field:
                if _id_field:
                    # noinspection PyTypeChecker
                    raise DocumentError(
                        loc=(name, field.name),
                        msg=f'Document has many fields id declared'
                    )
                _id_field = field

            # Unwrap ListMapper
            field_mapper = field.mapper
            is_many = False
            if isinstance(field_mapper, fields.ListMapper):
                field_mapper = field_mapper.mapper
                is_many = True

            # Add references
            if isinstance(field_mapper, fields.ReferencedDocumentMapper):
                # noinspection PyProtectedMember,PyUnresolvedReferences
                _references[field.name] = references.Reference(
                    document_cls=field_mapper._document_cls,
                    ref_field=field_mapper._ref_field,
                    key_name=field_mapper._key_name,
                    is_many=is_many,
                    name=field.name
                )

        if not _id_field:
            _id_field = fields.Field(
                mapper=fields.ObjectIdMapper(
                    default_factory=lambda: bson.ObjectId()
                ),
                alias='_id',
                id_field=True
            )

        # Set class props
        _cls.__fields__ = OrderedDict({'id': _id_field, **_cls.__fields__})
        _cls.__references__ = _references
        _cls.__collection_name__ = f'{name.lower()}s'
        _cls.id = _id_field

        return _cls


class BaseDocument(abc.ABC, metaclass=BaseDocumentMeta):
    """
    Base class for document.
    """
    if TYPE_CHECKING:
        __fields__: dict[str, fields.Field]
        __data__: dict[str, Any]

    def __init__(self, **data):
        """
        Initializes the base document class.

        Args:
            **data: Keyword arguments for field values.

        Raises:
            ValidationError: If validation fails for any field.

        """
        self.__data__ = {}
        errors = []
        for field in self.__fields__.values():
            value = data.get(field.alias, data.get(field.name, fields.EmptyValue))
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
            if exclude_empty and value is fields.EmptyValue:
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
                ) if value not in (fields.EmptyValue, None) else value

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
        **options
    ) -> dict:
        """
        Dumps the document data to JSON format.

        Args:
            by_alias (bool): Flag to dump by alias.
            exclude_null (bool): Flag to exclude null fields.
            **options: Additional options.

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
        **options
    ) -> bson.SON:
        """
        Dumps the document data to BSON format.

        Args:
            by_alias (bool): Flag to dump by alias.
            exclude_null (bool): Flag to exclude null fields.
            **options: Additional options.

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
    """


class Document(BaseDocument, metaclass=DocumentMeta):
    """
    Class representing a document.
    """
    if TYPE_CHECKING:
        __collection_name__: str
        __references__: dict[str, references.Reference]
