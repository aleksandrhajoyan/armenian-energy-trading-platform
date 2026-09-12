"""Configured Regulatory Qdrant collection readiness composition.

This module translates already-constructed
``RegulatoryIntelligenceRuntimeSettings`` and
``QdrantDocumentVectorDistanceSettings`` into one
``QdrantDocumentVectorConfig`` plus one mapped Qdrant ``Distance``, then
delegates to ``verify_qdrant_document_collection_ready``. It does not load
environment values, construct clients, or own client lifetime.

Ownership:

* API composition root: owns ``verify_configured_regulatory_intelligence_collection_ready``.
* Injected: ``AsyncQdrantClient``.
* Injected: ``RegulatoryIntelligenceRuntimeSettings``.
* Injected: ``QdrantDocumentVectorDistanceSettings``.
* Chunk 109 mapper: owns provider-neutral distance translation.
* Chunk 107 verifier: owns read-only unnamed dense size/distance inspection.
* Client lifecycle, settings loading, ``create_app()``, and LangGraph remain
  deferred.
"""

from qdrant_client import AsyncQdrantClient

from energy_trading.api.composition.qdrant_document_vector_distance import (
    map_qdrant_document_vector_distance,
)
from energy_trading.infrastructure.vector_store.qdrant.collection_readiness import (
    verify_qdrant_document_collection_ready,
)
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
)
from energy_trading.shared.config.qdrant import QdrantDocumentVectorDistanceSettings
from energy_trading.shared.config.regulatory_intelligence import (
    RegulatoryIntelligenceRuntimeSettings,
)


async def verify_configured_regulatory_intelligence_collection_ready(
    *,
    client: AsyncQdrantClient,
    runtime_settings: RegulatoryIntelligenceRuntimeSettings,
    distance_settings: QdrantDocumentVectorDistanceSettings,
) -> None:
    """Verify the configured Regulatory collection exists and is compatible.

    The client and settings objects are already supplied. This function does
    not discover, load, close, or reconstruct them. A missing or incompatible
    collection fails closed through the published verifier.
    """

    qdrant_config = QdrantDocumentVectorConfig(
        collection_name=runtime_settings.qdrant_collection_name,
        vector_size=runtime_settings.qdrant_vector_size,
    )
    distance = map_qdrant_document_vector_distance(
        distance=distance_settings.document_vector_distance,
    )
    await verify_qdrant_document_collection_ready(
        client=client,
        config=qdrant_config,
        distance=distance,
    )
