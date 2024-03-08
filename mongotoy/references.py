import typing
from mongotoy import cache

if typing.TYPE_CHECKING:
    from mongotoy import documents, fields


# noinspection PyProtectedMember
def get_base_document_cls(document_cls: str) -> typing.Type['documents.BaseDocument']:
    """
    Get a document class by name from the registered documents.

    Args:
        document_cls (str): The name of the document class.

    Returns:
        typing.Type['documents.BaseDocument']: The document class.

    Raises:
        TypeError: If the document class is not found or not declared yet.

    """
    from mongotoy import documents
    if not cache.documents.exist_type(document_cls):
        raise TypeError(f'Document `{document_cls}` not found or not declared yet')
    document_cls = cache.documents.get_type(document_cls)

    if not issubclass(document_cls, documents.BaseDocument):
        # noinspection SpellCheckingInspection
        raise TypeError(f'Document {document_cls} must be subclass of mongotoy.BaseDocument')
    return document_cls


def get_document_cls(document_cls: str) -> typing.Type['documents.Document']:
    from mongotoy import documents
    document_cls = get_base_document_cls(document_cls)
    if not issubclass(document_cls, documents.Document):
        # noinspection SpellCheckingInspection
        raise TypeError(f'Document {document_cls} must be subclass of mongotoy.Document')
    return document_cls


def get_field(field_name: str, document_cls: typing.Type['documents.BaseDocument']) -> 'fields.Field':
    field = document_cls.__fields__.get(field_name)
    if not field:
        raise TypeError(f'Field `{document_cls.__name__}.{field}` not exist')
    return field


class Reference:
    """
    Class representing a reference to another document.
    """

    def __init__(
        self,
        document_cls: typing.Type['documents.BaseDocument'] | str,
        ref_field: str,
        key_name: str,
        is_many: bool,
        name: str = None
    ):
        """
        Initialize a reference.

        Args:
            document_cls (typing.Type['documents.BaseDocument'] | str): The referenced document class or its name.
            ref_field (str): The name of the field in the referenced document.
            key_name (str): The name of the key in the current document.
            is_many (bool): Indicates if the reference is to multiple documents.
            name (str): The name of the reference.

        """
        self._document_cls = document_cls
        self._ref_field = ref_field
        self._key_name = key_name
        self._is_many = is_many
        self._name = name

    @property
    def document_cls(self) -> typing.Type['documents.Document']:
        # noinspection SpellCheckingInspection
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
        ref_field = self.document_cls.__fields__.get(self._ref_field)
        if not ref_field:
            raise TypeError(f'Referenced field `{self.document_cls.__name__}.{ref_field}` not exist')
        return ref_field

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


def build_dereference_pipeline(references: list[Reference], deep: int = 0) -> list[dict]:
    # noinspection SpellCheckingInspection
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

    for reference in references:
        join_op = '$in' if reference.is_many else '$eq'
        match_exp = {join_op: [f"${reference.ref_field.alias}", "$$fk"]}

        # noinspection PyProtectedMember,PyTypeChecker
        pipeline.append(
            {
                # **(
                #     {
                #         # Fix for array field not present
                #         "$addFields": {
                #             reference.key_name: {
                #                 "$cond": {
                #                     "if": {
                #                         "$ne": [{"$type": f"${reference.key_name}"}, "array"]
                #                     },
                #                     "then": [],
                #                     "else": f"${reference.key_name}"
                #                 }
                #             }
                #         }
                #     } if reference.is_many else {}
                # ),
                "$lookup": {
                    'from': reference.document_cls.__collection_name__,
                    'let': {"fk": f"${reference.key_name}"},
                    'pipeline': [
                        {
                            "$match": {
                                "$expr": match_exp
                            }
                        },
                        *build_dereference_pipeline(
                            reference.document_cls.__references__.values(),
                            deep=deep - 1
                        ),
                        *([{'$limit': 1}] if not reference.is_many else [])
                    ],
                    'as': reference._name
                }
            }
        )
        if not reference.is_many:
            # noinspection PyProtectedMember
            pipeline.append(
                {
                    "$unwind": {
                        "path": f"${reference._name}",
                        "preserveNullAndEmptyArrays": True
                    }
                }
            )
    return pipeline


def get_reverse_references(
        document_cls: typing.Type['documents.Document']
) -> dict[typing.Type['documents.Document'], dict[str, Reference]]:
    from mongotoy import documents

    # Check all documents
    rev_references = {}
    for ref_document_cls in cache.documents.get_all_types():
        # Not is a Document class
        if not issubclass(ref_document_cls, documents.Document):
            continue

        # Match references
        refs = {
            field_name: reference
            for field_name, reference in ref_document_cls.__references__.items()
            if reference.document_cls is document_cls
        }
        if refs:
            rev_references[ref_document_cls] = refs

    return rev_references
