"""Typed OpenAI connection settings independent of process health and FastAPI.

These settings are loaded separately from ``AppSettings``. They are not
required for process health or ``create_app()``. This module does not import
the OpenAI SDK or construct a client.
"""

from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAISettings(BaseSettings):
    """OpenAI API credential configuration for the infrastructure client factory.

    The API key has no implicit default and must be supplied by environment or
    constructor. Model selection is not part of this settings object.
    """

    model_config = SettingsConfigDict(
        env_prefix="ENERGY_OPENAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    api_key: SecretStr = Field(
        min_length=1,
        repr=False,
        description="OpenAI API key. Never log or interpolate this value.",
    )

    @field_validator("api_key")
    @classmethod
    def reject_blank_api_key(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("must not be blank")
        return value


def load_openai_settings(*, env_file: str | Path | None = ".env") -> OpenAISettings:
    """Build OpenAI settings without a process-wide cache.

    Pass ``env_file=None`` in tests so a developer's local ``.env`` is ignored.
    """

    return OpenAISettings(_env_file=env_file)
