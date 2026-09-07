"""Application-owned Phase 2 agent-failure attribution.

This module preserves canonical ``AgentName`` identity when one concurrent
Phase 2 agent execution fails. The original Python exception remains the
causal failure through standard exception chaining.

Ownership:

* Application: owns ``ParallelIngestionAgentFailure``.
* Existing ``AgentName``: reused unchanged as the only constructor input.
* Original exception: retained only through standard exception chaining after
  ``raise ... from exc``.
* TaskGroup aggregation, error-code mapping, policy context construction,
  and graph routing remain deferred.

This is not a generic orchestration-failure hierarchy and is not a field on
``WorkflowState``.
"""

from energy_trading.application.agents.base import AgentName

_MESSAGE_TEMPLATE = "Parallel ingestion agent failed: {agent_name}."


def _require_agent_name(value: object) -> AgentName:
    if not isinstance(value, AgentName):
        msg = "agent_name must be an AgentName"
        raise TypeError(msg)
    return value


class ParallelIngestionAgentFailure(Exception):
    """Sanitized attribution wrapper for one failed Phase 2 agent task.

    Constructor input is only the canonical ``AgentName``. The outward
    message identifies that agent and does not include the original
    exception text or payload.
    """

    def __init__(self, agent_name: AgentName) -> None:
        resolved = _require_agent_name(agent_name)
        self.agent_name = resolved
        super().__init__(_MESSAGE_TEMPLATE.format(agent_name=resolved.value))
