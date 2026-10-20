"""Outer Phase 3 forecasting failure-runtime object composition.

This module wires a caller-supplied failure-fact selection port, a
caller-supplied attempt-number source, and a caller-supplied failure policy
into the already-published Phase 3 failure-handling services, ending in one
``ForecastingFailureRuntimeHandlingService``. It does not choose a selector,
attempt source, or policy, load configuration, or handle any failure.

Ownership:

* API composition root: owns ``build_forecasting_failure_runtime_handler``.
* Injected: ``ForecastingFailureSelectionPort``.
* Injected: ``ForecastingAttemptNumberPort``.
* Injected: ``FailurePolicyPort``.
* Application: owns the context-resolution, context-preparation, decision,
  handling, and runtime-handling services and all failure semantics.
* Concrete selector, attempt tracking, policy choice, retry/fallback, graph
  routing, and HTTP routes remain deferred.

The builder constructs objects only. It does not call application runtime
methods.
"""

from energy_trading.application.orchestration.failure_policy import FailurePolicyPort
from energy_trading.application.orchestration.forecasting_attempt_number import (
    ForecastingAttemptNumberPort,
)
from energy_trading.application.orchestration.forecasting_failure_context_preparation import (
    ForecastingFailureContextPreparationService,
)
from energy_trading.application.orchestration.forecasting_failure_context_resolution import (
    ForecastingFailureContextResolutionService,
)
from energy_trading.application.orchestration.forecasting_failure_decision import (
    ForecastingFailureDecisionService,
)
from energy_trading.application.orchestration.forecasting_failure_handling import (
    ForecastingFailureHandlingService,
)
from energy_trading.application.orchestration.forecasting_failure_runtime_handling import (
    ForecastingFailureRuntimeHandlingService,
)
from energy_trading.application.orchestration.forecasting_failure_selection import (
    ForecastingFailureSelectionPort,
)


def build_forecasting_failure_runtime_handler(
    *,
    selector: ForecastingFailureSelectionPort,
    attempt_number_source: ForecastingAttemptNumberPort,
    policy: FailurePolicyPort,
) -> ForecastingFailureRuntimeHandlingService:
    """Return a wired Phase 3 failure runtime handler.

    The three arguments are already-constructed application port
    implementations. This function does not discover, select, configure, or
    invoke them, and the caller keeps ownership of their lifetime.
    """

    context_resolution_service = ForecastingFailureContextResolutionService(
        selector,
        attempt_number_source,
    )
    context_preparation_service = ForecastingFailureContextPreparationService(
        context_resolution_service,
    )
    decision_service = ForecastingFailureDecisionService(policy)
    failure_handling_service = ForecastingFailureHandlingService(decision_service)
    return ForecastingFailureRuntimeHandlingService(
        context_preparation_service,
        failure_handling_service,
    )
