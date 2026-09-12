"""Settings-loaded Regulatory Intelligence managed runtime composition.

This module loads the four published typed settings objects through their
existing loaders, then delegates resource ownership to
``managed_regulatory_intelligence_runtime``. It does not construct clients,
import provider SDKs, or invoke collection readiness verification.

Ownership:

* API composition root: owns ``loaded_regulatory_intelligence_runtime``.
* Existing OpenAI settings loader: discovers ``OpenAISettings``.
* Existing Qdrant settings loader: discovers ``QdrantSettings``.
* Existing Regulatory runtime settings loader: discovers
  ``RegulatoryIntelligenceRuntimeSettings``.
* Existing document-vector distance settings loader: discovers
  ``QdrantDocumentVectorDistanceSettings``.
* Chunk 74 managed runtime: owns client lifetime, collection readiness
  verification, and service construction.
* Regulatory FastAPI lifespan consumes this runtime. Production
  ``create_app()`` reaches it indirectly through ``build_production_lifespan``.
  The exact yielded query-execution service is exposed by
  ``regulatory_intelligence_lifespan.py``. LangGraph remains deferred.

Entering the context loads settings and yields a service. It does not execute
a Regulatory query. Collection readiness verification is owned by the managed
runtime because that runtime owns the Qdrant client.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from energy_trading.api.composition.regulatory_intelligence_managed_runtime import (
    managed_regulatory_intelligence_runtime,
)
from energy_trading.application.orchestration.regulatory_intelligence_query_execution import (
    RegulatoryIntelligenceQueryExecutionService,
)
from energy_trading.shared.config.openai import load_openai_settings
from energy_trading.shared.config.qdrant import (
    load_qdrant_document_vector_distance_settings,
    load_qdrant_settings,
)
from energy_trading.shared.config.regulatory_intelligence import (
    load_regulatory_intelligence_runtime_settings,
)


@asynccontextmanager
async def loaded_regulatory_intelligence_runtime(
    *,
    env_file: str | Path | None = ".env",
) -> AsyncIterator[RegulatoryIntelligenceQueryExecutionService]:
    """Yield a wired Regulatory Intelligence service from loaded settings.

    The four existing typed loaders remain authoritative. This function does
    not parse environment values itself or invoke provider operations.
    """

    openai_settings = load_openai_settings(env_file=env_file)
    qdrant_settings = load_qdrant_settings(env_file=env_file)
    regulatory_settings = load_regulatory_intelligence_runtime_settings(env_file=env_file)
    distance_settings = load_qdrant_document_vector_distance_settings(env_file=env_file)
    async with managed_regulatory_intelligence_runtime(
        openai_settings=openai_settings,
        qdrant_settings=qdrant_settings,
        regulatory_settings=regulatory_settings,
        distance_settings=distance_settings,
    ) as service:
        yield service
