"""Application-owned Phase 3 runtime failure-handling composition.

This module sequences an already-observed ``BaseExceptionGroup`` through
the published failure-context preparation service and the published
prepared failure-handling service.

Ownership:

* Application: owns ``ForecastingFailureRuntimeHandlingService``.
* Injected: ``ForecastingFailureContextPreparationService``.
* Injected: ``ForecastingFailureHandlingService``.
* Existing preparation, decision, action, and transition modules remain
  the owners of their respective semantics.
* Graph routing remains deferred.

The service does not inspect exception groups, does not decide a
policy action, and does not reimplement terminal transitions.
"""

from energy_trading.application.orchestration.forecasting_failure_context_preparation import (  # noqa: E501
    ForecastingFailureContextPreparationService,
)
from energy_trading.application.orchestration.forecasting_failure_handling import (
    ForecastingFailureHandlingService,
)
from energy_trading.application.orchestration.state import WorkflowState


class ForecastingFailureRuntimeHandlingService:
    """Phase-3-specific composition of failure-context preparation then handling.

    Constructor dependencies are the published preparation and handling
    services. ``handle`` prepares context from the current snapshot and
    failure group, then forwards that context plus the original state.
    """

    def __init__(
        self,
        context_preparation_service: ForecastingFailureContextPreparationService,
        failure_handling_service: ForecastingFailureHandlingService,
    ) -> None:
        self._context_preparation_service = context_preparation_service
        self._failure_handling_service = failure_handling_service

    async def handle(
        self,
        *,
        state: WorkflowState,
        failure_group: BaseExceptionGroup,
    ) -> WorkflowState:
        """Prepare then handle one Phase 3 exception group against ``state``.

        Context preparation is awaited exactly once with ``state.workflow_id``,
        ``state.phase``, and the supplied group as ``error``. The returned
        context and the original ``state`` are forwarded unchanged to the
        handling service.
        """

        context = await self._context_preparation_service.prepare(
            workflow_id=state.workflow_id,
            phase=state.phase,
            error=failure_group,
        )
        return await self._failure_handling_service.handle(state=state, context=context)
