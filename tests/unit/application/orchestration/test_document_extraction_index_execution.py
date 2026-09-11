"""Document extraction-to-index execution composes extraction with indexing."""

from __future__ import annotations

import inspect
from typing import cast

import pytest

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration import (
    DocumentExtractionIndexExecutionService,
    DocumentVectorIndexExecutionService,
)
from energy_trading.application.ports.document_extraction import (
    DocumentExtractionPort,
    DocumentExtractionResult,
    ExtractedDocumentChunk,
)
from energy_trading.domain.models import AdapterDiagnostic, DLQRecord
from tests.unit.domain._factories import diagnostic, dlq

_EXTRACT_UNAVAILABLE_MESSAGE = "Document extraction is unavailable."
_INDEX_UNAVAILABLE_MESSAGE = "Document vector index execution is unavailable."


class _RecordingExtractor:
    """Test-only recorder. Not a production Protocol or abstraction."""

    def __init__(
        self,
        *,
        result: DocumentExtractionResult | None = None,
        error: BaseException | None = None,
        source_name: str = "fake-document",
    ) -> None:
        self._result = result
        self._error = error
        self._source_name = source_name
        self.calls = 0

    @property
    def source_name(self) -> str:
        return self._source_name

    async def extract(self) -> DocumentExtractionResult:
        self.calls += 1
        if self._error is not None:
            raise self._error
        if self._result is None:
            msg = "recording extractor must return a result"
            raise AssertionError(msg)
        return self._result


class _RecordingIndexExecution:
    """Test-only recorder. Not a production service or abstraction."""

    def __init__(self, *, error: BaseException | None = None) -> None:
        self._error = error
        self.calls: list[tuple[ExtractedDocumentChunk, ...]] = []

    async def execute(self, *, chunks: tuple[ExtractedDocumentChunk, ...]) -> None:
        self.calls.append(chunks)
        if self._error is not None:
            raise self._error


def _as_extraction_port(extractor: _RecordingExtractor) -> DocumentExtractionPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return extractor


def _execution_service(
    extractor: _RecordingExtractor,
    index_execution: _RecordingIndexExecution,
) -> DocumentExtractionIndexExecutionService:
    return DocumentExtractionIndexExecutionService(
        _as_extraction_port(extractor),
        cast(DocumentVectorIndexExecutionService, index_execution),
    )


def _chunk(**overrides: object) -> ExtractedDocumentChunk:
    values: dict[str, object] = {
        "document_id": "doc-1",
        "chunk_id": "chunk-1",
        "ordinal": 0,
        "text": "Normalized extracted text.",
        "page_number": 1,
    }
    values.update(overrides)
    return ExtractedDocumentChunk(**values)  # type: ignore[arg-type]


def _result(
    *,
    chunks: tuple[ExtractedDocumentChunk, ...] = (),
    diagnostics: tuple[AdapterDiagnostic, ...] = (),
    dlq_records: tuple[DLQRecord, ...] = (),
) -> DocumentExtractionResult:
    return DocumentExtractionResult(
        source_name="fake-document",
        document_id="doc-1",
        chunks=chunks,
        diagnostics=diagnostics,
        dlq_records=dlq_records,
    )


def test_fakes_do_not_inherit_published_types() -> None:
    assert DocumentExtractionPort not in _RecordingExtractor.__mro__
    assert DocumentVectorIndexExecutionService not in _RecordingIndexExecution.__mro__


def test_constructor_accepts_exactly_the_two_published_dependencies() -> None:
    signature = inspect.signature(DocumentExtractionIndexExecutionService.__init__)
    assert tuple(signature.parameters) == (
        "self",
        "document_extraction_port",
        "index_execution_service",
    )
    assert signature.parameters["document_extraction_port"].annotation is DocumentExtractionPort
    assert (
        signature.parameters["index_execution_service"].annotation
        is DocumentVectorIndexExecutionService
    )
    service = _execution_service(
        _RecordingExtractor(result=_result()),
        _RecordingIndexExecution(),
    )
    assert isinstance(service, DocumentExtractionIndexExecutionService)


def test_execute_signature_accepts_only_self_and_returns_extraction_result() -> None:
    signature = inspect.signature(DocumentExtractionIndexExecutionService.execute)
    assert tuple(signature.parameters) == ("self",)
    assert signature.return_annotation is DocumentExtractionResult
    assert inspect.iscoroutinefunction(DocumentExtractionIndexExecutionService.execute)


async def test_non_empty_extraction_indexes_exact_chunks_and_returns_original_result() -> None:
    chunks = (_chunk(),)
    extraction_result = _result(chunks=chunks)
    extractor = _RecordingExtractor(result=extraction_result)
    index_execution = _RecordingIndexExecution()
    service = _execution_service(extractor, index_execution)

    returned = await service.execute()

    assert returned is extraction_result
    assert extractor.calls == 1
    assert index_execution.calls == [chunks]
    assert index_execution.calls[0] is extraction_result.chunks
    assert len(index_execution.calls) == 1


async def test_empty_extraction_skips_index_execution_and_preserves_diagnostics() -> None:
    empty_chunks: tuple[ExtractedDocumentChunk, ...] = ()
    diagnostics = (diagnostic(code="pdf_no_extractable_text"),)
    dlq_records = (dlq(),)
    extraction_result = _result(
        chunks=empty_chunks,
        diagnostics=diagnostics,
        dlq_records=dlq_records,
    )
    extractor = _RecordingExtractor(result=extraction_result)
    index_execution = _RecordingIndexExecution()
    service = _execution_service(extractor, index_execution)

    returned = await service.execute()

    assert returned is extraction_result
    assert extractor.calls == 1
    assert index_execution.calls == []
    assert returned.chunks is empty_chunks
    assert returned.diagnostics is diagnostics
    assert returned.dlq_records is dlq_records


async def test_extraction_exception_propagates_without_calling_index() -> None:
    error = DependencyUnavailableError(_EXTRACT_UNAVAILABLE_MESSAGE)
    extractor = _RecordingExtractor(error=error)
    index_execution = _RecordingIndexExecution()
    service = _execution_service(extractor, index_execution)

    with pytest.raises(DependencyUnavailableError) as caught:
        await service.execute()

    assert caught.value is error
    assert caught.value.message == _EXTRACT_UNAVAILABLE_MESSAGE
    assert extractor.calls == 1
    assert index_execution.calls == []


async def test_index_exception_propagates_after_exactly_one_extraction() -> None:
    error = DependencyUnavailableError(_INDEX_UNAVAILABLE_MESSAGE)
    chunks = (_chunk(),)
    extraction_result = _result(chunks=chunks)
    extractor = _RecordingExtractor(result=extraction_result)
    index_execution = _RecordingIndexExecution(error=error)
    service = _execution_service(extractor, index_execution)

    with pytest.raises(DependencyUnavailableError) as caught:
        await service.execute()

    assert caught.value is error
    assert caught.value.message == _INDEX_UNAVAILABLE_MESSAGE
    assert extractor.calls == 1
    assert index_execution.calls == [chunks]
    assert index_execution.calls[0] is extraction_result.chunks
    assert len(index_execution.calls) == 1


async def test_equivalent_extraction_is_deterministic_without_mutation() -> None:
    chunks = (_chunk(),)
    first_result = _result(chunks=chunks)
    second_result = _result(chunks=chunks)
    first_extractor = _RecordingExtractor(result=first_result)
    second_extractor = _RecordingExtractor(result=second_result)
    first_index = _RecordingIndexExecution()
    second_index = _RecordingIndexExecution()

    first_returned = await _execution_service(first_extractor, first_index).execute()
    second_returned = await _execution_service(second_extractor, second_index).execute()

    assert first_returned is first_result
    assert second_returned is second_result
    assert first_returned == second_returned
    assert first_index.calls[0] is first_result.chunks
    assert second_index.calls[0] is second_result.chunks
    assert first_result.chunks == chunks
    assert second_result.chunks == chunks
