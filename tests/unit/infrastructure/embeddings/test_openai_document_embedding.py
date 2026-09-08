"""Offline unit tests for the OpenAI document-chunk embedding adapter.

No live OpenAI network call, API key, or real ``AsyncOpenAI`` client is used.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from math import inf, nan
from types import SimpleNamespace
from typing import Any, cast

import pytest
from openai import APIConnectionError, OpenAIError

from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.application.ports.document_embedding import (
    DocumentChunkEmbedding,
    DocumentEmbeddingPort,
)
from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk
from energy_trading.infrastructure.embeddings.openai_document_embedding import (
    OpenAIDocumentEmbeddingAdapter,
)

_MODEL = "text-embedding-3-small"
_VECTOR = [0.125, -0.25, 0.5]
_VECTOR_B = [0.5, 0.0, -1.0]
_UNAVAILABLE_MESSAGE = "Document embedding is unavailable."
_INVALID_CHUNKS_MESSAGE = "Document embedding chunks must be extracted document chunks."
_PROVIDER_LEAK = "sk-test-leak Confidential regulatory clause."
_CONFIDENTIAL_TEXT = "Confidential regulatory clause."


@dataclass
class _FakeEmbeddings:
    """Test-only embeddings resource. Not a production OpenAI client."""

    create_calls: list[dict[str, object]] = field(default_factory=list)
    error: BaseException | None = None
    response: object | None = None

    async def create(self, **kwargs: object) -> object:
        self.create_calls.append(kwargs)
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


@dataclass
class _RecordingEndpoint:
    create_calls: list[dict[str, object]] = field(default_factory=list)

    async def create(self, **kwargs: object) -> object:
        self.create_calls.append(kwargs)
        raise AssertionError("non-embeddings OpenAI resource must not be called")


@dataclass
class _FakeOpenAIClient:
    """Structural fake for the injected ``AsyncOpenAI`` embeddings surface."""

    embeddings: _FakeEmbeddings = field(default_factory=_FakeEmbeddings)
    chat: _RecordingEndpoint = field(default_factory=_RecordingEndpoint)
    completions: _RecordingEndpoint = field(default_factory=_RecordingEndpoint)
    responses: _RecordingEndpoint = field(default_factory=_RecordingEndpoint)


def _response(
    vectors: list[list[float] | object],
    *,
    indexes: list[int] | None = None,
) -> object:
    if indexes is None:
        return SimpleNamespace(data=[SimpleNamespace(embedding=vector) for vector in vectors])
    return SimpleNamespace(
        data=[
            SimpleNamespace(embedding=vector, index=index)
            for vector, index in zip(vectors, indexes, strict=True)
        ]
    )


def _chunk(
    *,
    document_id: str = "doc-1",
    chunk_id: str = "chunk-1",
    ordinal: int = 0,
    text: str = "Normalized extracted text.",
    page_number: int | None = 1,
) -> ExtractedDocumentChunk:
    return ExtractedDocumentChunk(
        document_id=document_id,
        chunk_id=chunk_id,
        ordinal=ordinal,
        text=text,
        page_number=page_number,
    )


def _adapter(
    client: _FakeOpenAIClient,
    *,
    model: str = _MODEL,
) -> OpenAIDocumentEmbeddingAdapter:
    return OpenAIDocumentEmbeddingAdapter(
        client=cast(Any, client),
        model=model,
    )


def test_adapter_does_not_inherit_the_application_port() -> None:
    assert DocumentEmbeddingPort not in OpenAIDocumentEmbeddingAdapter.__mro__


def test_adapter_structurally_satisfies_document_embedding_port() -> None:
    adapter = _adapter(_FakeOpenAIClient())
    port: DocumentEmbeddingPort = adapter
    assert inspect.iscoroutinefunction(port.embed)
    signature = inspect.signature(OpenAIDocumentEmbeddingAdapter.embed)
    assert list(signature.parameters) == ["self", "chunks"]
    assert signature.return_annotation in {
        tuple[DocumentChunkEmbedding, ...],
        "tuple[DocumentChunkEmbedding, ...]",
    }


def test_constructor_is_keyword_only_client_and_model() -> None:
    signature = inspect.signature(OpenAIDocumentEmbeddingAdapter.__init__)
    assert tuple(signature.parameters) == ("self", "client", "model")
    assert signature.parameters["client"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["model"].kind is inspect.Parameter.KEYWORD_ONLY


def test_constructor_does_not_require_an_api_key_or_construct_a_client() -> None:
    client = _FakeOpenAIClient()
    adapter = _adapter(client)
    assert adapter._client is client
    assert adapter._model is _MODEL
    assert not hasattr(adapter, "api_key")


async def test_one_chunk_makes_exactly_one_float_embeddings_request() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = _response([_VECTOR])
    adapter = _adapter(client)
    chunk = _chunk(text=_CONFIDENTIAL_TEXT)

    result = await adapter.embed((chunk,))

    assert client.embeddings.create_calls == [
        {
            "model": _MODEL,
            "input": [_CONFIDENTIAL_TEXT],
            "encoding_format": "float",
        }
    ]
    assert client.embeddings.create_calls[0]["input"] == [_CONFIDENTIAL_TEXT]
    assert client.embeddings.create_calls[0]["input"][0] is chunk.text
    assert client.chat.create_calls == []
    assert client.completions.create_calls == []
    assert client.responses.create_calls == []
    assert result == (
        DocumentChunkEmbedding(
            document_id="doc-1",
            chunk_id="chunk-1",
            vector=(0.125, -0.25, 0.5),
        ),
    )
    assert type(result[0]) is DocumentChunkEmbedding
    assert type(result[0]).__module__ == DocumentChunkEmbedding.__module__


async def test_normalized_chunk_text_is_forwarded_without_rewriting() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = _response([_VECTOR])
    adapter = _adapter(client)
    text = "Keep  internal   spacing."
    chunk = _chunk(text=text)

    await adapter.embed((chunk,))

    forwarded = client.embeddings.create_calls[0]["input"][0]
    assert forwarded is chunk.text
    assert forwarded == "Keep  internal   spacing."


async def test_model_string_is_forwarded_unchanged() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = _response([_VECTOR])
    model = "  custom-embedding-model  "
    adapter = _adapter(client, model=model)

    await adapter.embed((_chunk(),))

    assert client.embeddings.create_calls[0]["model"] is model


async def test_multiple_chunks_preserve_text_order_identity_and_vectors() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = _response([_VECTOR, _VECTOR_B])
    adapter = _adapter(client)
    chunks = (
        _chunk(document_id="doc-a", chunk_id="chunk-z", ordinal=0, text="Last label first."),
        _chunk(document_id="doc-b", chunk_id="chunk-a", ordinal=1, text="First label second."),
    )

    result = await adapter.embed(chunks)

    assert client.embeddings.create_calls[0]["input"] == [
        "Last label first.",
        "First label second.",
    ]
    assert [item.document_id for item in result] == ["doc-a", "doc-b"]
    assert [item.chunk_id for item in result] == ["chunk-z", "chunk-a"]
    assert result[0].vector == (0.125, -0.25, 0.5)
    assert result[1].vector == (0.5, 0.0, -1.0)


async def test_provider_index_reorders_to_input_order() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = _response([_VECTOR_B, _VECTOR], indexes=[1, 0])
    adapter = _adapter(client)
    chunks = (
        _chunk(chunk_id="chunk-1", ordinal=0, text="First."),
        _chunk(chunk_id="chunk-2", ordinal=1, text="Second."),
    )

    result = await adapter.embed(chunks)

    assert [item.chunk_id for item in result] == ["chunk-1", "chunk-2"]
    assert result[0].vector == (0.125, -0.25, 0.5)
    assert result[1].vector == (0.5, 0.0, -1.0)


async def test_empty_input_returns_empty_tuple_without_provider_call() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = _response([_VECTOR])
    adapter = _adapter(client)

    result = await adapter.embed(())

    assert result == ()
    assert client.embeddings.create_calls == []
    assert client.chat.create_calls == []


async def test_non_tuple_chunks_are_invalid_without_provider_call() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = _response([_VECTOR])
    adapter = _adapter(client)

    with pytest.raises(InvalidRequestError, match=_INVALID_CHUNKS_MESSAGE) as caught:
        await adapter.embed([_chunk()])  # type: ignore[arg-type]

    assert caught.value.message == _INVALID_CHUNKS_MESSAGE
    assert client.embeddings.create_calls == []


async def test_non_chunk_tuple_is_invalid_without_exposing_text() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = _response([_VECTOR])
    adapter = _adapter(client)

    with pytest.raises(InvalidRequestError, match=_INVALID_CHUNKS_MESSAGE) as caught:
        await adapter.embed((_CONFIDENTIAL_TEXT,))  # type: ignore[arg-type]

    assert caught.value.message == _INVALID_CHUNKS_MESSAGE
    assert _CONFIDENTIAL_TEXT not in caught.value.message
    assert "Confidential" not in caught.value.message
    assert client.embeddings.create_calls == []


async def test_openai_sdk_failure_becomes_sanitized_dependency_unavailable() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.error = OpenAIError(_PROVIDER_LEAK)
    adapter = _adapter(client)
    chunk = _chunk(text=_CONFIDENTIAL_TEXT)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE) as caught:
        await adapter.embed((chunk,))

    assert type(caught.value) is DependencyUnavailableError
    assert not isinstance(caught.value, OpenAIError)
    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert _CONFIDENTIAL_TEXT not in caught.value.message
    assert "Confidential" not in caught.value.message
    assert "sk-test-leak" not in caught.value.message
    assert _PROVIDER_LEAK not in caught.value.message
    assert isinstance(caught.value.__cause__, OpenAIError)
    assert client.embeddings.create_calls == [
        {
            "model": _MODEL,
            "input": [_CONFIDENTIAL_TEXT],
            "encoding_format": "float",
        }
    ]


async def test_openai_connection_error_is_translated() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.error = APIConnectionError(request=None)  # type: ignore[arg-type]
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE) as caught:
        await adapter.embed((_chunk(text="Confidential regulatory clause."),))

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert "Confidential" not in caught.value.message
    assert isinstance(caught.value.__cause__, APIConnectionError)
    assert not isinstance(caught.value, APIConnectionError)


async def test_fewer_provider_embeddings_fail_closed() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = _response([_VECTOR])
    adapter = _adapter(client)
    chunks = (
        _chunk(chunk_id="chunk-1", ordinal=0, text="First."),
        _chunk(chunk_id="chunk-2", ordinal=1, text="Second."),
    )

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE) as caught:
        await adapter.embed(chunks)

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert "First." not in caught.value.message
    assert "Second." not in caught.value.message


async def test_more_provider_embeddings_fail_closed() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = _response([_VECTOR, _VECTOR_B])
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE) as caught:
        await adapter.embed((_chunk(),))

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert "Normalized extracted text." not in caught.value.message


async def test_missing_provider_data_is_dependency_unavailable() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = SimpleNamespace()
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE):
        await adapter.embed((_chunk(),))


async def test_duplicate_provider_indexes_fail_closed() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = _response([_VECTOR, _VECTOR_B], indexes=[0, 0])
    adapter = _adapter(client)
    chunks = (
        _chunk(chunk_id="chunk-1", ordinal=0, text="First."),
        _chunk(chunk_id="chunk-2", ordinal=1, text="Second."),
    )

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE):
        await adapter.embed(chunks)


@pytest.mark.parametrize(
    "embedding",
    [
        [],
        [1.0, nan],
        [1.0, inf],
        [1.0, 1],
    ],
)
async def test_malformed_provider_vector_is_dependency_unavailable(
    embedding: object,
) -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = SimpleNamespace(data=[SimpleNamespace(embedding=embedding)])
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE) as caught:
        await adapter.embed((_chunk(text=_CONFIDENTIAL_TEXT),))

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert _CONFIDENTIAL_TEXT not in caught.value.message
    assert "nan" not in caught.value.message.lower()
    assert "inf" not in caught.value.message.lower()


async def test_non_iterable_embedding_is_dependency_unavailable() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = SimpleNamespace(data=[SimpleNamespace(embedding=None)])
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE):
        await adapter.embed((_chunk(),))


async def test_inconsistent_vector_dimensions_fail_closed() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = _response([_VECTOR, [0.5, 0.0]])
    adapter = _adapter(client)
    chunks = (
        _chunk(chunk_id="chunk-1", ordinal=0, text="First."),
        _chunk(chunk_id="chunk-2", ordinal=1, text="Second."),
    )

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE) as caught:
        await adapter.embed(chunks)

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert "First." not in caught.value.message
    assert "Second." not in caught.value.message
