"""Chronological Consumer Load feature-row train/evaluation split.

This outer ML transformation partitions already-built Chunk 135
``ConsumerLoadLag24hFeatureRow`` values at an explicit UTC cutoff. It
does not train a model and does not rebuild history.

Ownership:

* Application: owns live inference via ``ConsumerLoadForecastModelPort``.
* ML: owns this offline chronological split. Returned values are ML
  preparation tuples, not workflow state and not ``LoadForecastPoint``.
* Already-built feature rows are the only input. This module does not
  rebuild history and does not belong to application orchestration.

Partition rule:

* ``training_rows``: ``target_timestamp < cutoff``
* ``evaluation_rows``: ``target_timestamp >= cutoff``

A row whose timestamp equals the cutoff belongs to evaluation. Original
row order is preserved. Malformed chronology, mixed consumers, empty
input, and empty partitions fail closed. Ratio-based and randomized
partitions are not used.

The splitter remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass  # noqa: I001

from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.consumer_load.lag_24h_features import ConsumerLoadLag24hFeatureRow
from energy_trading.domain.value_objects.time import UtcDateTime

_EMPTY_ROWS_MESSAGE = "Consumer Load chronological feature split requires at least one feature row."
_MIXED_CONSUMER_MESSAGE = (
    "Consumer Load chronological feature split requires rows from exactly one consumer."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Consumer Load chronological feature split requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "Consumer Load chronological feature split requires strictly increasing target timestamps."
)
_EMPTY_TRAINING_MESSAGE = (
    "Consumer Load chronological feature split requires a non-empty training partition."
)
_EMPTY_EVALUATION_MESSAGE = (
    "Consumer Load chronological feature split requires a non-empty evaluation partition."
)


@dataclass(frozen=True, slots=True)
class ConsumerLoadChronologicalFeatureSplit:
    """Training and evaluation partitions of exact 24h lag feature rows."""

    training_rows: tuple[ConsumerLoadLag24hFeatureRow, ...]
    evaluation_rows: tuple[ConsumerLoadLag24hFeatureRow, ...]


def split_consumer_load_feature_rows_chronologically(
    *,
    rows: tuple[ConsumerLoadLag24hFeatureRow, ...],
    cutoff: UtcDateTime,
) -> ConsumerLoadChronologicalFeatureSplit:
    """Partition chronological feature rows at an explicit UTC cutoff."""

    if not rows:
        raise InvalidRequestError(_EMPTY_ROWS_MESSAGE)
    _require_single_consumer(rows)
    _require_strict_chronology(rows)
    training_rows = tuple(row for row in rows if row.target_timestamp < cutoff)
    evaluation_rows = tuple(row for row in rows if row.target_timestamp >= cutoff)
    if not training_rows:
        raise InvalidRequestError(_EMPTY_TRAINING_MESSAGE)
    if not evaluation_rows:
        raise InvalidRequestError(_EMPTY_EVALUATION_MESSAGE)
    return ConsumerLoadChronologicalFeatureSplit(
        training_rows=training_rows,
        evaluation_rows=evaluation_rows,
    )


def _require_single_consumer(rows: tuple[ConsumerLoadLag24hFeatureRow, ...]) -> None:
    consumer_ids = {row.consumer_id for row in rows}
    if len(consumer_ids) > 1:
        raise InvalidRequestError(_MIXED_CONSUMER_MESSAGE)


def _require_strict_chronology(rows: tuple[ConsumerLoadLag24hFeatureRow, ...]) -> None:
    previous = rows[0]
    for current in rows[1:]:
        if previous.target_timestamp == current.target_timestamp:
            raise InvalidRequestError(_DUPLICATE_TIMESTAMP_MESSAGE)
        if previous.target_timestamp > current.target_timestamp:
            raise InvalidRequestError(_OUT_OF_ORDER_MESSAGE)
        previous = current
