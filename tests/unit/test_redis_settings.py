"""Unit tests for typed Redis cache settings.

These tests must not require a running Redis server and must not read a local ``.env``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from energy_trading.shared.config.redis import RedisSettings, load_redis_settings

SENTINEL_PASSWORD = "sentinel-redis-password-chunk17"

_REDIS_ENV_KEYS = (
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_DB",
    "REDIS_PASSWORD",
    "REDIS_SSL",
    "REDIS_SOCKET_TIMEOUT_SECONDS",
    "REDIS_MAX_CONNECTIONS",
)


@pytest.fixture(autouse=True)
def clear_redis_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _REDIS_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _settings(**overrides: object) -> RedisSettings:
    payload: dict[str, object] = {"host": "localhost"}
    payload.update(overrides)
    return RedisSettings(_env_file=None, **payload)


def test_valid_explicit_redis_settings() -> None:
    settings = _settings(
        host="cache.internal",
        port=6380,
        db=2,
        password=SENTINEL_PASSWORD,
        ssl=True,
        socket_timeout_seconds=1.5,
        max_connections=4,
    )
    assert settings.host == "cache.internal"
    assert settings.port == 6380
    assert settings.db == 2
    assert settings.password is not None
    assert settings.password.get_secret_value() == SENTINEL_PASSWORD
    assert settings.ssl is True
    assert settings.socket_timeout_seconds == 1.5
    assert settings.max_connections == 4


def test_default_port_is_6379() -> None:
    assert _settings().port == 6379


def test_default_db_is_0() -> None:
    assert _settings().db == 0


def test_default_ssl_is_false() -> None:
    assert _settings().ssl is False


def test_default_timeout_is_five_seconds() -> None:
    assert _settings().socket_timeout_seconds == 5.0


def test_default_max_connections_is_10() -> None:
    assert _settings().max_connections == 10


def test_blank_host_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _settings(host="")
    with pytest.raises(ValidationError):
        _settings(host="   ")


def test_host_whitespace_is_normalized() -> None:
    settings = _settings(host="  redis.internal  ")
    assert settings.host == "redis.internal"


@pytest.mark.parametrize("port", [0, -1, 65536, 70000])
def test_invalid_port_is_rejected(port: int) -> None:
    with pytest.raises(ValidationError) as exc_info:
        _settings(port=port, password=SENTINEL_PASSWORD)
    assert SENTINEL_PASSWORD not in str(exc_info.value)


def test_negative_db_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _settings(db=-1)


@pytest.mark.parametrize("timeout", [0, -1.0])
def test_non_positive_timeout_is_rejected(timeout: float) -> None:
    with pytest.raises(ValidationError):
        _settings(socket_timeout_seconds=timeout)


@pytest.mark.parametrize("max_connections", [0, -1])
def test_non_positive_max_connections_is_rejected(max_connections: int) -> None:
    with pytest.raises(ValidationError):
        _settings(max_connections=max_connections)


def test_optional_password_is_none_by_default() -> None:
    settings = _settings()
    assert settings.password is None


def test_blank_password_normalizes_to_none() -> None:
    assert _settings(password="").password is None
    assert _settings(password="   ").password is None


def test_nonblank_password_is_not_stripped() -> None:
    settings = _settings(password="  keep-spaces  ")
    assert settings.password is not None
    assert settings.password.get_secret_value() == "  keep-spaces  "


def test_password_is_masked_in_repr() -> None:
    settings = _settings(password=SENTINEL_PASSWORD)
    rendered = repr(settings)
    assert SENTINEL_PASSWORD not in rendered
    assert SENTINEL_PASSWORD not in str(settings)
    assert settings.password is not None
    assert settings.password.get_secret_value() == SENTINEL_PASSWORD


def test_local_env_file_does_not_contaminate_explicit_settings(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "REDIS_HOST=from-local-env-file",
                "REDIS_PORT=2345",
                "REDIS_PASSWORD=from-local-env-file-secret",
            ]
        ),
        encoding="utf-8",
    )
    settings = RedisSettings(host="explicit-host", _env_file=None)
    assert settings.host == "explicit-host"
    assert settings.port == 6379
    assert settings.password is None
    assert "from-local-env-file" not in repr(settings)
    assert "from-local-env-file-secret" not in repr(settings)


def test_load_redis_settings_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_HOST", "cache.internal")
    monkeypatch.setenv("REDIS_PORT", "6381")
    monkeypatch.setenv("REDIS_DB", "3")
    monkeypatch.setenv("REDIS_PASSWORD", SENTINEL_PASSWORD)
    monkeypatch.setenv("REDIS_SSL", "true")
    monkeypatch.setenv("REDIS_SOCKET_TIMEOUT_SECONDS", "2.5")
    monkeypatch.setenv("REDIS_MAX_CONNECTIONS", "8")
    settings = load_redis_settings(env_file=None)
    assert settings.host == "cache.internal"
    assert settings.port == 6381
    assert settings.db == 3
    assert settings.password is not None
    assert settings.password.get_secret_value() == SENTINEL_PASSWORD
    assert settings.ssl is True
    assert settings.socket_timeout_seconds == 2.5
    assert settings.max_connections == 8
    assert SENTINEL_PASSWORD not in repr(settings)
