"""Deterministic Consumption time-series structural validation.

Duplicate detection always runs after individual canonical records exist.
Interval-grid alignment runs only when an explicit ``IntervalGrid`` is
supplied. Missing-interval detection, interpolation, and sorting are out of
scope.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime

from energy_trading.infrastructure.adapters.structured.normalization import (
    NormalizationConfigurationError,
)
from energy_trading.infrastructure.adapters.structured.time_series.models import (
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
    """Fail duplicate groups closed and optionally reject off-grid timestamps.

    Valid output preserves the input candidate order. Duplicate classification
    takes precedence over interval misalignment. This function does not sort,
    interpolate, fill gaps, or choose a duplicate winner.
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
    return ConsumptionSeriesValidationResult(
        valid_candidates=tuple(valid),
        issues=tuple(issues),
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
