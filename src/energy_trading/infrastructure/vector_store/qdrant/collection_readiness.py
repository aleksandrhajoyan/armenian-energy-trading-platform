"""Read-only Qdrant document collection readiness verification.

This module inspects already-provisioned collection metadata. It does not
create, update, or delete collections, select a vector metric, embed, index,
search, load settings, or own client lifetime.
"""

from typing import Final

from qdrant_client import AsyncQdrantClient
from qdrant_client.common.client_exceptions import ResourceExhaustedResponse
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
from qdrant_client.http.models import VectorParams

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
)

_MSG_UNAVAILABLE: Final[str] = "Document vector collection is unavailable."
_QDRANT_BACKEND_ERRORS: Final[tuple[type[BaseException], ...]] = (
    UnexpectedResponse,
    ResponseHandlingException,
    ResourceExhaustedResponse,
)


async def verify_qdrant_document_collection_ready(
    *,
    client: AsyncQdrantClient,
    config: QdrantDocumentVectorConfig,
) -> None:
    """Verify an existing collection has a compatible unnamed dense vector.

    Compatibility is unnamed ``VectorParams`` whose size equals
    ``config.vector_size``. Named-vector mappings, missing dense configuration,
    and provider failures fail closed. The configured vector metric is not
    inspected.
    """

    try:
        info = await client.get_collection(collection_name=config.collection_name)
    except _QDRANT_BACKEND_ERRORS as exc:
        raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc
    collection_config = getattr(info, "config", None)
    params = getattr(collection_config, "params", None)
    vectors = getattr(params, "vectors", None)
    if not isinstance(vectors, VectorParams):
        raise DependencyUnavailableError(_MSG_UNAVAILABLE)
    if vectors.size != config.vector_size:
        raise DependencyUnavailableError(_MSG_UNAVAILABLE)
