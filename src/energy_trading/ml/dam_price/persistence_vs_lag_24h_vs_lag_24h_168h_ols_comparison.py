"""Aligned three-way persistence-versus-OLS DAM Price MAE comparison.

This outer ML transformation aligns already-produced Chunk 171 persistence
backtest cases with already-produced Chunk 176 one-feature OLS predictions
and already-produced Chunk 182 two-feature OLS predictions, then delegates
scoring to the published Chunk 172, Chunk 177, and Chunk 183 MAE evaluators.

Ownership:

* Application: owns live inference via ``DAMPriceForecastModelPort``.
* ML: owns this offline aligned comparison. Returned values are ML comparison
  evidence, not workflow state and not ``PriceForecastPoint``.
* Aggregate MAE result objects alone are not sufficient. Fair comparison
  requires the same market, the same currency, the same target timestamps,
  the same actual price observations, and equal cohort size across all three
  cohorts. Predicted amounts may differ; that difference is what is being
  compared.

Chunk 186 owns three-way alignment and composition only. It consumes the
published persistence backtest case type and the published one-feature and
two-feature prediction artifact types, and calls the three published MAE
evaluators directly. It does not call the published pairwise comparison
functions, rebuild persistence cases, invoke either predictor, fit, build
features, split data, convert currency, or calculate MAE itself.

The comparison reports ``case_count``, the shared currency, persistence MAE,
one-feature OLS MAE, and two-feature OLS MAE side by side. It does not choose
a production model, declare a winner, rank models, compute a relative change,
or apply an acceptance threshold.

The comparison remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass

from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.value_objects.quantities import CurrencyCode, FiniteDecimal
from energy_trading.ml.dam_price.lag_24h_168h_linear_regression_evaluation import (
    evaluate_dam_price_lag_24h_168h_linear_regression_mae,
)
from energy_trading.ml.dam_price.lag_24h_168h_linear_regression_prediction import (
    DAMPriceLag24h168hLinearRegressionPrediction,
)
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

_EMPTY_ALL_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires a "
    "non-empty aligned cohort."
)
_EMPTY_PERSISTENCE_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires a "
    "non-empty persistence cohort."
)
_EMPTY_LAG_24H_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires a "
    "non-empty one-feature cohort."
)
_EMPTY_LAG_24H_168H_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires a "
    "non-empty two-feature cohort."
)
_UNEQUAL_LENGTH_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
    "equal persistence, one-feature, and two-feature case counts."
)
_MIXED_PERSISTENCE_MARKET_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
    "persistence cases from exactly one market."
)
_MIXED_LAG_24H_MARKET_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
    "one-feature predictions from exactly one market."
)
_MIXED_LAG_24H_168H_MARKET_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
    "two-feature predictions from exactly one market."
)
_MARKET_MISMATCH_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
    "persistence cases, one-feature predictions, and two-feature predictions from the same "
    "market."
)
_PERSISTENCE_CURRENCY_COHERENCE_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
    "matching predicted and actual persistence currency."
)
_MIXED_PERSISTENCE_CURRENCY_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
    "persistence cases in exactly one currency."
)
_MIXED_LAG_24H_CURRENCY_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
    "one-feature predictions in exactly one currency."
)
_MIXED_LAG_24H_168H_CURRENCY_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
    "two-feature predictions in exactly one currency."
)
_CURRENCY_MISMATCH_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
    "persistence cases, one-feature predictions, and two-feature predictions in the same "
    "currency."
)
_DUPLICATE_PERSISTENCE_TIMESTAMP_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
    "unique persistence target timestamps."
)
_DUPLICATE_LAG_24H_TIMESTAMP_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
    "unique one-feature target timestamps."
)
_DUPLICATE_LAG_24H_168H_TIMESTAMP_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
    "unique two-feature target timestamps."
)
_OUT_OF_ORDER_PERSISTENCE_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
    "strictly increasing persistence target timestamps."
)
_OUT_OF_ORDER_LAG_24H_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
    "strictly increasing one-feature target timestamps."
)
_OUT_OF_ORDER_LAG_24H_168H_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
    "strictly increasing two-feature target timestamps."
)
_TIMESTAMP_MISMATCH_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
    "matching target timestamps at each aligned index."
)
_ACTUAL_MISMATCH_MESSAGE = (
    "DAM Price persistence-versus-one-feature-versus-two-feature OLS MAE comparison requires "
    "matching actual price amounts at each aligned index."
)


@dataclass(frozen=True, slots=True)
class DAMPricePersistenceVsLag24hVsLag24h168hOLSMAEComparison:
    """Aligned persistence, one-feature, and two-feature OLS MAE evidence."""

    case_count: int
    currency: CurrencyCode
    persistence_mae_amount_per_mwh: FiniteDecimal
    lag_24h_mae_amount_per_mwh: FiniteDecimal
    lag_24h_168h_mae_amount_per_mwh: FiniteDecimal


def compare_dam_price_persistence_vs_lag_24h_vs_lag_24h_168h_ols_mae(
    *,
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    lag_24h_predictions: tuple[DAMPriceLag24hLinearRegressionPrediction, ...],
    lag_24h_168h_predictions: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
) -> DAMPricePersistenceVsLag24hVsLag24h168hOLSMAEComparison:
    """Return aligned persistence, one-feature, and two-feature OLS MAE."""

    _require_nonempty_equal_cohort(
        persistence_cases,
        lag_24h_predictions,
        lag_24h_168h_predictions,
    )
    currency = _require_single_shared_market_and_currency(
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
    lag_24h_result = evaluate_dam_price_lag_24h_linear_regression_mae(
        predictions=lag_24h_predictions,
    )
    lag_24h_168h_result = evaluate_dam_price_lag_24h_168h_linear_regression_mae(
        predictions=lag_24h_168h_predictions,
    )
    return DAMPricePersistenceVsLag24hVsLag24h168hOLSMAEComparison(
        case_count=len(persistence_cases),
        currency=currency,
        persistence_mae_amount_per_mwh=persistence_result.mae_amount_per_mwh,
        lag_24h_mae_amount_per_mwh=lag_24h_result.mae_amount_per_mwh,
        lag_24h_168h_mae_amount_per_mwh=lag_24h_168h_result.mae_amount_per_mwh,
    )


def _require_nonempty_equal_cohort(
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    lag_24h_predictions: tuple[DAMPriceLag24hLinearRegressionPrediction, ...],
    lag_24h_168h_predictions: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
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


def _require_single_shared_market_and_currency(
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    lag_24h_predictions: tuple[DAMPriceLag24hLinearRegressionPrediction, ...],
    lag_24h_168h_predictions: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
) -> str:
    """Return the shared currency after proving three-way market and currency alignment."""

    persistence_markets = {case.market_id for case in persistence_cases}
    lag_24h_markets = {prediction.market_id for prediction in lag_24h_predictions}
    lag_24h_168h_markets = {prediction.market_id for prediction in lag_24h_168h_predictions}
    if len(persistence_markets) > 1:
        raise InvalidRequestError(_MIXED_PERSISTENCE_MARKET_MESSAGE)
    if len(lag_24h_markets) > 1:
        raise InvalidRequestError(_MIXED_LAG_24H_MARKET_MESSAGE)
    if len(lag_24h_168h_markets) > 1:
        raise InvalidRequestError(_MIXED_LAG_24H_168H_MARKET_MESSAGE)
    if (
        persistence_markets != lag_24h_markets
        or persistence_markets != lag_24h_168h_markets
        or lag_24h_markets != lag_24h_168h_markets
    ):
        raise InvalidRequestError(_MARKET_MISMATCH_MESSAGE)
    for case in persistence_cases:
        if case.predicted_price.currency != case.actual_price.currency:
            raise InvalidRequestError(_PERSISTENCE_CURRENCY_COHERENCE_MESSAGE)
    persistence_currencies = {case.actual_price.currency for case in persistence_cases}
    lag_24h_currencies = {prediction.currency for prediction in lag_24h_predictions}
    lag_24h_168h_currencies = {prediction.currency for prediction in lag_24h_168h_predictions}
    if len(persistence_currencies) > 1:
        raise InvalidRequestError(_MIXED_PERSISTENCE_CURRENCY_MESSAGE)
    if len(lag_24h_currencies) > 1:
        raise InvalidRequestError(_MIXED_LAG_24H_CURRENCY_MESSAGE)
    if len(lag_24h_168h_currencies) > 1:
        raise InvalidRequestError(_MIXED_LAG_24H_168H_CURRENCY_MESSAGE)
    if (
        persistence_currencies != lag_24h_currencies
        or persistence_currencies != lag_24h_168h_currencies
        or lag_24h_currencies != lag_24h_168h_currencies
    ):
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


def _require_lag_24h_chronology(
    lag_24h_predictions: tuple[DAMPriceLag24hLinearRegressionPrediction, ...],
) -> None:
    previous = lag_24h_predictions[0]
    for current in lag_24h_predictions[1:]:
        if previous.target_timestamp == current.target_timestamp:
            raise InvalidRequestError(_DUPLICATE_LAG_24H_TIMESTAMP_MESSAGE)
        if previous.target_timestamp > current.target_timestamp:
            raise InvalidRequestError(_OUT_OF_ORDER_LAG_24H_MESSAGE)
        previous = current


def _require_lag_24h_168h_chronology(
    lag_24h_168h_predictions: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
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
    lag_24h_predictions: tuple[DAMPriceLag24hLinearRegressionPrediction, ...],
    lag_24h_168h_predictions: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
) -> None:
    """Prove three-way positional identity without truncation or realignment.

    Equal cardinality was already established, so an explicit index loop is
    used instead of ``zip``: there is no shortest-cohort truncation semantic
    and no opportunity to silently pair mismatched positions.
    """

    for index in range(len(persistence_cases)):
        persistence_case = persistence_cases[index]
        lag_24h_prediction = lag_24h_predictions[index]
        lag_24h_168h_prediction = lag_24h_168h_predictions[index]
        if (
            persistence_case.target_timestamp != lag_24h_prediction.target_timestamp
            or persistence_case.target_timestamp != lag_24h_168h_prediction.target_timestamp
            or lag_24h_prediction.target_timestamp != lag_24h_168h_prediction.target_timestamp
        ):
            raise InvalidRequestError(_TIMESTAMP_MISMATCH_MESSAGE)
        if (
            persistence_case.actual_price.amount_per_mwh != lag_24h_prediction.actual_amount_per_mwh
            or persistence_case.actual_price.amount_per_mwh
            != lag_24h_168h_prediction.actual_amount_per_mwh
            or lag_24h_prediction.actual_amount_per_mwh
            != lag_24h_168h_prediction.actual_amount_per_mwh
        ):
            raise InvalidRequestError(_ACTUAL_MISMATCH_MESSAGE)
