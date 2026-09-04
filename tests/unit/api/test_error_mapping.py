"""API exception translation and error-envelope tests."""

from __future__ import annotations

import json
import logging
from typing import Any, ClassVar

import pytest
from fastapi import FastAPI, Query
from httpx import ASGITransport, AsyncClient, Response

from energy_trading.api.app import create_app
from energy_trading.application.errors import (
    ApplicationError,
    ConflictError,
    DependencyUnavailableError,
    InvalidRequestError,
    ResourceNotFoundError,
)
from energy_trading.shared.observability.logging import CorrelationIdFilter, JsonLogFormatter

from .helpers import api_client, make_test_settings

_SENSITIVE_RUNTIME_MESSAGE = "database password=super-secret-test-value"
_UNMAPPED_APPLICATION_MESSAGE = "safe-but-unmapped-message"
_FUTURE_ERROR_MESSAGE = "future-specific-unmapped-message"


class FutureApplicationError(ApplicationError):
    """Test-only subclass that is intentionally absent from the HTTP mapping."""

    code: ClassVar[str] = "future_application_error"


def _error_app() -> FastAPI:
    application = create_app(make_test_settings())

    @application.get("/__test__/invalid-request", response_model=None)
    async def invalid_request() -> None:
        raise InvalidRequestError("The request is invalid.")

    @application.get("/__test__/missing", response_model=None)
    async def missing() -> None:
        raise ResourceNotFoundError("Resource was not found.")

    @application.get("/__test__/conflict", response_model=None)
    async def conflict() -> None:
        raise ConflictError("The request conflicts with current state.")

    @application.get("/__test__/unavailable", response_model=None)
    async def unavailable() -> None:
        raise DependencyUnavailableError("A required dependency is unavailable.")

    @application.get("/__test__/unmapped-base", response_model=None)
    async def unmapped_base() -> None:
        raise ApplicationError(_UNMAPPED_APPLICATION_MESSAGE)

    @application.get("/__test__/unmapped-future", response_model=None)
    async def unmapped_future() -> None:
        raise FutureApplicationError(_FUTURE_ERROR_MESSAGE)

    @application.get("/__test__/validate")
    async def validate(limit: int = Query(gt=0)) -> dict[str, int]:
        return {"limit": limit}

    @application.get("/__test__/boom", response_model=None)
    async def boom() -> None:
        raise RuntimeError(_SENSITIVE_RUNTIME_MESSAGE)

    return application


def _assert_standard_envelope(
    response: Response,
    *,
    status_code: int,
    code: str,
    message: str,
) -> dict[str, Any]:
    assert response.status_code == status_code
    payload = response.json()
    error = payload["error"]
    assert error["code"] == code
    assert error["message"] == message
    assert error["correlation_id"]
    assert response.headers["x-correlation-id"] == error["correlation_id"]
    assert "traceback" not in response.text.lower()
    return error  # type: ignore[no-any-return]


@pytest.mark.parametrize(
    ("path", "status_code", "code", "message"),
    [
        ("/__test__/invalid-request", 400, "invalid_request", "The request is invalid."),
        ("/__test__/missing", 404, "resource_not_found", "Resource was not found."),
        ("/__test__/conflict", 409, "conflict", "The request conflicts with current state."),
        (
            "/__test__/unavailable",
            503,
            "dependency_unavailable",
            "A required dependency is unavailable.",
        ),
    ],
)
async def test_application_errors_map_to_standard_envelope(
    path: str,
    status_code: int,
    code: str,
    message: str,
) -> None:
    async with api_client(_error_app()) as client:
        response = await client.get(path, headers={"X-Correlation-ID": f"map-{code}"})

    error = _assert_standard_envelope(
        response,
        status_code=status_code,
        code=code,
        message=message,
    )
    assert error["correlation_id"] == f"map-{code}"


async def test_bare_application_error_fails_closed_to_sanitized_500() -> None:
    payloads: list[dict[str, Any]] = []

    class RecordingHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            payloads.append(json.loads(self.format(record)))

    handler = RecordingHandler()
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(JsonLogFormatter())
    logger = logging.getLogger("energy_trading")
    logger.addHandler(handler)
    try:
        async with api_client(_error_app()) as client:
            response = await client.get(
                "/__test__/unmapped-base",
                headers={"X-Correlation-ID": "unmapped-base-1"},
            )
    finally:
        logger.removeHandler(handler)

    error = _assert_standard_envelope(
        response,
        status_code=500,
        code="internal_error",
        message="An unexpected internal error occurred.",
    )
    assert error["correlation_id"] == "unmapped-base-1"
    assert _UNMAPPED_APPLICATION_MESSAGE not in response.text
    assert "application_error" not in response.text
    diagnostic_logs = [
        payload
        for payload in payloads
        if "Unmapped application error" in str(payload.get("message", ""))
    ]
    assert diagnostic_logs
    assert any(payload.get("correlation_id") == "unmapped-base-1" for payload in diagnostic_logs)
    assert any("ApplicationError" in str(payload.get("message", "")) for payload in diagnostic_logs)


async def test_unknown_application_error_subclass_fails_closed_to_sanitized_500() -> None:
    async with api_client(_error_app()) as client:
        response = await client.get(
            "/__test__/unmapped-future",
            headers={"X-Correlation-ID": "unmapped-future-1"},
        )

    error = _assert_standard_envelope(
        response,
        status_code=500,
        code="internal_error",
        message="An unexpected internal error occurred.",
    )
    assert error["correlation_id"] == "unmapped-future-1"
    assert _FUTURE_ERROR_MESSAGE not in response.text
    assert "future_application_error" not in response.text
    assert "FutureApplicationError" not in response.text


async def test_request_validation_error_is_sanitized() -> None:
    async with api_client(_error_app()) as client:
        response = await client.get(
            "/__test__/validate",
            params={"limit": "super-secret-input-value"},
            headers={"X-Correlation-ID": "validation-1"},
        )

    error = _assert_standard_envelope(
        response,
        status_code=422,
        code="request_validation_error",
        message="Request validation failed.",
    )
    assert error["correlation_id"] == "validation-1"
    details = error["details"]
    assert isinstance(details, list)
    assert details
    first = details[0]
    assert "field" in first
    assert "message" in first
    assert "type" in first
    assert "query.limit" in first["field"]
    assert "super-secret-input-value" not in response.text
    assert '"input"' not in response.text
    for detail in details:
        assert "input" not in detail


async def test_unknown_route_uses_standard_envelope() -> None:
    async with api_client() as client:
        response = await client.get(
            "/api/v1/this-route-does-not-exist",
            headers={"X-Correlation-ID": "missing-route"},
        )

    error = _assert_standard_envelope(
        response,
        status_code=404,
        code="not_found",
        message="The requested resource was not found.",
    )
    assert error["correlation_id"] == "missing-route"


async def test_unexpected_exception_is_sanitized_and_logged() -> None:
    payloads: list[dict[str, Any]] = []

    class RecordingHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            payloads.append(json.loads(self.format(record)))

    handler = RecordingHandler()
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(JsonLogFormatter())
    logger = logging.getLogger("energy_trading")
    logger.addHandler(handler)
    application = _error_app()
    transport = ASGITransport(app=application, raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/__test__/boom",
                headers={"X-Correlation-ID": "boom-1"},
            )
    finally:
        logger.removeHandler(handler)

    error = _assert_standard_envelope(
        response,
        status_code=500,
        code="internal_error",
        message="An unexpected internal error occurred.",
    )
    assert error["correlation_id"] == "boom-1"
    body = response.text
    assert "super-secret-test-value" not in body
    assert "RuntimeError" not in body
    assert "Traceback" not in body
    assert "energy_trading" not in body
    assert "exception_handlers" not in body

    exception_logs = [payload for payload in payloads if "exception" in payload]
    assert exception_logs
    assert any(payload.get("correlation_id") == "boom-1" for payload in exception_logs)
    assert any(
        "super-secret-test-value" in str(payload.get("exception")) for payload in exception_logs
    )


async def test_unexpected_exception_emits_distinct_completion_event() -> None:
    payloads: list[dict[str, Any]] = []

    class RecordingHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            payloads.append(json.loads(self.format(record)))

    handler = RecordingHandler()
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(JsonLogFormatter())
    logger = logging.getLogger("energy_trading")
    logger.addHandler(handler)
    application = _error_app()
    transport = ASGITransport(app=application, raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/__test__/boom",
                headers={"X-Correlation-ID": "boom-complete-1"},
            )
    finally:
        logger.removeHandler(handler)

    error = _assert_standard_envelope(
        response,
        status_code=500,
        code="internal_error",
        message="An unexpected internal error occurred.",
    )
    assert error["correlation_id"] == "boom-complete-1"

    exception_logs = [
        payload
        for payload in payloads
        if payload.get("message") == "Unhandled exception during request processing"
    ]
    completion_logs = [
        payload for payload in payloads if payload.get("event") == "http_request_completed"
    ]
    assert len(exception_logs) == 1
    assert len(completion_logs) == 1
    completion = completion_logs[0]
    assert completion["correlation_id"] == "boom-complete-1"
    assert completion["method"] == "GET"
    assert completion["path"] == "/__test__/boom"
    assert completion["status_code"] == 500
    assert exception_logs[0]["correlation_id"] == "boom-complete-1"
    assert "event" not in exception_logs[0]
