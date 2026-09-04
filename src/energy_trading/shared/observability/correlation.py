"""Per-request correlation ID context using contextvars."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from re import Pattern
from re import compile as compile_regex
from uuid import uuid4

CORRELATION_HEADER: str = "X-Correlation-ID"
MAX_CORRELATION_ID_LENGTH: int = 128
_CORRELATION_ID_PATTERN: Pattern[str] = compile_regex(r"^[A-Za-z0-9._:-]{1,128}$")

_CORRELATION_ID: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    """Return the current correlation ID, or ``None`` when no request is bound."""

    return _CORRELATION_ID.get()


def generate_correlation_id() -> str:
    """Return a new UUID-based correlation ID."""

    return str(uuid4())


def is_valid_correlation_id(value: str) -> bool:
    """Return whether ``value`` is a conservatively acceptable correlation ID."""

    if not value or len(value) > MAX_CORRELATION_ID_LENGTH:
        return False
    return _CORRELATION_ID_PATTERN.fullmatch(value) is not None


def _set_correlation_id(correlation_id: str) -> Token[str | None]:
    return _CORRELATION_ID.set(correlation_id)


def _reset_correlation_id(token: Token[str | None]) -> None:
    _CORRELATION_ID.reset(token)


@contextmanager
def correlation_id_scope(correlation_id: str) -> Iterator[str]:
    """Bind ``correlation_id`` for the duration of the calling context."""

    token = _set_correlation_id(correlation_id)
    try:
        yield correlation_id
    finally:
        _reset_correlation_id(token)
