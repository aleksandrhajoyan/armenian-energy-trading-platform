"""Non-destructive Qdrant document collection ensure orchestration.

This module probes collection existence once, then delegates to create-only or
verify-only helpers. It does not duplicate create or verify internals, default a
metric, embed, index, search, load settings, or own client lifetime.
"""

from typing import Final

from qdrant_client import AsyncQdrantClient
from qdrant_client.common.client_exceptions import ResourceExhaustedResponse
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
from qdrant_client.http.models import Distance

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.infrastructure.vector_store.qdrant.collection_creation import (
    create_qdrant_document_collection,
)
from energy_trading.infrastructure.vector_store.qdrant.collection_readiness import (
    verify_qdrant_document_collection_ready,
)
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
)

_MSG_UNAVAILABLE: Final[str] = "Document vector collection availability could not be determined."
_QDRANT_BACKEND_ERRORS: Final[tuple[type[BaseException], ...]] = (
    UnexpectedResponse,
    ResponseHandlingException,
    ResourceExhaustedResponse,
)


async def ensure_qdrant_document_collection_ready(
    *,
    client: AsyncQdrantClient,
    config: QdrantDocumentVectorConfig,
    distance: Distance,
) -> None:
    """Create a missing collection or verify a present one.

    Existence is probed once. ``False`` delegates to create-only
    ``create_qdrant_document_collection``. ``True`` delegates to verify-only
    ``verify_qdrant_document_collection_ready``. The caller-supplied distance is
    forwarded unchanged. Incompatible existing collections fail closed through
    the verifier. This function does not retry, recreate, update, or delete.
    """

    try:
        exists = await client.collection_exists(
            collection_name=config.collection_name,
        )
    except _QDRANT_BACKEND_ERRORS as exc:
        raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc
    if exists is False:
        await create_qdrant_document_collection(
            client=client,
            config=config,
            distance=distance,
        )
        return
    await verify_qdrant_document_collection_ready(
        client=client,
        config=config,
        distance=distance,
    )
