"""Offline unit tests for the OpenAI document query-embedding adapter.

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
from energy_trading.application.ports.document_query_embedding import (
    DocumentQueryEmbedding,
    DocumentQueryEmbeddingPort,
)
from energy_trading.infrastructure.embeddings.openai_query_embedding import (
    OpenAIDocumentQueryEmbeddingAdapter,
)

_SENTINEL_QUERY = "  regulatory sentinel  "
_MODEL = "text-embedding-3-small"
_VECTOR = [0.125, -0.25, 0.5]
_UNAVAILABLE_MESSAGE = "Document query embedding is unavailable."
_INVALID_QUERY_MESSAGE = "Query text must be a non-empty string."
_PROVIDER_LEAK = "sk-test-leak Confidential regulatory search query."


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


def _response(vectors: list[list[float] | object] | None) -> object:
    if vectors is None:
        return SimpleNamespace()
    return SimpleNamespace(data=[SimpleNamespace(embedding=vector) for vector in vectors])


def _adapter(
    client: _FakeOpenAIClient,
    *,
    model: str = _MODEL,
) -> OpenAIDocumentQueryEmbeddingAdapter:
    return OpenAIDocumentQueryEmbeddingAdapter(
        client=cast(Any, client),
        model=model,
    )


def test_adapter_does_not_inherit_the_application_port() -> None:
    assert DocumentQueryEmbeddingPort not in OpenAIDocumentQueryEmbeddingAdapter.__mro__


def test_adapter_structurally_satisfies_query_embedding_port() -> None:
    adapter = _adapter(_FakeOpenAIClient())
    port: DocumentQueryEmbeddingPort = adapter
    assert inspect.iscoroutinefunction(port.embed_query)
    signature = inspect.signature(OpenAIDocumentQueryEmbeddingAdapter.embed_query)
    assert list(signature.parameters) == ["self", "query_text"]
    assert signature.return_annotation in {DocumentQueryEmbedding, "DocumentQueryEmbedding"}


def test_constructor_is_keyword_only_client_and_model() -> None:
    signature = inspect.signature(OpenAIDocumentQueryEmbeddingAdapter.__init__)
    assert tuple(signature.parameters) == ("self", "client", "model")
    assert signature.parameters["client"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["model"].kind is inspect.Parameter.KEYWORD_ONLY


def test_constructor_does_not_require_an_api_key() -> None:
    client = _FakeOpenAIClient()
    adapter = _adapter(client)
    assert adapter._client is client
    assert adapter._model is _MODEL
    assert not hasattr(adapter, "api_key")


async def test_valid_query_makes_exactly_one_float_embeddings_request() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = _response([_VECTOR])
    adapter = _adapter(client)

    result = await adapter.embed_query(_SENTINEL_QUERY)

    assert client.embeddings.create_calls == [
        {
            "model": _MODEL,
            "input": _SENTINEL_QUERY,
            "encoding_format": "float",
        }
    ]
    assert client.embeddings.create_calls[0]["input"] is _SENTINEL_QUERY
    assert client.embeddings.create_calls[0]["input"] != _SENTINEL_QUERY.strip()
    assert client.chat.create_calls == []
    assert client.completions.create_calls == []
    assert client.responses.create_calls == []
    assert isinstance(result, DocumentQueryEmbedding)
    assert result.vector == (0.125, -0.25, 0.5)
    assert type(result) is DocumentQueryEmbedding
    assert type(result).__module__ == DocumentQueryEmbedding.__module__


async def test_model_string_is_forwarded_unchanged() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = _response([_VECTOR])
    model = "  custom-embedding-model  "
    adapter = _adapter(client, model=model)

    await adapter.embed_query("nonblank query")

    assert client.embeddings.create_calls[0]["model"] is model


@pytest.mark.parametrize("query_text", ["", "   ", "\t\n"])
async def test_blank_query_is_invalid_request_without_provider_call(
    query_text: str,
) -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = _response([_VECTOR])
    adapter = _adapter(client)

    with pytest.raises(InvalidRequestError, match=_INVALID_QUERY_MESSAGE) as caught:
        await adapter.embed_query(query_text)

    assert client.embeddings.create_calls == []
    assert caught.value.message == _INVALID_QUERY_MESSAGE
    assert repr(query_text) not in caught.value.message
    if query_text:
        assert query_text not in caught.value.message
    assert "   " not in caught.value.message
    assert "\t" not in caught.value.message
    assert "\n" not in caught.value.message


async def test_openai_sdk_failure_becomes_sanitized_dependency_unavailable() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.error = OpenAIError(_PROVIDER_LEAK)
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE) as caught:
        await adapter.embed_query(_SENTINEL_QUERY)

    assert type(caught.value) is DependencyUnavailableError
    assert not isinstance(caught.value, OpenAIError)
    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert _SENTINEL_QUERY not in caught.value.message
    assert "regulatory sentinel" not in caught.value.message
    assert "sk-test-leak" not in caught.value.message
    assert _PROVIDER_LEAK not in caught.value.message
    assert isinstance(caught.value.__cause__, OpenAIError)
    assert client.embeddings.create_calls == [
        {
            "model": _MODEL,
            "input": _SENTINEL_QUERY,
            "encoding_format": "float",
        }
    ]


async def test_openai_connection_error_is_translated() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.error = APIConnectionError(request=None)  # type: ignore[arg-type]
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE) as caught:
        await adapter.embed_query("Confidential regulatory search query.")

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert "Confidential" not in caught.value.message
    assert isinstance(caught.value.__cause__, APIConnectionError)
    assert not isinstance(caught.value, APIConnectionError)


async def test_empty_provider_data_is_dependency_unavailable() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = SimpleNamespace(data=[])
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE) as caught:
        await adapter.embed_query(_SENTINEL_QUERY)

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert _SENTINEL_QUERY not in caught.value.message
    assert client.embeddings.create_calls


async def test_missing_provider_data_is_dependency_unavailable() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = SimpleNamespace()
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE):
        await adapter.embed_query(_SENTINEL_QUERY)


async def test_multiple_embeddings_for_one_query_fail_closed() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = _response([_VECTOR, [1.0, 2.0, 3.0]])
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE) as caught:
        await adapter.embed_query(_SENTINEL_QUERY)

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert _SENTINEL_QUERY not in caught.value.message


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
        await adapter.embed_query(_SENTINEL_QUERY)

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert _SENTINEL_QUERY not in caught.value.message
    assert "nan" not in caught.value.message.lower()
    assert "inf" not in caught.value.message.lower()


async def test_non_iterable_embedding_is_dependency_unavailable() -> None:
    client = _FakeOpenAIClient()
    client.embeddings.response = SimpleNamespace(data=[SimpleNamespace(embedding=None)])
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE):
        await adapter.embed_query(_SENTINEL_QUERY)
