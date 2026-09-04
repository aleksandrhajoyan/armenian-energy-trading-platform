"""Deterministic Consumption time-series structural validation.

Duplicate detection always runs after individual canonical records exist.
Interval-grid alignment and internal gap reporting run only when an explicit
``IntervalGrid`` is supplied. Interpolation, synthetic fill, and outward
sorting are out of scope.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime

from energy_trading.infrastructure.adapters.structured.normalization import (
    NormalizationConfigurationError,
)
from energy_trading.infrastructure.adapters.structured.time_series.models import (
    ConsumptionGap,
    ConsumptionRecordCandidate,
    ConsumptionSeriesIssue,
    ConsumptionSeriesValidationResult,
    IntervalGrid,
    duplicate_timestamp_issue,
    interval_misaligned_issue,
)

_ObservationKey = tuple[str, datetime]


def validate_consumption_series(
    candidates: Sequence[ConsumptionRecordCandidate],
    interval_grid: IntervalGrid | None = None,
) -> ConsumptionSeriesValidationResult:
    """Fail duplicate groups closed, optionally reject off-grid timestamps, and
    report compact internal gaps.

    Valid output preserves the input candidate order. Duplicate classification
    takes precedence over interval misalignment. Gap detection inspects only
    surviving candidates and does not invent leading or trailing coverage.
    This function does not sort outward records, interpolate, fill gaps, or
    choose a duplicate winner.
    """

    if interval_grid is not None and not isinstance(interval_grid, IntervalGrid):
        raise NormalizationConfigurationError("interval_grid must be an IntervalGrid")
    ordered = _require_candidates(candidates)
    duplicate_indexes = _duplicate_indexes(ordered)

    valid: list[ConsumptionRecordCandidate] = []
    issues: list[ConsumptionSeriesIssue] = []
    for index, candidate in enumerate(ordered):
        if index in duplicate_indexes:
            issues.append(duplicate_timestamp_issue(candidate.source_position))
            continue
        if interval_grid is not None and not interval_grid.is_aligned(candidate.record.timestamp):
            issues.append(interval_misaligned_issue(candidate.source_position))
            continue
        valid.append(candidate)
    surviving = tuple(valid)
    return ConsumptionSeriesValidationResult(
        valid_candidates=surviving,
        issues=tuple(issues),
        gaps=_detect_gaps(surviving, interval_grid),
    )


def _require_candidates(
    value: Sequence[ConsumptionRecordCandidate],
) -> tuple[ConsumptionRecordCandidate, ...]:
    ordered = tuple(value)
    if not all(isinstance(item, ConsumptionRecordCandidate) for item in ordered):
        msg = "candidates must contain ConsumptionRecordCandidate values"
        raise TypeError(msg)
    return ordered


def _duplicate_indexes(candidates: tuple[ConsumptionRecordCandidate, ...]) -> frozenset[int]:
    groups: dict[_ObservationKey, list[int]] = defaultdict(list)
    for index, candidate in enumerate(candidates):
        key: _ObservationKey = (candidate.record.consumer_id, candidate.record.timestamp)
        groups[key].append(index)
    return frozenset(index for indexes in groups.values() if len(indexes) > 1 for index in indexes)


def _detect_gaps(
    candidates: tuple[ConsumptionRecordCandidate, ...],
    interval_grid: IntervalGrid | None,
) -> tuple[ConsumptionGap, ...]:
    if interval_grid is None:
        return ()
    grouped: dict[str, list[datetime]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.record.consumer_id].append(candidate.record.timestamp)
    gaps: list[ConsumptionGap] = []
    for consumer_id in sorted(grouped):
        timestamps = sorted(grouped[consumer_id])
        for previous, current in zip(timestamps, timestamps[1:], strict=False):
            gap = _gap_between(consumer_id, previous, current, interval_grid)
            if gap is not None:
                gaps.append(gap)
    return tuple(gaps)


def _gap_between(
    consumer_id: str,
    previous: datetime,
    current: datetime,
    interval_grid: IntervalGrid,
) -> ConsumptionGap | None:
    step_count = interval_grid.step_count_between(previous, current)
    if step_count <= 1:
        return None
    return ConsumptionGap(
        consumer_id=consumer_id,
        first_missing_timestamp=interval_grid.offset(previous, 1),
        last_missing_timestamp=interval_grid.offset(current, -1),
        missing_count=step_count - 1,
    )
