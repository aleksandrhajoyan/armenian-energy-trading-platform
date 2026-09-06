"""Application-owned document vector retrieval port contract."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from energy_trading.application.errors import (
    DependencyUnavailableError,
    InvalidRequestError,
)
from energy_trading.application.ports import (
    DocumentVectorSearchPort,
    DocumentVectorSearchQuery,
    ExtractedDocumentChunk,
)


class _FakeDocumentVectorSearch:
    """Test-only fake that structurally satisfies ``DocumentVectorSearchPort``.

    Not a production search implementation. Not exported from application or
    infrastructure.
    """

    def __init__(
        self,
        *,
        hits: tuple[ExtractedDocumentChunk, ...] = (),
        unavailable: bool = False,
        expected_dimension: int | None = None,
    ) -> None:
        self._hits = hits
        self._unavailable = unavailable
        self._expected_dimension = expected_dimension

    async def search(
        self,
        query: DocumentVectorSearchQuery,
    ) -> tuple[ExtractedDocumentChunk, ...]:
        if self._unavailable:
            raise DependencyUnavailableError("Document vector search is unavailable.")
        if self._expected_dimension is not None and len(query.vector) != self._expected_dimension:
            raise InvalidRequestError("Query vector dimension is incompatible with the index.")
        identities = [(item.document_id, item.chunk_id) for item in self._hits]
        if len(identities) != len(set(identities)):
            raise DependencyUnavailableError("Document vector search is unavailable.")
        if len(self._hits) > query.limit:
            raise DependencyUnavailableError("Document vector search is unavailable.")
        return self._hits


def _as_search_port(search: _FakeDocumentVectorSearch) -> DocumentVectorSearchPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return search


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


def _query(**overrides: object) -> DocumentVectorSearchQuery:
    values: dict[str, object] = {
        "vector": (1.0, 0.0, -0.25),
        "limit": 5,
    }
    values.update(overrides)
    return DocumentVectorSearchQuery(**values)  # type: ignore[arg-type]


def test_query_is_valid() -> None:
    query = _query()
    assert query.vector == (1.0, 0.0, -0.25)
    assert query.limit == 5
    assert isinstance(query.vector, tuple)


def test_query_is_immutable() -> None:
    query = _query()
    with pytest.raises(FrozenInstanceError):
        query.limit = 1  # type: ignore[misc]


def test_query_vector_must_be_a_tuple() -> None:
    with pytest.raises(TypeError, match="vector must be a tuple"):
        _query(vector=[1.0, 0.0])  # type: ignore[arg-type]


def test_query_rejects_empty_vector() -> None:
    with pytest.raises(ValueError, match="vector must contain at least one element"):
        _query(vector=())


def test_query_accepts_finite_positive_negative_and_zero_floats() -> None:
    query = _query(vector=(1.5, 0.0, -2.25))
    assert query.vector == (1.5, 0.0, -2.25)


def test_query_rejects_nan() -> None:
    with pytest.raises(ValueError, match="vector elements must be finite"):
        _query(vector=(1.0, nan))


def test_query_rejects_positive_infinity() -> None:
    with pytest.raises(ValueError, match="vector elements must be finite"):
        _query(vector=(1.0, inf))


def test_query_rejects_negative_infinity() -> None:
    with pytest.raises(ValueError, match="vector elements must be finite"):
        _query(vector=(1.0, -inf))


def test_query_rejects_non_float_vector_member() -> None:
    with pytest.raises(TypeError, match="vector elements must be finite"):
        _query(vector=(1.0, 1))  # type: ignore[arg-type]


def test_query_accepts_positive_integer_limit() -> None:
    query = _query(limit=3)
    assert query.limit == 3


def test_query_rejects_zero_limit() -> None:
    with pytest.raises(ValueError, match="limit must be greater than 0"):
        _query(limit=0)


def test_query_rejects_negative_limit() -> None:
    with pytest.raises(ValueError, match="limit must be greater than 0"):
        _query(limit=-1)


@pytest.mark.parametrize("limit", [True, False])
def test_query_rejects_boolean_limit(limit: bool) -> None:
    with pytest.raises(TypeError, match="limit must be an integer"):
        _query(limit=limit)


def test_fake_structurally_satisfies_search_port() -> None:
    port: DocumentVectorSearchPort = _as_search_port(_FakeDocumentVectorSearch())
    assert inspect.iscoroutinefunction(port.search)
    assert list(inspect.signature(_FakeDocumentVectorSearch.search).parameters) == [
        "self",
        "query",
    ]


async def test_zero_matches_returns_empty_tuple() -> None:
    port = _as_search_port(_FakeDocumentVectorSearch(hits=()))
    results = await port.search(_query())
    assert results == ()


async def test_returns_one_result() -> None:
    chunk = _chunk()
    port = _as_search_port(_FakeDocumentVectorSearch(hits=(chunk,)))
    results = await port.search(_query(limit=5))
    assert results == (chunk,)
    assert isinstance(results[0], ExtractedDocumentChunk)


async def test_returns_multiple_results_in_ranked_order() -> None:
    first = _chunk(chunk_id="chunk-a", ordinal=0, text="Most relevant.")
    second = _chunk(chunk_id="chunk-b", ordinal=1, text="Less relevant.")
    third = _chunk(chunk_id="chunk-c", ordinal=2, text="Least relevant.")
    port = _as_search_port(_FakeDocumentVectorSearch(hits=(first, second, third)))
    results = await port.search(_query(limit=5))
    assert results == (first, second, third)
    assert [item.chunk_id for item in results] == ["chunk-a", "chunk-b", "chunk-c"]


async def test_fewer_than_requested_limit_is_valid() -> None:
    first = _chunk(chunk_id="chunk-1", ordinal=0, text="First.")
    second = _chunk(chunk_id="chunk-2", ordinal=1, text="Second.")
    port = _as_search_port(_FakeDocumentVectorSearch(hits=(first, second)))
    results = await port.search(_query(limit=5))
    assert len(results) == 2
    assert len(results) < 5


async def test_never_returns_more_than_requested_limit() -> None:
    hits = (
        _chunk(chunk_id="chunk-1", ordinal=0, text="First."),
        _chunk(chunk_id="chunk-2", ordinal=1, text="Second."),
    )
    port = _as_search_port(_FakeDocumentVectorSearch(hits=hits))
    results = await port.search(_query(limit=2))
    assert len(results) <= 2
    assert results == hits


async def test_same_chunk_id_under_different_documents_is_allowed() -> None:
    first = _chunk(document_id="doc-a", chunk_id="chunk-shared", text="Alpha.")
    second = _chunk(document_id="doc-b", chunk_id="chunk-shared", text="Beta.")
    port = _as_search_port(_FakeDocumentVectorSearch(hits=(first, second)))
    results = await port.search(_query(limit=5))
    assert results == (first, second)


async def test_duplicate_logical_identity_is_dependency_unavailable() -> None:
    first = _chunk(document_id="doc-1", chunk_id="chunk-1", text="Confidential clause.")
    duplicate = _chunk(document_id="doc-1", chunk_id="chunk-1", text="Confidential clause.")
    port = _as_search_port(_FakeDocumentVectorSearch(hits=(first, duplicate)))
    query = _query(vector=(0.5, -1.0, 2.0), limit=5)
    with pytest.raises(
        DependencyUnavailableError, match="Document vector search is unavailable"
    ) as caught:
        await port.search(query)
    message = caught.value.message
    assert first.text not in message
    assert str(query.vector) not in message


async def test_too_many_backend_hits_is_dependency_unavailable() -> None:
    hits = (
        _chunk(chunk_id="chunk-1", ordinal=0, text="Secret first."),
        _chunk(chunk_id="chunk-2", ordinal=1, text="Secret second."),
        _chunk(chunk_id="chunk-3", ordinal=2, text="Secret third."),
    )
    port = _as_search_port(_FakeDocumentVectorSearch(hits=hits))
    query = _query(vector=(9.0, 8.0), limit=2)
    with pytest.raises(
        DependencyUnavailableError, match="Document vector search is unavailable"
    ) as caught:
        await port.search(query)
    message = caught.value.message
    assert hits[0].text not in message
    assert str(query.vector) not in message


async def test_backend_failure_is_sanitized_dependency_unavailable() -> None:
    chunk = _chunk(text="Confidential regulatory clause.")
    port = _as_search_port(_FakeDocumentVectorSearch(hits=(chunk,), unavailable=True))
    query = _query(vector=(3.0, -4.0, 5.0), limit=3)
    with pytest.raises(
        DependencyUnavailableError, match="Document vector search is unavailable"
    ) as caught:
        await port.search(query)
    message = caught.value.message
    assert chunk.text not in message
    assert str(query.vector) not in message
    assert "Confidential" not in message
    assert "traceback" not in message.lower()
    assert "http://" not in message
    assert "api_key" not in message.lower()


async def test_incompatible_query_dimension_is_sanitized_invalid_request() -> None:
    chunk = _chunk(text="Indexed regulatory clause.")
    port = _as_search_port(
        _FakeDocumentVectorSearch(hits=(chunk,), expected_dimension=3),
    )
    query = _query(vector=(1.0, 2.0), limit=5)
    with pytest.raises(
        InvalidRequestError, match="Query vector dimension is incompatible"
    ) as caught:
        await port.search(query)
    message = caught.value.message
    assert str(query.vector) not in message
    assert chunk.text not in message
    assert "1.0" not in message
