"""Transport-neutral application errors.

These types describe use-case failure semantics. They must not include HTTP
status codes, framework types, stack traces as contract data, or raw external
payloads. HTTP translation belongs exclusively to the API boundary.
"""

from typing import ClassVar


class ApplicationError(Exception):
    """Base application failure. Contains no transport or HTTP semantics."""

    code: ClassVar[str] = "application_error"

    def __init__(self, message: str) -> None:
        cleaned = message.strip()
        if not cleaned:
            msg = "ApplicationError message must be a non-empty string"
            raise ValueError(msg)
        self.message = cleaned
        super().__init__(cleaned)


class InvalidRequestError(ApplicationError):
    """The request cannot be processed because it is semantically invalid."""

    code: ClassVar[str] = "invalid_request"


class ResourceNotFoundError(ApplicationError):
    """A requested application resource does not exist."""

    code: ClassVar[str] = "resource_not_found"


class ConflictError(ApplicationError):
    """The request conflicts with current application state."""

    code: ClassVar[str] = "conflict"


class DependencyUnavailableError(ApplicationError):
    """A required application dependency is unavailable."""

    code: ClassVar[str] = "dependency_unavailable"
