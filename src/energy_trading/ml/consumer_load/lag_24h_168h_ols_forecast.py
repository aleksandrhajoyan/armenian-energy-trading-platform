"""Lag-24h plus lag-168h OLS Consumer Load Forecast candidate adapter.

This outer ML adapter structurally implements
``ConsumerLoadForecastModelPort``. It applies already-fitted Chunk 143
two-feature OLS parameters to exact ``T - 24h`` and ``T - 168h`` history
observations. It does not fit, retrain, or select a production model.

Ownership:

* Application: owns ``ConsumerLoadForecastModelPort`` and
  ``ConsumerLoadForecastModelRequest``. Canonical live output remains
  ``LoadForecastPoint.value_mw: NonNegativeMW``.
* ML: owns this candidate numerical implementation. Offline Chunk 144
  signed-finite predictions remain valid experimental evidence and are
  not the live output type.
* Identity fields are caller-supplied. This module does not invent
  ``forecast_run_id``, ``generated_at``, clocks, or UUIDs.
* Missing or duplicate exact lag observations fail closed. A non-finite
  or negative finite raw prediction fails closed with existing
  ``InvalidRequestError`` before ``LoadForecastPoint`` construction.
  There is no clamping, absolute-value repair, nearest-neighbor,
  interpolation, persistence fallback, or partial success.

The adapter remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from datetime import datetime, timedelta
from math import isfinite

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint
from energy_trading.domain.models.observations import ConsumptionRecord
from energy_trading.ml.consumer_load.lag_24h_168h_linear_regression import (
    ConsumerLoadLag24h168hLinearRegressionFit,
)

_LAG_24H = timedelta(hours=24)
_LAG_168H = timedelta(hours=168)
_MISSING_LAG_24H_MESSAGE = (
    "Consumer Load trained OLS live inference requires exactly one history "
    "observation at the 24-hour lag."
)
_MISSING_LAG_168H_MESSAGE = (
    "Consumer Load trained OLS live inference requires exactly one history "
    "observation at the 168-hour lag."
)
_DUPLICATE_LAG_24H_MESSAGE = (
    "Consumer Load trained OLS live inference requires a unique 24-hour lag observation."
)
_DUPLICATE_LAG_168H_MESSAGE = (
    "Consumer Load trained OLS live inference requires a unique 168-hour lag observation."
)
_NON_FINITE_FIT_MESSAGE = (
    "Consumer Load trained OLS live inference requires finite fitted coefficients and intercept."
)
_NON_FINITE_PREDICTION_MESSAGE = (
    "Consumer Load trained OLS live inference requires a finite forecast value."
)
_NEGATIVE_PREDICTION_MESSAGE = (
    "Consumer Load trained OLS live inference requires a non-negative forecast value."
)


class Lag24h168hOLSConsumerLoadForecastModel:
    """Apply already-fitted two-feature OLS parameters to exact lag evidence."""

    def __init__(self, *, fit: ConsumerLoadLag24h168hLinearRegressionFit) -> None:
        _require_finite_fit(fit)
        self._fit = fit

    async def forecast(
        self,
        *,
        request: ConsumerLoadForecastModelRequest,
    ) -> tuple[LoadForecastPoint, ...]:
        """Return canonical MW points in requested target order."""

        return tuple(
            _point_for_target(self._fit, request, target) for target in request.target_timestamps
        )


def _require_finite_fit(fit: ConsumerLoadLag24h168hLinearRegressionFit) -> None:
    if (
        not isfinite(fit.lag_24h_coefficient)
        or not isfinite(fit.lag_168h_coefficient)
        or not isfinite(fit.intercept_mw)
    ):
        raise InvalidRequestError(_NON_FINITE_FIT_MESSAGE)


def _point_for_target(
    fit: ConsumerLoadLag24h168hLinearRegressionFit,
    request: ConsumerLoadForecastModelRequest,
    target: datetime,
) -> LoadForecastPoint:
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
    predicted_value_mw = (
        fit.intercept_mw
        + fit.lag_24h_coefficient * lag_24h.value_mw
        + fit.lag_168h_coefficient * lag_168h.value_mw
    )
    if not isfinite(predicted_value_mw):
        raise InvalidRequestError(_NON_FINITE_PREDICTION_MESSAGE)
    if predicted_value_mw < 0:
        raise InvalidRequestError(_NEGATIVE_PREDICTION_MESSAGE)
    return LoadForecastPoint(
        forecast_run_id=request.forecast_run_id,
        consumer_id=request.consumer_id,
        generated_at=request.generated_at,
        target_timestamp=target,
        value_mw=predicted_value_mw,
    )


def _unique_lag_observation(
    history: tuple[ConsumptionRecord, ...],
    reference: datetime,
    *,
    missing_message: str,
    duplicate_message: str,
) -> ConsumptionRecord:
    matches = tuple(record for record in history if record.timestamp == reference)
    if len(matches) == 0:
        raise InvalidRequestError(missing_message)
    if len(matches) != 1:
        raise InvalidRequestError(duplicate_message)
    return matches[0]
