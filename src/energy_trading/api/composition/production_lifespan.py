"""Production FastAPI lifespan composition boundary.

This module nests the already-published Regulatory Intelligence and document
vector index lifespan callbacks for a single FastAPI process. It does not
install the composite into ``create_app()``, expose indexing on application
state, or invoke provider operations.

Ownership:

* API composition root: owns ``build_production_lifespan``.
* Chunk 76 Regulatory lifespan: owns Regulatory runtime exposure.
* Chunk 92 document vector index lifespan: owns unused indexing runtime.
* ``create_app()`` remains on the existing Regulatory lifespan.

Constructing the returned callback is lazy. Child lifespan factories retain
their own runtime ownership. Regulatory is the outer context; document vector
index is the inner context.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from energy_trading.api.composition.document_vector_index_lifespan import (
    build_document_vector_index_lifespan,
)
from energy_trading.api.composition.regulatory_intelligence_lifespan import (
    build_regulatory_intelligence_lifespan,
)


def build_production_lifespan(
    *,
    env_file: str | Path | None = ".env",
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Return a FastAPI lifespan that nests the two published child lifespans.

    Constructing this callback does not load settings or enter either runtime.
    """

    regulatory_lifespan = build_regulatory_intelligence_lifespan(env_file=env_file)
    document_vector_index_lifespan = build_document_vector_index_lifespan(env_file=env_file)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with regulatory_lifespan(app):
            async with document_vector_index_lifespan(app):
                yield

    return lifespan
