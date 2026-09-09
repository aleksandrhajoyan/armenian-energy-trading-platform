"""Provider-aware document vector index object composition.

This module constructs the published OpenAI document-embedding and Qdrant
vector-index adapters from already created clients, then delegates
application wiring to ``build_document_vector_index_execution``. It does not
load settings, construct clients, or invoke embedding or indexing.

Ownership:

* API composition root: owns ``build_document_vector_index_provider_runtime``.
* Injected: ``AsyncOpenAI``.
* Injected: ``AsyncQdrantClient``.
* Injected: ``QdrantDocumentVectorConfig``.
* Injected: explicit document-embedding model string.
* Chunk 86 builder: owns application object composition.
* Client lifecycle, ``create_app()``, Regulatory runtime, LangGraph, and
  document extraction remain deferred.

The builder constructs objects only. It does not call provider or application
runtime methods.
"""

from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient

from energy_trading.api.composition.document_vector_index_execution import (
    build_document_vector_index_execution,
)
from energy_trading.application.orchestration.document_vector_index_execution import (
    DocumentVectorIndexExecutionService,
)
from energy_trading.infrastructure.embeddings.openai_document_embedding import (
    OpenAIDocumentEmbeddingAdapter,
)
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
    QdrantDocumentVectorIndex,
)


def build_document_vector_index_provider_runtime(
    *,
    openai_client: AsyncOpenAI,
    qdrant_client: AsyncQdrantClient,
    qdrant_config: QdrantDocumentVectorConfig,
    document_embedding_model: str,
) -> DocumentVectorIndexExecutionService:
    """Return a wired document vector index service from concrete providers.

    The clients, Qdrant vector configuration, and model string are already
    supplied. This function does not discover, configure, close, or invoke
    them.
    """

    document_embedding_port = OpenAIDocumentEmbeddingAdapter(
        client=openai_client,
        model=document_embedding_model,
    )
    document_vector_index_port = QdrantDocumentVectorIndex(
        qdrant_client,
        qdrant_config,
    )
    return build_document_vector_index_execution(
        document_embedding_port=document_embedding_port,
        document_vector_index_port=document_vector_index_port,
    )
