"""Explicit IANA timezone resolution for structured timestamps.

No timezone is inferred. Unix epoch numbers and Excel serial dates are not
interpreted. Date-only values are not treated as local midnight.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from energy_trading.infrastructure.adapters.structured.normalization.errors import (
    NormalizationConfigurationError,
    SourceValueNormalizationError,
)


def resolve_source_timezone(name: str | None) -> ZoneInfo | None:
    """Validate an optional IANA timezone at adapter construction."""

    if name is None:
        return None
    if not isinstance(name, str):
        raise NormalizationConfigurationError("source_timezone must be an IANA timezone name")
    cleaned = name.strip()
    if not cleaned:
        raise NormalizationConfigurationError(
            "source_timezone must be a non-empty IANA timezone name"
        )
    try:
        return ZoneInfo(cleaned)
    except ZoneInfoNotFoundError as exc:
        raise NormalizationConfigurationError(
            "source_timezone is not a known IANA timezone"
        ) from exc


def normalize_timestamp_to_utc(
    value: object,
    source_timezone: ZoneInfo | None,
) -> datetime:
    """Produce an aware UTC datetime from an explicit source representation.

    Already-aware values keep their represented instant. Naive values require
    ``source_timezone``. Ambiguous and nonexistent DST local clocks fail closed.
    """

    parsed = _parse_timestamp(value)
    if parsed.tzinfo is not None:
        return parsed.astimezone(UTC)
    if source_timezone is None:
        raise SourceValueNormalizationError("naive timestamp has no source timezone")
    return _localize_naive(parsed, source_timezone)


def _parse_timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return _parse_timestamp_text(value)
    raise SourceValueNormalizationError("timestamp source representation is invalid")


def _parse_timestamp_text(value: str) -> datetime:
    text = value.strip()
    if not text or _is_bare_numeric_text(text) or _is_date_only_text(text):
        raise SourceValueNormalizationError("timestamp source representation is invalid")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise SourceValueNormalizationError("timestamp source representation is invalid") from exc
    if not isinstance(parsed, datetime):
        raise SourceValueNormalizationError("timestamp source representation is invalid")
    return parsed


def _is_date_only_text(value: str) -> bool:
    return "T" not in value and " " not in value


def _is_bare_numeric_text(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _localize_naive(value: datetime, zone: ZoneInfo) -> datetime:
    first = value.replace(tzinfo=zone, fold=0)
    second = value.replace(tzinfo=zone, fold=1)
    utc_first = first.astimezone(UTC)
    utc_second = second.astimezone(UTC)
    if utc_first != utc_second:
        raise SourceValueNormalizationError("local timestamp is DST-ambiguous")
    wall = utc_first.astimezone(zone).replace(tzinfo=None)
    if wall != value:
        raise SourceValueNormalizationError("local timestamp does not exist in timezone")
    return utc_first
