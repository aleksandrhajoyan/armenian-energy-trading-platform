"""Outer Phase 3 forecasting execution object composition.

This module wires caller-supplied application model ports into the two
already-published forecasting agents and the already-published concurrent
forecasting executor. It does not choose a model, load configuration,
construct providers, or invoke forecasting.

Ownership:

* API composition root: owns ``build_parallel_forecasting_execution_service``.
* Injected: ``ConsumerLoadForecastModelPort``.
* Injected: ``DAMPriceForecastModelPort``.
* Application: owns both forecasting agents and the parallel executor.
* Concrete model choice, workflow context, graph routing, and HTTP routes
  remain deferred.

The builder constructs objects only. It does not call application runtime
methods.
"""

from energy_trading.application.agents.consumer_load_forecast import ConsumerLoadForecastAgent
from energy_trading.application.agents.dam_price_forecast import DAMPriceForecastAgent
from energy_trading.application.orchestration.forecasting_executor import (
    ParallelForecastingExecutionService,
)
from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelPort,
)
from energy_trading.application.ports.dam_price_forecast_model import DAMPriceForecastModelPort


def build_parallel_forecasting_execution_service(
    *,
    consumer_load_model: ConsumerLoadForecastModelPort,
    dam_price_model: DAMPriceForecastModelPort,
) -> ParallelForecastingExecutionService:
    """Return a wired parallel forecasting execution service.

    The two arguments are already-constructed application model port
    implementations. This function does not discover, select, configure, or
    invoke them.
    """

    consumer_load_forecast = ConsumerLoadForecastAgent(consumer_load_model)
    dam_price_forecast = DAMPriceForecastAgent(dam_price_model)
    return ParallelForecastingExecutionService(
        consumer_load_forecast,
        dam_price_forecast,
    )
