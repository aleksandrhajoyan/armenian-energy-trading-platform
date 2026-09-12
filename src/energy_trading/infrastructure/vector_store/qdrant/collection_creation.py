"""Explicit Qdrant document collection creation.

This module creates a new unnamed dense-vector collection from an already
created client, existing collection targeting, and a caller-supplied distance.
It does not probe existence, recreate, update, delete, select a default
metric, embed, index, search, load settings, or own client lifetime.
"""

from typing import Final

from qdrant_client import AsyncQdrantClient
from qdrant_client.common.client_exceptions import ResourceExhaustedResponse
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
from qdrant_client.http.models import Distance, VectorParams

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
)

_MSG_UNAVAILABLE: Final[str] = "Document vector collection could not be created."
_QDRANT_BACKEND_ERRORS: Final[tuple[type[BaseException], ...]] = (
    UnexpectedResponse,
    ResponseHandlingException,
    ResourceExhaustedResponse,
)


async def create_qdrant_document_collection(
    *,
    client: AsyncQdrantClient,
    config: QdrantDocumentVectorConfig,
    distance: Distance,
) -> None:
    """Create one unnamed dense document collection.

    The caller supplies the Qdrant distance. This function does not default a
    metric, look up existing collections, or retry.
    """

    try:
        created = await client.create_collection(
            collection_name=config.collection_name,
            vectors_config=VectorParams(size=config.vector_size, distance=distance),
        )
    except _QDRANT_BACKEND_ERRORS as exc:
        raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc
    if not created:
        raise DependencyUnavailableError(_MSG_UNAVAILABLE)
