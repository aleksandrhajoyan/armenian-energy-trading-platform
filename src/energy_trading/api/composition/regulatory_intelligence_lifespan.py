"""FastAPI-compatible Regulatory Intelligence lifespan boundary.

This module owns FastAPI lifespan entry and exit of the already-published
settings-loaded Regulatory runtime. While the lifespan is active it stores the
exact Chunk 75 service on ``app.state``. It does not add an accessor,
dependency, or HTTP route, and it does not invoke provider operations.

Ownership:

* API composition root: owns ``build_regulatory_intelligence_lifespan``.
* Chunk 75 loaded runtime: owns settings loading and managed-runtime lifetime.
* ``create_app()`` installs this lifespan. HTTP routes, typed accessors, and
  LangGraph remain deferred.

Constructing the returned callback is lazy. Only entering the lifespan context
enters Chunk 75. The composed service is stored on application state only while
that context is active and is removed before Chunk 75 teardown.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from energy_trading.api.composition.regulatory_intelligence_loaded_runtime import (
    loaded_regulatory_intelligence_runtime,
)


def build_regulatory_intelligence_lifespan(
    *,
    env_file: str | Path | None = ".env",
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Return a FastAPI lifespan callback that owns Chunk 75 resource lifetime.

    Constructing this callback does not load settings or enter the runtime.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with loaded_regulatory_intelligence_runtime(env_file=env_file) as service:
            app.state.regulatory_intelligence_query_execution_service = service
            try:
                yield
            finally:
                del app.state.regulatory_intelligence_query_execution_service

    return lifespan
