"""Configured document vector index object composition.

This module translates already-constructed
``DocumentVectorIndexRuntimeSettings`` into the explicit arguments required
by ``build_document_vector_index_provider_runtime``. It does not load
environment values, construct clients, or invoke provider operations.

Ownership:

* API composition root: owns ``build_document_vector_index_configured_runtime``.
* Injected: ``AsyncOpenAI``.
* Injected: ``AsyncQdrantClient``.
* Injected: ``DocumentVectorIndexRuntimeSettings``.
* Chunk 87 builder: owns provider adapter construction.
* Chunk 86 builder: owns application object composition.
* Client lifecycle, settings loading, ``create_app()``, and LangGraph remain
  deferred.

The builder constructs a Qdrant vector config and delegates. It does not call
provider or application runtime methods.
"""

from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient

from energy_trading.api.composition.document_vector_index_runtime import (
    build_document_vector_index_provider_runtime,
)
from energy_trading.application.orchestration.document_vector_index_execution import (
    DocumentVectorIndexExecutionService,
)
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
)
from energy_trading.shared.config.document_vector_index import (
    DocumentVectorIndexRuntimeSettings,
)


def build_document_vector_index_configured_runtime(
    *,
    openai_client: AsyncOpenAI,
    qdrant_client: AsyncQdrantClient,
    settings: DocumentVectorIndexRuntimeSettings,
) -> DocumentVectorIndexExecutionService:
    """Return a wired document vector index service from clients and settings.

    The clients and document-index runtime settings are already supplied. This
    function does not discover, load, close, or invoke them.
    """

    qdrant_config = QdrantDocumentVectorConfig(
        collection_name=settings.qdrant_collection_name,
        vector_size=settings.qdrant_vector_size,
    )
    return build_document_vector_index_provider_runtime(
        openai_client=openai_client,
        qdrant_client=qdrant_client,
        qdrant_config=qdrant_config,
        document_embedding_model=settings.document_embedding_model,
    )
