"""Aligned persistence-versus-trained OLS DAM Price MAE comparison.

This outer ML transformation aligns already-produced Chunk 171 persistence
backtest cases with already-produced Chunk 176 trained OLS predictions, then
delegates scoring to the published Chunk 172 and Chunk 177 MAE evaluators.

Ownership:

* Application: owns live inference via ``DAMPriceForecastModelPort``.
* ML: owns this offline aligned comparison. Returned values are ML comparison
  evidence, not workflow state and not ``PriceForecastPoint``.
* Aggregate MAE result objects alone are not sufficient. Fair comparison
  requires the same market, the same currency, the same target timestamps,
  the same actual price observations, and equal cohort size.

Chunk 178 owns alignment and composition only. It does not fit, predict,
rebuild history, build features, split data, or calculate MAE itself.

The comparison reports ``case_count``, the shared currency, persistence MAE,
and trained OLS MAE. It does not choose a production model, declare a winner,
compute a relative change, or apply an acceptance threshold.

The comparison remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass

from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.value_objects.quantities import CurrencyCode, FiniteDecimal
from energy_trading.ml.dam_price.lag_24h_linear_regression_evaluation import (
    evaluate_dam_price_lag_24h_linear_regression_mae,
)
from energy_trading.ml.dam_price.lag_24h_linear_regression_prediction import (
    DAMPriceLag24hLinearRegressionPrediction,
)
from energy_trading.ml.dam_price.previous_day_persistence_backtest import (
    PreviousDayPersistenceBacktestCase,
)
from energy_trading.ml.dam_price.previous_day_persistence_evaluation import (
    evaluate_previous_day_persistence_mae,
)

_EMPTY_BOTH_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires a non-empty aligned cohort."
)
_EMPTY_PERSISTENCE_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires a non-empty persistence "
    "cohort."
)
_EMPTY_TRAINED_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires a non-empty trained OLS "
    "cohort."
)
_UNEQUAL_LENGTH_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires equal persistence and "
    "trained case counts."
)
_MIXED_PERSISTENCE_MARKET_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires persistence cases from "
    "exactly one market."
)
_MIXED_TRAINED_MARKET_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires trained predictions from "
    "exactly one market."
)
_MARKET_MISMATCH_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires persistence cases and "
    "trained predictions from the same market."
)
_PERSISTENCE_CURRENCY_COHERENCE_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires matching predicted and "
    "actual persistence currency."
)
_MIXED_PERSISTENCE_CURRENCY_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires persistence cases in "
    "exactly one currency."
)
_MIXED_TRAINED_CURRENCY_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires trained predictions in "
    "exactly one currency."
)
_CURRENCY_MISMATCH_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires persistence cases and "
    "trained predictions in the same currency."
)
_DUPLICATE_PERSISTENCE_TIMESTAMP_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires unique persistence target "
    "timestamps."
)
_DUPLICATE_TRAINED_TIMESTAMP_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires unique trained target "
    "timestamps."
)
_OUT_OF_ORDER_PERSISTENCE_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires strictly increasing "
    "persistence target timestamps."
)
_OUT_OF_ORDER_TRAINED_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires strictly increasing "
    "trained target timestamps."
)
_TIMESTAMP_MISMATCH_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires matching target timestamps "
    "at each aligned index."
)
_ACTUAL_MISMATCH_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires matching actual price "
    "amounts at each aligned index."
)


@dataclass(frozen=True, slots=True)
class DAMPricePersistenceVsTrainedOLSMAEComparison:
    """Aligned persistence and trained OLS MAE evidence for one cohort."""

    case_count: int
    currency: CurrencyCode
    persistence_mae_amount_per_mwh: FiniteDecimal
    trained_ols_mae_amount_per_mwh: FiniteDecimal


def compare_dam_price_persistence_vs_trained_ols_mae(
    *,
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    trained_predictions: tuple[DAMPriceLag24hLinearRegressionPrediction, ...],
) -> DAMPricePersistenceVsTrainedOLSMAEComparison:
    """Return aligned persistence and trained OLS MAE for one shared cohort."""

    _require_nonempty_equal_cohort(persistence_cases, trained_predictions)
    currency = _require_single_shared_market_and_currency(persistence_cases, trained_predictions)
    _require_persistence_chronology(persistence_cases)
    _require_trained_chronology(trained_predictions)
    _require_pairwise_alignment(persistence_cases, trained_predictions)
    persistence_result = evaluate_previous_day_persistence_mae(cases=persistence_cases)
    trained_result = evaluate_dam_price_lag_24h_linear_regression_mae(
        predictions=trained_predictions,
    )
    return DAMPricePersistenceVsTrainedOLSMAEComparison(
        case_count=len(persistence_cases),
        currency=currency,
        persistence_mae_amount_per_mwh=persistence_result.mae_amount_per_mwh,
        trained_ols_mae_amount_per_mwh=trained_result.mae_amount_per_mwh,
    )


def _require_nonempty_equal_cohort(
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    trained_predictions: tuple[DAMPriceLag24hLinearRegressionPrediction, ...],
) -> None:
    if not persistence_cases and not trained_predictions:
        raise InvalidRequestError(_EMPTY_BOTH_MESSAGE)
    if not persistence_cases:
        raise InvalidRequestError(_EMPTY_PERSISTENCE_MESSAGE)
    if not trained_predictions:
        raise InvalidRequestError(_EMPTY_TRAINED_MESSAGE)
    if len(persistence_cases) != len(trained_predictions):
        raise InvalidRequestError(_UNEQUAL_LENGTH_MESSAGE)


def _require_single_shared_market_and_currency(
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    trained_predictions: tuple[DAMPriceLag24hLinearRegressionPrediction, ...],
) -> str:
    """Return the shared currency after proving market and currency alignment."""

    persistence_markets = {case.market_id for case in persistence_cases}
    trained_markets = {prediction.market_id for prediction in trained_predictions}
    if len(persistence_markets) > 1:
        raise InvalidRequestError(_MIXED_PERSISTENCE_MARKET_MESSAGE)
    if len(trained_markets) > 1:
        raise InvalidRequestError(_MIXED_TRAINED_MARKET_MESSAGE)
    if persistence_markets != trained_markets:
        raise InvalidRequestError(_MARKET_MISMATCH_MESSAGE)
    for case in persistence_cases:
        if case.predicted_price.currency != case.actual_price.currency:
            raise InvalidRequestError(_PERSISTENCE_CURRENCY_COHERENCE_MESSAGE)
    persistence_currencies = {case.actual_price.currency for case in persistence_cases}
    trained_currencies = {prediction.currency for prediction in trained_predictions}
    if len(persistence_currencies) > 1:
        raise InvalidRequestError(_MIXED_PERSISTENCE_CURRENCY_MESSAGE)
    if len(trained_currencies) > 1:
        raise InvalidRequestError(_MIXED_TRAINED_CURRENCY_MESSAGE)
    if persistence_currencies != trained_currencies:
        raise InvalidRequestError(_CURRENCY_MISMATCH_MESSAGE)
    return next(iter(persistence_currencies))


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


def _require_trained_chronology(
    trained_predictions: tuple[DAMPriceLag24hLinearRegressionPrediction, ...],
) -> None:
    previous = trained_predictions[0]
    for current in trained_predictions[1:]:
        if previous.target_timestamp == current.target_timestamp:
            raise InvalidRequestError(_DUPLICATE_TRAINED_TIMESTAMP_MESSAGE)
        if previous.target_timestamp > current.target_timestamp:
            raise InvalidRequestError(_OUT_OF_ORDER_TRAINED_MESSAGE)
        previous = current


def _require_pairwise_alignment(
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    trained_predictions: tuple[DAMPriceLag24hLinearRegressionPrediction, ...],
) -> None:
    """Prove positional identity without truncation or realignment.

    Equal cardinality was already established, so an explicit index loop is
    used instead of ``zip``: there is no shortest-cohort truncation semantic
    and no opportunity to silently pair mismatched positions.
    """

    for index in range(len(persistence_cases)):
        persistence_case = persistence_cases[index]
        trained_prediction = trained_predictions[index]
        if persistence_case.target_timestamp != trained_prediction.target_timestamp:
            raise InvalidRequestError(_TIMESTAMP_MISMATCH_MESSAGE)
        if persistence_case.actual_price.amount_per_mwh != trained_prediction.actual_amount_per_mwh:
            raise InvalidRequestError(_ACTUAL_MISMATCH_MESSAGE)
