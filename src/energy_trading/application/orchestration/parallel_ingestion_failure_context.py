"""Application-owned Phase 2 failure-policy context construction.

This module instantiates the published ``FailurePolicyContext`` from
already-sanitized typed failure facts supplied by the caller.

Ownership:

* Application: owns ``build_parallel_ingestion_failure_policy_context``.
* Existing ``FailurePolicyContext``: reused unchanged.
* Policy decision, action execution, terminal failure transition,
  exception capture, and graph routing remain deferred.

The function does not inspect exceptions, does not invent an agent
identity, and does not read ``WorkflowState``.
"""

from energy_trading.application.agents.base import AgentName
from energy_trading.application.orchestration.failure_policy import FailurePolicyContext
from energy_trading.application.orchestration.state import WorkflowPhase


def build_parallel_ingestion_failure_policy_context(
    *,
    phase: WorkflowPhase,
    error_code: str,
    attempt_number: int,
    agent_name: AgentName | None = None,
) -> FailurePolicyContext:
    """Return a published failure-policy context from typed caller facts.

    Keyword-only parameters match the published ``FailurePolicyContext``
    fields one-for-one. Existing constructor validation runs unchanged.
    ``agent_name`` keeps the published optional default of ``None``; this
    function does not choose an agent identity.
    """

    return FailurePolicyContext(
        phase=phase,
        error_code=error_code,
        attempt_number=attempt_number,
        agent_name=agent_name,
    )
