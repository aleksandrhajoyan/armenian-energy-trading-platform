"""Unit tests for typed application settings."""

import pytest
from pydantic import ValidationError

from energy_trading.shared.config.settings import (
    AppEnvironment,
    AppSettings,
    clear_settings_cache,
    get_settings,
    load_settings,
)


def test_default_settings_are_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("APP_NAME", "APP_ENV", "ENVIRONMENT", "API_PREFIX", "LOG_LEVEL"):
        monkeypatch.delenv(key, raising=False)

    settings = load_settings(env_file=None)

    assert settings.app_name == "AI Energy Trading Platform"
    assert settings.environment is AppEnvironment.DEVELOPMENT
    assert settings.api_prefix == "/api/v1"
    assert settings.log_level == "INFO"


def test_environment_variable_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "Override Service")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_PREFIX", "/api/v1")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    settings = load_settings(env_file=None)

    assert settings.app_name == "Override Service"
    assert settings.environment is AppEnvironment.PRODUCTION
    assert settings.log_level == "WARNING"


def test_environment_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        AppSettings.model_validate({"environment": "staging"})


def test_log_level_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        AppSettings.model_validate({"log_level": "VERBOSE"})


def test_extra_environment_variables_do_not_crash_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POSTGRES_PASSWORD", "not-a-real-secret")
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("QDRANT_API_KEY", "placeholder")

    settings = load_settings(env_file=None)

    assert settings.environment is AppEnvironment.DEVELOPMENT


def test_settings_cache_can_be_cleared(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    clear_settings_cache()
    first = get_settings()
    second = get_settings()
    assert first is second
    assert first.environment is AppEnvironment.TEST

    monkeypatch.setenv("APP_ENV", "production")
    assert get_settings().environment is AppEnvironment.TEST

    clear_settings_cache()
    refreshed = get_settings()
    assert refreshed is not first
    assert refreshed.environment is AppEnvironment.PRODUCTION
