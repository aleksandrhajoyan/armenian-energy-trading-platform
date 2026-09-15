"""Lag-24h plus lag-168h ordinary-least-squares Consumer Load MAE evaluation.

This outer ML transformation scores already-produced Chunk 144
``ConsumerLoadLag24h168hLinearRegressionPrediction`` values. It calculates
MAE only.

Ownership:

* Application: owns live inference via ``ConsumerLoadForecastModelPort``.
* ML: owns this offline trained-model MAE evaluator. Returned values are
  ML evaluation results, not workflow state and not a live forecast
  point.
* Already-produced prediction artifacts are the only input. This module
  does not fit, predict, rebuild features, split data, or belong to
  application orchestration.

MAE remains in MW:

``MAE = mean(|predicted_value_mw - actual_value_mw|)``

A negative finite prediction is valid experimental evidence and is
scored with the ordinary absolute difference. An empty prediction tuple
is undefined and fails closed with existing ``InvalidRequestError``.
Mixed consumers, malformed chronology, and non-finite values or MAE
fail closed. Weighting, rounding, and MW↔MWh conversion are not
implemented.

This contract is independent of the published one-feature OLS MAE
evaluator. The evaluator remains unwired from agents, API composition,
FastAPI, LangGraph, and ``ForecastingExecutionPort``. It does not
compare models or choose a production adapter.
"""

from dataclasses import dataclass
from math import isfinite

from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.consumer_load.lag_24h_168h_linear_regression_prediction import (
    ConsumerLoadLag24h168hLinearRegressionPrediction,
)

_EMPTY_PREDICTIONS_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression MAE evaluation "
    "requires at least one prediction."
)
_MIXED_CONSUMER_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression MAE evaluation "
    "requires predictions from exactly one consumer."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression MAE evaluation "
    "requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression MAE evaluation "
    "requires strictly increasing target timestamps."
)
_NON_FINITE_VALUES_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression MAE evaluation "
    "requires finite predicted and actual values."
)
_NON_FINITE_MAE_MESSAGE = (
    "Consumer Load 24-hour and 168-hour lag linear regression MAE evaluation requires a finite MAE."
)


@dataclass(frozen=True, slots=True)
class ConsumerLoadLag24h168hLinearRegressionMAEResult:
    """MAE over supplied lag-24h plus lag-168h OLS evaluation predictions."""

    case_count: int
    mae_mw: float


def evaluate_consumer_load_lag_24h_168h_linear_regression_mae(
    *,
    predictions: tuple[ConsumerLoadLag24h168hLinearRegressionPrediction, ...],
) -> ConsumerLoadLag24h168hLinearRegressionMAEResult:
    """Return MAE in MW over the supplied two-feature OLS evaluation predictions."""

    if not predictions:
        raise InvalidRequestError(_EMPTY_PREDICTIONS_MESSAGE)
    _require_single_consumer(predictions)
    _require_strict_chronology(predictions)
    total_abs_error = 0.0
    for prediction in predictions:
        if not isfinite(prediction.predicted_value_mw) or not isfinite(prediction.actual_value_mw):
            raise InvalidRequestError(_NON_FINITE_VALUES_MESSAGE)
        absolute_error = abs(prediction.predicted_value_mw - prediction.actual_value_mw)
        if not isfinite(absolute_error):
            raise InvalidRequestError(_NON_FINITE_MAE_MESSAGE)
        total_abs_error += absolute_error
    if not isfinite(total_abs_error):
        raise InvalidRequestError(_NON_FINITE_MAE_MESSAGE)
    mae_mw = total_abs_error / len(predictions)
    if not isfinite(mae_mw):
        raise InvalidRequestError(_NON_FINITE_MAE_MESSAGE)
    return ConsumerLoadLag24h168hLinearRegressionMAEResult(
        case_count=len(predictions),
        mae_mw=mae_mw,
    )


def _require_single_consumer(
    predictions: tuple[ConsumerLoadLag24h168hLinearRegressionPrediction, ...],
) -> None:
    consumer_ids = {prediction.consumer_id for prediction in predictions}
    if len(consumer_ids) > 1:
        raise InvalidRequestError(_MIXED_CONSUMER_MESSAGE)


def _require_strict_chronology(
    predictions: tuple[ConsumerLoadLag24h168hLinearRegressionPrediction, ...],
) -> None:
    previous = predictions[0]
    for current in predictions[1:]:
        if previous.target_timestamp == current.target_timestamp:
            raise InvalidRequestError(_DUPLICATE_TIMESTAMP_MESSAGE)
        if previous.target_timestamp > current.target_timestamp:
            raise InvalidRequestError(_OUT_OF_ORDER_MESSAGE)
        previous = current
