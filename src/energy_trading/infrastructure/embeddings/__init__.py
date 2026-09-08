"""Query-text embedding infrastructure adapters.

This package exposes the OpenAI document query-embedding adapter. It does
not construct ``AsyncOpenAI``, load credentials, or wire ``create_app()``.
"""

from energy_trading.infrastructure.embeddings.openai_query_embedding import (
    OpenAIDocumentQueryEmbeddingAdapter,
)

__all__ = ["OpenAIDocumentQueryEmbeddingAdapter"]
