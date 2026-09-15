"""Aligned three-way persistence-versus-OLS Consumer Load MAE comparison.

This outer ML transformation aligns already-produced Chunk 133 persistence
backtest cases with already-produced Chunk 138 one-feature OLS
predictions and already-produced Chunk 144 two-feature OLS predictions,
then delegates scoring to the published Chunk 134, Chunk 139, and
Chunk 145 MAE evaluators.

Ownership:

* Application: owns live inference via ``ConsumerLoadForecastModelPort``.
* ML: owns this offline aligned comparison. Returned values are ML
  comparison evidence, not workflow state and not a live forecast
  point.
* Aggregate MAE result objects alone are not sufficient. Fair comparison
  requires the same consumer, the same target timestamps, the same actual
  MW labels, and equal cohort size across all three cohorts.

Chunk 148 owns three-way alignment and composition only. It does not
fit, predict, rebuild features, split data, or calculate MAE itself.
It does not call the published pairwise comparison functions.

The comparison reports ``case_count``, persistence MAE, one-feature OLS
MAE, and two-feature OLS MAE. It does not choose a production model or
compute a relative change.

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
from energy_trading.ml.consumer_load.previous_day_persistence_backtest import (
    PreviousDayPersistenceBacktestCase,
)
from energy_trading.ml.consumer_load.previous_day_persistence_evaluation import (
    evaluate_previous_day_persistence_mae,
)

_EMPTY_ALL_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires a non-empty aligned cohort."
)
_EMPTY_PERSISTENCE_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires a non-empty persistence cohort."
)
_EMPTY_LAG_24H_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires a non-empty one-feature cohort."
)
_EMPTY_LAG_24H_168H_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires a non-empty two-feature cohort."
)
_UNEQUAL_LENGTH_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires equal persistence, one-feature, and two-feature case "
    "counts."
)
_MIXED_PERSISTENCE_CONSUMER_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires persistence cases from exactly one consumer."
)
_MIXED_LAG_24H_CONSUMER_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires one-feature predictions from exactly one consumer."
)
_MIXED_LAG_24H_168H_CONSUMER_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires two-feature predictions from exactly one consumer."
)
_CONSUMER_MISMATCH_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires persistence cases, one-feature predictions, and "
    "two-feature predictions from the same consumer."
)
_DUPLICATE_PERSISTENCE_TIMESTAMP_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires unique persistence target timestamps."
)
_DUPLICATE_LAG_24H_TIMESTAMP_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires unique one-feature target timestamps."
)
_DUPLICATE_LAG_24H_168H_TIMESTAMP_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires unique two-feature target timestamps."
)
_OUT_OF_ORDER_PERSISTENCE_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires strictly increasing persistence target timestamps."
)
_OUT_OF_ORDER_LAG_24H_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires strictly increasing one-feature target timestamps."
)
_OUT_OF_ORDER_LAG_24H_168H_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires strictly increasing two-feature target timestamps."
)
_TIMESTAMP_MISMATCH_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires matching target timestamps at each aligned index."
)
_ACTUAL_MISMATCH_MESSAGE = (
    "Consumer Load persistence-versus-one-feature-versus-two-feature OLS MAE "
    "comparison requires matching actual MW values at each aligned index."
)


@dataclass(frozen=True, slots=True)
class ConsumerLoadPersistenceVsLag24hVsLag24h168hOLSMAEComparison:
    """Aligned persistence, one-feature, and two-feature OLS MAE evidence."""

    case_count: int
    persistence_mae_mw: float
    lag_24h_mae_mw: float
    lag_24h_168h_mae_mw: float


def compare_consumer_load_persistence_vs_lag_24h_vs_lag_24h_168h_ols_mae(
    *,
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    lag_24h_predictions: tuple[ConsumerLoadLag24hLinearRegressionPrediction, ...],
    lag_24h_168h_predictions: tuple[ConsumerLoadLag24h168hLinearRegressionPrediction, ...],
) -> ConsumerLoadPersistenceVsLag24hVsLag24h168hOLSMAEComparison:
    """Return aligned persistence, one-feature, and two-feature OLS MAE."""

    _require_nonempty_equal_cohort(
        persistence_cases,
        lag_24h_predictions,
        lag_24h_168h_predictions,
    )
    _require_single_shared_consumer(
        persistence_cases,
        lag_24h_predictions,
        lag_24h_168h_predictions,
    )
    _require_persistence_chronology(persistence_cases)
    _require_lag_24h_chronology(lag_24h_predictions)
    _require_lag_24h_168h_chronology(lag_24h_168h_predictions)
    _require_three_way_alignment(
        persistence_cases,
        lag_24h_predictions,
        lag_24h_168h_predictions,
    )
    persistence_result = evaluate_previous_day_persistence_mae(cases=persistence_cases)
    lag_24h_result = evaluate_consumer_load_lag_24h_linear_regression_mae(
        predictions=lag_24h_predictions,
    )
    lag_24h_168h_result = evaluate_consumer_load_lag_24h_168h_linear_regression_mae(
        predictions=lag_24h_168h_predictions,
    )
    return ConsumerLoadPersistenceVsLag24hVsLag24h168hOLSMAEComparison(
        case_count=len(persistence_cases),
        persistence_mae_mw=persistence_result.mae_mw,
        lag_24h_mae_mw=lag_24h_result.mae_mw,
        lag_24h_168h_mae_mw=lag_24h_168h_result.mae_mw,
    )


def _require_nonempty_equal_cohort(
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    lag_24h_predictions: tuple[ConsumerLoadLag24hLinearRegressionPrediction, ...],
    lag_24h_168h_predictions: tuple[ConsumerLoadLag24h168hLinearRegressionPrediction, ...],
) -> None:
    if not persistence_cases and not lag_24h_predictions and not lag_24h_168h_predictions:
        raise InvalidRequestError(_EMPTY_ALL_MESSAGE)
    if not persistence_cases:
        raise InvalidRequestError(_EMPTY_PERSISTENCE_MESSAGE)
    if not lag_24h_predictions:
        raise InvalidRequestError(_EMPTY_LAG_24H_MESSAGE)
    if not lag_24h_168h_predictions:
        raise InvalidRequestError(_EMPTY_LAG_24H_168H_MESSAGE)
    if (
        len(persistence_cases) != len(lag_24h_predictions)
        or len(persistence_cases) != len(lag_24h_168h_predictions)
        or len(lag_24h_predictions) != len(lag_24h_168h_predictions)
    ):
        raise InvalidRequestError(_UNEQUAL_LENGTH_MESSAGE)


def _require_single_shared_consumer(
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    lag_24h_predictions: tuple[ConsumerLoadLag24hLinearRegressionPrediction, ...],
    lag_24h_168h_predictions: tuple[ConsumerLoadLag24h168hLinearRegressionPrediction, ...],
) -> None:
    persistence_consumers = {case.consumer_id for case in persistence_cases}
    lag_24h_consumers = {prediction.consumer_id for prediction in lag_24h_predictions}
    lag_24h_168h_consumers = {prediction.consumer_id for prediction in lag_24h_168h_predictions}
    if len(persistence_consumers) > 1:
        raise InvalidRequestError(_MIXED_PERSISTENCE_CONSUMER_MESSAGE)
    if len(lag_24h_consumers) > 1:
        raise InvalidRequestError(_MIXED_LAG_24H_CONSUMER_MESSAGE)
    if len(lag_24h_168h_consumers) > 1:
        raise InvalidRequestError(_MIXED_LAG_24H_168H_CONSUMER_MESSAGE)
    if (
        persistence_consumers != lag_24h_consumers
        or persistence_consumers != lag_24h_168h_consumers
        or lag_24h_consumers != lag_24h_168h_consumers
    ):
        raise InvalidRequestError(_CONSUMER_MISMATCH_MESSAGE)


def _require_persistence_chronology(
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
) -> None:
    previous = persistence_cases[0]
    for current in persistence_cases[1:]:
        if previous.target_timestamp == current.target_timestamp:
            raise InvalidRequestError(_DUPLICATE_PERSISTENCE_TIMESTAMP_MESSAGE)
        if previous.target_timestamp > current.target_timestamp:
            raise InvalidRequestError(_OUT_OF_ORDER_PERSISTENCE_MESSAGE)
        previous = current


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


def _require_three_way_alignment(
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    lag_24h_predictions: tuple[ConsumerLoadLag24hLinearRegressionPrediction, ...],
    lag_24h_168h_predictions: tuple[ConsumerLoadLag24h168hLinearRegressionPrediction, ...],
) -> None:
    for persistence_case, lag_24h_prediction, lag_24h_168h_prediction in zip(
        persistence_cases,
        lag_24h_predictions,
        lag_24h_168h_predictions,
        strict=True,
    ):
        if (
            persistence_case.target_timestamp != lag_24h_prediction.target_timestamp
            or persistence_case.target_timestamp != lag_24h_168h_prediction.target_timestamp
            or lag_24h_prediction.target_timestamp != lag_24h_168h_prediction.target_timestamp
        ):
            raise InvalidRequestError(_TIMESTAMP_MISMATCH_MESSAGE)
        if (
            persistence_case.actual_value_mw != lag_24h_prediction.actual_value_mw
            or persistence_case.actual_value_mw != lag_24h_168h_prediction.actual_value_mw
            or lag_24h_prediction.actual_value_mw != lag_24h_168h_prediction.actual_value_mw
        ):
            raise InvalidRequestError(_ACTUAL_MISMATCH_MESSAGE)
