"""FastAPI-compatible document vector index lifespan boundary.

This module owns FastAPI lifespan entry and exit of the already-published
settings-loaded document vector index runtime. It does not install that
lifespan into ``create_app()``, expose the composed service, or invoke
provider operations.

Ownership:

* API composition root: owns ``build_document_vector_index_lifespan``.
* Chunk 91 loaded runtime: owns settings loading and managed-runtime lifetime.
* ``create_app()``, HTTP routes, app state, and LangGraph remain deferred.

Constructing the returned callback is lazy. Only entering the lifespan context
enters Chunk 91. The composed service is intentionally unused.
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
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        async with loaded_document_vector_index_runtime(env_file=env_file):
            yield

    return lifespan
