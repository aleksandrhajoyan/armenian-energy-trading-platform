"""Exact 24-hour and 168-hour lag DAM Price supervised feature rows.

This outer ML transformation builds chronological historical feature rows
for a future trained DAM Price model. It does not train a model, does not
predict, and does not calculate metrics.

Ownership:

* Application: owns live inference via ``DAMPriceForecastModelPort``.
* ML: owns this offline feature-row builder. Returned values are ML
  supervised rows, not workflow state and not ``PriceForecastPoint``.
* Canonical ``MarketPriceRecord`` history is the only input. This module does
  not belong to application orchestration, and it does not depend on the
  previous-day persistence inference adapter, backtest cases, MAE evaluator,
  the Chunk 173 one-feature row, the Chunk 174 splitter, the Chunk 175 fit,
  the Chunk 176 prediction, the Chunk 177 evaluator, or the Chunk 178
  comparison. The richer two-lag experiment is independent of the published
  one-feature experiment and is not built by widening it.

A row exists only for an exact triple:

* ``lag_24h_amount_per_mwh`` is the canonical ``EnergyPrice`` amount at
  exactly ``T - 24 hours``
* ``lag_168h_amount_per_mwh`` is the canonical ``EnergyPrice`` amount at
  exactly ``T - 168 hours``
* ``target_amount_per_mwh`` is the canonical ``EnergyPrice`` amount at ``T``

A 168-hour lag means exactly 168 elapsed hours. It is not the same weekday,
not a calendar week, not the previous trading week, and not a market-session
predecessor. Near timestamps, tolerance windows, interpolation, resampling,
forward or backward fill, 167-hour or 169-hour substitution, nearest previous
observation, rolling statistics, volume, volatility, returns, spreads, and
calendar or time-of-day features are not used.

A target whose exact 24-hour or exact 168-hour observation is absent is
omitted rather than raising, and no partial row is produced. Duplicate
timestamps, mixed market identity, or mixed currency fail closed before any
row is returned. Canonical ``FiniteDecimal`` amounts are copied unchanged, so
negative and zero prices remain valid. ``volume_mwh`` is ignored.

The builder remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.models.observations import MarketPriceRecord
from energy_trading.domain.value_objects.quantities import (
    CurrencyCode,
    EntityId,
    FiniteDecimal,
)
from energy_trading.domain.value_objects.time import UtcDateTime

_LAG_24H = timedelta(hours=24)
_LAG_168H = timedelta(hours=168)
_MIXED_MARKET_MESSAGE = (
    "DAM Price 24-hour and 168-hour lag features require history from exactly one market."
)
_MIXED_CURRENCY_MESSAGE = (
    "DAM Price 24-hour and 168-hour lag features require history in exactly one currency."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "DAM Price 24-hour and 168-hour lag features require unique historical timestamps."
)


@dataclass(frozen=True, slots=True)
class DAMPriceLag24h168hFeatureRow:
    """One exact ``T`` / ``T - 24h`` / ``T - 168h`` DAM Price supervised row."""

    market_id: EntityId
    currency: CurrencyCode
    target_timestamp: UtcDateTime
    lag_24h_amount_per_mwh: FiniteDecimal
    lag_168h_amount_per_mwh: FiniteDecimal
    target_amount_per_mwh: FiniteDecimal


def build_dam_price_lag_24h_168h_feature_rows(
    *,
    history: tuple[MarketPriceRecord, ...],
) -> tuple[DAMPriceLag24h168hFeatureRow, ...]:
    """Return chronological exact-triple feature rows, skipping incomplete lags."""

    if not history:
        return ()
    _require_single_market(history)
    _require_single_currency(history)
    by_timestamp = _unique_timestamp_index(history)
    return tuple(
        _row_for_target(by_timestamp, target)
        for target in sorted(by_timestamp)
        if (target - _LAG_24H) in by_timestamp and (target - _LAG_168H) in by_timestamp
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


def _row_for_target(
    by_timestamp: dict[datetime, MarketPriceRecord],
    target: datetime,
) -> DAMPriceLag24h168hFeatureRow:
    target_record = by_timestamp[target]
    lag_24h_record = by_timestamp[target - _LAG_24H]
    lag_168h_record = by_timestamp[target - _LAG_168H]
    return DAMPriceLag24h168hFeatureRow(
        market_id=target_record.market_id,
        currency=target_record.price.currency,
        target_timestamp=target,
        lag_24h_amount_per_mwh=lag_24h_record.price.amount_per_mwh,
        lag_168h_amount_per_mwh=lag_168h_record.price.amount_per_mwh,
        target_amount_per_mwh=target_record.price.amount_per_mwh,
    )
