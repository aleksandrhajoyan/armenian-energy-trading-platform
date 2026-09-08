"""Typed Regulatory Intelligence runtime settings.

These settings are loaded separately from ``AppSettings``, ``OpenAISettings``,
and ``QdrantSettings``. They are not required for process health or
``create_app()``. This module does not import provider SDKs, construct
clients, or build Regulatory runtime objects.

Environment variables:

* ``ENERGY_REGULATORY_QUERY_EMBEDDING_MODEL``
* ``ENERGY_REGULATORY_CONSTRAINT_INFERENCE_MODEL``
* ``ENERGY_REGULATORY_QDRANT_COLLECTION_NAME``
* ``ENERGY_REGULATORY_QDRANT_VECTOR_SIZE``
"""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RegulatoryIntelligenceRuntimeSettings(BaseSettings):
    """Regulatory Intelligence runtime-specific configuration.

    Model identifiers and Qdrant document-collection targeting have no implicit
    defaults and must be supplied by environment or constructor. Connection
    credentials, provider clients, adapters, and prompts are not part of this
    settings object.
    """

    model_config = SettingsConfigDict(
        env_prefix="ENERGY_REGULATORY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    query_embedding_model: str = Field(
        min_length=1,
        description="Model identifier for Regulatory query-text embedding.",
    )
    constraint_inference_model: str = Field(
        min_length=1,
        description="Model identifier for Regulatory constraint inference.",
    )
    qdrant_collection_name: str = Field(
        min_length=1,
        description="Qdrant collection name for Regulatory document vectors.",
    )
    qdrant_vector_size: int = Field(
        gt=0,
        description="Embedding dimension of the Regulatory document vector collection.",
    )

    @field_validator(
        "query_embedding_model",
        "constraint_inference_model",
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


def load_regulatory_intelligence_runtime_settings(
    *,
    env_file: str | Path | None = ".env",
) -> RegulatoryIntelligenceRuntimeSettings:
    """Build Regulatory Intelligence runtime settings without a process-wide cache.

    Pass ``env_file=None`` in tests so a developer's local ``.env`` is ignored.
    """

    return RegulatoryIntelligenceRuntimeSettings(_env_file=env_file)
