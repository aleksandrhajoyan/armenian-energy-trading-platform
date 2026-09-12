"""Application-owned Regulatory Intelligence workflow-step seam.

This module is the typed orchestration boundary through which future
workflow code can invoke Regulatory Intelligence. It does
not construct the query-execution service and does not know providers.

Ownership:

* Application: owns ``RegulatoryIntelligenceWorkflowRequest`` and
  ``RegulatoryIntelligenceWorkflowStep``.
* Injected: already-constructed ``RegulatoryIntelligenceQueryExecutionService``.
* Existing ``RegulatoryIntelligenceResult``: reused unchanged.
* Existing ``AgentPort``: satisfied structurally. There is no new port.
* Existing ``AgentName.REGULATORY_INTELLIGENCE``: reused unchanged.
* Provider clients, settings, API composition, collection readiness,
  graph topology, and ``WorkflowState`` result slots remain deferred.

The step does not inherit a base class.
"""

from dataclasses import dataclass

from energy_trading.application.agents.base import AgentName
from energy_trading.application.agents.regulatory_intelligence import (
    RegulatoryIntelligenceResult,
)
from energy_trading.application.orchestration.regulatory_intelligence_query_execution import (
    RegulatoryIntelligenceQueryExecutionService,
)


@dataclass(frozen=True, slots=True)
class RegulatoryIntelligenceWorkflowRequest:
    """Immutable orchestration request: query text plus an explicit limit.

    This is an application DTO, not a domain entity and not a workflow
    snapshot. It carries no provider, model, collection, credential, or
    runtime fields. Limit and query-text validation remain owned by the
    injected query-execution path.
    """

    query_text: str
    limit: int


class RegulatoryIntelligenceWorkflowStep:
    """Thin AgentPort-compatible seam over Regulatory query execution.

    Constructor dependency is the published query-execution service.
    ``run`` awaits ``execute`` exactly once with the request fields and
    returns that ``RegulatoryIntelligenceResult`` unchanged.
    """

    def __init__(
        self,
        query_execution_service: RegulatoryIntelligenceQueryExecutionService,
    ) -> None:
        self._query_execution_service = query_execution_service

    @property
    def name(self) -> AgentName:
        return AgentName.REGULATORY_INTELLIGENCE

    async def run(
        self,
        request: RegulatoryIntelligenceWorkflowRequest,
    ) -> RegulatoryIntelligenceResult:
        """Delegate the typed request to the injected query-execution service.

        Failures propagate with their original identity. The returned
        result is the object produced by the service.
        """

        return await self._query_execution_service.execute(
            query_text=request.query_text,
            limit=request.limit,
        )
