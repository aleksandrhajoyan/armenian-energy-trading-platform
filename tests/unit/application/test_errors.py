"""Unit tests for transport-neutral application errors."""

import inspect

import pytest

from energy_trading.application.errors import (
    ApplicationError,
    ConflictError,
    DependencyUnavailableError,
    InvalidRequestError,
    ResourceNotFoundError,
)


@pytest.mark.parametrize(
    ("error_type", "code"),
    [
        (InvalidRequestError, "invalid_request"),
        (ResourceNotFoundError, "resource_not_found"),
        (ConflictError, "conflict"),
        (DependencyUnavailableError, "dependency_unavailable"),
    ],
)
def test_application_errors_have_stable_codes_and_messages(
    error_type: type[ApplicationError],
    code: str,
) -> None:
    error = error_type("Safe public message.")
    assert isinstance(error, ApplicationError)
    assert error.code == code
    assert error.message == "Safe public message."
    assert str(error) == "Safe public message."
    assert not hasattr(error, "status_code")
    assert "status_code" not in inspect.signature(error_type.__init__).parameters


def test_application_error_rejects_empty_message() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        InvalidRequestError("   ")
