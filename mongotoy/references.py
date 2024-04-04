import typing

from mongotoy import cache

if typing.TYPE_CHECKING:
    from mongotoy import documents, fields


# noinspection SpellCheckingInspection
def get_embedded_document_cls(doc_type: typing.Type | str) -> typing.Type['documents.EmbeddedDocument']:
    """
    Get the embedded document class based on its type or name.

    Args:
        doc_type (Type | str): The type or name of the embedded document.

    Returns:
        Type['documents.EmbeddedDocument']: The embedded document class.

    Raises:
        TypeError: If the provided type is not a subclass of mongotoy.EmbeddedDocument.
    """
    from mongotoy import documents

    doc_cls = cache.documents.get_type(doc_type, do_raise=True)

    if not issubclass(doc_cls, documents.EmbeddedDocument):
        raise TypeError(f'Type {doc_cls} is not a mongotoy.EmbeddedDocument subclass')

    return doc_cls


# noinspection SpellCheckingInspection
def get_document_cls(doc_type: typing.Type | str) -> typing.Type['documents.Document']:
    """
    Get the document class based on its type or name.

    Args:
        doc_type (Type | str): The type or name of the document.

    Returns:
        Type['documents.Document']: The document class.

    Raises:
        TypeError: If the provided type is not a subclass of mongotoy.Document.
    """
    from mongotoy import documents

    doc_cls = cache.documents.get_type(doc_type, do_raise=True)

    if not issubclass(doc_cls, documents.Document):
        raise TypeError(f'Type {doc_cls} is not a mongotoy.Document subclass')

    return doc_cls


def get_field(field_name: str, document_cls: typing.Type['documents.BaseDocument']) -> 'fields.Field':
    """
    Get the field from a document class based on the field's name.

    Args:
        field_name (str): The name of the field.
        document_cls (Type['documents.BaseDocument']): The document class containing the field.

    Returns:
        'fields.Field': The field object.

    Raises:
        TypeError: If the field does not exist in the document class.
    """
    field = document_cls.__fields__.get(field_name)

    if not field:
        raise TypeError(f'Field `{document_cls.__name__}.{field}` does not exist')

    return field


class Reference:
    """
    Represents a reference to another document.

    Args:
        document_cls (typing.Type['documents.BaseDocument'] | str): The referenced document class or its name.
        ref_field (str): The name of the field in the referenced document.
        key_name (str): The name of the key in the current document.
        is_many (bool): Indicates if the reference is to multiple documents.
        name (str): The name of the reference.
    """

    def __init__(
        self,
        document_cls: typing.Type['documents.BaseDocument'] | str,
        ref_field: str,
        key_name: str,
        is_many: bool,
        name: str = None
    ):
        self._document_cls = document_cls
        self._ref_field = ref_field
        self._key_name = key_name
        self._is_many = is_many
        self._name = name

    # noinspection SpellCheckingInspection
    @property
    def document_cls(self) -> typing.Type['documents.Document']:
        """
        Get the referenced document class.

        Returns:
            typing.Type['documents.Document']: The referenced document class.

        Raises:
            TypeError: If the referenced document is not a subclass of mongotoy.Document.
        """
        return get_document_cls(self._document_cls)

    @property
    def ref_field(self) -> 'fields.Field':
        """
        Get the referenced field.

        Returns:
            'fields.Field': The referenced field.

        Raises:
            TypeError: If the referenced field does not exist.
        """
        return get_field(self._ref_field, self.document_cls)

    @property
    def key_name(self) -> str:
        """
        Get the key name.

        Returns:
            str: The key name.
        """
        return self._key_name

    @property
    def is_many(self) -> bool:
        """
        Check if the reference is to multiple documents.

        Returns:
            bool: True if the reference is to multiple documents, False otherwise.
        """
        return self._is_many


# noinspection PyProtectedMember,PyTypeChecker,SpellCheckingInspection
def build_dereference_pipeline(references: list[Reference], deep: int = 0) -> list[dict]:
    """
    Build a pipeline for dereferencing documents.

    Args:
        references (list[Reference]): The list of references.
        deep (int): The depth of dereferencing.

    Returns:
        list[dict]: The pipeline for dereferencing.
    """
    pipeline = []
    if deep == 0:
        return pipeline

    for ref in references:
        pipeline.append(
            {
                "$lookup": {
                    'from': ref.document_cls.__collection_name__,
                    'let': {"fk": f"${ref.key_name}"},
                    'pipeline': [
                        {
                            "$match": {
                                "$expr": {
                                    '$in' if ref.is_many else '$eq': [f"${ref.ref_field.alias}", '$$fk']
                                }
                            }
                        },
                        *build_dereference_pipeline(
                            ref.document_cls.__references__.values(),
                            deep=deep - 1
                        ),
                        *([] if ref.is_many else [{'$limit': 1}])
                    ],
                    'as': ref._name
                }
            }
        )
        if not ref.is_many:
            pipeline.append(
                {
                    "$unwind": {
                        "path": f"${ref._name}",
                        "preserveNullAndEmptyArrays": True
                    }
                }
            )

    return pipeline


def get_reverse_references(
    document_cls: typing.Type['documents.Document']
) -> dict[typing.Type['documents.Document'], dict[str, Reference]]:
    """
    Retrieve reverse references for a given document class.

    Args:
        document_cls (typing.Type['documents.Document']): The document class.

    Returns:
        dict[typing.Type['documents.Document'], dict[str, Reference]]: A dictionary mapping document classes
        to dictionaries containing reverse references.
    """
    from mongotoy import documents

    # Store reverse references
    reverse_references = {}

    # Iterate over all document classes
    for ref_document_cls in cache.documents.get_all_types():
        # Skip classes that are not subclasses of Document
        if not issubclass(ref_document_cls, documents.Document):
            continue

        # Find references pointing to the given document class
        refs = {
            field_name: reference
            for field_name, reference in ref_document_cls.__references__.items()
            if reference.document_cls is document_cls
        }

        # If there are any matching references, store them in the result dictionary
        if refs:
            reverse_references[ref_document_cls] = refs

    return reverse_references
