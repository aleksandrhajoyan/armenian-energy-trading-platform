"""Unit tests for typed OpenAI connection settings.

These tests must not require a live OpenAI API and must not read a local ``.env``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from energy_trading.shared.config.openai import OpenAISettings, load_openai_settings
from energy_trading.shared.config.settings import load_settings
from tests.architecture.import_inspection import SRC_ROOT, imported_modules

SENTINEL_API_KEY = "sentinel-openai-api-key-chunk70"

_OPENAI_ENV_KEYS = ("ENERGY_OPENAI_API_KEY",)


@pytest.fixture(autouse=True)
def clear_openai_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _OPENAI_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _settings(**overrides: object) -> OpenAISettings:
    payload: dict[str, object] = {"api_key": SENTINEL_API_KEY}
    payload.update(overrides)
    return OpenAISettings(_env_file=None, **payload)


def test_valid_explicit_openai_settings() -> None:
    settings = _settings()
    assert isinstance(settings.api_key, SecretStr)
    assert settings.api_key.get_secret_value() == SENTINEL_API_KEY
    assert set(OpenAISettings.model_fields) == {"api_key"}


def test_api_key_is_secret_str() -> None:
    settings = _settings()
    assert type(settings.api_key) is SecretStr


def test_missing_api_key_fails_validation() -> None:
    with pytest.raises(ValidationError):
        OpenAISettings(_env_file=None)


def test_load_openai_settings_without_key_fails() -> None:
    with pytest.raises(ValidationError):
        load_openai_settings(env_file=None)


def test_empty_api_key_fails() -> None:
    with pytest.raises(ValidationError):
        _settings(api_key="")


def test_whitespace_only_api_key_fails() -> None:
    with pytest.raises(ValidationError):
        _settings(api_key="   ")
    with pytest.raises(ValidationError):
        _settings(api_key="\t\n")


def test_nonblank_secret_is_preserved_internally() -> None:
    settings = _settings(api_key="  keep-spaces  ")
    assert settings.api_key.get_secret_value() == "  keep-spaces  "


def test_api_key_is_masked_in_repr() -> None:
    settings = _settings()
    assert SENTINEL_API_KEY not in repr(settings)


def test_api_key_is_masked_in_str() -> None:
    settings = _settings()
    assert SENTINEL_API_KEY not in str(settings)
    assert settings.api_key.get_secret_value() == SENTINEL_API_KEY


def test_load_openai_settings_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENERGY_OPENAI_API_KEY", SENTINEL_API_KEY)
    settings = load_openai_settings(env_file=None)
    assert settings.api_key.get_secret_value() == SENTINEL_API_KEY
    assert SENTINEL_API_KEY not in repr(settings)


def test_env_file_none_prevents_local_env_contamination(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ENERGY_OPENAI_API_KEY=from-local-env-file-secret\n",
        encoding="utf-8",
    )
    settings = OpenAISettings(api_key=SENTINEL_API_KEY, _env_file=None)
    assert settings.api_key.get_secret_value() == SENTINEL_API_KEY
    assert "from-local-env-file-secret" not in repr(settings)
    assert "from-local-env-file-secret" not in str(settings)


def test_no_model_or_provider_settings_are_present() -> None:
    settings = _settings()
    assert not hasattr(settings, "model")
    assert not hasattr(settings, "embedding_model")
    assert not hasattr(settings, "inference_model")
    assert not hasattr(settings, "temperature")
    assert not hasattr(settings, "base_url")
    assert not hasattr(settings, "organization")
    assert not hasattr(settings, "timeout")
    assert "model" not in OpenAISettings.model_fields
    assert "base_url" not in OpenAISettings.model_fields


def test_app_settings_do_not_require_openai_configuration() -> None:
    settings = load_settings(env_file=None)
    assert type(settings).__name__ == "AppSettings"
    assert settings.api_prefix == "/api/v1"


def test_openai_settings_are_separate_from_app_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENERGY_OPENAI_API_KEY", SENTINEL_API_KEY)
    app_settings = load_settings(env_file=None)
    assert type(app_settings).__name__ == "AppSettings"
    assert SENTINEL_API_KEY not in repr(app_settings)
    openai_settings = load_openai_settings(env_file=None)
    assert openai_settings.api_key.get_secret_value() == SENTINEL_API_KEY


def test_constructing_settings_does_not_import_openai_sdk() -> None:
    settings_path = SRC_ROOT / "energy_trading" / "shared" / "config" / "openai.py"
    modules = imported_modules(settings_path)
    assert "openai" not in modules
    settings = _settings()
    assert settings.api_key.get_secret_value() == SENTINEL_API_KEY
