"""Infrastructure-local Consumption time-series validation types.

These objects stay inside the ACL. They are not application port payloads and
do not carry raw source rows, headers, or filesystem paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from energy_trading.domain.models.observations import ConsumptionRecord
from energy_trading.infrastructure.adapters.structured.normalization import (
    NormalizationConfigurationError,
)

_MICROSECONDS_PER_SECOND = 1_000_000
_SECONDS_PER_DAY = 86_400
_CANONICAL_TIMESTAMP_FIELD = "timestamp"


class ConsumptionSeriesIssueCode(StrEnum):
    """Machine-readable structural failure for one Consumption candidate."""

    DUPLICATE_TIMESTAMP = "consumption_duplicate_timestamp"
    INTERVAL_MISALIGNED = "consumption_interval_misaligned"


MISSING_INTERVAL_GAP_CODE = "consumption_missing_interval_gap"


@dataclass(frozen=True, slots=True)
class IntervalGrid:
    """Explicit timestamp lattice. Cadence is never inferred."""

    interval: timedelta
    anchor: datetime

    def __post_init__(self) -> None:
        interval = _require_positive_interval(self.interval)
        anchor = _require_aware_anchor(self.anchor).astimezone(UTC)
        object.__setattr__(self, "interval", interval)
        object.__setattr__(self, "anchor", anchor)

    def is_aligned(self, timestamp: datetime) -> bool:
        """Return whether ``timestamp`` lies on this interval lattice."""

        if timestamp.tzinfo is None:
            msg = "timestamp must be timezone-aware"
            raise ValueError(msg)
        delta = timestamp.astimezone(UTC) - self.anchor
        return _timedelta_microseconds(delta) % _timedelta_microseconds(self.interval) == 0

    def step_count_between(self, earlier: datetime, later: datetime) -> int:
        """Return how many configured intervals lie between two aware instants."""

        if earlier.tzinfo is None or later.tzinfo is None:
            msg = "timestamp must be timezone-aware"
            raise ValueError(msg)
        delta = later.astimezone(UTC) - earlier.astimezone(UTC)
        return _timedelta_microseconds(delta) // _timedelta_microseconds(self.interval)

    def offset(self, timestamp: datetime, steps: int) -> datetime:
        """Shift an aware timestamp by an integer number of grid intervals."""

        if timestamp.tzinfo is None:
            msg = "timestamp must be timezone-aware"
            raise ValueError(msg)
        if type(steps) is not int:
            msg = "steps must be an int"
            raise TypeError(msg)
        return timestamp.astimezone(UTC) + (self.interval * steps)


@dataclass(frozen=True, slots=True)
class ConsumptionRecordCandidate:
    """Canonical record plus infrastructure-only source provenance."""

    record: ConsumptionRecord
    source_position: int

    def __post_init__(self) -> None:
        record = _require_consumption_record(self.record)
        if type(self.source_position) is not int:
            msg = "source_position must be an int"
            raise TypeError(msg)
        object.__setattr__(self, "record", record)


@dataclass(frozen=True, slots=True)
class ConsumptionSeriesIssue:
    """One structural finding tied to a source row position."""

    source_position: int
    code: ConsumptionSeriesIssueCode
    field_name: str
    message: str

    def __post_init__(self) -> None:
        if type(self.source_position) is not int:
            msg = "source_position must be an int"
            raise TypeError(msg)
        code = _require_issue_code(self.code)
        field_name = _require_non_empty("field_name", self.field_name)
        message = _require_non_empty("message", self.message)
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "field_name", field_name)
        object.__setattr__(self, "message", message)


@dataclass(frozen=True, slots=True)
class ConsumptionGap:
    """Compact internal missing-interval range for one consumer.

    This is not a source-row finding and has no ``source_position``. It must
    never cross into application ports or canonical records.
    """

    consumer_id: str
    first_missing_timestamp: datetime
    last_missing_timestamp: datetime
    missing_count: int

    def __post_init__(self) -> None:
        consumer_id = _require_non_empty("consumer_id", self.consumer_id)
        first_missing = _require_aware_timestamp(self.first_missing_timestamp).astimezone(UTC)
        last_missing = _require_aware_timestamp(self.last_missing_timestamp).astimezone(UTC)
        missing_count = _require_positive_count(self.missing_count)
        if first_missing > last_missing:
            msg = "first_missing_timestamp must not be after last_missing_timestamp"
            raise ValueError(msg)
        if missing_count == 1 and first_missing != last_missing:
            msg = "single-interval gaps must have identical first and last timestamps"
            raise ValueError(msg)
        object.__setattr__(self, "consumer_id", consumer_id)
        object.__setattr__(self, "first_missing_timestamp", first_missing)
        object.__setattr__(self, "last_missing_timestamp", last_missing)
        object.__setattr__(self, "missing_count", missing_count)

    def diagnostic_message(self) -> str:
        noun = "interval" if self.missing_count == 1 else "intervals"
        return f"Consumption series is missing {self.missing_count} {noun} on the configured grid."


@dataclass(frozen=True, slots=True)
class ConsumptionSeriesValidationResult:
    """Deterministic batch outcome. Valid candidates stay in source order."""

    valid_candidates: tuple[ConsumptionRecordCandidate, ...]
    issues: tuple[ConsumptionSeriesIssue, ...]
    gaps: tuple[ConsumptionGap, ...]

    def __post_init__(self) -> None:
        valid_candidates = _require_tuple(
            "valid_candidates",
            self.valid_candidates,
            ConsumptionRecordCandidate,
        )
        issues = _require_tuple("issues", self.issues, ConsumptionSeriesIssue)
        gaps = _require_tuple("gaps", self.gaps, ConsumptionGap)
        object.__setattr__(self, "valid_candidates", valid_candidates)
        object.__setattr__(self, "issues", issues)
        object.__setattr__(self, "gaps", gaps)


def duplicate_timestamp_issue(source_position: int) -> ConsumptionSeriesIssue:
    return ConsumptionSeriesIssue(
        source_position=source_position,
        code=ConsumptionSeriesIssueCode.DUPLICATE_TIMESTAMP,
        field_name=_CANONICAL_TIMESTAMP_FIELD,
        message="Consumption source contains a duplicate canonical timestamp.",
    )


def interval_misaligned_issue(source_position: int) -> ConsumptionSeriesIssue:
    return ConsumptionSeriesIssue(
        source_position=source_position,
        code=ConsumptionSeriesIssueCode.INTERVAL_MISALIGNED,
        field_name=_CANONICAL_TIMESTAMP_FIELD,
        message="Consumption timestamp is not aligned to the configured interval grid.",
    )


def _require_consumption_record(value: object) -> ConsumptionRecord:
    if not isinstance(value, ConsumptionRecord):
        msg = "record must be a ConsumptionRecord"
        raise TypeError(msg)
    return value


def _require_issue_code(value: object) -> ConsumptionSeriesIssueCode:
    if not isinstance(value, ConsumptionSeriesIssueCode):
        msg = "code must be a ConsumptionSeriesIssueCode"
        raise TypeError(msg)
    return value


def _require_positive_interval(value: object) -> timedelta:
    if not isinstance(value, timedelta):
        raise NormalizationConfigurationError("interval must be a timedelta")
    if value <= timedelta(0):
        raise NormalizationConfigurationError("interval must be a positive timedelta")
    return value


def _require_aware_anchor(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise NormalizationConfigurationError("anchor must be a datetime")
    if value.tzinfo is None:
        raise NormalizationConfigurationError("anchor must be a timezone-aware datetime")
    return value


def _require_aware_timestamp(value: object) -> datetime:
    if not isinstance(value, datetime):
        msg = "timestamp must be a datetime"
        raise TypeError(msg)
    if value.tzinfo is None:
        msg = "timestamp must be timezone-aware"
        raise ValueError(msg)
    return value


def _require_positive_count(value: object) -> int:
    if type(value) is not int:
        msg = "missing_count must be an int"
        raise TypeError(msg)
    if value < 1:
        msg = "missing_count must be a positive int"
        raise ValueError(msg)
    return value


def _timedelta_microseconds(value: timedelta) -> int:
    return (
        value.days * _SECONDS_PER_DAY * _MICROSECONDS_PER_SECOND
        + value.seconds * _MICROSECONDS_PER_SECOND
        + value.microseconds
    )


def _require_non_empty(field_name: str, value: object) -> str:
    if not isinstance(value, str):
        msg = f"{field_name} must be a string"
        raise TypeError(msg)
    cleaned = value.strip()
    if not cleaned:
        msg = f"{field_name} must be a non-empty string"
        raise ValueError(msg)
    return cleaned


def _require_tuple[T](field_name: str, value: object, item_type: type[T]) -> tuple[T, ...]:
    if not isinstance(value, tuple):
        msg = f"{field_name} must be an immutable tuple"
        raise TypeError(msg)
    if not all(isinstance(item, item_type) for item in value):
        msg = f"{field_name} must contain {item_type.__name__} values"
        raise TypeError(msg)
    return value
