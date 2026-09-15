"""Lag-24h plus lag-168h ordinary-least-squares Consumer Load evaluation prediction.

This outer ML transformation applies already-fitted Chunk 143 OLS
parameters to already-built Chunk 141 evaluation rows. It does not fit,
split, rebuild history, or calculate metrics.

Ownership:

* Application: owns live inference via ``ConsumerLoadForecastModelPort``.
* ML: owns this offline trained-model evaluation prediction. Returned
  values are ML evaluation artifacts, not workflow state and not a live
  forecast point.
* Already-fitted two-feature parameters and already-built evaluation
  rows are the only inputs. This module does not belong to application
  orchestration.

Prediction:

* ``predicted_value_mw = intercept_mw + lag_24h_coefficient * lag_24h_mw
  + lag_168h_coefficient * lag_168h_mw``
* ``actual_value_mw`` copies the row target unchanged
* Evaluation identity (``consumer_id``, ``target_timestamp``) is preserved
* Input evaluation-row order is preserved

A negative finite prediction is valid experimental evidence and is not
clamped. Empty evaluation input, mixed consumers, malformed chronology,
and non-finite parameters or results fail closed. External ML libraries
are not used.

This contract is independent of the published one-feature OLS predictor.
The predictor remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass
from math import isfinite

from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.value_objects.quantities import EntityId, NonNegativeMW
from energy_trading.domain.value_objects.time import UtcDateTime
from energy_trading.ml.consumer_load.lag_24h_168h_features import (
    ConsumerLoadLag24h168hFeatureRow,
)
from energy_trading.ml.consumer_load.lag_24h_168h_linear_regression import (
    ConsumerLoadLag24h168hLinearRegressionFit,
)

_EMPTY_ROWS_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression prediction "
    "requires at least one evaluation row."
)
_MIXED_CONSUMER_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression prediction "
    "requires rows from exactly one consumer."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression prediction "
    "requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression prediction "
    "requires strictly increasing target timestamps."
)
_NON_FINITE_FIT_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression prediction "
    "requires finite fitted coefficients and intercept."
)
_NON_FINITE_PREDICTION_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression prediction "
    "requires finite predicted values."
)


@dataclass(frozen=True, slots=True)
class ConsumerLoadLag24h168hLinearRegressionPrediction:
    """One evaluated lag-24h plus lag-168h OLS prediction observation."""

    consumer_id: EntityId
    target_timestamp: UtcDateTime
    predicted_value_mw: float
    actual_value_mw: NonNegativeMW


def predict_consumer_load_lag_24h_168h_linear_regression(
    *,
    fit: ConsumerLoadLag24h168hLinearRegressionFit,
    evaluation_rows: tuple[ConsumerLoadLag24h168hFeatureRow, ...],
) -> tuple[ConsumerLoadLag24h168hLinearRegressionPrediction, ...]:
    """Apply fitted two-feature OLS parameters to chronological evaluation rows."""

    if not evaluation_rows:
        raise InvalidRequestError(_EMPTY_ROWS_MESSAGE)
    if (
        not isfinite(fit.lag_24h_coefficient)
        or not isfinite(fit.lag_168h_coefficient)
        or not isfinite(fit.intercept_mw)
    ):
        raise InvalidRequestError(_NON_FINITE_FIT_MESSAGE)
    _require_single_consumer(evaluation_rows)
    _require_strict_chronology(evaluation_rows)
    predictions: list[ConsumerLoadLag24h168hLinearRegressionPrediction] = []
    for row in evaluation_rows:
        predictions.append(_prediction_for_row(fit, row))
    return tuple(predictions)


def _prediction_for_row(
    fit: ConsumerLoadLag24h168hLinearRegressionFit,
    row: ConsumerLoadLag24h168hFeatureRow,
) -> ConsumerLoadLag24h168hLinearRegressionPrediction:
    predicted_value_mw = (
        fit.intercept_mw
        + fit.lag_24h_coefficient * row.lag_24h_mw
        + fit.lag_168h_coefficient * row.lag_168h_mw
    )
    if not isfinite(predicted_value_mw):
        raise InvalidRequestError(_NON_FINITE_PREDICTION_MESSAGE)
    return ConsumerLoadLag24h168hLinearRegressionPrediction(
        consumer_id=row.consumer_id,
        target_timestamp=row.target_timestamp,
        predicted_value_mw=predicted_value_mw,
        actual_value_mw=row.target_value_mw,
    )


def _require_single_consumer(rows: tuple[ConsumerLoadLag24h168hFeatureRow, ...]) -> None:
    consumer_ids = {row.consumer_id for row in rows}
    if len(consumer_ids) > 1:
        raise InvalidRequestError(_MIXED_CONSUMER_MESSAGE)


def _require_strict_chronology(rows: tuple[ConsumerLoadLag24h168hFeatureRow, ...]) -> None:
    previous = rows[0]
    for current in rows[1:]:
        if previous.target_timestamp == current.target_timestamp:
            raise InvalidRequestError(_DUPLICATE_TIMESTAMP_MESSAGE)
        if previous.target_timestamp > current.target_timestamp:
            raise InvalidRequestError(_OUT_OF_ORDER_MESSAGE)
        previous = current
