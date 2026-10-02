"""Lag-24h plus lag-168h ordinary-least-squares DAM Price evaluation prediction.

This outer ML transformation applies already-fitted Chunk 181 two-feature OLS
parameters to already-built Chunk 179 evaluation rows. It does not fit,
split, rebuild history, or calculate metrics.

Ownership:

* Application: owns live inference via ``DAMPriceForecastModelPort``.
* ML: owns this offline two-feature trained-model evaluation prediction.
  Returned values are ML evaluation artifacts, not workflow state and not a
  live forecast.
* Already-fitted two-feature parameters and already-built two-lag evaluation
  rows are the only inputs. This module does not consume the Chunk 180 split
  object, does not call the Chunk 181 fitter, and does not belong to
  application orchestration. It is independent of the published one-feature
  Chunk 176 predictor and does not fall back to it.

Prediction:

* ``predicted_amount_per_mwh`` is
  ``lag_24h_coefficient * lag_24h_amount_per_mwh
  + lag_168h_coefficient * lag_168h_amount_per_mwh
  + intercept_amount_per_mwh``
* ``actual_amount_per_mwh`` copies the row target unchanged
* Evaluation identity (``market_id``, ``currency``, ``target_timestamp``) is
  preserved
* Input evaluation-row order is preserved

All arithmetic stays in canonical ``Decimal``: no float conversion, rounding,
quantization, clamping, scaling, standardization, or currency conversion is
performed. The predicted amount is an offline ML evaluation value on a
currency-qualified price scale, not a canonical market-price observation, so
it is not wrapped as ``EnergyPrice`` and it is not a ``PriceForecastPoint``.
Negative and zero finite predictions are valid experimental evidence and are
not clamped. Currency is carried as identity and semantic context only; it
never participates in the arithmetic.

Empty evaluation input, mixed markets, mixed currencies, malformed
chronology, non-finite fitted parameters, non-finite row values, Decimal
arithmetic signals, and non-finite computed predictions all fail closed.
External ML libraries are not used.

The predictor remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from dataclasses import dataclass
from decimal import Decimal, DecimalException

from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.value_objects.quantities import (
    CurrencyCode,
    EntityId,
    FiniteDecimal,
)
from energy_trading.domain.value_objects.time import UtcDateTime
from energy_trading.ml.dam_price.lag_24h_168h_features import DAMPriceLag24h168hFeatureRow
from energy_trading.ml.dam_price.lag_24h_168h_linear_regression import (
    DAMPriceLag24h168hLinearRegressionFit,
)

_EMPTY_ROWS_MESSAGE = (
    "DAM Price 24h+168h linear regression prediction requires at least one evaluation row."
)
_MIXED_MARKET_MESSAGE = (
    "DAM Price 24h+168h linear regression prediction requires rows from exactly one market."
)
_MIXED_CURRENCY_MESSAGE = (
    "DAM Price 24h+168h linear regression prediction requires rows in exactly one currency."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "DAM Price 24h+168h linear regression prediction requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "DAM Price 24h+168h linear regression prediction requires strictly increasing "
    "target timestamps."
)
_NON_FINITE_FIT_MESSAGE = (
    "DAM Price 24h+168h linear regression prediction requires finite fitted "
    "coefficients and intercept."
)
_NON_FINITE_INPUT_MESSAGE = (
    "DAM Price 24h+168h linear regression prediction requires finite feature and target values."
)
_NON_FINITE_PREDICTION_MESSAGE = (
    "DAM Price 24h+168h linear regression prediction requires finite predicted values."
)


@dataclass(frozen=True, slots=True)
class DAMPriceLag24h168hLinearRegressionPrediction:
    """One evaluated lag-24h plus lag-168h OLS prediction observation."""

    market_id: EntityId
    currency: CurrencyCode
    target_timestamp: UtcDateTime
    predicted_amount_per_mwh: FiniteDecimal
    actual_amount_per_mwh: FiniteDecimal


def predict_dam_price_lag_24h_168h_linear_regression(
    *,
    fit: DAMPriceLag24h168hLinearRegressionFit,
    evaluation_rows: tuple[DAMPriceLag24h168hFeatureRow, ...],
) -> tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...]:
    """Apply fitted two-feature OLS parameters to chronological two-lag rows."""

    if not evaluation_rows:
        raise InvalidRequestError(_EMPTY_ROWS_MESSAGE)
    _require_single_market(evaluation_rows)
    _require_single_currency(evaluation_rows)
    _require_strict_chronology(evaluation_rows)
    _require_finite_fit(fit)
    return tuple(_prediction_for_row(fit, row) for row in evaluation_rows)


def _prediction_for_row(
    fit: DAMPriceLag24h168hLinearRegressionFit,
    row: DAMPriceLag24h168hFeatureRow,
) -> DAMPriceLag24h168hLinearRegressionPrediction:
    predicted_amount_per_mwh = _predicted_amount_per_mwh(fit, row)
    return DAMPriceLag24h168hLinearRegressionPrediction(
        market_id=row.market_id,
        currency=row.currency,
        target_timestamp=row.target_timestamp,
        predicted_amount_per_mwh=predicted_amount_per_mwh,
        actual_amount_per_mwh=row.target_amount_per_mwh,
    )


def _predicted_amount_per_mwh(
    fit: DAMPriceLag24h168hLinearRegressionFit,
    row: DAMPriceLag24h168hFeatureRow,
) -> Decimal:
    """Return the Decimal two-feature OLS prediction, failing closed on arithmetic.

    Decimal arithmetic can raise a signal for a valid-looking cohort whose
    products or sum leave the representable range. The multiplications and
    additions are therefore performed under a narrowed Decimal-exception guard
    so that such a cohort becomes the same sanitized failure family rather
    than leaking raw numeric inputs. Only ``DecimalException`` is translated,
    so no broad exception handling is introduced.
    """

    if (
        not row.lag_24h_amount_per_mwh.is_finite()
        or not row.lag_168h_amount_per_mwh.is_finite()
        or not row.target_amount_per_mwh.is_finite()
    ):
        raise InvalidRequestError(_NON_FINITE_INPUT_MESSAGE)
    try:
        predicted_amount_per_mwh = (
            fit.lag_24h_coefficient * row.lag_24h_amount_per_mwh
            + fit.lag_168h_coefficient * row.lag_168h_amount_per_mwh
            + fit.intercept_amount_per_mwh
        )
    except DecimalException as error:
        msg = _NON_FINITE_PREDICTION_MESSAGE
        raise InvalidRequestError(msg) from error
    if not predicted_amount_per_mwh.is_finite():
        raise InvalidRequestError(_NON_FINITE_PREDICTION_MESSAGE)
    return predicted_amount_per_mwh


def _require_finite_fit(fit: DAMPriceLag24h168hLinearRegressionFit) -> None:
    if (
        not fit.lag_24h_coefficient.is_finite()
        or not fit.lag_168h_coefficient.is_finite()
        or not fit.intercept_amount_per_mwh.is_finite()
    ):
        raise InvalidRequestError(_NON_FINITE_FIT_MESSAGE)


def _require_single_market(rows: tuple[DAMPriceLag24h168hFeatureRow, ...]) -> None:
    market_ids = {row.market_id for row in rows}
    if len(market_ids) > 1:
        raise InvalidRequestError(_MIXED_MARKET_MESSAGE)


def _require_single_currency(rows: tuple[DAMPriceLag24h168hFeatureRow, ...]) -> None:
    currencies = {row.currency for row in rows}
    if len(currencies) > 1:
        raise InvalidRequestError(_MIXED_CURRENCY_MESSAGE)


def _require_strict_chronology(rows: tuple[DAMPriceLag24h168hFeatureRow, ...]) -> None:
    previous = rows[0]
    for current in rows[1:]:
        if previous.target_timestamp == current.target_timestamp:
            raise InvalidRequestError(_DUPLICATE_TIMESTAMP_MESSAGE)
        if previous.target_timestamp > current.target_timestamp:
            raise InvalidRequestError(_OUT_OF_ORDER_MESSAGE)
        previous = current
