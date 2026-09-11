"""Settings-loaded document vector index managed runtime composition.

This module loads the three published typed settings objects through their
existing loaders, then delegates resource ownership to
``managed_document_vector_index_runtime``. It does not construct clients,
import provider SDKs, or invoke provider operations.

Ownership:

* API composition root: owns ``loaded_document_vector_index_runtime``.
* Existing OpenAI settings loader: discovers ``OpenAISettings``.
* Existing Qdrant settings loader: discovers ``QdrantSettings``.
* Existing document-index runtime settings loader: discovers
  ``DocumentVectorIndexRuntimeSettings``.
* Chunk 90 managed runtime: owns client lifetime and service construction.
* Document-index FastAPI lifespan consumes this runtime. Production
  ``create_app()`` reaches it indirectly through ``build_production_lifespan``.
  The exact yielded execution service is exposed by
  ``document_vector_index_lifespan.py``. HTTP indexing, automatic indexing,
  and LangGraph remain deferred.

Entering the context loads settings and yields a service. It does not execute
indexing.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from energy_trading.api.composition.document_vector_index_managed_runtime import (
    managed_document_vector_index_runtime,
)
from energy_trading.application.orchestration.document_vector_index_execution import (
    DocumentVectorIndexExecutionService,
)
from energy_trading.shared.config.document_vector_index import (
    load_document_vector_index_runtime_settings,
)
from energy_trading.shared.config.openai import load_openai_settings
from energy_trading.shared.config.qdrant import load_qdrant_settings


@asynccontextmanager
async def loaded_document_vector_index_runtime(
    *,
    env_file: str | Path | None = ".env",
) -> AsyncIterator[DocumentVectorIndexExecutionService]:
    """Yield a wired document vector index service from loaded settings.

    The three existing typed loaders remain authoritative. This function does
    not parse environment values itself or invoke provider operations.
    """

    openai_settings = load_openai_settings(env_file=env_file)
    qdrant_settings = load_qdrant_settings(env_file=env_file)
    document_vector_index_settings = load_document_vector_index_runtime_settings(env_file=env_file)
    async with managed_document_vector_index_runtime(
        openai_settings=openai_settings,
        qdrant_settings=qdrant_settings,
        document_vector_index_settings=document_vector_index_settings,
    ) as service:
        yield service
