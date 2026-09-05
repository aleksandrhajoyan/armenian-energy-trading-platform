"""Typed PostgreSQL/TimescaleDB settings independent of the runtime engine.

These settings are loaded separately from ``AppSettings``. They are not required
for process health or ``create_app()``.
"""

from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL connection and pool configuration.

    Identity fields (host, database, username, password) have no implicit
    defaults and must be supplied by environment or constructor. Operational
    pool values have safe non-secret defaults.
    """

    model_config = SettingsConfigDict(
        env_prefix="ENERGY_DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    host: str = Field(min_length=1, description="PostgreSQL hostname.")
    port: int = Field(default=5432, ge=1, le=65535, description="PostgreSQL TCP port.")
    database: str = Field(min_length=1, description="PostgreSQL database name.")
    username: str = Field(min_length=1, description="PostgreSQL username.")
    password: SecretStr = Field(
        min_length=1,
        repr=False,
        description="PostgreSQL password. Never log or interpolate this value.",
    )
    pool_size: int = Field(default=5, gt=0, description="SQLAlchemy connection pool size.")
    max_overflow: int = Field(
        default=10,
        ge=0,
        description="SQLAlchemy pool connections allowed above pool_size.",
    )
    pool_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        description="Seconds to wait for a pool connection.",
    )

    @field_validator("host", "database", "username", mode="before")
    @classmethod
    def strip_required_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("must not be blank")
            return stripped
        return value

    @field_validator("password")
    @classmethod
    def reject_blank_password(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("must not be blank")
        return value


def load_database_settings(*, env_file: str | Path | None = ".env") -> DatabaseSettings:
    """Build database settings without a process-wide cache.

    Pass ``env_file=None`` in tests so a developer's local ``.env`` is ignored.
    """

    return DatabaseSettings(_env_file=env_file)
