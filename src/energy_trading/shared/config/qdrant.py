"""Typed Qdrant connection settings independent of process health and FastAPI.

These settings are loaded separately from ``AppSettings``. They are not
required for process health or ``create_app()``. This module does not import
the Qdrant SDK or construct a client.
"""

from pathlib import Path

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
