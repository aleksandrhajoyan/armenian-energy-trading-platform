"""Structured JSON logging using the Python standard library.

Configuration is explicit and must be invoked from the composition root.
This module does not configure logging on import.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Final

from energy_trading.shared.observability.correlation import get_correlation_id

JSON_HANDLER_NAME: Final[str] = "energy_trading_json"
ENERGY_TRADING_LOGGER_NAME: Final[str] = "energy_trading"

_ALLOWED_EXTRA_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "event",
        "method",
        "path",
        "status_code",
        "duration_ms",
    }
)


class CorrelationIdFilter(logging.Filter):
    """Stamp the current correlation ID onto the log record at emit time."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.__dict__["correlation_id"] = get_correlation_id()
        return True


class JsonLogFormatter(logging.Formatter):
    """Format log records as machine-readable JSON.

    Unknown logger extras are ignored so secrets cannot leak through ``extra=``.
    """

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).isoformat(
            timespec="milliseconds"
        )
        if timestamp.endswith("+00:00"):
            timestamp = f"{timestamp[:-6]}Z"

        correlation_id: str | None
        if "correlation_id" in record.__dict__:
            stamped = record.__dict__["correlation_id"]
            correlation_id = stamped if isinstance(stamped, str) else None
        else:
            correlation_id = get_correlation_id()

        payload: dict[str, object] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id,
        }

        for field_name in _ALLOWED_EXTRA_FIELDS:
            if field_name in record.__dict__:
                payload[field_name] = record.__dict__[field_name]

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str) -> None:
    """Configure the ``energy_trading`` logger for JSON output.

    Idempotent: repeated calls update the level and do not stack handlers.
    Does not reconfigure the root logger or pytest's log capture.
    """

    logger = logging.getLogger(ENERGY_TRADING_LOGGER_NAME)
    logger.setLevel(level.upper())

    existing = _json_handlers(logger)
    if existing:
        for handler in existing:
            handler.setLevel(logging.DEBUG)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.name = JSON_HANDLER_NAME
    handler.setLevel(logging.DEBUG)
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)
    logger.propagate = False


def _json_handlers(logger: logging.Logger) -> list[logging.Handler]:
    return [handler for handler in logger.handlers if handler.name == JSON_HANDLER_NAME]
