"""Centralized FastAPI/Starlette exception translation to the API error envelope."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from energy_trading.api.errors import ApiError, ApiErrorDetail, ApiErrorResponse
from energy_trading.api.middleware import correlation_id_from_scope
from energy_trading.application.errors import (
    ApplicationError,
    ConflictError,
    DependencyUnavailableError,
    InvalidRequestError,
    ResourceNotFoundError,
)
from energy_trading.shared.observability.correlation import (
    CORRELATION_HEADER,
    correlation_id_scope,
    generate_correlation_id,
    get_correlation_id,
)
from energy_trading.shared.observability.logging import ENERGY_TRADING_LOGGER_NAME

logger = logging.getLogger(f"{ENERGY_TRADING_LOGGER_NAME}.api.errors")

REQUEST_VALIDATION_ERROR_CODE = "request_validation_error"
INTERNAL_ERROR_CODE = "internal_error"
NOT_FOUND_CODE = "not_found"
METHOD_NOT_ALLOWED_CODE = "method_not_allowed"
HTTP_ERROR_CODE = "http_error"

INTERNAL_ERROR_MESSAGE = "An unexpected internal error occurred."
REQUEST_VALIDATION_ERROR_MESSAGE = "Request validation failed."
NOT_FOUND_MESSAGE = "The requested resource was not found."
METHOD_NOT_ALLOWED_MESSAGE = "Method not allowed."
HTTP_ERROR_MESSAGE = "An HTTP error occurred."

_APPLICATION_ERROR_STATUS: dict[type[ApplicationError], int] = {
    InvalidRequestError: 400,
    ResourceNotFoundError: 404,
    ConflictError: 409,
    DependencyUnavailableError: 503,
}


def register_exception_handlers(application: FastAPI) -> None:
    """Attach centralized exception handlers to ``application``."""

    application.add_exception_handler(ApplicationError, _application_error_handler)
    application.add_exception_handler(RequestValidationError, _request_validation_error_handler)
    application.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    application.add_exception_handler(Exception, _unhandled_exception_handler)


def mapped_http_status_for_application_error(exc: ApplicationError) -> int | None:
    """Return the explicit HTTP status for a known application error, else ``None``.

    Unmapped types fail closed at the handler; they are not treated as HTTP 400.
    """

    for error_type, status_code in _APPLICATION_ERROR_STATUS.items():
        if isinstance(exc, error_type):
            return status_code
    return None


def sanitize_validation_details(
    errors: Sequence[Mapping[str, Any]],
) -> tuple[ApiErrorDetail, ...]:
    """Convert framework validation errors into public, sanitized details."""

    details: list[ApiErrorDetail] = []
    for error in errors:
        location = error.get("loc", ())
        if isinstance(location, (list, tuple)):
            field = ".".join(str(part) for part in location) if location else "request"
        else:
            field = str(location) if location else "request"
        message = error.get("msg", "Invalid value")
        error_type = error.get("type", "value_error")
        details.append(
            ApiErrorDetail(
                field=field,
                message=str(message),
                type=str(error_type),
            )
        )
    return tuple(details)


def resolve_request_correlation_id(request: Request) -> str:
    """Return the request correlation ID from context or ASGI scope state."""

    current = get_correlation_id()
    if current is not None:
        return current
    stored = correlation_id_from_scope(request.scope)
    if stored is not None:
        return stored
    return generate_correlation_id()


def error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: tuple[ApiErrorDetail, ...] | None = None,
) -> JSONResponse:
    """Build a JSON error response using the standard envelope."""

    correlation_id = resolve_request_correlation_id(request)
    envelope = ApiErrorResponse(
        error=ApiError(
            code=code,
            message=message,
            correlation_id=correlation_id,
            details=details,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(mode="json", exclude_none=True),
        headers={CORRELATION_HEADER: correlation_id},
    )


def _unmapped_application_error_response(
    request: Request,
    exc: ApplicationError,
) -> JSONResponse:
    """Fail closed: unknown application errors are not presented as client errors."""

    correlation_id = resolve_request_correlation_id(request)
    with correlation_id_scope(correlation_id):
        logger.error(
            "Unmapped application error at API translation boundary: type=%s code=%s",
            type(exc).__name__,
            exc.code,
            exc_info=exc,
        )
        return error_response(
            request=request,
            status_code=500,
            code=INTERNAL_ERROR_CODE,
            message=INTERNAL_ERROR_MESSAGE,
        )


async def _application_error_handler(request: Request, exc: Exception) -> JSONResponse:
    application_error = cast(ApplicationError, exc)
    status_code = mapped_http_status_for_application_error(application_error)
    if status_code is None:
        return _unmapped_application_error_response(request, application_error)
    return error_response(
        request=request,
        status_code=status_code,
        code=application_error.code,
        message=application_error.message,
    )


async def _request_validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    validation_error = cast(RequestValidationError, exc)
    details = sanitize_validation_details(validation_error.errors())
    return error_response(
        request=request,
        status_code=422,
        code=REQUEST_VALIDATION_ERROR_CODE,
        message=REQUEST_VALIDATION_ERROR_MESSAGE,
        details=details,
    )


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    http_exc = cast(StarletteHTTPException, exc)
    if http_exc.status_code == 404:
        code = NOT_FOUND_CODE
        message = NOT_FOUND_MESSAGE
    elif http_exc.status_code == 405:
        code = METHOD_NOT_ALLOWED_CODE
        message = METHOD_NOT_ALLOWED_MESSAGE
    else:
        code = HTTP_ERROR_CODE
        message = HTTP_ERROR_MESSAGE
    return error_response(
        request=request,
        status_code=http_exc.status_code,
        code=code,
        message=message,
    )


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = resolve_request_correlation_id(request)
    with correlation_id_scope(correlation_id):
        logger.exception(
            "Unhandled exception during request processing",
            exc_info=exc,
        )
        return error_response(
            request=request,
            status_code=500,
            code=INTERNAL_ERROR_CODE,
            message=INTERNAL_ERROR_MESSAGE,
        )
