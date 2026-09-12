"""Typed Qdrant connection settings independent of process health and FastAPI.

These settings are loaded separately from ``AppSettings``. They are not
required for process health or ``create_app()``. This module does not import
the Qdrant SDK or construct a client.
"""

from enum import StrEnum
from pathlib import Path
from typing import Final

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class QdrantSettings(BaseSettings):
    """Qdrant HTTP connection configuration for the future vector-store adapter.

    Identity field ``host`` has no implicit default and must be supplied by
    environment or constructor. Operational values have safe non-secret defaults.
    """

    model_config = SettingsConfigDict(
        env_prefix="QDRANT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    host: str = Field(min_length=1, description="Qdrant hostname.")
    port: int = Field(default=6333, ge=1, le=65535, description="Qdrant HTTP/REST TCP port.")
    https: bool = Field(default=False, description="Use HTTPS for the Qdrant HTTP client.")
    api_key: SecretStr | None = Field(
        default=None,
        repr=False,
        description="Optional Qdrant API key. Never log or interpolate this value.",
    )
    timeout_seconds: int = Field(
        default=5,
        gt=0,
        description="Seconds for Qdrant HTTP request timeouts.",
    )

    @field_validator("host", mode="before")
    @classmethod
    def strip_required_host(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("must not be blank")
            return stripped
        return value

    @field_validator("port", "timeout_seconds", mode="before")
    @classmethod
    def reject_boolean_integers(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("must be an integer, not a boolean")
        return value

    @field_validator("api_key", mode="before")
    @classmethod
    def empty_api_key_to_none(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, SecretStr):
            raw = value.get_secret_value()
            if not raw.strip():
                return None
            return value
        if isinstance(value, str):
            if not value.strip():
                return None
            return value
        return value


def load_qdrant_settings(*, env_file: str | Path | None = ".env") -> QdrantSettings:
    """Build Qdrant settings without a process-wide cache.

    Pass ``env_file=None`` in tests so a developer's local ``.env`` is ignored.
    """

    return QdrantSettings(_env_file=env_file)


class QdrantDocumentVectorDistance(StrEnum):
    """Provider-neutral document-vector distance identifiers.

    Canonical values are lowercase Qdrant metric names. This enum does not
    import the Qdrant SDK and does not select a production default.
    """

    COSINE = "cosine"
    DOT = "dot"
    EUCLID = "euclid"
    MANHATTAN = "manhattan"


_CANONICAL_DOCUMENT_VECTOR_DISTANCES: Final[frozenset[str]] = frozenset(
    member.value for member in QdrantDocumentVectorDistance
)


class QdrantDocumentVectorDistanceSettings(BaseSettings):
    """Explicit document-vector distance configuration.

    This contract is separate from connection ``QdrantSettings``. It is not
    required for process health, ``create_app()``, or Qdrant HTTP client
    construction. There is no default metric.

    Environment variables:

    * ``QDRANT_DOCUMENT_VECTOR_DISTANCE``
    """

    model_config = SettingsConfigDict(
        env_prefix="QDRANT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    document_vector_distance: QdrantDocumentVectorDistance = Field(
        description="Document-vector distance. Must be cosine, dot, euclid, or manhattan.",
    )

    @field_validator("document_vector_distance", mode="before")
    @classmethod
    def require_canonical_distance(cls, value: object) -> object:
        if isinstance(value, QdrantDocumentVectorDistance):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if stripped not in _CANONICAL_DOCUMENT_VECTOR_DISTANCES:
                raise ValueError("must be one of: cosine, dot, euclid, manhattan")
            return stripped
        return value


def load_qdrant_document_vector_distance_settings(
    *,
    env_file: str | Path | None = ".env",
) -> QdrantDocumentVectorDistanceSettings:
    """Build document-vector distance settings without a process-wide cache.

    Pass ``env_file=None`` in tests so a developer's local ``.env`` is ignored.
    """

    return QdrantDocumentVectorDistanceSettings(_env_file=env_file)
