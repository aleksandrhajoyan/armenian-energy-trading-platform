"""Explicit one-shot loaded PDF extraction-to-index execution.

This module enters the published loaded PDF runtime and awaits the
application use case exactly once. It does not inspect the filesystem,
load settings itself, or construct provider clients.

Ownership:

* API composition root: owns ``execute_loaded_pdf_document_extraction_index``.
* Injected: local ``Path``, ``document_id``, ``source_name``.
* Existing ``env_file`` contract: forwarded unchanged.
* Chunk 103 loaded runtime: owns construction and provider-client lifetime.
* Chunk 101 application service: owns extract-then-conditional-index.
* Production wiring, OCR, acquisition, and graph routing remain deferred.

The function constructs, executes once, and returns the original result.
It does not reconstruct diagnostics or invoke nested ports directly.
"""

from pathlib import Path

from energy_trading.api.composition.pdf_document_extraction_index_loaded_runtime import (
    loaded_pdf_document_extraction_index_runtime,
)
from energy_trading.application.ports.document_extraction import DocumentExtractionResult


async def execute_loaded_pdf_document_extraction_index(
    *,
    path: Path,
    document_id: str,
    source_name: str,
    env_file: str | Path | None = ".env",
) -> DocumentExtractionResult:
    """Execute one loaded PDF extraction-to-index pass and return its result.

    The loaded PDF runtime remains authoritative for construction and client
    lifetime. This function does not parse environment values itself or call
    nested extraction or index ports.
    """

    async with loaded_pdf_document_extraction_index_runtime(
        path=path,
        document_id=document_id,
        source_name=source_name,
        env_file=env_file,
    ) as service:
        result = await service.execute()
    return result
