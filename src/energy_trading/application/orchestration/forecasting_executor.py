"""Application-owned concurrent Phase 3 forecasting executor.

This module is the first concrete implementation of
``ForecastingExecutionPort``. It injects the two existing Phase 3
application agents, runs them concurrently with ``asyncio.TaskGroup``,
and returns ``ForecastingSuccess`` only when both branches succeed.

When a branch raises an ordinary ``Exception``, the executor wraps that
failure as ``ForecastingAgentFailure`` with the canonical ``AgentName``
for that branch. Sibling ``TaskGroup`` cancellation is not reclassified
as a forecast-agent failure. This executor does not record workflow
context or apply a forecasting transition.

Ownership:

* Application: owns ``ParallelForecastingExecutionService``.
* Existing agents: invoked through their published ``run`` methods.
* Existing contracts: ``ForecastingPlan`` and ``ForecastingSuccess`` are
  reused unchanged.
* Graph runtime, workflow context, retry policy, model selection,
  persistence, and API composition remain deferred.

The executor satisfies ``ForecastingExecutionPort`` structurally. It does
not inherit a base class.
"""

import asyncio
from collections.abc import Awaitable

from energy_trading.application.agents.base import AgentName
from energy_trading.application.agents.consumer_load_forecast import ConsumerLoadForecastAgent
from energy_trading.application.agents.dam_price_forecast import DAMPriceForecastAgent
from energy_trading.application.orchestration.forecasting_agent_failure import (
    ForecastingAgentFailure,
)
from energy_trading.application.orchestration.forecasting_plan import ForecastingPlan
from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess


class ParallelForecastingExecutionService:
    """Concurrent all-success executor for Consumer Load and DAM forecasts.

    Constructor dependencies are the two concrete application agents. The
    executor does not own model adapters, graph runtime, or workflow
    context. Native ``asyncio.TaskGroup`` cancellation and exception
    propagation apply when a branch raises. Attribution is added only for
    ordinary agent execution failures.
    """

    def __init__(
        self,
        consumer_load_forecast: ConsumerLoadForecastAgent,
        dam_price_forecast: DAMPriceForecastAgent,
    ) -> None:
        self._consumer_load_forecast = consumer_load_forecast
        self._dam_price_forecast = dam_price_forecast

    async def execute(self, *, plan: ForecastingPlan) -> ForecastingSuccess:
        """Run both plan branches concurrently and return the success aggregate.

        Both tasks are created before the ``TaskGroup`` context waits for
        completion. ``ForecastingSuccess`` is constructed only after every
        branch has returned its existing canonical tuple.
        """

        async with asyncio.TaskGroup() as group:
            consumer_task = group.create_task(
                self._run_attributed(
                    AgentName.CONSUMER_LOAD_FORECAST,
                    self._consumer_load_forecast.run(plan.consumer_load_request),
                )
            )
            dam_task = group.create_task(
                self._run_attributed(
                    AgentName.DAM_PRICE_FORECAST,
                    self._dam_price_forecast.run(plan.dam_price_request),
                )
            )
        return ForecastingSuccess(
            consumer_load_forecast=consumer_task.result(),
            dam_price_forecast=dam_task.result(),
        )

    async def _run_attributed[T](self, agent_name: AgentName, operation: Awaitable[T]) -> T:
        """Await one agent ``run`` and attribute ordinary failures to ``agent_name``.

        ``asyncio.CancelledError`` is a ``BaseException`` and is not wrapped.
        """

        try:
            return await operation
        except Exception as exc:
            raise ForecastingAgentFailure(agent_name) from exc
