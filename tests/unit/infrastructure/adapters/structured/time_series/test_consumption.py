"""Consumption time-series duplicate and interval-grid validation tests."""

from datetime import UTC, datetime, timedelta, timezone

from energy_trading.domain.models.observations import ConsumptionRecord
from energy_trading.infrastructure.adapters.structured.time_series import (
    ConsumptionRecordCandidate,
    ConsumptionSeriesIssueCode,
    IntervalGrid,
    validate_consumption_series,
)

_PLUS_FOUR = timezone(timedelta(hours=4))
_ANCHOR = datetime(2026, 9, 5, 0, 0, tzinfo=UTC)
_HOURLY = IntervalGrid(interval=timedelta(hours=1), anchor=_ANCHOR)


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


def test_different_timestamps_same_consumer_are_valid() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 9, 5, 0, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", datetime(2026, 9, 5, 1, 0, tzinfo=UTC), 2.0, 3),
        )
    )
    assert len(result.valid_candidates) == 2
    assert result.issues == ()


def test_same_timestamp_different_consumers_are_valid() -> None:
    stamp = datetime(2026, 9, 5, 0, 0, tzinfo=UTC)
    result = validate_consumption_series(
        (
            _candidate("consumer-a", stamp, 1.0, 2),
            _candidate("consumer-b", stamp, 2.0, 3),
        )
    )
    assert [item.record.consumer_id for item in result.valid_candidates] == [
        "consumer-a",
        "consumer-b",
    ]
    assert result.issues == ()


def test_no_interval_grid_imposes_no_cadence_restriction() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 9, 5, 0, 30, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", datetime(2026, 9, 5, 1, 17, tzinfo=UTC), 2.0, 3),
        )
    )
    assert len(result.valid_candidates) == 2
    assert result.issues == ()


def test_exact_duplicate_fails_every_group_member() -> None:
    stamp = datetime(2026, 9, 5, 0, 0, tzinfo=UTC)
    result = validate_consumption_series(
        (
            _candidate("consumer-1", stamp, 12.5, 2),
            _candidate("consumer-1", stamp, 12.5, 3),
        )
    )
    assert result.valid_candidates == ()
    assert [issue.source_position for issue in result.issues] == [2, 3]
    assert all(
        issue.code is ConsumptionSeriesIssueCode.DUPLICATE_TIMESTAMP for issue in result.issues
    )
    assert all(issue.field_name == "timestamp" for issue in result.issues)


def test_conflicting_duplicate_fails_every_group_member() -> None:
    stamp = datetime(2026, 9, 5, 0, 0, tzinfo=UTC)
    result = validate_consumption_series(
        (
            _candidate("consumer-1", stamp, 12.5, 2),
            _candidate("consumer-1", stamp, 13.0, 3),
        )
    )
    assert result.valid_candidates == ()
    values = {issue.code for issue in result.issues}
    assert values == {ConsumptionSeriesIssueCode.DUPLICATE_TIMESTAMP}


def test_canonically_equivalent_offsets_are_duplicates() -> None:
    result = validate_consumption_series(
        (
            _candidate(
                "consumer-1",
                datetime(2026, 9, 5, 0, 0, tzinfo=_PLUS_FOUR),
                12.5,
                2,
            ),
            _candidate(
                "consumer-1",
                datetime(2026, 9, 4, 20, 0, tzinfo=UTC),
                13.0,
                3,
            ),
        )
    )
    assert result.valid_candidates == ()
    assert [issue.code for issue in result.issues] == [
        ConsumptionSeriesIssueCode.DUPLICATE_TIMESTAMP,
        ConsumptionSeriesIssueCode.DUPLICATE_TIMESTAMP,
    ]
    assert (
        result.issues[0].message == "Consumption source contains a duplicate canonical timestamp."
    )
    assert "consumer-1" not in result.issues[0].message
    assert "12.5" not in result.issues[0].message
    assert "2026" not in result.issues[0].message


def test_nonadjacent_duplicates_are_detected() -> None:
    stamp = datetime(2026, 9, 5, 0, 0, tzinfo=UTC)
    other = datetime(2026, 9, 5, 1, 0, tzinfo=UTC)
    result = validate_consumption_series(
        (
            _candidate("consumer-a", stamp, 1.0, 2),
            _candidate("consumer-b", other, 2.0, 3),
            _candidate("consumer-a", stamp, 1.0, 4),
        )
    )
    assert [item.record.consumer_id for item in result.valid_candidates] == ["consumer-b"]
    assert [issue.source_position for issue in result.issues] == [2, 4]


def test_more_than_two_duplicates_all_fail() -> None:
    stamp = datetime(2026, 9, 5, 0, 0, tzinfo=UTC)
    result = validate_consumption_series(
        (
            _candidate("consumer-1", stamp, 1.0, 2),
            _candidate("consumer-1", stamp, 1.0, 3),
            _candidate("consumer-1", stamp, 2.0, 4),
        )
    )
    assert result.valid_candidates == ()
    assert [issue.source_position for issue in result.issues] == [2, 3, 4]


def test_valid_candidates_preserve_source_order() -> None:
    stamp = datetime(2026, 9, 5, 0, 0, tzinfo=UTC)
    result = validate_consumption_series(
        (
            _candidate("keep-a", datetime(2026, 9, 5, 1, 0, tzinfo=UTC), 1.0, 2),
            _candidate("dup", stamp, 2.0, 3),
            _candidate("keep-c", datetime(2026, 9, 5, 2, 0, tzinfo=UTC), 3.0, 4),
            _candidate("dup", stamp, 2.0, 5),
            _candidate("keep-e", datetime(2026, 9, 5, 3, 0, tzinfo=UTC), 4.0, 6),
        )
    )
    assert [item.record.consumer_id for item in result.valid_candidates] == [
        "keep-a",
        "keep-c",
        "keep-e",
    ]


def test_hourly_on_grid_timestamps_are_valid() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 9, 5, 0, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", datetime(2026, 9, 5, 1, 0, tzinfo=UTC), 2.0, 3),
            _candidate("consumer-1", datetime(2026, 9, 5, 2, 0, tzinfo=UTC), 3.0, 4),
        ),
        interval_grid=_HOURLY,
    )
    assert len(result.valid_candidates) == 3
    assert result.issues == ()


def test_off_grid_timestamp_is_invalid() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 9, 5, 0, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", datetime(2026, 9, 5, 0, 30, tzinfo=UTC), 2.0, 3),
            _candidate("consumer-1", datetime(2026, 9, 5, 1, 0, tzinfo=UTC), 3.0, 4),
        ),
        interval_grid=_HOURLY,
    )
    assert [item.source_position for item in result.valid_candidates] == [2, 4]
    assert len(result.issues) == 1
    assert result.issues[0].code is ConsumptionSeriesIssueCode.INTERVAL_MISALIGNED
    assert result.issues[0].source_position == 3
    assert result.issues[0].field_name == "timestamp"
    assert "00:30" not in result.issues[0].message
    assert "anchor" not in result.issues[0].message


def test_pre_anchor_timestamp_uses_integer_microsecond_modulo() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 9, 4, 22, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", datetime(2026, 9, 4, 22, 30, tzinfo=UTC), 2.0, 3),
        ),
        interval_grid=_HOURLY,
    )
    assert [item.source_position for item in result.valid_candidates] == [2]
    assert result.issues[0].code is ConsumptionSeriesIssueCode.INTERVAL_MISALIGNED
    assert result.issues[0].source_position == 3


def test_hourly_gap_is_not_a_missing_interval_failure() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 9, 5, 0, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", datetime(2026, 9, 5, 2, 0, tzinfo=UTC), 2.0, 3),
        ),
        interval_grid=_HOURLY,
    )
    assert len(result.valid_candidates) == 2
    assert result.issues == ()
    assert all("missing" not in issue.code for issue in result.issues)
    assert all("gap" not in issue.code for issue in result.issues)


def test_out_of_order_aligned_timestamps_preserve_source_order() -> None:
    result = validate_consumption_series(
        (
            _candidate("consumer-1", datetime(2026, 9, 5, 2, 0, tzinfo=UTC), 1.0, 2),
            _candidate("consumer-1", datetime(2026, 9, 5, 0, 0, tzinfo=UTC), 2.0, 3),
            _candidate("consumer-1", datetime(2026, 9, 5, 1, 0, tzinfo=UTC), 3.0, 4),
        ),
        interval_grid=_HOURLY,
    )
    assert [item.record.timestamp for item in result.valid_candidates] == [
        datetime(2026, 9, 5, 2, 0, tzinfo=UTC),
        datetime(2026, 9, 5, 0, 0, tzinfo=UTC),
        datetime(2026, 9, 5, 1, 0, tzinfo=UTC),
    ]
    assert result.issues == ()


def test_duplicate_classification_precedes_interval_misalignment() -> None:
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
    assert [issue.source_position for issue in result.issues] == [2, 4]
    assert all(
        issue.code is ConsumptionSeriesIssueCode.DUPLICATE_TIMESTAMP for issue in result.issues
    )
    assert ConsumptionSeriesIssueCode.INTERVAL_MISALIGNED not in {
        issue.code for issue in result.issues
    }
