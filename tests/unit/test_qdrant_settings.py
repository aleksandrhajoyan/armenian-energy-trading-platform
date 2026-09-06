"""Unit tests for typed Qdrant connection settings.

These tests must not require a running Qdrant server and must not read a local ``.env``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from energy_trading.shared.config.qdrant import QdrantSettings, load_qdrant_settings
from energy_trading.shared.config.settings import load_settings

SENTINEL_API_KEY = "sentinel-qdrant-api-key-chunk22"

_QDRANT_ENV_KEYS = (
    "QDRANT_HOST",
    "QDRANT_PORT",
    "QDRANT_HTTPS",
    "QDRANT_API_KEY",
    "QDRANT_TIMEOUT_SECONDS",
)


@pytest.fixture(autouse=True)
def clear_qdrant_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _QDRANT_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _settings(**overrides: object) -> QdrantSettings:
    payload: dict[str, object] = {"host": "localhost"}
    payload.update(overrides)
    return QdrantSettings(_env_file=None, **payload)


def test_valid_explicit_qdrant_settings() -> None:
    settings = _settings(
        host="vectors.internal",
        port=6334,
        https=True,
        api_key=SENTINEL_API_KEY,
        timeout_seconds=8,
    )
    assert settings.host == "vectors.internal"
    assert settings.port == 6334
    assert settings.https is True
    assert settings.api_key is not None
    assert settings.api_key.get_secret_value() == SENTINEL_API_KEY
    assert settings.timeout_seconds == 8


def test_host_is_required() -> None:
    with pytest.raises(ValidationError):
        QdrantSettings(_env_file=None)


def test_host_whitespace_is_normalized() -> None:
    settings = _settings(host="  qdrant.internal  ")
    assert settings.host == "qdrant.internal"


def test_blank_host_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _settings(host="")
    with pytest.raises(ValidationError):
        _settings(host="   ")


def test_default_port_is_6333() -> None:
    assert _settings().port == 6333


def test_explicit_port_is_accepted() -> None:
    assert _settings(port=7333).port == 7333


@pytest.mark.parametrize("port", [0, -1, 65536, 70000])
def test_invalid_port_is_rejected(port: int) -> None:
    with pytest.raises(ValidationError) as exc_info:
        _settings(port=port, api_key=SENTINEL_API_KEY)
    assert SENTINEL_API_KEY not in str(exc_info.value)


@pytest.mark.parametrize("port", [True, False])
def test_boolean_port_is_rejected(port: bool) -> None:
    with pytest.raises(ValidationError):
        _settings(port=port)


def test_default_https_is_false() -> None:
    assert _settings().https is False


def test_explicit_https_true_is_accepted() -> None:
    assert _settings(https=True).https is True


def test_optional_api_key_is_none_by_default() -> None:
    settings = _settings()
    assert settings.api_key is None


def test_blank_api_key_normalizes_to_none() -> None:
    assert _settings(api_key="").api_key is None
    assert _settings(api_key="   ").api_key is None


def test_nonblank_api_key_is_retained() -> None:
    settings = _settings(api_key="  keep-spaces  ")
    assert settings.api_key is not None
    assert settings.api_key.get_secret_value() == "  keep-spaces  "


def test_api_key_is_masked_in_repr_and_str() -> None:
    settings = _settings(api_key=SENTINEL_API_KEY)
    rendered = repr(settings)
    assert SENTINEL_API_KEY not in rendered
    assert SENTINEL_API_KEY not in str(settings)
    assert settings.api_key is not None
    assert settings.api_key.get_secret_value() == SENTINEL_API_KEY


def test_default_timeout_is_five_seconds() -> None:
    assert _settings().timeout_seconds == 5


def test_explicit_timeout_is_accepted() -> None:
    assert _settings(timeout_seconds=12).timeout_seconds == 12


@pytest.mark.parametrize("timeout", [0, -1])
def test_non_positive_timeout_is_rejected(timeout: int) -> None:
    with pytest.raises(ValidationError):
        _settings(timeout_seconds=timeout)


@pytest.mark.parametrize("timeout", [True, False])
def test_boolean_timeout_is_rejected(timeout: bool) -> None:
    with pytest.raises(ValidationError):
        _settings(timeout_seconds=timeout)


def test_local_env_file_does_not_contaminate_explicit_settings(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "QDRANT_HOST=from-local-env-file",
                "QDRANT_PORT=2345",
                "QDRANT_API_KEY=from-local-env-file-secret",
            ]
        ),
        encoding="utf-8",
    )
    settings = QdrantSettings(host="explicit-host", _env_file=None)
    assert settings.host == "explicit-host"
    assert settings.port == 6333
    assert settings.api_key is None
    assert "from-local-env-file" not in repr(settings)
    assert "from-local-env-file-secret" not in repr(settings)


def test_load_qdrant_settings_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QDRANT_HOST", "vectors.internal")
    monkeypatch.setenv("QDRANT_PORT", "6335")
    monkeypatch.setenv("QDRANT_HTTPS", "true")
    monkeypatch.setenv("QDRANT_API_KEY", SENTINEL_API_KEY)
    monkeypatch.setenv("QDRANT_TIMEOUT_SECONDS", "9")
    settings = load_qdrant_settings(env_file=None)
    assert settings.host == "vectors.internal"
    assert settings.port == 6335
    assert settings.https is True
    assert settings.api_key is not None
    assert settings.api_key.get_secret_value() == SENTINEL_API_KEY
    assert settings.timeout_seconds == 9
    assert SENTINEL_API_KEY not in repr(settings)


def test_app_settings_do_not_require_qdrant_configuration() -> None:
    settings = load_settings(env_file=None)
    assert type(settings).__name__ == "AppSettings"
    assert settings.api_prefix == "/api/v1"


def test_qdrant_settings_are_separate_from_app_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QDRANT_HOST", "vectors.internal")
    monkeypatch.setenv("QDRANT_API_KEY", SENTINEL_API_KEY)
    app_settings = load_settings(env_file=None)
    assert type(app_settings).__name__ == "AppSettings"
    assert SENTINEL_API_KEY not in repr(app_settings)
    qdrant_settings = load_qdrant_settings(env_file=None)
    assert qdrant_settings.host == "vectors.internal"
