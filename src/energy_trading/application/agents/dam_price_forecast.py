"""DAM Price Forecast Agent application boundary.

This module is the eighth concrete application agent. It consumes the
already-published ``DAMPriceForecastModelRequest``, calls the injected
application model port once, and returns the exact canonical
``PriceForecastPoint`` tuple. Numerical forecasting, feature engineering,
currency conversion, and model files never enter here.

Ownership:

* Application: owns the concrete agent.
* Injected ``DAMPriceForecastModelPort``: supplies already-canonical
  forecast points from the published request.
* Future ML adapter: structurally implements that port. LightGBM/XGBoost,
  training, serialization, and feature pipelines remain outside this module.
* LangGraph, workflow context, persistence, retry, fallback, API composition,
  and Phase-3 routing remain deferred.

The agent satisfies ``AgentPort`` structurally. It does not inherit a base
class and is not registered in a factory. It does not calculate prices.
"""

from energy_trading.application.agents.base import AgentName
from energy_trading.application.ports.dam_price_forecast_model import (
    DAMPriceForecastModelPort,
    DAMPriceForecastModelRequest,
)
from energy_trading.domain.models.forecasting import PriceForecastPoint


class DAMPriceForecastAgent:
    """Thin application agent over the DAM Price Forecast model port.

    ``run`` awaits ``DAMPriceForecastModelPort.forecast`` exactly once
    with the supplied request and returns that tuple unchanged. It does not
    reconstruct points, convert currencies, fill missing intervals, retry,
    or call an LLM.
    """

    def __init__(self, model: DAMPriceForecastModelPort) -> None:
        self._model = model

    @property
    def name(self) -> AgentName:
        return AgentName.DAM_PRICE_FORECAST

    async def run(self, request: DAMPriceForecastModelRequest) -> tuple[PriceForecastPoint, ...]:
        return await self._model.forecast(request=request)
