"""Application-owned Phase 3 tuple-level failure-fact classification.

This module classifies already-attributed ``ForecastingAgentFailure``
objects into sanitized ``ForecastingFailureFact`` values by delegating
each element to the existing one-leaf classifier. It does not select a
primary failure, inspect causal exceptions, or construct policy context.

Ownership:

* Application: owns ``classify_forecasting_agent_failures``.
* Existing ``classify_forecasting_agent_failure``: reused unchanged.
* Existing ``ForecastingAgentFailure``: reused unchanged as input.
* Existing ``ForecastingFailureFact``: reused unchanged as output.
* Multi-failure selection, attempt tracking, policy-context
  construction, policy/action handling, and graph routing remain deferred.

The composer does not duplicate error-code mapping.
"""

from energy_trading.application.orchestration.forecasting_agent_failure import (
    ForecastingAgentFailure,
)
from energy_trading.application.orchestration.forecasting_failure_fact import (
    ForecastingFailureFact,
    classify_forecasting_agent_failure,
)


def classify_forecasting_agent_failures(
    failures: tuple[ForecastingAgentFailure, ...],
) -> tuple[ForecastingFailureFact, ...]:
    """Return sanitized Phase 3 failure facts for already-attributed leaves.

    Each input element is classified independently by the existing one-leaf
    classifier. Encounter order, cardinality, and duplicate agent identities
    are preserved. An empty input yields an empty output.
    """

    return tuple(classify_forecasting_agent_failure(failure) for failure in failures)
