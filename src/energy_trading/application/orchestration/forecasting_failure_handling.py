"""Application-owned Phase 3 prepared failure-handling composition.

This module sequences an already-built ``FailurePolicyContext`` through
the published decision service and the published action executor.

Ownership:

* Application: owns ``ForecastingFailureHandlingService``.
* Injected service: ``ForecastingFailureDecisionService``.
* Existing ``execute_forecasting_failure_action``: owns action
  semantics.
* Context construction, raw exception capture, retry/fallback mechanics,
  and graph routing remain deferred.

The service does not construct policy context, does not branch on
``FailureAction``, and does not reimplement terminal transitions.
"""

from energy_trading.application.orchestration.failure_policy import FailurePolicyContext
from energy_trading.application.orchestration.forecasting_failure_action import (
    execute_forecasting_failure_action,
)
from energy_trading.application.orchestration.forecasting_failure_decision import (
    ForecastingFailureDecisionService,
)
from energy_trading.application.orchestration.state import WorkflowState


class ForecastingFailureHandlingService:
    """Phase-3-specific composition of failure decision then action execution.

    Constructor dependency is the published decision service. ``handle``
    awaits that service exactly once and forwards the returned action to
    the published executor without interpreting it.
    """

    def __init__(self, decision_service: ForecastingFailureDecisionService) -> None:
        self._decision_service = decision_service

    async def handle(
        self,
        *,
        state: WorkflowState,
        context: FailurePolicyContext,
    ) -> WorkflowState:
        """Decide then execute one already-prepared Phase 3 failure.

        The injected decision service is awaited exactly once with the
        supplied context. The returned action and supplied state are
        passed unchanged to ``execute_forecasting_failure_action``.
        """

        action = await self._decision_service.decide(context)
        return execute_forecasting_failure_action(state=state, action=action)
