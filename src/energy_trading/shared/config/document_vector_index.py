"""Typed document vector index runtime settings.

These settings are loaded separately from ``AppSettings``, ``OpenAISettings``,
``QdrantSettings``, and ``RegulatoryIntelligenceRuntimeSettings``. They are
not required for process health or ``create_app()``. This module does not
import provider SDKs, construct clients, or build indexing runtime objects.

Environment variables:

* ``ENERGY_DOCUMENT_INDEX_DOCUMENT_EMBEDDING_MODEL``
* ``ENERGY_DOCUMENT_INDEX_QDRANT_COLLECTION_NAME``
* ``ENERGY_DOCUMENT_INDEX_QDRANT_VECTOR_SIZE``
"""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DocumentVectorIndexRuntimeSettings(BaseSettings):
    """Document vector index runtime-specific configuration.

    The document-embedding model identifier and Qdrant document-collection
    targeting have no implicit defaults and must be supplied by environment or
    constructor. Connection credentials, provider clients, adapters, and
    query/inference models are not part of this settings object.
    """

    model_config = SettingsConfigDict(
        env_prefix="ENERGY_DOCUMENT_INDEX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    document_embedding_model: str = Field(
        min_length=1,
        description="Model identifier for document-chunk embedding.",
    )
    qdrant_collection_name: str = Field(
        min_length=1,
        description="Qdrant collection name for indexed document vectors.",
    )
    qdrant_vector_size: int = Field(
        gt=0,
        description="Embedding dimension of the document vector collection.",
    )

    @field_validator(
        "document_embedding_model",
        "qdrant_collection_name",
        mode="before",
    )
    @classmethod
    def strip_required_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("must not be blank")
            return stripped
        return value

    @field_validator("qdrant_vector_size", mode="before")
    @classmethod
    def reject_boolean_integers(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("must be an integer, not a boolean")
        return value


def load_document_vector_index_runtime_settings(
    *,
    env_file: str | Path | None = ".env",
) -> DocumentVectorIndexRuntimeSettings:
    """Build document vector index runtime settings without a process-wide cache.

    Pass ``env_file=None`` in tests so a developer's local ``.env`` is ignored.
    """

    return DocumentVectorIndexRuntimeSettings(_env_file=env_file)
