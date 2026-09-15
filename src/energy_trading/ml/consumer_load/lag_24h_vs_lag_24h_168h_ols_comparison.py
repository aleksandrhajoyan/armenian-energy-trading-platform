"""Aligned one-feature versus two-feature OLS Consumer Load MAE comparison.

This outer ML transformation aligns already-produced Chunk 138 one-feature
OLS predictions with already-produced Chunk 144 two-feature OLS
predictions, then delegates scoring to the published Chunk 139 and
Chunk 145 MAE evaluators.

Ownership:

* Application: owns live inference via ``ConsumerLoadForecastModelPort``.
* ML: owns this offline aligned comparison. Returned values are ML
  comparison evidence, not workflow state and not a live forecast
  point.
* Aggregate MAE result objects alone are not sufficient. Fair comparison
  requires the same consumer, the same target timestamps, the same actual
  MW labels, and equal cohort size.

Chunk 146 owns alignment and composition only. It does not fit, predict,
rebuild features, split data, or calculate MAE itself.

The comparison reports ``case_count``, one-feature MAE, and two-feature
MAE. It does not choose a production model or compute a relative change.

The comparison remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass

from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.consumer_load.lag_24h_168h_linear_regression_evaluation import (
    evaluate_consumer_load_lag_24h_168h_linear_regression_mae,
)
from energy_trading.ml.consumer_load.lag_24h_168h_linear_regression_prediction import (
    ConsumerLoadLag24h168hLinearRegressionPrediction,
)
from energy_trading.ml.consumer_load.lag_24h_linear_regression_evaluation import (
    evaluate_consumer_load_lag_24h_linear_regression_mae,
)
from energy_trading.ml.consumer_load.lag_24h_linear_regression_prediction import (
    ConsumerLoadLag24hLinearRegressionPrediction,
)

_EMPTY_BOTH_MESSAGE = (
    "Consumer Load one-feature versus two-feature OLS MAE comparison requires "
    "a non-empty aligned cohort."
)
_EMPTY_LAG_24H_MESSAGE = (
    "Consumer Load one-feature versus two-feature OLS MAE comparison requires "
    "a non-empty one-feature cohort."
)
_EMPTY_LAG_24H_168H_MESSAGE = (
    "Consumer Load one-feature versus two-feature OLS MAE comparison requires "
    "a non-empty two-feature cohort."
)
_UNEQUAL_LENGTH_MESSAGE = (
    "Consumer Load one-feature versus two-feature OLS MAE comparison requires "
    "equal one-feature and two-feature case counts."
)
_MIXED_LAG_24H_CONSUMER_MESSAGE = (
    "Consumer Load one-feature versus two-feature OLS MAE comparison requires "
    "one-feature predictions from exactly one consumer."
)
_MIXED_LAG_24H_168H_CONSUMER_MESSAGE = (
    "Consumer Load one-feature versus two-feature OLS MAE comparison requires "
    "two-feature predictions from exactly one consumer."
)
_CONSUMER_MISMATCH_MESSAGE = (
    "Consumer Load one-feature versus two-feature OLS MAE comparison requires "
    "one-feature and two-feature predictions from the same consumer."
)
_DUPLICATE_LAG_24H_TIMESTAMP_MESSAGE = (
    "Consumer Load one-feature versus two-feature OLS MAE comparison requires "
    "unique one-feature target timestamps."
)
_DUPLICATE_LAG_24H_168H_TIMESTAMP_MESSAGE = (
    "Consumer Load one-feature versus two-feature OLS MAE comparison requires "
    "unique two-feature target timestamps."
)
_OUT_OF_ORDER_LAG_24H_MESSAGE = (
    "Consumer Load one-feature versus two-feature OLS MAE comparison requires "
    "strictly increasing one-feature target timestamps."
)
_OUT_OF_ORDER_LAG_24H_168H_MESSAGE = (
    "Consumer Load one-feature versus two-feature OLS MAE comparison requires "
    "strictly increasing two-feature target timestamps."
)
_TIMESTAMP_MISMATCH_MESSAGE = (
    "Consumer Load one-feature versus two-feature OLS MAE comparison requires "
    "matching target timestamps at each aligned index."
)
_ACTUAL_MISMATCH_MESSAGE = (
    "Consumer Load one-feature versus two-feature OLS MAE comparison requires "
    "matching actual MW values at each aligned index."
)


@dataclass(frozen=True, slots=True)
class ConsumerLoadLag24hVsLag24h168hOLSMAEComparison:
    """Aligned one-feature and two-feature OLS MAE evidence for one cohort."""

    case_count: int
    lag_24h_mae_mw: float
    lag_24h_168h_mae_mw: float


def compare_consumer_load_lag_24h_vs_lag_24h_168h_ols_mae(
    *,
    lag_24h_predictions: tuple[ConsumerLoadLag24hLinearRegressionPrediction, ...],
    lag_24h_168h_predictions: tuple[ConsumerLoadLag24h168hLinearRegressionPrediction, ...],
) -> ConsumerLoadLag24hVsLag24h168hOLSMAEComparison:
    """Return aligned one-feature and two-feature OLS MAE for one shared cohort."""

    _require_nonempty_equal_cohort(lag_24h_predictions, lag_24h_168h_predictions)
    _require_single_shared_consumer(lag_24h_predictions, lag_24h_168h_predictions)
    _require_lag_24h_chronology(lag_24h_predictions)
    _require_lag_24h_168h_chronology(lag_24h_168h_predictions)
    _require_pairwise_alignment(lag_24h_predictions, lag_24h_168h_predictions)
    lag_24h_result = evaluate_consumer_load_lag_24h_linear_regression_mae(
        predictions=lag_24h_predictions,
    )
    lag_24h_168h_result = evaluate_consumer_load_lag_24h_168h_linear_regression_mae(
        predictions=lag_24h_168h_predictions,
    )
    return ConsumerLoadLag24hVsLag24h168hOLSMAEComparison(
        case_count=len(lag_24h_predictions),
        lag_24h_mae_mw=lag_24h_result.mae_mw,
        lag_24h_168h_mae_mw=lag_24h_168h_result.mae_mw,
    )


def _require_nonempty_equal_cohort(
    lag_24h_predictions: tuple[ConsumerLoadLag24hLinearRegressionPrediction, ...],
    lag_24h_168h_predictions: tuple[ConsumerLoadLag24h168hLinearRegressionPrediction, ...],
) -> None:
    if not lag_24h_predictions and not lag_24h_168h_predictions:
        raise InvalidRequestError(_EMPTY_BOTH_MESSAGE)
    if not lag_24h_predictions:
        raise InvalidRequestError(_EMPTY_LAG_24H_MESSAGE)
    if not lag_24h_168h_predictions:
        raise InvalidRequestError(_EMPTY_LAG_24H_168H_MESSAGE)
    if len(lag_24h_predictions) != len(lag_24h_168h_predictions):
        raise InvalidRequestError(_UNEQUAL_LENGTH_MESSAGE)


def _require_single_shared_consumer(
    lag_24h_predictions: tuple[ConsumerLoadLag24hLinearRegressionPrediction, ...],
    lag_24h_168h_predictions: tuple[ConsumerLoadLag24h168hLinearRegressionPrediction, ...],
) -> None:
    lag_24h_consumers = {prediction.consumer_id for prediction in lag_24h_predictions}
    lag_24h_168h_consumers = {prediction.consumer_id for prediction in lag_24h_168h_predictions}
    if len(lag_24h_consumers) > 1:
        raise InvalidRequestError(_MIXED_LAG_24H_CONSUMER_MESSAGE)
    if len(lag_24h_168h_consumers) > 1:
        raise InvalidRequestError(_MIXED_LAG_24H_168H_CONSUMER_MESSAGE)
    if lag_24h_consumers != lag_24h_168h_consumers:
        raise InvalidRequestError(_CONSUMER_MISMATCH_MESSAGE)


def _require_lag_24h_chronology(
    lag_24h_predictions: tuple[ConsumerLoadLag24hLinearRegressionPrediction, ...],
) -> None:
    previous = lag_24h_predictions[0]
    for current in lag_24h_predictions[1:]:
        if previous.target_timestamp == current.target_timestamp:
            raise InvalidRequestError(_DUPLICATE_LAG_24H_TIMESTAMP_MESSAGE)
        if previous.target_timestamp > current.target_timestamp:
            raise InvalidRequestError(_OUT_OF_ORDER_LAG_24H_MESSAGE)
        previous = current


def _require_lag_24h_168h_chronology(
    lag_24h_168h_predictions: tuple[ConsumerLoadLag24h168hLinearRegressionPrediction, ...],
) -> None:
    previous = lag_24h_168h_predictions[0]
    for current in lag_24h_168h_predictions[1:]:
        if previous.target_timestamp == current.target_timestamp:
            raise InvalidRequestError(_DUPLICATE_LAG_24H_168H_TIMESTAMP_MESSAGE)
        if previous.target_timestamp > current.target_timestamp:
            raise InvalidRequestError(_OUT_OF_ORDER_LAG_24H_168H_MESSAGE)
        previous = current


def _require_pairwise_alignment(
    lag_24h_predictions: tuple[ConsumerLoadLag24hLinearRegressionPrediction, ...],
    lag_24h_168h_predictions: tuple[ConsumerLoadLag24h168hLinearRegressionPrediction, ...],
) -> None:
    for lag_24h_prediction, lag_24h_168h_prediction in zip(
        lag_24h_predictions,
        lag_24h_168h_predictions,
        strict=True,
    ):
        if lag_24h_prediction.target_timestamp != lag_24h_168h_prediction.target_timestamp:
            raise InvalidRequestError(_TIMESTAMP_MISMATCH_MESSAGE)
        if lag_24h_prediction.actual_value_mw != lag_24h_168h_prediction.actual_value_mw:
            raise InvalidRequestError(_ACTUAL_MISMATCH_MESSAGE)
