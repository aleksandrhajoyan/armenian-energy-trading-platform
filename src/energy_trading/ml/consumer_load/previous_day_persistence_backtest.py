"""Exact previous-day persistence Consumer Load backtest cases.

This outer ML transformation builds chronological historical evaluation
cases for the Chunk 132 persistence baseline. It does not train a model
and does not calculate metrics.

Ownership:

* Application: owns live inference via ``ConsumerLoadForecastModelPort``.
* ML: owns this offline evaluation-case builder. Returned values are ML
  evaluation cases, not workflow state and not ``LoadForecastPoint``.
* Canonical ``ConsumptionRecord`` history is the only input. This module
  does not belong to application orchestration.

Live inference versus backtest construction:

* Chunk 132 inference receives explicit requested targets. A missing exact
  ``T - 24h`` lag fails closed.
* This builder derives candidate targets from historical observations.
  A candidate whose exact ``T - 24h`` pair is missing is skipped, not
  imputed. The first historical day therefore yields no case.

A case exists only for an exact pair:

``prediction(T) = actual(T - 24 hours)``

Near timestamps, interpolation, resampling, weekly lag, local-calendar
previous day, and smoothing are not used. Duplicate timestamps or mixed
consumer identity fail closed before any case is returned. Canonical MW
values are copied unchanged.

The builder remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.models.observations import ConsumptionRecord
from energy_trading.domain.value_objects.quantities import EntityId, NonNegativeMW
from energy_trading.domain.value_objects.time import UtcDateTime

_LAG = timedelta(hours=24)
_MIXED_CONSUMER_MESSAGE = (
    "Previous-day persistence backtest requires history from exactly one consumer."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Previous-day persistence backtest requires unique historical timestamps."
)


@dataclass(frozen=True, slots=True)
class PreviousDayPersistenceBacktestCase:
    """One exact ``T`` / ``T - 24h`` Consumer Load evaluation pair."""

    consumer_id: EntityId
    target_timestamp: UtcDateTime
    predicted_value_mw: NonNegativeMW
    actual_value_mw: NonNegativeMW


def build_previous_day_persistence_backtest_cases(
    *,
    history: tuple[ConsumptionRecord, ...],
) -> tuple[PreviousDayPersistenceBacktestCase, ...]:
    """Return chronological exact-pair cases, skipping incomplete lags."""

    if not history:
        return ()
    _require_single_consumer(history)
    by_timestamp = _unique_timestamp_index(history)
    cases = tuple(
        _case_for_target(by_timestamp, target)
        for target in sorted(by_timestamp)
        if (target - _LAG) in by_timestamp
    )
    return cases


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


def _case_for_target(
    by_timestamp: dict[datetime, ConsumptionRecord],
    target: datetime,
) -> PreviousDayPersistenceBacktestCase:
    actual = by_timestamp[target]
    predicted = by_timestamp[target - _LAG]
    return PreviousDayPersistenceBacktestCase(
        consumer_id=actual.consumer_id,
        target_timestamp=target,
        predicted_value_mw=predicted.value_mw,
        actual_value_mw=actual.value_mw,
    )
