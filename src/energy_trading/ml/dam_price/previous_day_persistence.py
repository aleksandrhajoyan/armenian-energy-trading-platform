"""Exact previous-day persistence DAM Price Forecast baseline.

This outer ML adapter structurally implements
``DAMPriceForecastModelPort``. It copies canonical ``EnergyPrice`` from the
unique history observation at ``T - 24 hours`` and does not train a model.

Ownership:

* Application: owns ``DAMPriceForecastModelPort`` and
  ``DAMPriceForecastModelRequest``.
* ML: owns this deterministic baseline. It is a benchmark/reference
  implementation, not a production-trained champion model and not an
  Armenia-specific market-behavior claim.
* Identity fields are caller-supplied. This module does not invent
  ``forecast_run_id``, ``generated_at``, clocks, or UUIDs.
* Missing or duplicate exact lag observations fail closed with existing
  ``InvalidRequestError``. There is no nearest-neighbor, interpolation,
  weekly fallback, market-session inference, or partial success.

The adapter remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from datetime import datetime, timedelta

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.ports.dam_price_forecast_model import (
    DAMPriceForecastModelRequest,
)
from energy_trading.domain.models.forecasting import PriceForecastPoint
from energy_trading.domain.models.observations import MarketPriceRecord

_LAG = timedelta(hours=24)
_MISSING_LAG_MESSAGE = (
    "Previous-day persistence requires exactly one history observation at the 24-hour lag."
)
_DUPLICATE_LAG_MESSAGE = "Previous-day persistence requires a unique 24-hour lag observation."


class PreviousDayPersistenceDAMPriceForecastModel:
    """Copy price from the unique exact ``T - 24h`` history observation."""

    async def forecast(
        self,
        *,
        request: DAMPriceForecastModelRequest,
    ) -> tuple[PriceForecastPoint, ...]:
        """Return canonical price points in requested target order."""

        return tuple(_point_for_target(request, target) for target in request.target_timestamps)


def _point_for_target(
    request: DAMPriceForecastModelRequest,
    target: datetime,
) -> PriceForecastPoint:
    matching_record = _unique_lag_observation(request.history, target - _LAG)
    return PriceForecastPoint(
        forecast_run_id=request.forecast_run_id,
        market_id=request.market_id,
        generated_at=request.generated_at,
        target_timestamp=target,
        price=matching_record.price,
    )


def _unique_lag_observation(
    history: tuple[MarketPriceRecord, ...],
    reference: datetime,
) -> MarketPriceRecord:
    matches = tuple(record for record in history if record.timestamp == reference)
    if len(matches) == 0:
        raise InvalidRequestError(_MISSING_LAG_MESSAGE)
    if len(matches) != 1:
        raise InvalidRequestError(_DUPLICATE_LAG_MESSAGE)
    return matches[0]
