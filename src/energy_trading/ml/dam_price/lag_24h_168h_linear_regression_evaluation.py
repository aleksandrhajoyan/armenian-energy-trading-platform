"""Lag-24h plus lag-168h ordinary-least-squares DAM Price MAE evaluation.

This outer ML transformation scores already-produced Chunk 182
``DAMPriceLag24h168hLinearRegressionPrediction`` values. It calculates MAE
only.

Ownership:

* Application: owns live inference via ``DAMPriceForecastModelPort``.
* ML: owns this offline two-feature trained-model MAE evaluator. Returned
  values are ML evaluation results, not workflow state and not
  ``PriceForecastPoint``.
* Chunk 182 owns which evaluation rows are scored and the supplied
  chronology. This module depends only on the Chunk 182 prediction artifact
  type; it never invokes the Chunk 182 predictor, and it does not fit
  parameters, rebuild features, split cohorts, or re-calculate predictions.

MAE remains a currency amount per MWh:

``MAE = mean(|predicted_amount_per_mwh - actual_amount_per_mwh|)``

Arithmetic stays in canonical ``Decimal``. The cohort must belong to exactly
one market and use exactly one currency. Every supplied prediction counts in
the denominator, including zero-error predictions. Target timestamps must be
strictly increasing and unique in supplied order; malformed cohorts fail
closed rather than being sorted, deduplicated, or repaired. An empty
prediction tuple is undefined and fails closed with existing
``InvalidRequestError``. There is no zero, NaN, infinity, or optional
sentinel result.

Canonical DAM prices may be negative. ``abs`` is used only for the error
difference required by MAE; it never mutates or sanitizes a price input.
Weighting, rounding, quantizing, clamping, scaling, and currency conversion
are not implemented, and no other metric is calculated. This contract is
independent of the published one-feature OLS MAE evaluator. There is no
comparison against the one-feature model or the persistence baseline, no
model selection, and no live inference.

The evaluator remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass
from decimal import Decimal, DecimalException

from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.value_objects.quantities import CurrencyCode, FiniteDecimal
from energy_trading.ml.dam_price.lag_24h_168h_linear_regression_prediction import (
    DAMPriceLag24h168hLinearRegressionPrediction,
)

_EMPTY_PREDICTIONS_MESSAGE = (
    "DAM Price 24h+168h linear regression MAE evaluation requires at least one prediction."
)
_MIXED_MARKET_MESSAGE = (
    "DAM Price 24h+168h linear regression MAE evaluation requires predictions from exactly "
    "one market."
)
_MIXED_CURRENCY_MESSAGE = (
    "DAM Price 24h+168h linear regression MAE evaluation requires predictions in exactly "
    "one currency."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "DAM Price 24h+168h linear regression MAE evaluation requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "DAM Price 24h+168h linear regression MAE evaluation requires strictly increasing "
    "target timestamps."
)
_NON_FINITE_VALUES_MESSAGE = (
    "DAM Price 24h+168h linear regression MAE evaluation requires finite predicted and "
    "actual values."
)
_NON_FINITE_MAE_MESSAGE = (
    "DAM Price 24h+168h linear regression MAE evaluation requires a finite MAE."
)


@dataclass(frozen=True, slots=True)
class DAMPriceLag24h168hLinearRegressionMAEResult:
    """MAE over supplied lag-24h plus lag-168h OLS evaluation predictions."""

    case_count: int
    currency: CurrencyCode
    mae_amount_per_mwh: FiniteDecimal


def evaluate_dam_price_lag_24h_168h_linear_regression_mae(
    *,
    predictions: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
) -> DAMPriceLag24h168hLinearRegressionMAEResult:
    """Return MAE as a currency amount per MWh over the supplied predictions."""

    if not predictions:
        raise InvalidRequestError(_EMPTY_PREDICTIONS_MESSAGE)
    _require_single_market(predictions)
    currency = _require_single_currency(predictions)
    _require_strict_chronology(predictions)
    _require_finite_values(predictions)
    total_abs_error = _total_absolute_error(predictions)
    try:
        mae_amount_per_mwh = total_abs_error / len(predictions)
    except DecimalException as error:
        msg = _NON_FINITE_MAE_MESSAGE
        raise InvalidRequestError(msg) from error
    if not mae_amount_per_mwh.is_finite():
        raise InvalidRequestError(_NON_FINITE_MAE_MESSAGE)
    return DAMPriceLag24h168hLinearRegressionMAEResult(
        case_count=len(predictions),
        currency=currency,
        mae_amount_per_mwh=mae_amount_per_mwh,
    )


def _total_absolute_error(
    predictions: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
) -> Decimal:
    """Accumulate absolute errors in Decimal, translating arithmetic failure closed.

    Decimal arithmetic can raise a signal for a valid-looking cohort whose
    values leave the representable range. Accumulation is therefore performed
    under a narrowed Decimal-exception guard so that such a cohort becomes the
    same sanitized failure family rather than leaking raw numeric inputs. Only
    ``DecimalException`` is translated, so no broad exception handling is
    introduced. A non-finite accumulated total also fails closed.
    """

    try:
        total_abs_error = abs(
            predictions[0].predicted_amount_per_mwh - predictions[0].actual_amount_per_mwh
        )
        for prediction in predictions[1:]:
            total_abs_error += abs(
                prediction.predicted_amount_per_mwh - prediction.actual_amount_per_mwh
            )
    except DecimalException as error:
        msg = _NON_FINITE_MAE_MESSAGE
        raise InvalidRequestError(msg) from error
    if not total_abs_error.is_finite():
        raise InvalidRequestError(_NON_FINITE_MAE_MESSAGE)
    return total_abs_error


def _require_finite_values(
    predictions: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
) -> None:
    for prediction in predictions:
        if not prediction.predicted_amount_per_mwh.is_finite():
            raise InvalidRequestError(_NON_FINITE_VALUES_MESSAGE)
        if not prediction.actual_amount_per_mwh.is_finite():
            raise InvalidRequestError(_NON_FINITE_VALUES_MESSAGE)


def _require_single_market(
    predictions: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
) -> None:
    market_ids = {prediction.market_id for prediction in predictions}
    if len(market_ids) > 1:
        raise InvalidRequestError(_MIXED_MARKET_MESSAGE)


def _require_single_currency(
    predictions: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
) -> CurrencyCode:
    currencies = {prediction.currency for prediction in predictions}
    if len(currencies) > 1:
        raise InvalidRequestError(_MIXED_CURRENCY_MESSAGE)
    return next(iter(currencies))


def _require_strict_chronology(
    predictions: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
) -> None:
    previous = predictions[0]
    for current in predictions[1:]:
        if previous.target_timestamp == current.target_timestamp:
            raise InvalidRequestError(_DUPLICATE_TIMESTAMP_MESSAGE)
        if previous.target_timestamp > current.target_timestamp:
            raise InvalidRequestError(_OUT_OF_ORDER_MESSAGE)
        previous = current
