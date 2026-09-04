"""Internal missing-interval detection and compact gap reporting tests."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone

import pytest

from energy_trading.domain.models.observations import ConsumptionRecord
from energy_trading.infrastructure.adapters.structured.time_series import (
    ConsumptionGap,
    ConsumptionRecordCandidate,
    ConsumptionSeriesIssueCode,
    IntervalGrid,
    validate_consumption_series,
)

_PLUS_FOUR = timezone(timedelta(hours=4))
_PLUS_TWO = timezone(timedelta(hours=2))
_ANCHOR = datetime(2026, 9, 5, 0, 0, tzinfo=UTC)
_HOURLY = IntervalGrid(interval=timedelta(hours=1), anchor=_ANCHOR)
_QUARTER_HOUR = IntervalGrid(interval=timedelta(minutes=15), anchor=_ANCHOR)


def _candidate(
    consumer_id: str,
    timestamp: datetime,
    value_mw: float,
    source_position: int,
) -> ConsumptionRecordCandidate:
    return ConsumptionRecordCandidate(
        record=ConsumptionRecord(
            consumer_id=consumer_id,
            timestamp=timestamp,
            value_mw=value_mw,
        ),
        source_position=source_position,
    )


def test_gap_is_immutable_and_equality_stable() -> None:
    first = ConsumptionGap(
        consumer_id="consumer-1",
        first_missing_timestamp=datetime(2026, 9, 5, 1, 0, tzinfo=UTC),
        last_missing_timestamp=datetime(2026, 9, 5, 4, 0, tzinfo=UTC),
        missing_count=4,
    )
    second = ConsumptionGap(
        consumer_id="consumer-1",
        first_missing_timestamp=datetime(2026, 9, 5, 5, 0, tzinfo=_PLUS_FOUR),
        last_missing_timestamp=datetime(2026, 9, 5, 8, 0, tzinfo=_PLUS_FOUR),
        missing_count=4,
    )
    assert first == second
    assert hash(first) == hash(second)
    with pytest.raises(FrozenInstanceError):
        first.missing_count = 1  # type: ignore[misc]


def test_gap_diagnostic_message_uses_singular_and_plural() -> None:
    one = ConsumptionGap(
        consumer_id="consumer-1",
        first_missing_timestamp=datetime(2026, 9, 5, 1, 0, tzinfo=UTC),
        last_missing_timestamp=datetime(2026, 9, 5, 1, 0, tzinfo=UTC),
        missing_count=1,
    )
    four = ConsumptionGap(
        consumer_id="consumer-1",
        first_missing_timestamp=datetime(2026, 9, 5, 1, 0, tzinfo=UTC),
        last_missing_timestamp=datetime(2026, 9, 5, 4, 0, tzinfo=UTC),
        missing_count=4,
    )
    assert one.diagnostic_message() == (
        "Consumption series is missing 1 interval on the configured grid."
    )
    assert four.diagnostic_message() == (
        "Consumption series is missing 4 intervals on the configured grid."
    )
    assert "consumer-1" not in one.diagnostic_message()
    assert "2026" not in four.diagnostic_message()


def test_no_grid_does_not_report_gaps() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 9, 5, 0, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", datetime(2026, 9, 5, 5, 0, tzinfo=UTC), 2.0, 3),
        )
    )
    assert len(result.valid_candidates) == 2
    assert result.gaps == ()


def test_consecutive_hourly_observations_have_no_gap() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 9, 5, 0, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", datetime(2026, 9, 5, 1, 0, tzinfo=UTC), 2.0, 3),
        ),
        interval_grid=_HOURLY,
    )
    assert result.gaps == ()
    assert result.issues == ()


def test_one_missing_hourly_interval() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 9, 5, 0, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", datetime(2026, 9, 5, 2, 0, tzinfo=UTC), 2.0, 3),
        ),
        interval_grid=_HOURLY,
    )
    assert len(result.gaps) == 1
    gap = result.gaps[0]
    assert gap.consumer_id == "consumer-1"
    assert gap.missing_count == 1
    assert gap.first_missing_timestamp == datetime(2026, 9, 5, 1, 0, tzinfo=UTC)
    assert gap.last_missing_timestamp == datetime(2026, 9, 5, 1, 0, tzinfo=UTC)
    assert [item.source_position for item in result.valid_candidates] == [2, 3]


def test_multi_slot_contiguous_gap_is_compact() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 9, 5, 0, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", datetime(2026, 9, 5, 5, 0, tzinfo=UTC), 2.0, 3),
        ),
        interval_grid=_HOURLY,
    )
    assert len(result.gaps) == 1
    gap = result.gaps[0]
    assert gap.missing_count == 4
    assert gap.first_missing_timestamp == datetime(2026, 9, 5, 1, 0, tzinfo=UTC)
    assert gap.last_missing_timestamp == datetime(2026, 9, 5, 4, 0, tzinfo=UTC)
    assert not hasattr(gap, "missing_timestamps")


def test_two_separate_gaps_are_not_merged() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 9, 5, 0, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", datetime(2026, 9, 5, 2, 0, tzinfo=UTC), 2.0, 3),
            _candidate("consumer-1", datetime(2026, 9, 5, 3, 0, tzinfo=UTC), 3.0, 4),
            _candidate("consumer-1", datetime(2026, 9, 5, 6, 0, tzinfo=UTC), 4.0, 5),
        ),
        interval_grid=_HOURLY,
    )
    assert [
        (gap.missing_count, gap.first_missing_timestamp, gap.last_missing_timestamp)
        for gap in result.gaps
    ] == [
        (1, datetime(2026, 9, 5, 1, 0, tzinfo=UTC), datetime(2026, 9, 5, 1, 0, tzinfo=UTC)),
        (2, datetime(2026, 9, 5, 4, 0, tzinfo=UTC), datetime(2026, 9, 5, 5, 0, tzinfo=UTC)),
    ]


def test_fifteen_minute_grid_reports_compact_gap() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 9, 5, 0, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", datetime(2026, 9, 5, 0, 45, tzinfo=UTC), 2.0, 3),
        ),
        interval_grid=_QUARTER_HOUR,
    )
    assert len(result.gaps) == 1
    assert result.gaps[0].missing_count == 2
    assert result.gaps[0].first_missing_timestamp == datetime(2026, 9, 5, 0, 15, tzinfo=UTC)
    assert result.gaps[0].last_missing_timestamp == datetime(2026, 9, 5, 0, 30, tzinfo=UTC)


def test_multiple_consumers_keep_independent_gaps() -> None:
    stamp_a0 = datetime(2026, 9, 5, 0, 0, tzinfo=UTC)
    stamp_a2 = datetime(2026, 9, 5, 2, 0, tzinfo=UTC)
    stamp_b0 = datetime(2026, 9, 5, 0, 0, tzinfo=UTC)
    stamp_b2 = datetime(2026, 9, 5, 2, 0, tzinfo=UTC)
    result = validate_consumption_series(
        (
            _candidate("consumer-a", stamp_a0, 1.0, 2),
            _candidate("consumer-b", stamp_b0, 2.0, 3),
            _candidate("consumer-a", stamp_a2, 3.0, 4),
            _candidate("consumer-b", stamp_b2, 4.0, 5),
        ),
        interval_grid=_HOURLY,
    )
    assert [gap.consumer_id for gap in result.gaps] == ["consumer-a", "consumer-b"]
    assert all(gap.missing_count == 1 for gap in result.gaps)


def test_complete_consumer_does_not_create_gap_for_incomplete_sibling() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-a", datetime(2026, 9, 5, 0, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-a", datetime(2026, 9, 5, 2, 0, tzinfo=UTC), 2.0, 3),
            _candidate("consumer-b", datetime(2026, 9, 5, 0, 0, tzinfo=UTC), 3.0, 4),
            _candidate("consumer-b", datetime(2026, 9, 5, 1, 0, tzinfo=UTC), 4.0, 5),
            _candidate("consumer-b", datetime(2026, 9, 5, 2, 0, tzinfo=UTC), 5.0, 6),
        ),
        interval_grid=_HOURLY,
    )
    assert [gap.consumer_id for gap in result.gaps] == ["consumer-a"]
    assert result.gaps[0].missing_count == 1


def test_single_record_has_no_internal_gap() -> None:
    result = validate_consumption_series(
        (_candidate("consumer-1", datetime(2026, 9, 5, 2, 0, tzinfo=UTC), 1.0, 2),),
        interval_grid=_HOURLY,
    )
    assert len(result.valid_candidates) == 1
    assert result.gaps == ()


def test_empty_candidates_have_no_gap() -> None:
    result = validate_consumption_series((), interval_grid=_HOURLY)
    assert result.valid_candidates == ()
    assert result.issues == ()
    assert result.gaps == ()


def test_out_of_order_candidates_detect_gap_without_sorting_output() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 9, 5, 2, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", datetime(2026, 9, 5, 0, 0, tzinfo=UTC), 2.0, 3),
        ),
        interval_grid=_HOURLY,
    )
    assert [item.record.timestamp for item in result.valid_candidates] == [
        datetime(2026, 9, 5, 2, 0, tzinfo=UTC),
        datetime(2026, 9, 5, 0, 0, tzinfo=UTC),
    ]
    assert result.gaps[0].first_missing_timestamp == datetime(2026, 9, 5, 1, 0, tzinfo=UTC)


def test_no_leading_or_trailing_coverage_is_inferred() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 9, 5, 2, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", datetime(2026, 9, 5, 3, 0, tzinfo=UTC), 2.0, 3),
        ),
        interval_grid=_HOURLY,
    )
    assert result.gaps == ()


def test_pre_anchor_missing_interval_uses_exact_arithmetic() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 9, 4, 21, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", datetime(2026, 9, 4, 23, 0, tzinfo=UTC), 2.0, 3),
        ),
        interval_grid=_HOURLY,
    )
    assert len(result.gaps) == 1
    assert result.gaps[0].missing_count == 1
    assert result.gaps[0].first_missing_timestamp == datetime(2026, 9, 4, 22, 0, tzinfo=UTC)


def test_gap_detection_uses_canonical_utc_instants() -> None:
    result = validate_consumption_series(
        (
            _candidate(
                "consumer-1",
                datetime(2026, 9, 5, 4, 0, tzinfo=_PLUS_FOUR),
                1.0,
                2,
            ),
            _candidate(
                "consumer-1",
                datetime(2026, 9, 5, 4, 0, tzinfo=_PLUS_TWO),
                2.0,
                3,
            ),
        ),
        interval_grid=_HOURLY,
    )
    assert result.gaps[0].missing_count == 1
    assert result.gaps[0].first_missing_timestamp == datetime(2026, 9, 5, 1, 0, tzinfo=UTC)


def test_large_gap_is_one_compact_range() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 1, 1, 0, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", datetime(2026, 1, 11, 0, 0, tzinfo=UTC), 2.0, 3),
        ),
        interval_grid=IntervalGrid(
            interval=timedelta(hours=1),
            anchor=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        ),
    )
    assert len(result.gaps) == 1
    gap = result.gaps[0]
    assert gap.missing_count == 239
    assert gap.first_missing_timestamp == datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    assert gap.last_missing_timestamp == datetime(2026, 1, 10, 23, 0, tzinfo=UTC)


def test_duplicate_rejection_can_create_canonical_gap() -> None:
    stamp_one = datetime(2026, 9, 5, 1, 0, tzinfo=UTC)
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 9, 5, 0, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", stamp_one, 2.0, 3),
            _candidate("consumer-1", stamp_one, 3.0, 4),
            _candidate("consumer-1", datetime(2026, 9, 5, 2, 0, tzinfo=UTC), 4.0, 5),
        ),
        interval_grid=_HOURLY,
    )
    assert [item.source_position for item in result.valid_candidates] == [2, 5]
    assert [issue.source_position for issue in result.issues] == [3, 4]
    assert all(
        issue.code is ConsumptionSeriesIssueCode.DUPLICATE_TIMESTAMP for issue in result.issues
    )
    assert len(result.gaps) == 1
    assert result.gaps[0].missing_count == 1
    assert result.gaps[0].first_missing_timestamp == stamp_one


def test_off_grid_rejection_can_create_canonical_gap() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 9, 5, 0, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", datetime(2026, 9, 5, 0, 30, tzinfo=UTC), 2.0, 3),
            _candidate("consumer-1", datetime(2026, 9, 5, 2, 0, tzinfo=UTC), 3.0, 4),
        ),
        interval_grid=_HOURLY,
    )
    assert [item.source_position for item in result.valid_candidates] == [2, 4]
    assert result.issues[0].code is ConsumptionSeriesIssueCode.INTERVAL_MISALIGNED
    assert result.issues[0].source_position == 3
    assert result.gaps[0].missing_count == 1
    assert result.gaps[0].first_missing_timestamp == datetime(2026, 9, 5, 1, 0, tzinfo=UTC)


def test_duplicate_precedence_over_interval_is_preserved_with_gaps() -> None:
    off_grid = datetime(2026, 9, 5, 0, 30, tzinfo=UTC)
    result = validate_consumption_series(
        (
            _candidate("consumer-1", off_grid, 1.0, 2),
            _candidate("consumer-1", datetime(2026, 9, 5, 1, 0, tzinfo=UTC), 2.0, 3),
            _candidate("consumer-1", off_grid, 3.0, 4),
        ),
        interval_grid=_HOURLY,
    )
    assert [item.source_position for item in result.valid_candidates] == [3]
    assert all(
        issue.code is ConsumptionSeriesIssueCode.DUPLICATE_TIMESTAMP for issue in result.issues
    )
    assert result.gaps == ()
