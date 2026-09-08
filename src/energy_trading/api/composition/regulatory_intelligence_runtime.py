"""Provider-aware Regulatory Intelligence object composition.

This module constructs the published OpenAI and Qdrant adapters from already
created clients, then delegates application wiring to
``build_regulatory_intelligence_query_execution``. It does not load settings,
construct clients, or invoke provider operations.

Ownership:

* API composition root: owns ``build_regulatory_intelligence_provider_runtime``.
* Injected: ``AsyncOpenAI``.
* Injected: ``AsyncQdrantClient``.
* Injected: ``QdrantDocumentVectorConfig``.
* Injected: explicit query-embedding and constraint-inference model strings.
* Chunk 67 builder: owns application object composition.
* Client lifecycle, ``create_app()``, and LangGraph remain deferred.

The builder constructs objects only. It does not call provider or application
runtime methods.
"""

from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient

from energy_trading.api.composition.regulatory_intelligence import (
    build_regulatory_intelligence_query_execution,
)
from energy_trading.application.orchestration.regulatory_intelligence_query_execution import (
    RegulatoryIntelligenceQueryExecutionService,
)
from energy_trading.infrastructure.embeddings.openai_query_embedding import (
    OpenAIDocumentQueryEmbeddingAdapter,
)
from energy_trading.infrastructure.regulatory.openai_constraint_inference import (
    OpenAIRegulatoryConstraintInferenceAdapter,
)
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
    QdrantDocumentVectorSearch,
)


def build_regulatory_intelligence_provider_runtime(
    *,
    openai_client: AsyncOpenAI,
    qdrant_client: AsyncQdrantClient,
    qdrant_vector_config: QdrantDocumentVectorConfig,
    query_embedding_model: str,
    constraint_inference_model: str,
) -> RegulatoryIntelligenceQueryExecutionService:
    """Return a wired Regulatory Intelligence service from concrete providers.

    The clients, Qdrant vector configuration, and model strings are already
    supplied. This function does not discover, configure, close, or invoke
    them.
    """

    document_query_embedding_port = OpenAIDocumentQueryEmbeddingAdapter(
        client=openai_client,
        model=query_embedding_model,
    )
    document_vector_search_port = QdrantDocumentVectorSearch(
        qdrant_client,
        qdrant_vector_config,
    )
    regulatory_constraint_inference_port = OpenAIRegulatoryConstraintInferenceAdapter(
        client=openai_client,
        model=constraint_inference_model,
    )
    return build_regulatory_intelligence_query_execution(
        document_query_embedding_port=document_query_embedding_port,
        document_vector_search_port=document_vector_search_port,
        regulatory_constraint_inference_port=regulatory_constraint_inference_port,
    )
