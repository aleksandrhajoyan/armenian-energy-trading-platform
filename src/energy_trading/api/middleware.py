"""Pure ASGI middleware for correlation IDs and HTTP request completion logs."""

from __future__ import annotations

import logging
import time

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from energy_trading.shared.observability.correlation import (
    CORRELATION_HEADER,
    correlation_id_scope,
    generate_correlation_id,
    is_valid_correlation_id,
)
from energy_trading.shared.observability.logging import ENERGY_TRADING_LOGGER_NAME

_CORRELATION_HEADER_BYTES = CORRELATION_HEADER.lower().encode("ascii")
_http_logger = logging.getLogger(f"{ENERGY_TRADING_LOGGER_NAME}.api.http")
SCOPE_CORRELATION_ID_KEY = "correlation_id"


def bind_correlation_id_to_scope(scope: Scope, correlation_id: str) -> None:
    """Persist the request correlation ID on ASGI scope state for outer handlers."""

    state = scope.setdefault("state", {})
    if isinstance(state, dict):
        state[SCOPE_CORRELATION_ID_KEY] = correlation_id
        return
    setattr(state, SCOPE_CORRELATION_ID_KEY, correlation_id)


def correlation_id_from_scope(scope: Scope) -> str | None:
    """Read a correlation ID previously bound onto ASGI scope state."""

    state = scope.get("state")
    if isinstance(state, dict):
        stored = state.get(SCOPE_CORRELATION_ID_KEY)
    else:
        stored = getattr(state, SCOPE_CORRELATION_ID_KEY, None)
    return stored if isinstance(stored, str) else None


def _incoming_correlation_id(scope: Scope) -> str | None:
    headers = scope.get("headers")
    if not isinstance(headers, list):
        return None
    for key, value in headers:
        if key == _CORRELATION_HEADER_BYTES:
            try:
                raw = value
                if not isinstance(raw, (bytes, bytearray)):
                    return None
                return raw.decode("ascii")
            except UnicodeDecodeError:
                return None
    return None


def resolve_correlation_id(scope: Scope) -> str:
    """Reuse a valid incoming correlation ID, otherwise generate a safe one."""

    incoming = _incoming_correlation_id(scope)
    if incoming is not None and is_valid_correlation_id(incoming):
        return incoming
    return generate_correlation_id()


class CorrelationMiddleware:
    """Bind a correlation ID in a ContextVar for the lifetime of one HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        correlation_id = resolve_correlation_id(scope)
        bind_correlation_id_to_scope(scope, correlation_id)

        async def send_with_correlation(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers[CORRELATION_HEADER] = correlation_id
            await send(message)

        with correlation_id_scope(correlation_id):
            await self.app(scope, receive, send_with_correlation)


class RequestLoggingMiddleware:
    """Log a structured completion event for every HTTP request.

    Logs path only. Does not log query strings, bodies, or sensitive headers.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.monotonic()
        method = str(scope.get("method", ""))
        path = str(scope.get("path", ""))
        status_code = 500

        async def send_and_capture(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_and_capture)
        except Exception:
            # Exception escaped to outer ServerErrorMiddleware. Record 500 once, then re-raise.
            status_code = 500
            raise
        finally:
            duration_ms = int((time.monotonic() - started) * 1000)
            _http_logger.info(
                "HTTP request completed",
                extra={
                    "event": "http_request_completed",
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
