"""Consumer Load Forecast Agent application boundary.

This module is the seventh concrete application agent. It consumes the
already-published ``ConsumerLoadForecastModelRequest``, calls the injected
application model port once, and returns the exact canonical
``LoadForecastPoint`` tuple. Numerical forecasting, feature engineering,
and model files never enter here.

Ownership:

* Application: owns the concrete agent.
* Injected ``ConsumerLoadForecastModelPort``: supplies already-canonical
  forecast points from the published request.
* Future ML adapter: structurally implements that port. LightGBM/XGBoost,
  training, serialization, and feature pipelines remain outside this module.
* LangGraph, workflow context, persistence, retry, fallback, API composition,
  and Phase-3 routing remain deferred.

The agent satisfies ``AgentPort`` structurally. It does not inherit a base
class and is not registered in a factory. It does not calculate forecasts.
"""

from energy_trading.application.agents.base import AgentName
from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelPort,
    ConsumerLoadForecastModelRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint


class ConsumerLoadForecastAgent:
    """Thin application agent over the Consumer Load Forecast model port.

    ``run`` awaits ``ConsumerLoadForecastModelPort.forecast`` exactly once
    with the supplied request and returns that tuple unchanged. It does not
    reconstruct points, convert MW, fill missing intervals, retry, or call
    an LLM.
    """

    def __init__(self, model: ConsumerLoadForecastModelPort) -> None:
        self._model = model

    @property
    def name(self) -> AgentName:
        return AgentName.CONSUMER_LOAD_FORECAST

    async def run(self, request: ConsumerLoadForecastModelRequest) -> tuple[LoadForecastPoint, ...]:
        return await self._model.forecast(request=request)
