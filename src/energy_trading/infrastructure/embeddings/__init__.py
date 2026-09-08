"""Embedding infrastructure adapters.

This package exposes OpenAI query-text and document-chunk embedding adapters.
It does not construct ``AsyncOpenAI``, load credentials, or wire ``create_app()``.
"""

from energy_trading.infrastructure.embeddings.openai_document_embedding import (
    OpenAIDocumentEmbeddingAdapter,
)
from energy_trading.infrastructure.embeddings.openai_query_embedding import (
    OpenAIDocumentQueryEmbeddingAdapter,
)

__all__ = [
    "OpenAIDocumentEmbeddingAdapter",
    "OpenAIDocumentQueryEmbeddingAdapter",
]
