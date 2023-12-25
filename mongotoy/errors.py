from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from mongotoy.documents import BaseDoc


class ErrorWrapper(Exception):
    """
    Wrapper class for handling errors in the mongotoy library.

    Args:
        - loc (str): The location where the error occurred.
        - error (Exception): The wrapped error instance.

    Properties:
        - loc (tuple[str]): The location where the error occurred, represented as a tuple of strings.
        - error (Exception): The wrapped error instance.

    Methods:
        - dump_dict(): Convert the error information to a dictionary for easy serialization.

    Example:
        ```python
        try:
            # Some code that may raise an exception
            ...
        except Exception as e:
            # Wrap the error with location information
            wrapped_error = ErrorWrapper(loc='module.function', error=e)
            # Access the wrapped error details
            location = wrapped_error.loc
            original_error = wrapped_error.error
            # Dump the error information as a dictionary
            error_dict = wrapped_error.dump_dict()
        ```
    """

    def __init__(self, loc: str, error: Exception):
        self._loc, self._error = self._unwrap_error((loc,), error)
        super().__init__(str(self._error))

    def _unwrap_error(self, loc: tuple[str], error: Exception) -> tuple[tuple[str], Exception]:
        """
        Recursively unwrap nested ErrorWrapper instances to get the original error and its location.

        Args:
            - loc (tuple[str]): The current location information.
            - error (Exception): The wrapped error instance.

        Returns:
            tuple[tuple[str], Exception]: The final location information and the original error.
        """
        if not isinstance(error, ErrorWrapper):
            return loc, error
        return self._unwrap_error((*loc, *error.loc), error.error)

    @property
    def loc(self) -> tuple[str]:
        """
        Get the location where the error occurred.

        Returns:
            tuple[str]: The location represented as a tuple of strings.
        """
        return self._loc

    @property
    def error(self) -> Exception:
        """
        Get the wrapped error instance.

        Returns:
            Exception: The wrapped error instance.
        """
        return self._error

    def dump_dict(self) -> dict:
        """
        Convert the error information to a dictionary.

        Returns:
            dict: A dictionary containing the location and string representation of the error.
        """
        return {
            'loc': list(self.loc),
            'error': str(self.error)
        }


class ValidationError(Exception):
    """
    Exception class to represent validation errors in the mongotoy library.

    Args:
        - errors (list[ErrorWrapper]): List of ErrorWrapper instances containing details of validation errors.

    Properties:
        - errors (list[ErrorWrapper]): List of ErrorWrapper instances representing validation errors.

    Methods:
        - dump_dict(): Convert the validation error information to a dictionary for easy serialization.

    Example:
        ```python
        try:
            # Some code that performs data validation
            ...
        except ValidationError as ve:
            # Access the list of validation errors
            validation_errors = ve.errors
            # Dump the validation error information as a dictionary
            validation_error_dict = ve.dump_dict()
        ```
    """

    def __init__(self, errors: list[ErrorWrapper]):
        self._errors = errors
        super().__init__(self._get_message())

    def _get_message(self) -> str:
        """
        Get the error message for the validation exception.

        Returns:
            str: The error message indicating the number of invalid fields.
        """
        return f'Invalid data into {len(self.errors)} fields'

    @property
    def errors(self) -> list[ErrorWrapper]:
        """
        Get the list of validation errors.

        Returns:
            list[ErrorWrapper]: List of ErrorWrapper instances representing validation errors.
        """
        return self._errors

    def dump_dict(self) -> dict:
        """
        Convert the validation error information to a dictionary.

        Returns:
            dict: A dictionary containing the details of validation errors.
        """
        return {
            'errors': [err.dump_dict() for err in self.errors]
        }


class DocumentValidationError(ValidationError):
    """
    Exception class representing validation errors specific to a document in the mongotoy library.

    Args:
        - errors (list[ValidationError]): List of ValidationError instances with details of document validation errors.
        - document_cls (Type['BaseDoc']): The document class associated with the validation errors.

    Properties:
        - document_cls (Type['BaseDoc']): The document class associated with the validation errors.

    Methods:
        - dump_dict(): Convert the document validation error information to a dictionary for easy serialization.

    Example:
        ```python
        try:
            # Some code that performs document data validation
            ...
        except DocumentValidationError as dve:
            # Access the document class
            document_class = dve.document_cls
            # Access the list of document validation errors
            document_validation_errors = dve.errors
            # Dump the document validation error information as a dictionary
            document_validation_error_dict = dve.dump_dict()
        ```
    """

    def __init__(self, errors: list[ValidationError], document_cls: Type['BaseDoc']):
        unwrapped_errors = []
        for err in errors:
            unwrapped_errors.extend(err.errors)

        self._document_cls = document_cls
        self._document_path = f'{self._document_cls.__module__}.{self._document_cls.__name__}'
        super().__init__(errors=unwrapped_errors)

    def _get_message(self) -> str:
        """
        Get the error message for the document validation exception.

        Returns:
            str: The error message indicating the invalid data in the document and its location.
        """
        msg = f'Invalid data at document {self._document_path}:'
        for err in self.errors:
            msg += f'\n  - {".".join(err.loc)}: {str(err)}'
        return msg

    def dump_dict(self) -> dict:
        """
        Convert the document validation error information to a dictionary.

        Returns:
            dict: A dictionary containing the details of document validation errors.
        """
        return {
            'document_cls': self._document_path,
            **super().dump_dict()
        }


class MapperError(Exception):
    """
    Exception class for errors related to mapping data between different structures.
    This can be raised when there are issues with the mapping process in the application.

    Example:
        ```python
        try:
            # Your code that may raise MapperError
        except MapperError as e:
            print(f"MapperError: {e}")
        ```
    """
    pass


class FieldError(Exception):
    """
    Exception class for errors related to fields in a document or data structure.
    This can be raised when there are issues with field definitions or field-specific operations.

    Example:
        ```python
        try:
            # Your code that may raise FieldError
        except FieldError as e:
            print(f"FieldError: {e}")
        ```
    """
    pass


class DocumentError(Exception):
    """
    Exception class for errors related to documents or data structures.
    This can be raised when there are issues with document-level operations or validations.

    Example:
        ```python
        try:
            # Your code that may raise DocumentError
        except DocumentError as e:
            print(f"DocumentError: {e}")
        ```
    """
    pass


class DocumentReferenceError(Exception):
    """
    Exception class for errors related to document references.
    This can be raised when there are issues with referring to or managing references between documents.

    Example:
        ```python
        try:
            # Your code that may raise DocumentReferenceError
        except DocumentReferenceError as e:
            print(f"DocumentReferenceError: {e}")
        ```
    """
    pass


class EngineError(Exception):
    """
    Exception class for errors related to the database engine or core functionality.
    This can be raised when there are critical issues that impact the communication with the database engine.

    Example:
        ```python
        try:
            # Your code that may raise EngineError
        except EngineError as e:
            print(f"Database Engine Error: {e}")
        ```
    """
    pass

