"""Configured document-index Qdrant collection ensure composition.

This module translates already-constructed
``DocumentVectorIndexRuntimeSettings`` and
``QdrantDocumentVectorDistanceSettings`` into one
``QdrantDocumentVectorConfig`` plus one mapped Qdrant ``Distance``, then
delegates to ``ensure_qdrant_document_collection_ready``. It does not load
environment values, construct clients, or own client lifetime.

Ownership:

* API composition root: owns ``ensure_configured_document_vector_index_collection_ready``.
* Injected: ``AsyncQdrantClient``.
* Injected: ``DocumentVectorIndexRuntimeSettings``.
* Injected: ``QdrantDocumentVectorDistanceSettings``.
* Chunk 109 mapper: owns provider-neutral distance translation.
* Chunk 108 ensure: owns create-if-missing / verify-if-present orchestration.
* Client lifecycle, settings loading, ``create_app()``, and LangGraph remain
  deferred.
"""

from qdrant_client import AsyncQdrantClient

from energy_trading.api.composition.qdrant_document_vector_distance import (
    map_qdrant_document_vector_distance,
)
from energy_trading.infrastructure.vector_store.qdrant.collection_ensure import (
    ensure_qdrant_document_collection_ready,
)
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
)
from energy_trading.shared.config.document_vector_index import (
    DocumentVectorIndexRuntimeSettings,
)
from energy_trading.shared.config.qdrant import QdrantDocumentVectorDistanceSettings


async def ensure_configured_document_vector_index_collection_ready(
    *,
    client: AsyncQdrantClient,
    runtime_settings: DocumentVectorIndexRuntimeSettings,
    distance_settings: QdrantDocumentVectorDistanceSettings,
) -> None:
    """Ensure the configured document-index collection exists or is compatible.

    The client and settings objects are already supplied. This function does
    not discover, load, close, or reconstruct them.
    """

    qdrant_config = QdrantDocumentVectorConfig(
        collection_name=runtime_settings.qdrant_collection_name,
        vector_size=runtime_settings.qdrant_vector_size,
    )
    distance = map_qdrant_document_vector_distance(
        distance=distance_settings.document_vector_distance,
    )
    await ensure_qdrant_document_collection_ready(
        client=client,
        config=qdrant_config,
        distance=distance,
    )
