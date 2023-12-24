from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from mongotoy.documents import BaseDocument


class ErrorWrapper(Exception):

    def __init__(self, loc: str, error: Exception):
        self._loc, self._error = self._unwrap_error((loc,), error)
        super().__init__(str(self._error))

    def _unwrap_error(self, loc: tuple[str], error: Exception) -> tuple[tuple[str], Exception]:
        if not isinstance(error, ErrorWrapper):
            return loc, error
        return self._unwrap_error((*loc, *error.loc), error.error)

    @property
    def loc(self) -> tuple[str]:
        return self._loc

    @property
    def error(self) -> Exception:
        return self._error

    def dump_dict(self) -> dict:
        return {
            'loc': list(self.loc),
            'error': str(self.error)
        }


class ValidationError(Exception):

    def __init__(self, errors: list[ErrorWrapper]):
        self._errors = errors
        super().__init__(self._get_message())

    def _get_message(self) -> str:
        return f'Invalid data into {len(self.errors)} fields'

    @property
    def errors(self) -> list[ErrorWrapper]:
        return self._errors

    def dump_dict(self) -> dict:
        return {
            'errors': [err.dump_dict() for err in self.errors]
        }


class DocumentValidationError(ValidationError):

    def __init__(self, errors: list[ValidationError], document_cls: Type['BaseDocument']):
        unwrapped_errors = []
        for err in errors:
            unwrapped_errors.extend(err.errors)

        self._document_cls = document_cls
        self._document_path = f'{self._document_cls.__module__}.{self._document_cls.__name__}'
        super().__init__(errors=unwrapped_errors)

    def _get_message(self) -> str:
        msg = f'Invalid data at document {self._document_path}:'
        for err in self.errors:
            msg += f'\n  - {".".join(err.loc)}: {str(err)}'
        return msg

    def dump_dict(self) -> dict:
        return {
            'document_cls': self._document_path,
            **super().dump_dict()
        }


class MapperError(Exception):
    pass


class FieldError(Exception):
    pass


class DocumentError(Exception):
    pass


class DocumentReferenceError(Exception):
    pass


class EngineError(Exception):
    pass
