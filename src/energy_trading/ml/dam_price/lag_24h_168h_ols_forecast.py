"""Lag-24h plus lag-168h OLS DAM Price Forecast candidate adapter.

This outer ML adapter structurally implements ``DAMPriceForecastModelPort``.
It applies already-fitted Chunk 181 two-feature Decimal OLS parameters to the
unique exact ``T - 24h`` and ``T - 168h`` history observations. It does not
fit, retrain, or select a production model.

Ownership:

* Application: owns ``DAMPriceForecastModelPort`` and
  ``DAMPriceForecastModelRequest``. Canonical live output remains
  ``PriceForecastPoint`` carrying a canonical ``EnergyPrice``.
* ML: owns this candidate numerical implementation. It is not a selected,
  best, or champion model and not an Armenia-specific market-behavior claim.
  The previous-day persistence baseline remains separately available.
* Identity fields are caller-supplied. This module does not invent
  ``forecast_run_id``, ``generated_at``, clocks, or UUIDs. The output price
  currency is ``request.currency``; it is never inferred from history.

Prediction:

* ``raw_prediction = lag_24h_coefficient * lag_24h_price
  + lag_168h_coefficient * lag_168h_price + intercept_amount_per_mwh``
* both lag prices are canonical ``MarketPriceRecord.price.amount_per_mwh``
  values at exactly 24 and 168 elapsed hours before the target

All arithmetic stays in canonical ``Decimal``: no float conversion, rounding,
quantization, scaling, clamping, or currency conversion is performed. DAM
prices are signed, so negative and zero finite predictions are valid and are
not clamped.

Non-finite fitted parameters, missing or duplicate exact lag observations,
Decimal arithmetic signals, and non-finite computed predictions fail closed
with existing ``InvalidRequestError``. There is no nearest-neighbor,
interpolation, one-feature or persistence fallback, or partial success.

The adapter remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from datetime import datetime, timedelta
from decimal import DecimalException

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.ports.dam_price_forecast_model import (
    DAMPriceForecastModelRequest,
)
from energy_trading.domain.models.forecasting import PriceForecastPoint
from energy_trading.domain.models.observations import MarketPriceRecord
from energy_trading.domain.value_objects.money import EnergyPrice
from energy_trading.ml.dam_price.lag_24h_168h_linear_regression import (
    DAMPriceLag24h168hLinearRegressionFit,
)

_LAG_24H = timedelta(hours=24)
_LAG_168H = timedelta(hours=168)
_MISSING_LAG_24H_MESSAGE = (
    "DAM Price trained OLS live inference requires exactly one history "
    "observation at the 24-hour lag."
)
_MISSING_LAG_168H_MESSAGE = (
    "DAM Price trained OLS live inference requires exactly one history "
    "observation at the 168-hour lag."
)
_DUPLICATE_LAG_24H_MESSAGE = (
    "DAM Price trained OLS live inference requires a unique 24-hour lag observation."
)
_DUPLICATE_LAG_168H_MESSAGE = (
    "DAM Price trained OLS live inference requires a unique 168-hour lag observation."
)
_NON_FINITE_FIT_MESSAGE = (
    "DAM Price trained OLS live inference requires finite fitted coefficients and intercept."
)
_NON_FINITE_PREDICTION_MESSAGE = (
    "DAM Price trained OLS live inference requires a finite forecast price."
)


class Lag24h168hOLSDAMPriceForecastModel:
    """Apply already-fitted two-feature Decimal OLS parameters to exact lag evidence."""

    def __init__(self, *, fit: DAMPriceLag24h168hLinearRegressionFit) -> None:
        _require_finite_fit(fit)
        self._fit = fit

    async def forecast(
        self,
        *,
        request: DAMPriceForecastModelRequest,
    ) -> tuple[PriceForecastPoint, ...]:
        """Return canonical price points in requested target order."""

        return tuple(
            _point_for_target(self._fit, request, target) for target in request.target_timestamps
        )


def _require_finite_fit(fit: DAMPriceLag24h168hLinearRegressionFit) -> None:
    if (
        not fit.lag_24h_coefficient.is_finite()
        or not fit.lag_168h_coefficient.is_finite()
        or not fit.intercept_amount_per_mwh.is_finite()
    ):
        raise InvalidRequestError(_NON_FINITE_FIT_MESSAGE)


def _point_for_target(
    fit: DAMPriceLag24h168hLinearRegressionFit,
    request: DAMPriceForecastModelRequest,
    target: datetime,
) -> PriceForecastPoint:
    lag_24h = _unique_lag_observation(
        request.history,
        target - _LAG_24H,
        missing_message=_MISSING_LAG_24H_MESSAGE,
        duplicate_message=_DUPLICATE_LAG_24H_MESSAGE,
    )
    lag_168h = _unique_lag_observation(
        request.history,
        target - _LAG_168H,
        missing_message=_MISSING_LAG_168H_MESSAGE,
        duplicate_message=_DUPLICATE_LAG_168H_MESSAGE,
    )
    try:
        raw_prediction = (
            fit.lag_24h_coefficient * lag_24h.price.amount_per_mwh
            + fit.lag_168h_coefficient * lag_168h.price.amount_per_mwh
            + fit.intercept_amount_per_mwh
        )
    except DecimalException as error:
        raise InvalidRequestError(_NON_FINITE_PREDICTION_MESSAGE) from error
    if not raw_prediction.is_finite():
        raise InvalidRequestError(_NON_FINITE_PREDICTION_MESSAGE)
    return PriceForecastPoint(
        forecast_run_id=request.forecast_run_id,
        market_id=request.market_id,
        generated_at=request.generated_at,
        target_timestamp=target,
        price=EnergyPrice(amount_per_mwh=raw_prediction, currency=request.currency),
    )


def _unique_lag_observation(
    history: tuple[MarketPriceRecord, ...],
    reference: datetime,
    *,
    missing_message: str,
    duplicate_message: str,
) -> MarketPriceRecord:
    matches = tuple(record for record in history if record.timestamp == reference)
    if len(matches) == 0:
        raise InvalidRequestError(missing_message)
    if len(matches) != 1:
        raise InvalidRequestError(duplicate_message)
    return matches[0]
