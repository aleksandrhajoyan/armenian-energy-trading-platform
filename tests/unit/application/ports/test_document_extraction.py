"""Unstructured document extraction application-port contracts."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError

import pytest

from energy_trading.application.ports import (
    DocumentExtractionPort,
    DocumentExtractionResult,
    ExtractedDocumentChunk,
)
from tests.unit.application.fakes import FakeDocumentExtractor, as_document_extraction_port
from tests.unit.domain._factories import diagnostic, dlq


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


def _result(**overrides: object) -> DocumentExtractionResult:
    values: dict[str, object] = {
        "source_name": "fake-document",
        "document_id": "doc-1",
        "chunks": (_chunk(),),
        "diagnostics": (),
        "dlq_records": (),
    }
    values.update(overrides)
    return DocumentExtractionResult(**values)  # type: ignore[arg-type]


def test_extracted_chunk_is_valid() -> None:
    chunk = _chunk()
    assert chunk.document_id == "doc-1"
    assert chunk.chunk_id == "chunk-1"
    assert chunk.ordinal == 0
    assert chunk.text == "Normalized extracted text."
    assert chunk.page_number == 1


def test_extracted_chunk_strips_identifiers_and_text() -> None:
    chunk = _chunk(document_id="  doc-1  ", chunk_id="  chunk-1  ", text="  body  ")
    assert chunk.document_id == "doc-1"
    assert chunk.chunk_id == "chunk-1"
    assert chunk.text == "body"


@pytest.mark.parametrize("document_id", ["", "   "])
def test_extracted_chunk_rejects_empty_document_id(document_id: str) -> None:
    with pytest.raises(ValueError, match="document_id"):
        _chunk(document_id=document_id)


@pytest.mark.parametrize("chunk_id", ["", "   "])
def test_extracted_chunk_rejects_empty_chunk_id(chunk_id: str) -> None:
    with pytest.raises(ValueError, match="chunk_id"):
        _chunk(chunk_id=chunk_id)


@pytest.mark.parametrize("text", ["", "   "])
def test_extracted_chunk_rejects_empty_text(text: str) -> None:
    with pytest.raises(ValueError, match="text"):
        _chunk(text=text)


def test_extracted_chunk_rejects_negative_ordinal() -> None:
    with pytest.raises(ValueError, match="ordinal"):
        _chunk(ordinal=-1)


def test_extracted_chunk_rejects_zero_page_number() -> None:
    with pytest.raises(ValueError, match="page_number"):
        _chunk(page_number=0)


def test_extracted_chunk_rejects_negative_page_number() -> None:
    with pytest.raises(ValueError, match="page_number"):
        _chunk(page_number=-1)


def test_extracted_chunk_allows_missing_page_number() -> None:
    chunk = _chunk(page_number=None)
    assert chunk.page_number is None


def test_extracted_chunk_is_immutable() -> None:
    chunk = _chunk()
    with pytest.raises(FrozenInstanceError):
        chunk.text = "mutated"  # type: ignore[misc]


def test_extraction_result_strips_source_and_document_ids() -> None:
    result = _result(source_name="  fake-document  ", document_id="  doc-1  ")
    assert result.source_name == "fake-document"
    assert result.document_id == "doc-1"


def test_extraction_result_is_valid_frozen_envelope() -> None:
    result = _result()
    assert result.source_name == "fake-document"
    assert result.document_id == "doc-1"
    assert isinstance(result.chunks, tuple)
    assert isinstance(result.diagnostics, tuple)
    assert isinstance(result.dlq_records, tuple)
    assert result.chunks[0].text == "Normalized extracted text."
    with pytest.raises(FrozenInstanceError):
        result.source_name = "mutated"  # type: ignore[misc]


def test_extraction_result_rejects_mutable_collections() -> None:
    with pytest.raises(TypeError, match="chunks must be an immutable tuple"):
        _result(chunks=[_chunk()])  # type: ignore[arg-type]


def test_extraction_result_rejects_wrong_chunk_type() -> None:
    with pytest.raises(TypeError, match="ExtractedDocumentChunk"):
        _result(chunks=({"text": "not a chunk"},))  # type: ignore[arg-type]


def test_extraction_result_rejects_wrong_diagnostic_type() -> None:
    with pytest.raises(TypeError, match="AdapterDiagnostic"):
        _result(diagnostics=("not-a-diagnostic",))  # type: ignore[arg-type]


def test_extraction_result_rejects_wrong_dlq_type() -> None:
    with pytest.raises(TypeError, match="DLQRecord"):
        _result(dlq_records=({"payload_reference": "blob://x"},))  # type: ignore[arg-type]


def test_extraction_result_rejects_document_id_mismatch() -> None:
    with pytest.raises(ValueError, match="document_id"):
        _result(chunks=(_chunk(document_id="other-doc"),))


def test_extraction_result_rejects_duplicate_chunk_ids() -> None:
    with pytest.raises(ValueError, match="chunk_id"):
        _result(
            chunks=(
                _chunk(chunk_id="chunk-1", ordinal=0),
                _chunk(chunk_id="chunk-1", ordinal=1, text="Second chunk."),
            )
        )


def test_extraction_result_allows_empty_chunks() -> None:
    result = _result(chunks=())
    assert result.chunks == ()
    assert result.diagnostics == ()
    assert result.dlq_records == ()


def test_extraction_result_supports_partial_success() -> None:
    result = _result(diagnostics=(diagnostic(),), dlq_records=(dlq(),))
    assert len(result.chunks) == 1
    assert len(result.diagnostics) == 1
    assert len(result.dlq_records) == 1
    assert result.dlq_records[0].payload_reference == "blob://ingestion/dlq-1"
    assert not hasattr(result, "raw_payload")
    assert not hasattr(result, "payload")


def test_extraction_result_supports_complete_failure() -> None:
    result = _result(chunks=(), diagnostics=(diagnostic(),), dlq_records=(dlq(),))
    assert result.chunks == ()
    assert len(result.diagnostics) == 1
    assert len(result.dlq_records) == 1
    assert result.dlq_records[0].payload_reference == "blob://ingestion/dlq-1"


async def test_fake_extractor_structurally_satisfies_async_port() -> None:
    adapter = FakeDocumentExtractor(chunks=(_chunk(),))
    port: DocumentExtractionPort = as_document_extraction_port(adapter)

    assert inspect.iscoroutinefunction(port.extract)
    result = await port.extract()

    assert result.source_name == "fake-document"
    assert result.document_id == "doc-1"
    assert len(result.chunks) == 1
    assert isinstance(result.chunks[0], ExtractedDocumentChunk)
    assert list(inspect.signature(FakeDocumentExtractor.extract).parameters) == ["self"]
