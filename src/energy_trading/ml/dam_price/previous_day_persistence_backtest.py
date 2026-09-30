"""Exact previous-day persistence DAM Price backtest cases.

This outer ML transformation builds chronological historical evaluation
cases for the Chunk 170 persistence baseline. It does not train a model
and does not calculate metrics.

Ownership:

* Application: owns live inference via ``DAMPriceForecastModelPort``.
* ML: owns this offline evaluation-case builder. Returned values are ML
  evaluation cases, not workflow state and not ``PriceForecastPoint``.
* Canonical ``MarketPriceRecord`` history is the only input. This module
  does not belong to application orchestration.

Live inference versus backtest construction:

* Chunk 170 inference receives explicit requested targets. A missing exact
  ``T - 24h`` lag fails closed.
* This builder derives candidate targets from historical observations.
  A candidate whose exact ``T - 24h`` pair is missing is skipped, not
  imputed. The first historical day therefore yields no case.

A case exists only for an exact pair:

``prediction(T) = actual(T - 24 hours)``

Near timestamps, interpolation, resampling, weekly lag, local-calendar
previous day, market sessions, and smoothing are not used. Duplicate
timestamps, mixed market identity, or mixed currency fail closed before
any case is returned. Canonical ``EnergyPrice`` values are copied
unchanged: no conversion, no rounding, no clamping, and no volume
weighting.

The builder remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.models.observations import MarketPriceRecord
from energy_trading.domain.value_objects.money import EnergyPrice
from energy_trading.domain.value_objects.quantities import EntityId
from energy_trading.domain.value_objects.time import UtcDateTime

_LAG = timedelta(hours=24)
_MIXED_MARKET_MESSAGE = (
    "Previous-day persistence backtest requires history from exactly one market."
)
_MIXED_CURRENCY_MESSAGE = (
    "Previous-day persistence backtest requires history in exactly one currency."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Previous-day persistence backtest requires unique historical timestamps."
)


@dataclass(frozen=True, slots=True)
class PreviousDayPersistenceBacktestCase:
    """One exact ``T`` / ``T - 24h`` DAM Price evaluation pair."""

    market_id: EntityId
    target_timestamp: UtcDateTime
    predicted_price: EnergyPrice
    actual_price: EnergyPrice


def build_previous_day_persistence_backtest_cases(
    *,
    history: tuple[MarketPriceRecord, ...],
) -> tuple[PreviousDayPersistenceBacktestCase, ...]:
    """Return chronological exact-pair cases, skipping incomplete lags."""

    if not history:
        return ()
    _require_single_market(history)
    _require_single_currency(history)
    by_timestamp = _unique_timestamp_index(history)
    return tuple(
        _case_for_target(by_timestamp, target)
        for target in sorted(by_timestamp)
        if (target - _LAG) in by_timestamp
    )


def _require_single_market(history: tuple[MarketPriceRecord, ...]) -> None:
    market_ids = {record.market_id for record in history}
    if len(market_ids) > 1:
        raise InvalidRequestError(_MIXED_MARKET_MESSAGE)


def _require_single_currency(history: tuple[MarketPriceRecord, ...]) -> None:
    currencies = {record.price.currency for record in history}
    if len(currencies) > 1:
        raise InvalidRequestError(_MIXED_CURRENCY_MESSAGE)


def _unique_timestamp_index(
    history: tuple[MarketPriceRecord, ...],
) -> dict[datetime, MarketPriceRecord]:
    by_timestamp: dict[datetime, MarketPriceRecord] = {}
    for record in history:
        if record.timestamp in by_timestamp:
            raise InvalidRequestError(_DUPLICATE_TIMESTAMP_MESSAGE)
        by_timestamp[record.timestamp] = record
    return by_timestamp


def _case_for_target(
    by_timestamp: dict[datetime, MarketPriceRecord],
    target: datetime,
) -> PreviousDayPersistenceBacktestCase:
    actual = by_timestamp[target]
    predicted = by_timestamp[target - _LAG]
    return PreviousDayPersistenceBacktestCase(
        market_id=actual.market_id,
        target_timestamp=target,
        predicted_price=predicted.price,
        actual_price=actual.price,
    )
