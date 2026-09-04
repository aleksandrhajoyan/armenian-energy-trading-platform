"""IntervalGrid and infrastructure-local time-series model tests."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone

import pytest

from energy_trading.domain.models.observations import ConsumptionRecord
from energy_trading.infrastructure.adapters.structured.normalization import (
    NormalizationConfigurationError,
)
from energy_trading.infrastructure.adapters.structured.time_series import (
    ConsumptionRecordCandidate,
    IntervalGrid,
)

_UTC_ANCHOR = datetime(2026, 9, 5, 0, 0, tzinfo=UTC)
_PLUS_FOUR = timezone(timedelta(hours=4))


def test_positive_one_hour_interval_is_accepted() -> None:
    grid = IntervalGrid(interval=timedelta(hours=1), anchor=_UTC_ANCHOR)
    assert grid.interval == timedelta(hours=1)
    assert grid.anchor == _UTC_ANCHOR
    assert grid.anchor.tzinfo is UTC


def test_positive_fifteen_minute_interval_is_accepted() -> None:
    grid = IntervalGrid(interval=timedelta(minutes=15), anchor=_UTC_ANCHOR)
    assert grid.interval == timedelta(minutes=15)


def test_zero_interval_is_rejected() -> None:
    with pytest.raises(NormalizationConfigurationError, match="positive"):
        IntervalGrid(interval=timedelta(0), anchor=_UTC_ANCHOR)


def test_negative_interval_is_rejected() -> None:
    with pytest.raises(NormalizationConfigurationError, match="positive"):
        IntervalGrid(interval=timedelta(hours=-1), anchor=_UTC_ANCHOR)


def test_naive_anchor_is_rejected() -> None:
    with pytest.raises(NormalizationConfigurationError, match="timezone-aware"):
        IntervalGrid(interval=timedelta(hours=1), anchor=datetime(2026, 9, 5, 0, 0))


def test_aware_non_utc_anchor_is_normalized_to_utc() -> None:
    grid = IntervalGrid(
        interval=timedelta(hours=1),
        anchor=datetime(2026, 9, 5, 4, 0, tzinfo=_PLUS_FOUR),
    )
    assert grid.anchor == _UTC_ANCHOR
    assert grid.anchor.tzinfo is UTC


def test_interval_grid_equality_and_immutability() -> None:
    first = IntervalGrid(interval=timedelta(hours=1), anchor=_UTC_ANCHOR)
    second = IntervalGrid(
        interval=timedelta(hours=1),
        anchor=datetime(2026, 9, 5, 4, 0, tzinfo=_PLUS_FOUR),
    )
    assert first == second
    assert hash(first) == hash(second)
    with pytest.raises(FrozenInstanceError):
        first.interval = timedelta(minutes=15)  # type: ignore[misc]


def test_candidate_is_immutable_and_keeps_source_position() -> None:
    record = ConsumptionRecord(
        consumer_id="consumer-1",
        timestamp=_UTC_ANCHOR,
        value_mw=12.5,
    )
    candidate = ConsumptionRecordCandidate(record=record, source_position=4)
    assert candidate.record is record
    assert candidate.source_position == 4
    with pytest.raises(FrozenInstanceError):
        candidate.source_position = 5  # type: ignore[misc]
