"""Document vector-search query preparation composes embedding into a search query."""

from __future__ import annotations

import inspect

import pytest

from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.application.orchestration import DocumentVectorSearchQueryPreparationService
from energy_trading.application.ports.document_query_embedding import (
    DocumentQueryEmbedding,
    DocumentQueryEmbeddingPort,
)
from energy_trading.application.ports.document_vector_search import DocumentVectorSearchQuery

_SENTINEL_VECTOR: tuple[float, ...] = (1.0, 0.0, -0.25)
_UNAVAILABLE_MESSAGE = "Document query embedding is unavailable."
_BLANK_QUERY_MESSAGE = "Query text must be a non-empty string."


class _FakeDocumentQueryEmbedder:
    """Test-only fake that structurally satisfies ``DocumentQueryEmbeddingPort``.

    Not a production embedding implementation. Not exported from application
    or infrastructure.
    """

    def __init__(
        self,
        *,
        vector: tuple[float, ...] = _SENTINEL_VECTOR,
        error: BaseException | None = None,
        reject_blank: bool = True,
    ) -> None:
        self._vector = vector
        self._error = error
        self._reject_blank = reject_blank
        self.calls: list[str] = []
        self.received_query_text: str | None = None

    async def embed_query(self, query_text: str) -> DocumentQueryEmbedding:
        self.calls.append(query_text)
        self.received_query_text = query_text
        if self._error is not None:
            raise self._error
        if self._reject_blank and not query_text.strip():
            raise InvalidRequestError(_BLANK_QUERY_MESSAGE)
        return DocumentQueryEmbedding(vector=self._vector)


def _as_query_embedding_port(
    embedder: _FakeDocumentQueryEmbedder,
) -> DocumentQueryEmbeddingPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return embedder


def _service(
    embedder: _FakeDocumentQueryEmbedder | None = None,
) -> tuple[DocumentVectorSearchQueryPreparationService, _FakeDocumentQueryEmbedder]:
    fake = _FakeDocumentQueryEmbedder() if embedder is None else embedder
    return DocumentVectorSearchQueryPreparationService(_as_query_embedding_port(fake)), fake


def test_fake_does_not_inherit_the_port() -> None:
    assert DocumentQueryEmbeddingPort not in _FakeDocumentQueryEmbedder.__mro__


def test_constructor_accepts_a_structural_query_embedding_port() -> None:
    signature = inspect.signature(DocumentVectorSearchQueryPreparationService.__init__)
    assert tuple(signature.parameters) == ("self", "document_query_embedding_port")
    assert (
        signature.parameters["document_query_embedding_port"].annotation
        is DocumentQueryEmbeddingPort
    )
    service, fake = _service()
    assert isinstance(service, DocumentVectorSearchQueryPreparationService)
    assert DocumentQueryEmbeddingPort not in type(fake).__mro__


def test_prepare_signature_is_keyword_only_query_text_and_limit() -> None:
    signature = inspect.signature(DocumentVectorSearchQueryPreparationService.prepare)
    assert tuple(signature.parameters) == ("self", "query_text", "limit")
    assert signature.parameters["query_text"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["limit"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["query_text"].annotation is str
    assert signature.parameters["limit"].annotation is int
    assert signature.return_annotation is DocumentVectorSearchQuery
    assert inspect.iscoroutinefunction(DocumentVectorSearchQueryPreparationService.prepare)


async def test_query_text_reaches_embed_query_unchanged() -> None:
    query_text = "Keep this exact query text, including punctuation!"
    service, fake = _service()

    await service.prepare(query_text=query_text, limit=5)

    assert fake.calls == [query_text]
    assert fake.received_query_text is query_text
    assert fake.received_query_text == query_text


async def test_query_text_surrounding_whitespace_is_not_trimmed() -> None:
    query_text = "  surrounding spaces are preserved  "
    service, fake = _service()

    await service.prepare(query_text=query_text, limit=3)

    assert fake.received_query_text is query_text
    assert fake.received_query_text == query_text
    assert fake.received_query_text != query_text.strip()
    assert fake.calls == [query_text]


async def test_embedding_port_is_awaited_exactly_once() -> None:
    service, fake = _service()

    await service.prepare(query_text="one regulatory query", limit=4)

    assert len(fake.calls) == 1


async def test_returned_query_uses_exact_embedding_vector_and_caller_limit() -> None:
    vector = (0.5, -1.25, 2.0)
    limit = 7
    service, _fake = _service(_FakeDocumentQueryEmbedder(vector=vector))

    result = await service.prepare(query_text="sentinel query", limit=limit)

    assert isinstance(result, DocumentVectorSearchQuery)
    assert result.vector == vector
    assert result.limit == limit
    assert result == DocumentVectorSearchQuery(vector=vector, limit=limit)


async def test_embedding_failure_propagates_without_fabricating_a_query() -> None:
    error = DependencyUnavailableError(_UNAVAILABLE_MESSAGE)
    fake = _FakeDocumentQueryEmbedder(error=error)
    service, _ = _service(fake)

    with pytest.raises(DependencyUnavailableError) as caught:
        await service.prepare(query_text="Confidential regulatory search query.", limit=5)

    assert caught.value is error
    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert fake.calls == ["Confidential regulatory search query."]


@pytest.mark.parametrize("query_text", ["", "   "])
async def test_blank_query_rejection_propagates_without_fallback_query(
    query_text: str,
) -> None:
    service, fake = _service()

    with pytest.raises(
        InvalidRequestError, match="Query text must be a non-empty string"
    ) as caught:
        await service.prepare(query_text=query_text, limit=5)

    assert caught.value.message == _BLANK_QUERY_MESSAGE
    assert repr(query_text) not in caught.value.message
    assert "   " not in caught.value.message
    assert fake.calls == [query_text]


@pytest.mark.parametrize("limit", [0, -1])
async def test_invalid_limit_preserves_query_validation_after_embedding(limit: int) -> None:
    service, fake = _service()

    with pytest.raises(ValueError, match="limit must be greater than 0"):
        await service.prepare(query_text="valid query text", limit=limit)

    assert fake.calls == ["valid query text"]


@pytest.mark.parametrize("limit", [True, False])
async def test_boolean_limit_preserves_query_type_error_after_embedding(limit: bool) -> None:
    service, fake = _service()

    with pytest.raises(TypeError, match="limit must be an integer"):
        await service.prepare(query_text="valid query text", limit=limit)

    assert fake.calls == ["valid query text"]


async def test_equivalent_inputs_produce_value_equivalent_queries() -> None:
    query_text = "same regulatory query"
    vector = (1.5, 0.0, -0.75)
    first_service, _ = _service(_FakeDocumentQueryEmbedder(vector=vector))
    second_service, _ = _service(_FakeDocumentQueryEmbedder(vector=vector))

    first = await first_service.prepare(query_text=query_text, limit=4)
    second = await second_service.prepare(query_text=query_text, limit=4)

    assert first == second
    assert first is not second
    assert first.vector == second.vector
    assert first.limit == second.limit
