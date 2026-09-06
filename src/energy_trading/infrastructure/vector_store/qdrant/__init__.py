"""Async Qdrant HTTP client foundation.

This package exposes the lazy ``AsyncQdrantClient`` factory. It does not
create a global client, connect on import, manage collections, or implement
document index/search ports. Future composition roots own client lifecycle
(``close``) and wiring.
"""

from energy_trading.infrastructure.vector_store.qdrant.client import create_qdrant_client

__all__ = [
    "create_qdrant_client",
]
