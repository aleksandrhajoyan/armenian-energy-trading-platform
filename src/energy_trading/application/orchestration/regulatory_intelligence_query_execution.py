"""Application-owned Regulatory Intelligence query execution.

This module composes already-published query preparation with the existing
Regulatory Intelligence Agent. Callers supply normalized query text and an
explicit search limit. The service does not embed, search, or infer.

Ownership:

* Application: owns ``RegulatoryIntelligenceQueryExecutionService``.
* Injected: ``DocumentVectorSearchQueryPreparationService``.
* Injected: ``RegulatoryIntelligenceAgent``.
* Existing ``RegulatoryIntelligenceRequest`` / ``RegulatoryIntelligenceResult``:
  reused unchanged.
* Embedding providers, vector-database adapters, inference providers, graph
  routing, and API composition remain deferred.

The service does not rewrite query text, clamp limits, or reconstruct results.
"""

from energy_trading.application.agents.regulatory_intelligence import (
    RegulatoryIntelligenceAgent,
    RegulatoryIntelligenceRequest,
    RegulatoryIntelligenceResult,
)
from energy_trading.application.orchestration.document_vector_search_query_preparation import (
    DocumentVectorSearchQueryPreparationService,
)


class RegulatoryIntelligenceQueryExecutionService:
    """Compose query text plus a limit through preparation into the agent.

    Constructor dependencies are the published query-preparation service and
    the published Regulatory Intelligence Agent. ``execute`` awaits
    preparation exactly once, constructs ``RegulatoryIntelligenceRequest``,
    and awaits ``run`` exactly once.
    """

    def __init__(
        self,
        query_preparation_service: DocumentVectorSearchQueryPreparationService,
        regulatory_intelligence_agent: RegulatoryIntelligenceAgent,
    ) -> None:
        self._query_preparation_service = query_preparation_service
        self._regulatory_intelligence_agent = regulatory_intelligence_agent

    async def execute(
        self,
        *,
        query_text: str,
        limit: int,
    ) -> RegulatoryIntelligenceResult:
        """Return the agent's result for query text and an explicit limit.

        Query text and limit are forwarded unchanged to query preparation.
        The returned result is the object produced by the agent.
        """

        prepared_query = await self._query_preparation_service.prepare(
            query_text=query_text,
            limit=limit,
        )
        request = RegulatoryIntelligenceRequest(search_query=prepared_query)
        return await self._regulatory_intelligence_agent.run(request)
