"""Production FastAPI lifespan composition boundary.

This module nests the already-published Regulatory Intelligence and document
vector index lifespan callbacks for a single FastAPI process. Production
``create_app()`` installs ``build_production_lifespan()`` as the default
lifespan. An explicit ``create_app(..., lifespan=...)`` argument still
replaces that default. This module only composes the two published lifespan
callbacks. It does not execute indexing or provider operations itself.

Ownership:

* API composition root: owns ``build_production_lifespan``.
* Production ``create_app()``: installs this factory as the default lifespan.
* Chunk 76 Regulatory lifespan: owns Regulatory query-service exposure.
* Chunk 92 document vector index lifespan: owns unused indexing runtime
  and exposes no service.

Wiring:

    create_app()
    → build_production_lifespan()
    → Regulatory lifespan
    → Document Vector Index lifespan

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
