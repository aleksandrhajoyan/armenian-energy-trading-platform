"""Outer Regulatory Intelligence object composition.

This module wires already-published application ports into already-published
application services and the Regulatory Intelligence Agent. It does not load
configuration, construct providers, or invoke retrieval or inference.

Ownership:

* API composition root: owns ``build_regulatory_intelligence_query_execution``.
* Injected: ``DocumentQueryEmbeddingPort``.
* Injected: ``DocumentVectorSearchPort``.
* Injected: ``RegulatoryConstraintInferencePort``.
* Application: owns query preparation, the agent, and query execution.
* Provider adapters, graph routing, and HTTP routes remain deferred.

The builder constructs objects only. It does not call application runtime
methods.
"""

from energy_trading.application.agents.regulatory_intelligence import RegulatoryIntelligenceAgent
from energy_trading.application.orchestration.document_vector_search_query_preparation import (
    DocumentVectorSearchQueryPreparationService,
)
from energy_trading.application.orchestration.regulatory_intelligence_query_execution import (
    RegulatoryIntelligenceQueryExecutionService,
)
from energy_trading.application.ports.document_query_embedding import DocumentQueryEmbeddingPort
from energy_trading.application.ports.document_vector_search import DocumentVectorSearchPort
from energy_trading.application.ports.regulatory_constraint_inference import (
    RegulatoryConstraintInferencePort,
)


def build_regulatory_intelligence_query_execution(
    *,
    document_query_embedding_port: DocumentQueryEmbeddingPort,
    document_vector_search_port: DocumentVectorSearchPort,
    regulatory_constraint_inference_port: RegulatoryConstraintInferencePort,
) -> RegulatoryIntelligenceQueryExecutionService:
    """Return a wired Regulatory Intelligence query-execution service.

    The three arguments are already-constructed application port
    implementations. This function does not discover, configure, or invoke
    them.
    """

    query_preparation_service = DocumentVectorSearchQueryPreparationService(
        document_query_embedding_port
    )
    regulatory_intelligence_agent = RegulatoryIntelligenceAgent(
        search=document_vector_search_port,
        inference=regulatory_constraint_inference_port,
    )
    return RegulatoryIntelligenceQueryExecutionService(
        query_preparation_service,
        regulatory_intelligence_agent,
    )
