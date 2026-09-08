"""OpenAI infrastructure adapter for document-chunk embedding.

This class structurally implements ``DocumentEmbeddingPort``. It does not
own the ``AsyncOpenAI`` lifecycle, load API keys, select a default model, or
wire ``create_app()``.

OpenAI SDK types terminate here. Callers receive only
``DocumentChunkEmbedding`` values.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from openai import AsyncOpenAI, OpenAIError

from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.application.ports.document_embedding import DocumentChunkEmbedding
from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk

_MSG_INVALID_CHUNKS: Final[str] = "Document embedding chunks must be extracted document chunks."
_MSG_UNAVAILABLE: Final[str] = "Document embedding is unavailable."


class OpenAIDocumentEmbeddingAdapter:
    """OpenAI embeddings adapter for already-normalized document chunks."""

    def __init__(self, *, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    async def embed(
        self,
        chunks: tuple[ExtractedDocumentChunk, ...],
    ) -> tuple[DocumentChunkEmbedding, ...]:
        """Return one embedding per input chunk, preserving order and identity."""

        if not isinstance(chunks, tuple):
            raise InvalidRequestError(_MSG_INVALID_CHUNKS)
        if not all(isinstance(chunk, ExtractedDocumentChunk) for chunk in chunks):
            raise InvalidRequestError(_MSG_INVALID_CHUNKS)
        if not chunks:
            return ()
        texts = [chunk.text for chunk in chunks]
        try:
            response = await self._client.embeddings.create(
                model=self._model,
                input=texts,
                encoding_format="float",
            )
        except OpenAIError as exc:
            raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc
        return _to_chunk_embeddings(chunks, response)


def _ordered_provider_items(data: object, expected: int) -> tuple[object, ...]:
    if not isinstance(data, Sequence) or isinstance(data, (str, bytes, bytearray)):
        raise DependencyUnavailableError(_MSG_UNAVAILABLE)
    if len(data) != expected:
        raise DependencyUnavailableError(_MSG_UNAVAILABLE)
    indexed: list[tuple[int, object]] = []
    for position, item in enumerate(data):
        index = getattr(item, "index", None)
        if index is None:
            indexed.append((position, item))
            continue
        if isinstance(index, bool) or not isinstance(index, int):
            raise DependencyUnavailableError(_MSG_UNAVAILABLE)
        indexed.append((index, item))
    if {index for index, _item in indexed} != set(range(expected)):
        raise DependencyUnavailableError(_MSG_UNAVAILABLE)
    indexed.sort(key=lambda pair: pair[0])
    return tuple(item for _index, item in indexed)


def _to_chunk_embeddings(
    chunks: tuple[ExtractedDocumentChunk, ...],
    response: object,
) -> tuple[DocumentChunkEmbedding, ...]:
    items = _ordered_provider_items(getattr(response, "data", None), len(chunks))
    embeddings: list[DocumentChunkEmbedding] = []
    for chunk, item in zip(chunks, items, strict=True):
        embedding = getattr(item, "embedding", None)
        if embedding is None:
            raise DependencyUnavailableError(_MSG_UNAVAILABLE)
        try:
            vector = tuple(embedding)
        except TypeError as exc:
            raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc
        try:
            embeddings.append(
                DocumentChunkEmbedding(
                    document_id=chunk.document_id,
                    chunk_id=chunk.chunk_id,
                    vector=vector,
                )
            )
        except (TypeError, ValueError) as exc:
            raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc
    dimensions = {len(item.vector) for item in embeddings}
    if len(dimensions) != 1:
        raise DependencyUnavailableError(_MSG_UNAVAILABLE)
    return tuple(embeddings)
