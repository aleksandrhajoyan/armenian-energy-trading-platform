"""Outer PDF extraction-to-index object composition.

This module wires a constructor-configured PDF text extraction adapter into
the published document extraction-to-index execution service. It does not
extract a PDF, execute indexing, inspect the filesystem, load settings, or
construct providers.

Ownership:

* API composition root: owns ``build_pdf_document_extraction_index_execution``.
* Injected: local ``Path``, ``document_id``, ``source_name``.
* Injected: ``DocumentVectorIndexExecutionService``.
* Infrastructure: owns ``PdfTextExtractionAdapter``.
* Application: owns ``DocumentExtractionIndexExecutionService``.
* Production wiring, OCR, acquisition, and graph routing remain deferred.

The builder constructs objects only. It does not call application runtime
methods.
"""

from pathlib import Path

from energy_trading.application.orchestration.document_extraction_index_execution import (
    DocumentExtractionIndexExecutionService,
)
from energy_trading.application.orchestration.document_vector_index_execution import (
    DocumentVectorIndexExecutionService,
)
from energy_trading.infrastructure.adapters.unstructured.pdf_text_extraction import (
    PdfTextExtractionAdapter,
)


def build_pdf_document_extraction_index_execution(
    *,
    path: Path,
    document_id: str,
    source_name: str,
    index_execution_service: DocumentVectorIndexExecutionService,
) -> DocumentExtractionIndexExecutionService:
    """Return a wired PDF extraction-to-index execution service.

    The path, identities, and index execution service are already supplied.
    This function does not inspect, extract, or invoke them.
    """

    document_extraction_port = PdfTextExtractionAdapter(
        path=path,
        document_id=document_id,
        source_name=source_name,
    )
    return DocumentExtractionIndexExecutionService(
        document_extraction_port,
        index_execution_service,
    )
