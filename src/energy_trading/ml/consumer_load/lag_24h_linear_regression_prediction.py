"""Lag-24h ordinary-least-squares Consumer Load evaluation prediction.

This outer ML transformation applies already-fitted Chunk 137 OLS
parameters to already-built Chunk 135 evaluation rows. It does not fit,
split, rebuild history, or calculate metrics.

Ownership:

* Application: owns live inference via ``ConsumerLoadForecastModelPort``.
* ML: owns this offline trained-model evaluation prediction. Returned
  values are ML evaluation artifacts, not workflow state and not a live
  forecast point.
* Already-fitted parameters and already-built evaluation rows are the
  only inputs. This module does not belong to application orchestration.

Prediction:

* ``predicted_value_mw = slope * lag_24h_mw + intercept_mw``
* ``actual_value_mw`` copies the row target unchanged
* Evaluation identity (``consumer_id``, ``target_timestamp``) is preserved
* Input evaluation-row order is preserved

A negative finite prediction is valid experimental evidence and is not
clamped. Empty evaluation input, mixed consumers, malformed chronology,
and non-finite parameters or results fail closed. External ML libraries
are not used.

The predictor remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass
from math import isfinite

from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.value_objects.quantities import EntityId, NonNegativeMW
from energy_trading.domain.value_objects.time import UtcDateTime
from energy_trading.ml.consumer_load.lag_24h_features import ConsumerLoadLag24hFeatureRow
from energy_trading.ml.consumer_load.lag_24h_linear_regression import (
    ConsumerLoadLag24hLinearRegressionFit,
)

_EMPTY_ROWS_MESSAGE = (
    "Consumer Load lag-24h linear regression prediction requires at least one evaluation row."
)
_MIXED_CONSUMER_MESSAGE = (
    "Consumer Load lag-24h linear regression prediction requires rows from exactly one consumer."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Consumer Load lag-24h linear regression prediction requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "Consumer Load lag-24h linear regression prediction requires strictly "
    "increasing target timestamps."
)
_NON_FINITE_FIT_MESSAGE = (
    "Consumer Load lag-24h linear regression prediction requires finite slope and intercept."
)
_NON_FINITE_PREDICTION_MESSAGE = (
    "Consumer Load lag-24h linear regression prediction requires finite predicted values."
)


@dataclass(frozen=True, slots=True)
class ConsumerLoadLag24hLinearRegressionPrediction:
    """One evaluated lag-24h OLS prediction observation."""

    consumer_id: EntityId
    target_timestamp: UtcDateTime
    predicted_value_mw: float
    actual_value_mw: NonNegativeMW


def predict_consumer_load_lag_24h_linear_regression(
    *,
    fit: ConsumerLoadLag24hLinearRegressionFit,
    evaluation_rows: tuple[ConsumerLoadLag24hFeatureRow, ...],
) -> tuple[ConsumerLoadLag24hLinearRegressionPrediction, ...]:
    """Apply fitted OLS parameters to chronological lag-24h evaluation rows."""

    if not evaluation_rows:
        raise InvalidRequestError(_EMPTY_ROWS_MESSAGE)
    if not isfinite(fit.slope) or not isfinite(fit.intercept_mw):
        raise InvalidRequestError(_NON_FINITE_FIT_MESSAGE)
    _require_single_consumer(evaluation_rows)
    _require_strict_chronology(evaluation_rows)
    return tuple(_prediction_for_row(fit, row) for row in evaluation_rows)


def _prediction_for_row(
    fit: ConsumerLoadLag24hLinearRegressionFit,
    row: ConsumerLoadLag24hFeatureRow,
) -> ConsumerLoadLag24hLinearRegressionPrediction:
    predicted_value_mw = fit.slope * row.lag_24h_mw + fit.intercept_mw
    if not isfinite(predicted_value_mw):
        raise InvalidRequestError(_NON_FINITE_PREDICTION_MESSAGE)
    return ConsumerLoadLag24hLinearRegressionPrediction(
        consumer_id=row.consumer_id,
        target_timestamp=row.target_timestamp,
        predicted_value_mw=predicted_value_mw,
        actual_value_mw=row.target_value_mw,
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
