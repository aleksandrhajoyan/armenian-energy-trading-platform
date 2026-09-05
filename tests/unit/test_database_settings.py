"""Unit tests for typed PostgreSQL database settings.

These tests must not require a running database and must not read a local ``.env``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from energy_trading.shared.config.database import DatabaseSettings, load_database_settings

SENTINEL_PASSWORD = "sentinel-db-password-chunk13"

_DB_ENV_KEYS = (
    "ENERGY_DB_HOST",
    "ENERGY_DB_PORT",
    "ENERGY_DB_DATABASE",
    "ENERGY_DB_USERNAME",
    "ENERGY_DB_PASSWORD",
    "ENERGY_DB_POOL_SIZE",
    "ENERGY_DB_MAX_OVERFLOW",
    "ENERGY_DB_POOL_TIMEOUT_SECONDS",
)


@pytest.fixture(autouse=True)
def clear_database_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _DB_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _settings(**overrides: object) -> DatabaseSettings:
    payload: dict[str, object] = {
        "host": "localhost",
        "database": "energy_trading",
        "username": "energy_trading",
        "password": SENTINEL_PASSWORD,
    }
    payload.update(overrides)
    return DatabaseSettings(_env_file=None, **payload)


def test_valid_database_settings() -> None:
    settings = _settings()
    assert settings.host == "localhost"
    assert settings.port == 5432
    assert settings.database == "energy_trading"
    assert settings.username == "energy_trading"
    assert settings.password.get_secret_value() == SENTINEL_PASSWORD
    assert settings.pool_size == 5
    assert settings.max_overflow == 10
    assert settings.pool_timeout_seconds == 30.0


def test_port_default_is_5432() -> None:
    settings = _settings()
    assert settings.port == 5432


def test_explicit_port_is_accepted() -> None:
    settings = _settings(port=6543)
    assert settings.port == 6543


@pytest.mark.parametrize("port", [0, -1, 65536, 70000])
def test_invalid_port_is_rejected(port: int) -> None:
    with pytest.raises(ValidationError) as exc_info:
        _settings(port=port)
    assert SENTINEL_PASSWORD not in str(exc_info.value)


def test_empty_host_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _settings(host="")
    assert SENTINEL_PASSWORD not in str(exc_info.value)


def test_blank_host_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _settings(host="   ")


def test_empty_database_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _settings(database="")
    assert SENTINEL_PASSWORD not in str(exc_info.value)


def test_empty_username_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _settings(username="")
    assert SENTINEL_PASSWORD not in str(exc_info.value)


def test_positive_pool_size_is_accepted() -> None:
    settings = _settings(pool_size=1)
    assert settings.pool_size == 1


@pytest.mark.parametrize("pool_size", [0, -1])
def test_non_positive_pool_size_is_rejected(pool_size: int) -> None:
    with pytest.raises(ValidationError) as exc_info:
        _settings(pool_size=pool_size)
    assert SENTINEL_PASSWORD not in str(exc_info.value)


def test_non_negative_max_overflow_is_accepted() -> None:
    settings = _settings(max_overflow=0)
    assert settings.max_overflow == 0
    settings = _settings(max_overflow=3)
    assert settings.max_overflow == 3


def test_negative_max_overflow_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _settings(max_overflow=-1)
    assert SENTINEL_PASSWORD not in str(exc_info.value)


def test_positive_timeout_is_accepted() -> None:
    settings = _settings(pool_timeout_seconds=0.5)
    assert settings.pool_timeout_seconds == 0.5


@pytest.mark.parametrize("timeout", [0, -1.0])
def test_non_positive_timeout_is_rejected(timeout: float) -> None:
    with pytest.raises(ValidationError) as exc_info:
        _settings(pool_timeout_seconds=timeout)
    assert SENTINEL_PASSWORD not in str(exc_info.value)


def test_password_is_masked_in_repr() -> None:
    settings = _settings()
    rendered = repr(settings)
    assert SENTINEL_PASSWORD not in rendered
    assert SENTINEL_PASSWORD not in str(settings)
    assert settings.password.get_secret_value() == SENTINEL_PASSWORD


def test_local_env_file_does_not_contaminate_explicit_settings(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "ENERGY_DB_HOST=from-local-env-file",
                "ENERGY_DB_PORT=2345",
                "ENERGY_DB_DATABASE=from-local-env-file",
                "ENERGY_DB_USERNAME=from-local-env-file",
                "ENERGY_DB_PASSWORD=from-local-env-file-secret",
            ]
        ),
        encoding="utf-8",
    )
    settings = DatabaseSettings(
        host="explicit-host",
        database="explicit-db",
        username="explicit-user",
        password=SENTINEL_PASSWORD,
        _env_file=None,
    )
    assert settings.host == "explicit-host"
    assert settings.database == "explicit-db"
    assert settings.username == "explicit-user"
    assert settings.port == 5432
    assert "from-local-env-file" not in repr(settings)
    assert "from-local-env-file-secret" not in repr(settings)


def test_load_database_settings_reads_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENERGY_DB_HOST", "db.internal")
    monkeypatch.setenv("ENERGY_DB_PORT", "5555")
    monkeypatch.setenv("ENERGY_DB_DATABASE", "trading")
    monkeypatch.setenv("ENERGY_DB_USERNAME", "app_user")
    monkeypatch.setenv("ENERGY_DB_PASSWORD", SENTINEL_PASSWORD)
    settings = load_database_settings(env_file=None)
    assert settings.host == "db.internal"
    assert settings.port == 5555
    assert settings.database == "trading"
    assert settings.username == "app_user"
    assert settings.password.get_secret_value() == SENTINEL_PASSWORD
    assert SENTINEL_PASSWORD not in repr(settings)
