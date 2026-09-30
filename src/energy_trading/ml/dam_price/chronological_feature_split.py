"""Chronological DAM Price feature-row train/evaluation split.

This outer ML transformation partitions already-built Chunk 173
``DAMPriceLag24hFeatureRow`` values at an explicit UTC cutoff. It does not
train a model, does not rebuild history, and does not alter any feature
value.

Ownership:

* Application: owns live inference via ``DAMPriceForecastModelPort``.
* ML: owns this offline chronological split. Returned values are ML
  preparation tuples, not workflow state and not a forecast.
* Already-built feature rows are the only input. This module does not
  rebuild history, does not call the feature builder, does not consume
  ``MarketPriceRecord``, and does not belong to application orchestration.

Partition rule:

* ``training_rows``: ``target_timestamp < cutoff``
* ``evaluation_rows``: ``target_timestamp >= cutoff``

A row whose timestamp equals the cutoff belongs to evaluation. The cutoff is
caller-supplied and is never derived from a ratio, row count, timestamp
statistics, a clock, or a random seed. Original row order is preserved inside
both partitions. Malformed chronology, mixed markets, mixed currencies,
empty input, and empty partitions fail closed. Ratio-based, shuffled, and
randomized partitions are not used.

Feature and target amounts are opaque to this module: only
``target_timestamp``, ``market_id``, and ``currency`` are inspected.

The splitter remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass

from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.value_objects.time import UtcDateTime
from energy_trading.ml.dam_price.lag_24h_features import DAMPriceLag24hFeatureRow

_EMPTY_ROWS_MESSAGE = "DAM Price chronological feature split requires at least one feature row."
_MIXED_MARKET_MESSAGE = (
    "DAM Price chronological feature split requires rows from exactly one market."
)
_MIXED_CURRENCY_MESSAGE = (
    "DAM Price chronological feature split requires rows in exactly one currency."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "DAM Price chronological feature split requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "DAM Price chronological feature split requires strictly increasing target timestamps."
)
_EMPTY_TRAINING_MESSAGE = (
    "DAM Price chronological feature split requires a non-empty training partition."
)
_EMPTY_EVALUATION_MESSAGE = (
    "DAM Price chronological feature split requires a non-empty evaluation partition."
)


@dataclass(frozen=True, slots=True)
class DAMPriceChronologicalFeatureSplit:
    """Training and evaluation partitions of exact 24h lag feature rows."""

    training_rows: tuple[DAMPriceLag24hFeatureRow, ...]
    evaluation_rows: tuple[DAMPriceLag24hFeatureRow, ...]


def split_dam_price_feature_rows_chronologically(
    *,
    rows: tuple[DAMPriceLag24hFeatureRow, ...],
    cutoff: UtcDateTime,
) -> DAMPriceChronologicalFeatureSplit:
    """Partition chronological feature rows at an explicit UTC cutoff."""

    if not rows:
        raise InvalidRequestError(_EMPTY_ROWS_MESSAGE)
    _require_single_market(rows)
    _require_single_currency(rows)
    _require_strict_chronology(rows)
    training_rows = tuple(row for row in rows if row.target_timestamp < cutoff)
    evaluation_rows = tuple(row for row in rows if row.target_timestamp >= cutoff)
    if not training_rows:
        raise InvalidRequestError(_EMPTY_TRAINING_MESSAGE)
    if not evaluation_rows:
        raise InvalidRequestError(_EMPTY_EVALUATION_MESSAGE)
    return DAMPriceChronologicalFeatureSplit(
        training_rows=training_rows,
        evaluation_rows=evaluation_rows,
    )


def _require_single_market(rows: tuple[DAMPriceLag24hFeatureRow, ...]) -> None:
    market_ids = {row.market_id for row in rows}
    if len(market_ids) > 1:
        raise InvalidRequestError(_MIXED_MARKET_MESSAGE)


def _require_single_currency(rows: tuple[DAMPriceLag24hFeatureRow, ...]) -> None:
    currencies = {row.currency for row in rows}
    if len(currencies) > 1:
        raise InvalidRequestError(_MIXED_CURRENCY_MESSAGE)


def _require_strict_chronology(rows: tuple[DAMPriceLag24hFeatureRow, ...]) -> None:
    previous = rows[0]
    for current in rows[1:]:
        if previous.target_timestamp == current.target_timestamp:
            raise InvalidRequestError(_DUPLICATE_TIMESTAMP_MESSAGE)
        if previous.target_timestamp > current.target_timestamp:
            raise InvalidRequestError(_OUT_OF_ORDER_MESSAGE)
        previous = current
