"""Managed Regulatory Intelligence runtime lifecycle.

This module owns provider-client lifetime for the Regulatory query-execution
service. It receives already-loaded typed settings, constructs clients through
existing factories, awaits configured collection readiness verification on that
same Qdrant client, delegates to
``build_regulatory_intelligence_configured_runtime``, and guarantees client
teardown.

Ownership:

* API composition root: owns ``managed_regulatory_intelligence_runtime``.
* Injected: ``OpenAISettings``.
* Injected: ``QdrantSettings``.
* Injected: ``RegulatoryIntelligenceRuntimeSettings``.
* Injected: ``QdrantDocumentVectorDistanceSettings``.
* Existing OpenAI factory: constructs the OpenAI client.
* Existing Qdrant factory: constructs the Qdrant client.
* Chunk 112 composition: owns configured collection readiness verification.
* Chunk 73 builder: owns configured service construction.
* Settings loading remains owned by the loaded runtime. FastAPI lifespan,
  ``create_app()``, and LangGraph do not import this module.

The manager constructs and yields a service. It does not load environment
values. Collection verification uses the managed Qdrant client; query
execution is not performed here. A missing or incompatible collection fails
closed without creating a collection.
"""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from energy_trading.api.composition.regulatory_intelligence_collection_readiness import (
    verify_configured_regulatory_intelligence_collection_ready,
)
from energy_trading.api.composition.regulatory_intelligence_configured_runtime import (
    build_regulatory_intelligence_configured_runtime,
)
from energy_trading.application.orchestration.regulatory_intelligence_query_execution import (
    RegulatoryIntelligenceQueryExecutionService,
)
from energy_trading.infrastructure.openai.client import create_openai_client
from energy_trading.infrastructure.vector_store.qdrant.client import create_qdrant_client
from energy_trading.shared.config.openai import OpenAISettings
from energy_trading.shared.config.qdrant import (
    QdrantDocumentVectorDistanceSettings,
    QdrantSettings,
)
from energy_trading.shared.config.regulatory_intelligence import (
    RegulatoryIntelligenceRuntimeSettings,
)


@asynccontextmanager
async def managed_regulatory_intelligence_runtime(
    *,
    openai_settings: OpenAISettings,
    qdrant_settings: QdrantSettings,
    regulatory_settings: RegulatoryIntelligenceRuntimeSettings,
    distance_settings: QdrantDocumentVectorDistanceSettings,
) -> AsyncIterator[RegulatoryIntelligenceQueryExecutionService]:
    """Yield a wired Regulatory Intelligence service and close its clients.

    The settings objects are already supplied. This function does not discover
    or load them. Client factories perform no provider I/O at construction.
    Collection readiness verification runs on the managed Qdrant client before
    the configured runtime is built.
    """

    async with AsyncExitStack() as stack:
        openai_client = create_openai_client(openai_settings)
        stack.push_async_callback(openai_client.close)
        qdrant_client = create_qdrant_client(qdrant_settings)
        stack.push_async_callback(qdrant_client.close)
        await verify_configured_regulatory_intelligence_collection_ready(
            client=qdrant_client,
            runtime_settings=regulatory_settings,
            distance_settings=distance_settings,
        )
        service = build_regulatory_intelligence_configured_runtime(
            openai_client=openai_client,
            qdrant_client=qdrant_client,
            settings=regulatory_settings,
        )
        yield service
