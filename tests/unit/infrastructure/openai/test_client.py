"""Unit tests for the async OpenAI client factory.

No live OpenAI process or API key is required. Tests must not issue provider
requests.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest
from openai import AsyncOpenAI

from energy_trading.infrastructure.openai.client import create_openai_client
from energy_trading.shared.config.openai import OpenAISettings
from tests.architecture.import_inspection import SRC_ROOT

SENTINEL_API_KEY = "sentinel-openai-api-key-chunk70"
CLIENT_PATH = SRC_ROOT / "energy_trading" / "infrastructure" / "openai" / "client.py"
PACKAGE_INIT_PATH = CLIENT_PATH.with_name("__init__.py")


@pytest.fixture(autouse=True)
def clear_openai_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENERGY_OPENAI_API_KEY", raising=False)


def _settings(**overrides: object) -> OpenAISettings:
    payload: dict[str, object] = {"api_key": SENTINEL_API_KEY}
    payload.update(overrides)
    return OpenAISettings(_env_file=None, **payload)


def _module_level_call_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            func = child.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


async def test_factory_returns_async_openai_client() -> None:
    settings = _settings()
    client = create_openai_client(settings)
    try:
        assert isinstance(client, AsyncOpenAI)
        assert type(client) is AsyncOpenAI
    finally:
        await client.close()


def test_factory_is_not_async() -> None:
    assert inspect.iscoroutinefunction(create_openai_client) is False


def test_factory_accepts_typed_openai_settings() -> None:
    signature = inspect.signature(create_openai_client)
    assert tuple(signature.parameters) == ("settings",)
    annotation = signature.parameters["settings"].annotation
    assert annotation in {OpenAISettings, "OpenAISettings"}
    assert signature.return_annotation in {AsyncOpenAI, "AsyncOpenAI"}


async def test_configured_secret_is_supplied_internally() -> None:
    settings = _settings()
    client = create_openai_client(settings)
    try:
        assert client.api_key == SENTINEL_API_KEY
        source = CLIENT_PATH.read_text(encoding="utf-8")
        assert "get_secret_value()" in source
        assert "print(" not in source
    finally:
        await client.close()


async def test_secret_is_absent_from_settings_representations() -> None:
    settings = _settings()
    client = create_openai_client(settings)
    try:
        assert SENTINEL_API_KEY not in repr(settings)
        assert SENTINEL_API_KEY not in str(settings)
        assert settings.api_key.get_secret_value() == SENTINEL_API_KEY
    finally:
        await client.close()


async def test_sdk_retries_are_disabled() -> None:
    client = create_openai_client(_settings())
    try:
        assert client.max_retries == 0
    finally:
        await client.close()


async def test_construction_performs_no_http_request() -> None:
    client = create_openai_client(_settings())
    try:
        assert isinstance(client, AsyncOpenAI)
        assert client.is_closed() is False
        source = CLIENT_PATH.read_text(encoding="utf-8")
        assert ".create(" not in source
        assert ".parse(" not in source
        assert "embeddings" not in source
        assert "responses" not in source
        assert "chat" not in source
    finally:
        await client.close()


async def test_repeated_factory_calls_create_distinct_clients() -> None:
    first = create_openai_client(_settings())
    second = create_openai_client(_settings())
    try:
        assert first is not second
    finally:
        await first.close()
        await second.close()


async def test_factory_does_not_mutate_settings() -> None:
    settings = _settings()
    before = settings.api_key.get_secret_value()
    client = create_openai_client(settings)
    try:
        assert settings.api_key.get_secret_value() == before
        assert settings.api_key.get_secret_value() == SENTINEL_API_KEY
        assert set(OpenAISettings.model_fields) == {"api_key"}
    finally:
        await client.close()


async def test_factory_does_not_select_a_model() -> None:
    client = create_openai_client(_settings())
    try:
        source = CLIENT_PATH.read_text(encoding="utf-8")
        assert "model=" not in source
        assert "embedding_model" not in source
        assert "inference_model" not in source
        assert not hasattr(client, "model")
    finally:
        await client.close()


async def test_caller_can_close_the_client() -> None:
    client = create_openai_client(_settings())
    assert client.is_closed() is False
    await client.close()
    assert client.is_closed() is True


def test_no_module_global_openai_client_is_created() -> None:
    client_calls = _module_level_call_names(CLIENT_PATH)
    package_calls = _module_level_call_names(PACKAGE_INIT_PATH)
    forbidden = {"AsyncOpenAI", "create_openai_client", "OpenAI"}
    assert client_calls.isdisjoint(forbidden)
    assert package_calls.isdisjoint(forbidden)
