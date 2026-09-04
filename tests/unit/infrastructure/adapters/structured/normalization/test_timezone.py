"""Timezone normalization primitive tests."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from energy_trading.infrastructure.adapters.structured.normalization import (
    NormalizationConfigurationError,
    SourceValueNormalizationError,
    normalize_timestamp_to_utc,
    resolve_source_timezone,
)

_BERLIN = ZoneInfo("Europe/Berlin")
_AMBIGUOUS = datetime(2026, 10, 25, 2, 30, 0)
_NONEXISTENT = datetime(2026, 3, 29, 2, 30, 0)


def test_aware_datetime_preserves_instant_in_utc() -> None:
    aware = datetime.fromisoformat("2026-09-05T00:00:00+04:00")
    result = normalize_timestamp_to_utc(aware, ZoneInfo("UTC"))
    assert result == datetime(2026, 9, 4, 20, 0, tzinfo=UTC)
    assert result.tzinfo is UTC


def test_aware_iso_string_preserves_instant_in_utc() -> None:
    result = normalize_timestamp_to_utc("2026-09-05T00:00:00+04:00", ZoneInfo("UTC"))
    assert result == datetime(2026, 9, 4, 20, 0, tzinfo=UTC)


def test_naive_datetime_without_timezone_fails() -> None:
    with pytest.raises(SourceValueNormalizationError):
        normalize_timestamp_to_utc(datetime(2026, 1, 15, 12, 0, 0), None)


def test_naive_string_without_timezone_fails() -> None:
    with pytest.raises(SourceValueNormalizationError):
        normalize_timestamp_to_utc("2026-01-15T12:00:00", None)


def test_naive_datetime_with_explicit_zone_converts_to_utc() -> None:
    result = normalize_timestamp_to_utc(datetime(2026, 1, 15, 12, 0, 0), _BERLIN)
    assert result == datetime(2026, 1, 15, 11, 0, tzinfo=UTC)


def test_naive_textual_datetime_with_explicit_zone_converts_to_utc() -> None:
    result = normalize_timestamp_to_utc("2026-01-15T12:00:00", _BERLIN)
    assert result == datetime(2026, 1, 15, 11, 0, tzinfo=UTC)


def test_bare_numeric_string_is_rejected() -> None:
    for value in ("1", "45200", "1710000000"):
        with pytest.raises(SourceValueNormalizationError):
            normalize_timestamp_to_utc(value, _BERLIN)


def test_numeric_source_is_rejected() -> None:
    for value in (1, 45200, 1710000000, 1710000000.0):
        with pytest.raises(SourceValueNormalizationError):
            normalize_timestamp_to_utc(value, _BERLIN)


def test_date_only_string_is_rejected() -> None:
    with pytest.raises(SourceValueNormalizationError):
        normalize_timestamp_to_utc("2026-09-05", _BERLIN)
    with pytest.raises(SourceValueNormalizationError):
        normalize_timestamp_to_utc(date(2026, 9, 5), _BERLIN)


def test_invalid_timezone_configuration_is_rejected() -> None:
    with pytest.raises(NormalizationConfigurationError):
        resolve_source_timezone("Not/AZone")
    with pytest.raises(NormalizationConfigurationError):
        resolve_source_timezone("  ")
    assert resolve_source_timezone(None) is None
    assert resolve_source_timezone("UTC") == ZoneInfo("UTC")


def test_ambiguous_dst_local_time_is_rejected() -> None:
    with pytest.raises(SourceValueNormalizationError):
        normalize_timestamp_to_utc(_AMBIGUOUS, _BERLIN)


def test_nonexistent_dst_local_time_is_rejected() -> None:
    with pytest.raises(SourceValueNormalizationError):
        normalize_timestamp_to_utc(_NONEXISTENT, _BERLIN)


def test_configured_zone_does_not_overwrite_aware_offset() -> None:
    result = normalize_timestamp_to_utc("2026-09-05T00:00:00+04:00", _BERLIN)
    assert result == datetime(2026, 9, 4, 20, 0, tzinfo=UTC)
