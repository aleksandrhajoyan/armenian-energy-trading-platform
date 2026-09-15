"""Exact 24-hour plus 168-hour lag Consumer Load supervised feature rows.

This outer ML transformation builds chronological historical feature
rows for a future trained Consumer Load model. It does not train a
model and does not calculate metrics.

Ownership:

* Application: owns live inference via ``ConsumerLoadForecastModelPort``.
* ML: owns this offline feature-row builder. Returned values are ML
  supervised rows, not workflow state and not ``LoadForecastPoint``.
* Canonical ``ConsumptionRecord`` history is the only input. This module
  does not belong to application orchestration.

A row exists only when all three exact observations exist:

* ``lag_24h_mw`` is the observation at exactly ``T - 24 hours``
* ``lag_168h_mw`` is the observation at exactly ``T - 168 hours``
* ``target_value_mw`` is the observation at ``T``

The weekly feature is 168 elapsed hours, not a weekday label. Near
timestamps, resampling, rolling statistics, and calendar/time-of-day
features are not used. Duplicate timestamps or mixed consumer identity
fail closed before any row is returned. Canonical MW values are copied
unchanged.

This contract is independent of the published one-feature 24-hour row.
Missing either required lag omits that target rather than imputing a
value.

The builder remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.models.observations import ConsumptionRecord
from energy_trading.domain.value_objects.quantities import EntityId, NonNegativeMW
from energy_trading.domain.value_objects.time import UtcDateTime

_LAG_24H = timedelta(hours=24)
_LAG_168H = timedelta(hours=168)
_MIXED_CONSUMER_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag features require history from exactly one consumer."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag features require unique historical timestamps."
)


@dataclass(frozen=True, slots=True)
class ConsumerLoadLag24h168hFeatureRow:
    """One exact ``T`` / ``T - 24h`` / ``T - 168h`` Consumer Load supervised row."""

    consumer_id: EntityId
    target_timestamp: UtcDateTime
    lag_24h_mw: NonNegativeMW
    lag_168h_mw: NonNegativeMW
    target_value_mw: NonNegativeMW


def build_consumer_load_lag_24h_168h_feature_rows(
    *,
    history: tuple[ConsumptionRecord, ...],
) -> tuple[ConsumerLoadLag24h168hFeatureRow, ...]:
    """Return chronological exact-triple feature rows, skipping incomplete lags."""

    if not history:
        return ()
    _require_single_consumer(history)
    by_timestamp = _unique_timestamp_index(history)
    return tuple(
        _row_for_target(by_timestamp, target)
        for target in sorted(by_timestamp)
        if (target - _LAG_24H) in by_timestamp and (target - _LAG_168H) in by_timestamp
    )


def _require_single_consumer(history: tuple[ConsumptionRecord, ...]) -> None:
    consumer_ids = {record.consumer_id for record in history}
    if len(consumer_ids) > 1:
        raise InvalidRequestError(_MIXED_CONSUMER_MESSAGE)


def _unique_timestamp_index(
    history: tuple[ConsumptionRecord, ...],
) -> dict[datetime, ConsumptionRecord]:
    by_timestamp: dict[datetime, ConsumptionRecord] = {}
    for record in history:
        if record.timestamp in by_timestamp:
            raise InvalidRequestError(_DUPLICATE_TIMESTAMP_MESSAGE)
        by_timestamp[record.timestamp] = record
    return by_timestamp


def _row_for_target(
    by_timestamp: dict[datetime, ConsumptionRecord],
    target: datetime,
) -> ConsumerLoadLag24h168hFeatureRow:
    actual = by_timestamp[target]
    lag_24h = by_timestamp[target - _LAG_24H]
    lag_168h = by_timestamp[target - _LAG_168H]
    return ConsumerLoadLag24h168hFeatureRow(
        consumer_id=actual.consumer_id,
        target_timestamp=target,
        lag_24h_mw=lag_24h.value_mw,
        lag_168h_mw=lag_168h.value_mw,
        target_value_mw=actual.value_mw,
    )
