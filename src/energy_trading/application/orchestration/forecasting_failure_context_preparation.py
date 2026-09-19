"""Application-owned Phase 3 failure-policy context preparation.

This module composes already-published ExceptionGroup extraction,
tuple-level sanitized classification, and failure-context resolution
into one ``FailurePolicyContext``.

Ownership:

* Application: owns ``ForecastingFailureContextPreparationService``.
* Injected: ``ForecastingFailureContextResolutionService``.
* Existing ``extract_forecasting_agent_failures``: reused unchanged.
* Existing ``classify_forecasting_agent_failures``: reused unchanged.
* Policy decision, action execution, and graph routing remain deferred.

The service does not interpret exceptions, does not select among facts,
and does not invoke failure policy.
"""

from energy_trading.application.orchestration.failure_policy import FailurePolicyContext
from energy_trading.application.orchestration.forecasting_exception_group import (
    extract_forecasting_agent_failures,
)
from energy_trading.application.orchestration.forecasting_failure_classification import (
    classify_forecasting_agent_failures,
)
from energy_trading.application.orchestration.forecasting_failure_context_resolution import (
    ForecastingFailureContextResolutionService,
)
from energy_trading.application.orchestration.state import WorkflowPhase


class ForecastingFailureContextPreparationService:
    """Phase-3-specific composition of extraction, classification, and context.

    Constructor dependency is the published context-resolution service.
    ``prepare`` extracts attributed leaves, classifies them, then awaits
    context resolution.
    """

    def __init__(
        self,
        context_resolution_service: ForecastingFailureContextResolutionService,
    ) -> None:
        self._context_resolution_service = context_resolution_service

    async def prepare(
        self,
        *,
        workflow_id: str,
        phase: WorkflowPhase,
        error: BaseException,
    ) -> FailurePolicyContext:
        """Return a published failure-policy context from one exception.

        Extraction and tuple classification are delegated to the published
        helpers. Context resolution is awaited exactly once with the
        supplied workflow identity, phase, and classified facts.
        """

        extracted_failures = extract_forecasting_agent_failures(error)  # type: ignore[arg-type]
        classified_facts = classify_forecasting_agent_failures(extracted_failures)
        return await self._context_resolution_service.resolve(
            workflow_id=workflow_id,
            phase=phase,
            facts=classified_facts,
        )
