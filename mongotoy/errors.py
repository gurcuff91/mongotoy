from typing import Union


class ErrorWrapper:
    """
    Wrapper class for handling errors in the mongotoy library.

    Args:
        - loc (str): The location where the error occurred.
        - error (Exception): The wrapped error instance.

    Raises:
        TypeError: If `loc` is not a tuple of strings.
    """

    def __init__(self, loc: tuple[str], error: Union[Exception, 'ErrorWrapper']):
        """
        Initialize ErrorWrapper object.

        Parameters:
            - loc (tuple[str]): The location where the error occurred.
            - error (Union[Exception, 'ErrorWrapper']): The wrapped error instance.

        Raises:
            TypeError: If `loc` is not a tuple of strings.
        """
        self._loc, self._error = self._unwrap_error(loc, error)

    def _unwrap_error(self, loc: tuple[str], error: Exception) -> tuple[tuple[str], Exception]:
        """
        Recursively unwrap nested ErrorWrapper instances to get the original error and its location.

        Parameters:
            - loc (tuple[str]): The current location information.
            - error (Exception): The wrapped error instance.

        Returns:
            tuple[tuple[str], Exception]: The final location information and the original error.

        Raises:
            TypeError: If `loc` is not a tuple of strings.
        """
        if not isinstance(loc, tuple) or not all(isinstance(x, str) for x in loc):
            raise TypeError("Location must be a tuple of strings.")

        if isinstance(error, ErrorWrapper):
            # noinspection PyTypeChecker
            return self._unwrap_error(loc + error.loc, error.error)
        return loc, error

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

    def get_message(self) -> str:
        """
        Get the formatted error message.

        Returns:
            str: The formatted error message.
        """
        return f'{".".join(self.loc)} -> {str(self.error)}'

    def dump_dict(self) -> dict:
        """
        Convert the error information to a dictionary.

        Returns:
            dict: A dictionary containing the location and string representation of the error.
        """
        return {
            'type': self.error.__class__.__name__,
            'loc': list(self.loc),
            'error': str(self.error)
        }


class ValidationError(Exception):
    """
    Exception class to represent data validation errors in the mongotoy library.

    Args:
        - errors (list[ErrorWrapper]): List of ErrorWrapper instances containing details of validation errors.

    Raises:
        TypeError: If `errors` is not a list of ErrorWrapper instances.
    """

    def __init__(self, errors: list[ErrorWrapper]):
        """
        Initialize ValidationError object.

        Parameters:
            - errors (list[ErrorWrapper]): List of ErrorWrapper instances containing details of validation errors.

        Raises:
            TypeError: If `errors` is not a list of ErrorWrapper instances.
        """
        if not all(isinstance(e, ErrorWrapper) for e in errors):
            raise TypeError("Errors must be a list of ErrorWrapper instances.")

        self._errors = errors
        super().__init__(self._get_message())

    def _get_message(self) -> str:
        """
        Get the error message for the validation exception.

        Returns:
            str: The error message indicating the number of invalid fields.
        """
        msg = f'Invalid data at:'
        for err in self.errors:
            msg += f'\n  * {err.get_message()}'
        return msg

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
            'type': 'ValidationError',
            'errors': [e.dump_dict() for e in self.errors]
        }


class DocumentError(Exception):
    """
    Exception class to represent errors related to document definitions in the mongotoy library.

    Args:
        - loc (tuple[str]): The location where the error occurred.
        - msg (str): The error message.
    """

    def __init__(self, loc: tuple[str], msg: str):
        """
        Initialize DocumentError object.

        Parameters:
            - loc (tuple[str]): The location where the error occurred.
            - msg (str): The error message.
        """
        super().__init__(f'[{".".join(loc)}]. {msg}')
