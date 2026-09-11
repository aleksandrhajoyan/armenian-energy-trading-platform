"""Settings-loaded PDF extraction-to-index runtime composition.

This module enters the published document-index loaded runtime, then
delegates object construction to ``build_pdf_document_extraction_index_execution``.
It does not inspect the filesystem, load settings itself, or construct
provider clients.

Ownership:

* API composition root: owns ``loaded_pdf_document_extraction_index_runtime``.
* Injected: local ``Path``, ``document_id``, ``source_name``.
* Existing document-index loaded runtime: owns provider-client lifetime and
  yields the index execution service.
* Chunk 102 builder: owns PDF adapter plus application-service construction.
* Production wiring, OCR, acquisition, and graph routing remain deferred.

Entering the context constructs and yields a service. It does not invoke
application runtime methods.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from energy_trading.api.composition.document_vector_index_loaded_runtime import (
    loaded_document_vector_index_runtime,
)
from energy_trading.api.composition.pdf_document_extraction_index import (
    build_pdf_document_extraction_index_execution,
)
from energy_trading.application.orchestration.document_extraction_index_execution import (
    DocumentExtractionIndexExecutionService,
)


@asynccontextmanager
async def loaded_pdf_document_extraction_index_runtime(
    *,
    path: Path,
    document_id: str,
    source_name: str,
    env_file: str | Path | None = ".env",
) -> AsyncIterator[DocumentExtractionIndexExecutionService]:
    """Yield a wired PDF extraction-to-index service from loaded settings.

    The document-index loaded runtime remains authoritative for settings and
    client lifetime. This function does not parse environment values itself
    or invoke application runtime methods.
    """

    async with loaded_document_vector_index_runtime(
        env_file=env_file,
    ) as index_execution_service:
        service = build_pdf_document_extraction_index_execution(
            path=path,
            document_id=document_id,
            source_name=source_name,
            index_execution_service=index_execution_service,
        )
        yield service
