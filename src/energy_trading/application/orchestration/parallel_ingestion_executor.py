"""Application-owned concurrent Phase 2 ingestion executor.

This module is the first concrete implementation of
``ParallelIngestionExecutionPort``. It injects the five existing Phase 2
application agents, runs them concurrently with ``asyncio.TaskGroup``, and
returns ``ParallelIngestionSuccess`` only when all five branches succeed.

Ownership:

* Application: owns ``ConcurrentParallelIngestionExecutor``.
* Existing agents: invoked through their published ``run`` methods.
* Existing contracts: ``ParallelIngestionPlan`` and
  ``ParallelIngestionSuccess`` are reused unchanged.
* Graph runtime, failure-policy execution, retry, fallback, degraded mode,
  persistence, and API composition remain deferred.

The executor satisfies ``ParallelIngestionExecutionPort`` structurally. It
does not inherit a base class.
"""

import asyncio

from energy_trading.application.agents.generation_availability import GenerationAvailabilityAgent
from energy_trading.application.agents.hydro_resources import HydroResourcesAgent
from energy_trading.application.agents.market_monitoring import MarketMonitoringAgent
from energy_trading.application.agents.news_intelligence import NewsIntelligenceAgent
from energy_trading.application.agents.weather_and_renewable_forecast import (
    WeatherAndRenewableForecastAgent,
)
from energy_trading.application.orchestration.parallel_ingestion import (
    ParallelIngestionPlan,
    ParallelIngestionSuccess,
)


class ConcurrentParallelIngestionExecutor:
    """Concurrent all-success executor for the five Phase 2 ingestion agents.

    Constructor dependencies are the five concrete application agents. The
    executor does not own source adapters, graph runtime, or failure policy.
    Native ``asyncio.TaskGroup`` cancellation and exception propagation apply
    when a branch raises.
    """

    def __init__(
        self,
        weather_and_renewable_forecast: WeatherAndRenewableForecastAgent,
        hydro_resources: HydroResourcesAgent,
        generation_availability: GenerationAvailabilityAgent,
        news_intelligence: NewsIntelligenceAgent,
        market_monitoring: MarketMonitoringAgent,
    ) -> None:
        self._weather_and_renewable_forecast = weather_and_renewable_forecast
        self._hydro_resources = hydro_resources
        self._generation_availability = generation_availability
        self._news_intelligence = news_intelligence
        self._market_monitoring = market_monitoring

    async def execute(self, plan: ParallelIngestionPlan) -> ParallelIngestionSuccess:
        """Run all five plan branches concurrently and return the success aggregate.

        All five tasks are created before the ``TaskGroup`` context waits for
        completion. ``ParallelIngestionSuccess`` is constructed only after every
        branch has returned its existing typed result DTO.
        """

        async with asyncio.TaskGroup() as group:
            weather_task = group.create_task(
                self._weather_and_renewable_forecast.run(plan.weather_and_renewable_forecast)
            )
            hydro_task = group.create_task(self._hydro_resources.run(plan.hydro_resources))
            generation_task = group.create_task(
                self._generation_availability.run(plan.generation_availability)
            )
            news_task = group.create_task(self._news_intelligence.run(plan.news_intelligence))
            market_task = group.create_task(self._market_monitoring.run(plan.market_monitoring))
        return ParallelIngestionSuccess(
            weather_and_renewable_forecast=weather_task.result(),
            hydro_resources=hydro_task.result(),
            generation_availability=generation_task.result(),
            news_intelligence=news_task.result(),
            market_monitoring=market_task.result(),
        )
