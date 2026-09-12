"""Application-owned Phase 3 forecasting workflow step.

This module composes the already-published context and execution
boundaries into one framework-neutral application service.

Ownership:

* Application: owns ``ForecastingWorkflowStep``.
* Injected ports: ``ForecastingWorkflowContextPort`` and
  ``ForecastingExecutionPort``.
* Graph runtime, concrete executor, context storage, phase/status
  transition, retry, fallback, degraded mode, and API composition
  remain deferred.

The step does not inherit a base class. It does not implement storage
and does not change ``WorkflowState``.
"""

from energy_trading.application.orchestration.forecasting_context import (
    ForecastingWorkflowContextPort,
)
from energy_trading.application.orchestration.forecasting_execution import (
    ForecastingExecutionPort,
)
from energy_trading.application.orchestration.state import WorkflowState


class ForecastingWorkflowStep:
    """Framework-neutral Phase 3 forecasting workflow composition.

    Constructor dependencies are the published context and execution
    ports. ``run`` resolves a prepared plan, executes it, records the
    all-two-success aggregate, and returns the original workflow state
    unchanged.
    """

    def __init__(
        self,
        context: ForecastingWorkflowContextPort,
        executor: ForecastingExecutionPort,
    ) -> None:
        self._context = context
        self._executor = executor

    async def run(self, state: WorkflowState) -> WorkflowState:
        """Resolve, execute, and record Phase 3 forecasting for ``state``.

        Failures propagate naturally. The original ``WorkflowState``
        object is returned unchanged.
        """

        plan = await self._context.resolve_plan(state=state)
        success = await self._executor.execute(plan=plan)
        await self._context.record_success(state=state, success=success)
        return state
