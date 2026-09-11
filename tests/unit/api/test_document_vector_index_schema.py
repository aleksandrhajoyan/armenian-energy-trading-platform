"""Document Vector Index HTTP request DTOs stay API-owned transport contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from energy_trading.api.schemas.document_vector_index import (
    DocumentVectorIndexChunkRequest,
    DocumentVectorIndexRequest,
)

_PROVIDER_FIELD_NAMES = frozenset(
    {
        "openai",
        "qdrant",
        "api_key",
        "model",
        "collection",
        "vector",
        "embedding",
        "url",
        "path",
        "bytes",
        "file",
        "upload",
        "score",
        "metadata",
    }
)


def _chunk_payload(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "document_id": "doc-1",
        "chunk_id": "chunk-1",
        "text": "already normalized chunk text",
        "ordinal": 0,
        "page_number": 1,
    }
    values.update(overrides)
    return values


def test_chunk_request_happy_path_preserves_typed_field_values() -> None:
    chunk = DocumentVectorIndexChunkRequest.model_validate(_chunk_payload())
    assert chunk.document_id == "doc-1"
    assert chunk.chunk_id == "chunk-1"
    assert chunk.text == "already normalized chunk text"
    assert chunk.ordinal == 0
    assert chunk.page_number == 1


def test_chunk_request_preserves_optional_page_number_none() -> None:
    chunk = DocumentVectorIndexChunkRequest(
        document_id="doc-1",
        chunk_id="chunk-1",
        text="body",
        ordinal=2,
    )
    assert chunk.page_number is None


def test_outer_request_preserves_chunk_tuple_order() -> None:
    first = DocumentVectorIndexChunkRequest.model_validate(_chunk_payload())
    second = DocumentVectorIndexChunkRequest.model_validate(
        _chunk_payload(chunk_id="chunk-2", ordinal=1, text="second chunk")
    )
    request = DocumentVectorIndexRequest(chunks=(first, second))
    assert request.chunks == (first, second)
    assert request.chunks[0].chunk_id == "chunk-1"
    assert request.chunks[1].chunk_id == "chunk-2"
    assert request.chunks[0].text == "already normalized chunk text"
    assert request.chunks[1].text == "second chunk"


def test_models_are_frozen() -> None:
    chunk = DocumentVectorIndexChunkRequest.model_validate(_chunk_payload())
    request = DocumentVectorIndexRequest(chunks=(chunk,))
    with pytest.raises(ValidationError):
        chunk.document_id = "other"
    with pytest.raises(ValidationError):
        request.chunks = ()


def test_unknown_fields_are_forbidden() -> None:
    with pytest.raises(ValidationError):
        DocumentVectorIndexChunkRequest.model_validate(_chunk_payload(collection="docs"))
    chunk = DocumentVectorIndexChunkRequest.model_validate(_chunk_payload())
    with pytest.raises(ValidationError):
        DocumentVectorIndexRequest.model_validate(
            {
                "chunks": [chunk.model_dump()],
                "embedding_model": "text-embedding-3-large",
            }
        )


def test_invalid_ordinal_type_fails_validation() -> None:
    with pytest.raises(ValidationError):
        DocumentVectorIndexChunkRequest.model_validate(_chunk_payload(ordinal=["0"]))


def test_invalid_page_number_type_fails_validation() -> None:
    with pytest.raises(ValidationError):
        DocumentVectorIndexChunkRequest.model_validate(_chunk_payload(page_number=["1"]))


def test_wrong_chunks_container_or_member_type_fails_validation() -> None:
    with pytest.raises(ValidationError):
        DocumentVectorIndexRequest.model_validate({"chunks": {"document_id": "doc-1"}})
    with pytest.raises(ValidationError):
        DocumentVectorIndexRequest.model_validate({"chunks": ("not-a-chunk",)})


def test_transport_models_do_not_expose_provider_or_upload_fields() -> None:
    field_names = {
        *DocumentVectorIndexChunkRequest.model_fields,
        *DocumentVectorIndexRequest.model_fields,
    }
    leaked = sorted(name for name in field_names if name in _PROVIDER_FIELD_NAMES)
    assert leaked == []
    assert tuple(DocumentVectorIndexChunkRequest.model_fields) == (
        "document_id",
        "chunk_id",
        "text",
        "ordinal",
        "page_number",
    )
    assert tuple(DocumentVectorIndexRequest.model_fields) == ("chunks",)


def test_module_does_not_define_a_response_or_execute_contract() -> None:
    import energy_trading.api.schemas.document_vector_index as module

    assert not hasattr(module, "DocumentVectorIndexResponse")
    assert not hasattr(DocumentVectorIndexChunkRequest, "execute")
    assert not hasattr(DocumentVectorIndexRequest, "execute")
    assert "execute" not in DocumentVectorIndexChunkRequest.model_fields
    assert "execute" not in DocumentVectorIndexRequest.model_fields
