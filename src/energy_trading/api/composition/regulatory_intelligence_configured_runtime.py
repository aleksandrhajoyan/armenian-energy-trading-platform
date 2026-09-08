"""Configured Regulatory Intelligence object composition.

This module translates already-constructed
``RegulatoryIntelligenceRuntimeSettings`` into the explicit arguments required
by ``build_regulatory_intelligence_provider_runtime``. It does not load
environment values, construct clients, or invoke provider operations.

Ownership:

* API composition root: owns ``build_regulatory_intelligence_configured_runtime``.
* Injected: ``AsyncOpenAI``.
* Injected: ``AsyncQdrantClient``.
* Injected: ``RegulatoryIntelligenceRuntimeSettings``.
* Chunk 71 builder: owns provider adapter construction.
* Chunk 67 builder: owns application object composition.
* Client lifecycle, settings loading, ``create_app()``, and LangGraph remain
  deferred.

The builder constructs a Qdrant vector config and delegates. It does not call
provider or application runtime methods.
"""

from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient

from energy_trading.api.composition.regulatory_intelligence_runtime import (
    build_regulatory_intelligence_provider_runtime,
)
from energy_trading.application.orchestration.regulatory_intelligence_query_execution import (
    RegulatoryIntelligenceQueryExecutionService,
)
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
)
from energy_trading.shared.config.regulatory_intelligence import (
    RegulatoryIntelligenceRuntimeSettings,
)


def build_regulatory_intelligence_configured_runtime(
    *,
    openai_client: AsyncOpenAI,
    qdrant_client: AsyncQdrantClient,
    settings: RegulatoryIntelligenceRuntimeSettings,
) -> RegulatoryIntelligenceQueryExecutionService:
    """Return a wired Regulatory Intelligence service from clients and settings.

    The clients and Regulatory runtime settings are already supplied. This
    function does not discover, load, close, or invoke them.
    """

    qdrant_vector_config = QdrantDocumentVectorConfig(
        collection_name=settings.qdrant_collection_name,
        vector_size=settings.qdrant_vector_size,
    )
    return build_regulatory_intelligence_provider_runtime(
        openai_client=openai_client,
        qdrant_client=qdrant_client,
        qdrant_vector_config=qdrant_vector_config,
        query_embedding_model=settings.query_embedding_model,
        constraint_inference_model=settings.constraint_inference_model,
    )
