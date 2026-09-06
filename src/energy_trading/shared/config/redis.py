"""Typed Redis cache settings independent of process health and FastAPI.

These settings are loaded separately from ``AppSettings``. They are not
required for process health or ``create_app()``.
"""

from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseSettings):
    """Redis connection configuration for the ephemeral cache adapter.

    Identity field ``host`` has no implicit default and must be supplied by
    environment or constructor. Operational values have safe non-secret defaults.
    """

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    host: str = Field(min_length=1, description="Redis hostname.")
    port: int = Field(default=6379, ge=1, le=65535, description="Redis TCP port.")
    db: int = Field(default=0, ge=0, description="Redis logical database index.")
    password: SecretStr | None = Field(
        default=None,
        repr=False,
        description="Optional Redis password. Never log or interpolate this value.",
    )
    ssl: bool = Field(default=False, description="Use TLS for the Redis connection.")
    socket_timeout_seconds: float = Field(
        default=5.0,
        gt=0,
        description="Seconds for Redis socket and connection timeouts.",
    )
    max_connections: int = Field(
        default=10,
        gt=0,
        description="Maximum connections in the Redis client pool.",
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

    @field_validator("password", mode="before")
    @classmethod
    def empty_password_to_none(cls, value: object) -> object:
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


def load_redis_settings(*, env_file: str | Path | None = ".env") -> RedisSettings:
    """Build Redis settings without a process-wide cache.

    Pass ``env_file=None`` in tests so a developer's local ``.env`` is ignored.
    """

    return RedisSettings(_env_file=env_file)
