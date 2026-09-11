"""PDF extraction-to-index composition wires published objects without I/O."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from energy_trading.api.composition import build_pdf_document_extraction_index_execution
from energy_trading.application.orchestration import (
    DocumentExtractionIndexExecutionService,
    DocumentVectorIndexEntryPreparationService,
    DocumentVectorIndexExecutionService,
)
from energy_trading.application.ports.document_embedding import (
    DocumentChunkEmbedding,
    DocumentEmbeddingPort,
)
from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk
from energy_trading.application.ports.document_vector_index import (
    DocumentVectorIndexEntry,
    DocumentVectorIndexPort,
)
from energy_trading.infrastructure.adapters.unstructured.pdf_text_extraction import (
    PdfTextExtractionAdapter,
)

_DOCUMENT_ID = "doc-chunk-102"
_SOURCE_NAME = "chunk-102-regulatory-pdf"
_MISSING_PDF = Path("missing-chunk-102-does-not-exist.pdf")


class _FakeDocumentEmbedder:
    """Test-only fake that structurally satisfies ``DocumentEmbeddingPort``."""

    def __init__(self) -> None:
        self.calls: list[tuple[ExtractedDocumentChunk, ...]] = []

    async def embed(
        self,
        chunks: tuple[ExtractedDocumentChunk, ...],
    ) -> tuple[DocumentChunkEmbedding, ...]:
        self.calls.append(chunks)
        raise AssertionError("document embedding must not be called")


class _FakeDocumentVectorIndex:
    """Test-only fake that structurally satisfies ``DocumentVectorIndexPort``."""

    def __init__(self) -> None:
        self.calls: list[tuple[DocumentVectorIndexEntry, ...]] = []

    async def index(self, entries: tuple[DocumentVectorIndexEntry, ...]) -> None:
        self.calls.append(entries)
        raise AssertionError("document vector index must not be called")


def _as_embedding_port(embedder: _FakeDocumentEmbedder) -> DocumentEmbeddingPort:
    return embedder


def _as_index_port(index: _FakeDocumentVectorIndex) -> DocumentVectorIndexPort:
    return index


def _index_execution_service(
    embedder: _FakeDocumentEmbedder | None = None,
    index: _FakeDocumentVectorIndex | None = None,
) -> DocumentVectorIndexExecutionService:
    return DocumentVectorIndexExecutionService(
        DocumentVectorIndexEntryPreparationService(
            _as_embedding_port(embedder or _FakeDocumentEmbedder())
        ),
        _as_index_port(index or _FakeDocumentVectorIndex()),
    )


def _build(
    *,
    path: Path = _MISSING_PDF,
    document_id: str = _DOCUMENT_ID,
    source_name: str = _SOURCE_NAME,
    index_execution_service: DocumentVectorIndexExecutionService | None = None,
) -> DocumentExtractionIndexExecutionService:
    return build_pdf_document_extraction_index_execution(
        path=path,
        document_id=document_id,
        source_name=source_name,
        index_execution_service=index_execution_service or _index_execution_service(),
    )


def test_builder_signature_is_keyword_only_path_identities_and_index_service() -> None:
    signature = inspect.signature(build_pdf_document_extraction_index_execution)
    assert tuple(signature.parameters) == (
        "path",
        "document_id",
        "source_name",
        "index_execution_service",
    )
    for name in signature.parameters:
        parameter = signature.parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["path"].annotation is Path
    assert signature.parameters["document_id"].annotation is str
    assert signature.parameters["source_name"].annotation is str
    assert (
        signature.parameters["index_execution_service"].annotation
        is DocumentVectorIndexExecutionService
    )
    assert signature.return_annotation is DocumentExtractionIndexExecutionService
    assert not inspect.iscoroutinefunction(build_pdf_document_extraction_index_execution)
    assert "clock" not in signature.parameters
    assert "settings" not in signature.parameters
    assert "env_file" not in signature.parameters


def test_builder_returns_extraction_index_execution_service() -> None:
    service = _build()
    assert isinstance(service, DocumentExtractionIndexExecutionService)
    assert type(service) is DocumentExtractionIndexExecutionService


def test_builder_wires_one_pdf_adapter_and_preserves_index_service_identity() -> None:
    index_execution = _index_execution_service()
    path = Path("unwired-chunk-102.pdf")
    service = _build(
        path=path,
        document_id=_DOCUMENT_ID,
        source_name=_SOURCE_NAME,
        index_execution_service=index_execution,
    )

    adapter = service._document_extraction_port
    assert isinstance(adapter, PdfTextExtractionAdapter)
    assert adapter._path is path
    assert adapter._path == path
    assert adapter._document_id is _DOCUMENT_ID
    assert adapter._document_id == _DOCUMENT_ID
    assert adapter._source_name is _SOURCE_NAME
    assert adapter.source_name == _SOURCE_NAME
    assert service._index_execution_service is index_execution


def test_builder_constructs_exactly_one_pdf_adapter_and_one_application_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter_calls: list[PdfTextExtractionAdapter] = []
    service_calls: list[DocumentExtractionIndexExecutionService] = []
    real_adapter = PdfTextExtractionAdapter
    real_service = DocumentExtractionIndexExecutionService

    def tracking_adapter(
        *,
        path: Path,
        document_id: str,
        source_name: str,
    ) -> PdfTextExtractionAdapter:
        adapter = real_adapter(
            path=path,
            document_id=document_id,
            source_name=source_name,
        )
        adapter_calls.append(adapter)
        return adapter

    def tracking_service(
        document_extraction_port: object,
        index_execution_service: DocumentVectorIndexExecutionService,
    ) -> DocumentExtractionIndexExecutionService:
        service = real_service(document_extraction_port, index_execution_service)
        service_calls.append(service)
        return service

    monkeypatch.setattr(
        "energy_trading.api.composition.pdf_document_extraction_index.PdfTextExtractionAdapter",
        tracking_adapter,
    )
    monkeypatch.setattr(
        "energy_trading.api.composition.pdf_document_extraction_index.DocumentExtractionIndexExecutionService",
        tracking_service,
    )
    index_execution = _index_execution_service()
    path = Path("counted-chunk-102.pdf")
    service = build_pdf_document_extraction_index_execution(
        path=path,
        document_id=_DOCUMENT_ID,
        source_name=_SOURCE_NAME,
        index_execution_service=index_execution,
    )
    assert len(adapter_calls) == 1
    assert len(service_calls) == 1
    assert service is service_calls[0]
    assert service._document_extraction_port is adapter_calls[0]
    assert service._index_execution_service is index_execution
    assert adapter_calls[0]._path is path
    assert adapter_calls[0]._document_id == _DOCUMENT_ID
    assert adapter_calls[0]._source_name == _SOURCE_NAME


def test_construction_succeeds_for_nonexistent_pdf_without_extraction_or_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    embedder = _FakeDocumentEmbedder()
    index = _FakeDocumentVectorIndex()
    index_execution = _index_execution_service(embedder, index)
    extract_calls = 0
    execute_calls = 0

    async def fail_extract(self: PdfTextExtractionAdapter) -> None:
        nonlocal extract_calls
        extract_calls += 1
        raise AssertionError("extract must not be called")

    async def fail_execute(
        self: DocumentVectorIndexExecutionService,
        *args: object,
        **kwargs: object,
    ) -> None:
        del args, kwargs
        nonlocal execute_calls
        execute_calls += 1
        raise AssertionError("execute must not be called")

    def fail_exists(self: Path) -> bool:
        raise AssertionError("path.exists must not be called")

    def fail_is_file(self: Path) -> bool:
        raise AssertionError("path.is_file must not be called")

    def fail_open(self: Path, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("path.open must not be called")

    def fail_stat(self: Path, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("path.stat must not be called")

    monkeypatch.setattr(PdfTextExtractionAdapter, "extract", fail_extract)
    monkeypatch.setattr(DocumentVectorIndexExecutionService, "execute", fail_execute)
    monkeypatch.setattr(Path, "exists", fail_exists)
    monkeypatch.setattr(Path, "is_file", fail_is_file)
    monkeypatch.setattr(Path, "open", fail_open)
    monkeypatch.setattr(Path, "stat", fail_stat)

    service = build_pdf_document_extraction_index_execution(
        path=_MISSING_PDF,
        document_id=_DOCUMENT_ID,
        source_name=_SOURCE_NAME,
        index_execution_service=index_execution,
    )

    assert isinstance(service, DocumentExtractionIndexExecutionService)
    adapter = service._document_extraction_port
    assert isinstance(adapter, PdfTextExtractionAdapter)
    assert adapter._path is _MISSING_PDF
    assert service._index_execution_service is index_execution
    assert extract_calls == 0
    assert execute_calls == 0
    assert embedder.calls == []
    assert index.calls == []
