"""Typed application settings independent of FastAPI."""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    """Runtime environment. Database/ML/LLM environments are not modeled yet."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class AppSettings(BaseSettings):
    """Application-level configuration needed for process startup and health.

    Extra unrelated environment variables are ignored so reserved/future
    service keys in `.env` cannot crash startup.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(
        default="AI Energy Trading Platform",
        description="Human-readable service name returned by health checks.",
    )
    environment: AppEnvironment = Field(
        default=AppEnvironment.DEVELOPMENT,
        validation_alias=AliasChoices("environment", "APP_ENV", "ENVIRONMENT"),
        description="Deployment environment.",
    )
    api_prefix: str = Field(
        default="/api/v1",
        description="Public HTTP route prefix.",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Process log level. Not a claim about downstream systems.",
    )


def load_settings(*, env_file: str | Path | None = ".env") -> AppSettings:
    """Build settings without using the process-wide cache.

    Pass ``env_file=None`` in tests so a developer's local ``.env`` is ignored.
    """

    return AppSettings(_env_file=env_file)


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached application settings."""

    return load_settings()


def clear_settings_cache() -> None:
    """Drop the cached settings instance (for tests and process reconfiguration)."""

    get_settings.cache_clear()
