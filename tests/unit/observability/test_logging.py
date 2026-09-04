"""Unit tests for structured JSON logging configuration and formatting."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from typing import Any

from energy_trading.api.app import create_app
from energy_trading.shared.config.settings import AppEnvironment, AppSettings
from energy_trading.shared.observability.correlation import correlation_id_scope
from energy_trading.shared.observability.logging import (
    ENERGY_TRADING_LOGGER_NAME,
    JSON_HANDLER_NAME,
    JsonLogFormatter,
    configure_logging,
)


def _record(message: str = "structured log message") -> logging.LogRecord:
    return logging.LogRecord(
        name="energy_trading.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )


def test_json_formatter_includes_required_fields() -> None:
    formatter = JsonLogFormatter()
    with correlation_id_scope("log-correlation-1"):
        payload = json.loads(formatter.format(_record()))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "energy_trading.test"
    assert payload["message"] == "structured log message"
    assert payload["correlation_id"] == "log-correlation-1"
    timestamp = payload["timestamp"]
    assert isinstance(timestamp, str)
    assert timestamp.endswith("Z")
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_json_formatter_uses_null_correlation_when_unbound() -> None:
    formatter = JsonLogFormatter()
    payload = json.loads(formatter.format(_record()))
    assert payload["correlation_id"] is None


def test_json_formatter_omits_unknown_extras() -> None:
    formatter = JsonLogFormatter()
    record = _record()
    record.password = "super-secret-test-value"  # noqa: S105
    record.authorization = "Bearer super-secret-test-value"
    record.event = "http_request_completed"
    record.method = "GET"
    record.path = "/api/v1/health"
    record.status_code = 200
    record.duration_ms = 3
    payload: dict[str, Any] = json.loads(formatter.format(record))
    dumped = json.dumps(payload)
    assert "super-secret-test-value" not in dumped
    assert "password" not in payload
    assert "authorization" not in payload
    assert payload["event"] == "http_request_completed"
    assert payload["method"] == "GET"
    assert payload["path"] == "/api/v1/health"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 3


def test_json_formatter_includes_exception_internally() -> None:
    formatter = JsonLogFormatter()
    try:
        raise RuntimeError("database password=super-secret-test-value")
    except RuntimeError:
        record = logging.LogRecord(
            name="energy_trading.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="internal failure",
            args=(),
            exc_info=sys.exc_info(),
        )
    payload = json.loads(formatter.format(record))
    assert "exception" in payload
    assert "super-secret-test-value" in str(payload["exception"])


def test_configure_logging_is_idempotent() -> None:
    configure_logging("INFO")
    configure_logging("DEBUG")
    configure_logging("INFO")
    logger = logging.getLogger(ENERGY_TRADING_LOGGER_NAME)
    json_handlers = [handler for handler in logger.handlers if handler.name == JSON_HANDLER_NAME]
    assert len(json_handlers) == 1
    assert logger.level == logging.INFO


def test_create_app_does_not_stack_duplicate_log_handlers() -> None:
    settings = AppSettings(_env_file=None, environment=AppEnvironment.TEST)
    create_app(settings)
    create_app(settings)
    logger = logging.getLogger(ENERGY_TRADING_LOGGER_NAME)
    json_handlers = [handler for handler in logger.handlers if handler.name == JSON_HANDLER_NAME]
    assert len(json_handlers) == 1
