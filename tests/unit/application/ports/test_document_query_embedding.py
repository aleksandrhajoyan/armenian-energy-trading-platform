"""Application-owned document query-text embedding port contract."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.application.ports import DocumentQueryEmbedding, DocumentQueryEmbeddingPort


class _FakeDocumentQueryEmbedder:
    """Test-only fake that structurally satisfies ``DocumentQueryEmbeddingPort``.

    Not a production embedding implementation. Not exported from application
    or infrastructure.
    """

    _VECTOR: tuple[float, ...] = (1.0, 0.0, -0.25)

    def __init__(self, *, unavailable: bool = False) -> None:
        self._unavailable = unavailable
        self.received_query_text: str | None = None

    async def embed_query(self, query_text: str) -> DocumentQueryEmbedding:
        if self._unavailable:
            raise DependencyUnavailableError("Document query embedding is unavailable.")
        if not query_text.strip():
            raise InvalidRequestError("Query text must be a non-empty string.")
        self.received_query_text = query_text
        return DocumentQueryEmbedding(vector=self._VECTOR)


def _as_query_embedding_port(
    embedder: _FakeDocumentQueryEmbedder,
) -> DocumentQueryEmbeddingPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return embedder


def _embedding(**overrides: object) -> DocumentQueryEmbedding:
    values: dict[str, object] = {
        "vector": (1.0, 0.0, -0.25),
    }
    values.update(overrides)
    return DocumentQueryEmbedding(**values)  # type: ignore[arg-type]


def test_embedding_is_valid() -> None:
    embedding = _embedding()
    assert embedding.vector == (1.0, 0.0, -0.25)
    assert isinstance(embedding.vector, tuple)


def test_embedding_is_immutable() -> None:
    embedding = _embedding()
    with pytest.raises(FrozenInstanceError):
        embedding.vector = (0.0,)  # type: ignore[misc]


def test_embedding_uses_slots() -> None:
    embedding = _embedding()
    assert hasattr(type(embedding), "__slots__")


def test_embedding_accepts_one_finite_float() -> None:
    embedding = _embedding(vector=(1.5,))
    assert embedding.vector == (1.5,)


def test_embedding_accepts_finite_positive_negative_and_zero_floats() -> None:
    embedding = _embedding(vector=(1.5, 0.0, -2.25))
    assert embedding.vector == (1.5, 0.0, -2.25)


def test_embedding_vector_must_be_a_tuple() -> None:
    with pytest.raises(TypeError, match="vector must be a tuple"):
        _embedding(vector=[1.0, 0.0])  # type: ignore[arg-type]


def test_embedding_rejects_empty_vector() -> None:
    with pytest.raises(ValueError, match="vector must contain at least one element"):
        _embedding(vector=())


def test_embedding_rejects_nan() -> None:
    with pytest.raises(ValueError, match="vector elements must be finite"):
        _embedding(vector=(1.0, nan))


def test_embedding_rejects_positive_infinity() -> None:
    with pytest.raises(ValueError, match="vector elements must be finite"):
        _embedding(vector=(1.0, inf))


def test_embedding_rejects_negative_infinity() -> None:
    with pytest.raises(ValueError, match="vector elements must be finite"):
        _embedding(vector=(1.0, -inf))


def test_embedding_rejects_non_float_vector_member() -> None:
    with pytest.raises(TypeError, match="vector elements must be finite"):
        _embedding(vector=(1.0, 1))  # type: ignore[arg-type]


def test_embedding_rejects_boolean_vector_member() -> None:
    with pytest.raises(TypeError, match="vector elements must be finite"):
        _embedding(vector=(True, 1.0))  # type: ignore[arg-type]


def test_embedding_rejects_extra_fields() -> None:
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        DocumentQueryEmbedding(vector=(1.0,), provider="openai")  # type: ignore[call-arg]


def test_embedding_value_equality_is_deterministic() -> None:
    first = _embedding(vector=(1.0, -0.5))
    second = _embedding(vector=(1.0, -0.5))
    different = _embedding(vector=(1.0, 0.5))
    assert first == second
    assert first is not second
    assert first != different


def test_fake_does_not_inherit_the_port() -> None:
    assert DocumentQueryEmbeddingPort not in _FakeDocumentQueryEmbedder.__mro__


def test_fake_structurally_satisfies_query_embedding_port() -> None:
    port: DocumentQueryEmbeddingPort = _as_query_embedding_port(_FakeDocumentQueryEmbedder())
    assert inspect.iscoroutinefunction(port.embed_query)
    assert list(inspect.signature(_FakeDocumentQueryEmbedder.embed_query).parameters) == [
        "self",
        "query_text",
    ]
    annotation = inspect.signature(_FakeDocumentQueryEmbedder.embed_query).return_annotation
    assert annotation in {DocumentQueryEmbedding, "DocumentQueryEmbedding"}


async def test_fake_receives_exact_query_text() -> None:
    query_text = "Keep this exact query text, including punctuation!"
    fake = _FakeDocumentQueryEmbedder()
    port = _as_query_embedding_port(fake)
    result = await port.embed_query(query_text)
    assert fake.received_query_text is query_text
    assert fake.received_query_text == query_text
    assert isinstance(result, DocumentQueryEmbedding)
    assert result.vector == (1.0, 0.0, -0.25)


async def test_fake_does_not_transform_query_text() -> None:
    query_text = "  surrounding spaces are preserved  "
    fake = _FakeDocumentQueryEmbedder()
    port = _as_query_embedding_port(fake)
    await port.embed_query(query_text)
    assert fake.received_query_text == query_text
    assert fake.received_query_text != query_text.strip()


@pytest.mark.parametrize("query_text", ["", "   "])
async def test_fake_rejects_blank_query_text_without_echoing_it(query_text: str) -> None:
    fake = _FakeDocumentQueryEmbedder()
    port = _as_query_embedding_port(fake)
    with pytest.raises(
        InvalidRequestError, match="Query text must be a non-empty string"
    ) as caught:
        await port.embed_query(query_text)
    assert fake.received_query_text is None
    assert repr(query_text) not in caught.value.message
    assert "   " not in caught.value.message


async def test_fake_can_represent_sanitized_dependency_unavailable_error() -> None:
    query_text = "Confidential regulatory search query."
    port = _as_query_embedding_port(_FakeDocumentQueryEmbedder(unavailable=True))
    with pytest.raises(
        DependencyUnavailableError, match="Document query embedding is unavailable"
    ) as caught:
        await port.embed_query(query_text)
    message = caught.value.message
    assert query_text not in message
    assert "Confidential" not in message
    assert "traceback" not in message.lower()
    assert "http://" not in message
    assert "api_key" not in message.lower()
