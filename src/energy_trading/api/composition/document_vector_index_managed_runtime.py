"""Managed document vector index runtime lifecycle.

This module owns provider-client lifetime for the document vector index
execution service. It receives already-loaded typed settings, constructs
clients through existing factories, awaits configured collection readiness
on that same Qdrant client, delegates to
``build_document_vector_index_configured_runtime``, and guarantees client
teardown.

Ownership:

* API composition root: owns ``managed_document_vector_index_runtime``.
* Injected: ``OpenAISettings``.
* Injected: ``QdrantSettings``.
* Injected: ``DocumentVectorIndexRuntimeSettings``.
* Injected: ``QdrantDocumentVectorDistanceSettings``.
* Existing OpenAI factory: constructs the OpenAI client.
* Existing Qdrant factory: constructs the Qdrant client.
* Chunk 110 composition: owns configured collection ensure.
* Chunk 89 builder: owns configured service construction.
* Settings loading remains owned by the loaded runtime. FastAPI lifespan,
  ``create_app()``, and LangGraph do not import this module.

The manager constructs and yields a service. It does not load environment
values. Collection ensure uses the managed Qdrant client; indexing is not
executed here.
"""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from energy_trading.api.composition.document_vector_index_collection_ensure import (
    ensure_configured_document_vector_index_collection_ready,
)
from energy_trading.api.composition.document_vector_index_configured_runtime import (
    build_document_vector_index_configured_runtime,
)
from energy_trading.application.orchestration.document_vector_index_execution import (
    DocumentVectorIndexExecutionService,
)
from energy_trading.infrastructure.openai.client import create_openai_client
from energy_trading.infrastructure.vector_store.qdrant.client import create_qdrant_client
from energy_trading.shared.config.document_vector_index import (
    DocumentVectorIndexRuntimeSettings,
)
from energy_trading.shared.config.openai import OpenAISettings
from energy_trading.shared.config.qdrant import (
    QdrantDocumentVectorDistanceSettings,
    QdrantSettings,
)


@asynccontextmanager
async def managed_document_vector_index_runtime(
    *,
    openai_settings: OpenAISettings,
    qdrant_settings: QdrantSettings,
    document_vector_index_settings: DocumentVectorIndexRuntimeSettings,
    distance_settings: QdrantDocumentVectorDistanceSettings,
) -> AsyncIterator[DocumentVectorIndexExecutionService]:
    """Yield a wired document vector index service and close its clients.

    The settings objects are already supplied. This function does not discover
    or load them. Client factories perform no provider I/O at construction.
    Collection ensure runs on the managed Qdrant client before the configured
    runtime is built.
    """

    async with AsyncExitStack() as stack:
        openai_client = create_openai_client(openai_settings)
        stack.push_async_callback(openai_client.close)
        qdrant_client = create_qdrant_client(qdrant_settings)
        stack.push_async_callback(qdrant_client.close)
        await ensure_configured_document_vector_index_collection_ready(
            client=qdrant_client,
            runtime_settings=document_vector_index_settings,
            distance_settings=distance_settings,
        )
        service = build_document_vector_index_configured_runtime(
            openai_client=openai_client,
            qdrant_client=qdrant_client,
            settings=document_vector_index_settings,
        )
        yield service
