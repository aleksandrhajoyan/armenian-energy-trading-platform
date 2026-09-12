"""Async Qdrant HTTP client foundation and document vector adapters.

This package exposes the lazy ``AsyncQdrantClient`` factory, the offline
document index/search adapters, a read-only collection-readiness verifier,
an explicit create-only collection operation, and a non-destructive
create-if-missing / verify-if-present ensure operation. It does not create a
global client, connect on import, automatically provision collections, or wire
``create_app()``. Future composition roots own client lifecycle (``close``)
and wiring.
"""

from energy_trading.infrastructure.vector_store.qdrant.client import create_qdrant_client
from energy_trading.infrastructure.vector_store.qdrant.collection_creation import (
    create_qdrant_document_collection,
)
from energy_trading.infrastructure.vector_store.qdrant.collection_ensure import (
    ensure_qdrant_document_collection_ready,
)
from energy_trading.infrastructure.vector_store.qdrant.collection_readiness import (
    verify_qdrant_document_collection_ready,
)
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
    QdrantDocumentVectorIndex,
    QdrantDocumentVectorSearch,
)

__all__ = [
    "QdrantDocumentVectorConfig",
    "QdrantDocumentVectorIndex",
    "QdrantDocumentVectorSearch",
    "create_qdrant_client",
    "create_qdrant_document_collection",
    "ensure_qdrant_document_collection_ready",
    "verify_qdrant_document_collection_ready",
]
