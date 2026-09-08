"""OpenAI infrastructure adapter for document query-text embedding.

This class structurally implements ``DocumentQueryEmbeddingPort``. It does
not own the ``AsyncOpenAI`` lifecycle, load API keys, select a default
model, or wire ``create_app()``.

OpenAI SDK types terminate here. Callers receive only
``DocumentQueryEmbedding``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from openai import AsyncOpenAI, OpenAIError

from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.application.ports.document_query_embedding import DocumentQueryEmbedding

_MSG_INVALID_QUERY: Final[str] = "Query text must be a non-empty string."
_MSG_UNAVAILABLE: Final[str] = "Document query embedding is unavailable."


class OpenAIDocumentQueryEmbeddingAdapter:
    """OpenAI embeddings adapter for already-normalized query text."""

    def __init__(self, *, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    async def embed_query(self, query_text: str) -> DocumentQueryEmbedding:
        """Return a finite embedding vector for one query string."""

        if not query_text.strip():
            raise InvalidRequestError(_MSG_INVALID_QUERY)
        try:
            response = await self._client.embeddings.create(
                model=self._model,
                input=query_text,
                encoding_format="float",
            )
        except OpenAIError as exc:
            raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc
        return _to_query_embedding(response)


def _to_query_embedding(response: object) -> DocumentQueryEmbedding:
    data = getattr(response, "data", None)
    if not isinstance(data, Sequence) or isinstance(data, (str, bytes, bytearray)):
        raise DependencyUnavailableError(_MSG_UNAVAILABLE)
    if len(data) != 1:
        raise DependencyUnavailableError(_MSG_UNAVAILABLE)
    embedding = getattr(data[0], "embedding", None)
    if embedding is None:
        raise DependencyUnavailableError(_MSG_UNAVAILABLE)
    try:
        vector = tuple(embedding)
    except TypeError as exc:
        raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc
    try:
        return DocumentQueryEmbedding(vector=vector)
    except (TypeError, ValueError) as exc:
        raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc
