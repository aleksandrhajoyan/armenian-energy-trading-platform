"""FastAPI-compatible document vector index lifespan boundary.

This module owns FastAPI lifespan entry and exit of the already-published
settings-loaded document vector index runtime. While the lifespan is active it
stores the exact Chunk 91 service on ``app.state``. It does not add an
accessor, dependency, or HTTP route, and it does not invoke provider
operations.

Ownership:

* API composition root: owns ``build_document_vector_index_lifespan``.
* Chunk 91 loaded runtime: owns settings loading and managed-runtime lifetime.
* Production ``create_app()`` enters this lifespan through
  ``build_production_lifespan``. HTTP routes, typed accessors, and LangGraph
  remain deferred.

Constructing the returned callback is lazy. Only entering the lifespan context
enters Chunk 91. The composed service is stored on application state only while
that context is active and is removed before Chunk 91 teardown.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from energy_trading.api.composition.document_vector_index_loaded_runtime import (
    loaded_document_vector_index_runtime,
)


def build_document_vector_index_lifespan(
    *,
    env_file: str | Path | None = ".env",
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Return a FastAPI lifespan callback that owns Chunk 91 resource lifetime.

    Constructing this callback does not load settings or enter the runtime.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with loaded_document_vector_index_runtime(env_file=env_file) as service:
            app.state.document_vector_index_execution_service = service
            try:
                yield
            finally:
                del app.state.document_vector_index_execution_service

    return lifespan
