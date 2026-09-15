"""Exact previous-day persistence Consumer Load Forecast baseline.

This outer ML adapter structurally implements
``ConsumerLoadForecastModelPort``. It copies canonical MW from the unique
history observation at ``T - 24 hours`` and does not train a model.

Ownership:

* Application: owns ``ConsumerLoadForecastModelPort`` and
  ``ConsumerLoadForecastModelRequest``.
* ML: owns this deterministic baseline. It is a benchmark/reference
  implementation, not a production-trained champion model.
* Identity fields are caller-supplied. This module does not invent
  ``forecast_run_id``, ``generated_at``, clocks, or UUIDs.
* Missing or duplicate exact lag observations fail closed with existing
  ``InvalidRequestError``. There is no nearest-neighbor, interpolation,
  weekly fallback, or partial success.

The adapter remains unwired from agents, API composition, FastAPI,
LangGraph, and ``ForecastingExecutionPort``.
"""

from datetime import datetime, timedelta

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint
from energy_trading.domain.models.observations import ConsumptionRecord

_LAG = timedelta(hours=24)
_MISSING_LAG_MESSAGE = (
    "Previous-day persistence requires exactly one history observation at the 24-hour lag."
)
_DUPLICATE_LAG_MESSAGE = "Previous-day persistence requires a unique 24-hour lag observation."


class PreviousDayPersistenceConsumerLoadForecastModel:
    """Copy MW from the unique exact ``T - 24h`` history observation."""

    async def forecast(
        self,
        *,
        request: ConsumerLoadForecastModelRequest,
    ) -> tuple[LoadForecastPoint, ...]:
        """Return canonical MW points in requested target order."""

        return tuple(_point_for_target(request, target) for target in request.target_timestamps)


def _point_for_target(
    request: ConsumerLoadForecastModelRequest,
    target: datetime,
) -> LoadForecastPoint:
    matching_record = _unique_lag_observation(request.history, target - _LAG)
    return LoadForecastPoint(
        forecast_run_id=request.forecast_run_id,
        consumer_id=request.consumer_id,
        generated_at=request.generated_at,
        target_timestamp=target,
        value_mw=matching_record.value_mw,
    )


def _unique_lag_observation(
    history: tuple[ConsumptionRecord, ...],
    reference: datetime,
) -> ConsumptionRecord:
    matches = tuple(record for record in history if record.timestamp == reference)
    if len(matches) == 0:
        raise InvalidRequestError(_MISSING_LAG_MESSAGE)
    if len(matches) != 1:
        raise InvalidRequestError(_DUPLICATE_LAG_MESSAGE)
    return matches[0]
