"""Unit tests for the async Qdrant HTTP client factory.

No live Qdrant process is required. Tests must not issue collection, point,
search, health, or version commands.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any

import pytest
from qdrant_client import AsyncQdrantClient

from energy_trading.infrastructure.vector_store.qdrant.client import create_qdrant_client
from energy_trading.shared.config.qdrant import QdrantSettings
from tests.architecture.import_inspection import SRC_ROOT

SENTINEL_API_KEY = "sentinel-qdrant-api-key-chunk22"
CLIENT_PATH = (
    SRC_ROOT / "energy_trading" / "infrastructure" / "vector_store" / "qdrant" / "client.py"
)
PACKAGE_INIT_PATH = CLIENT_PATH.with_name("__init__.py")
FACTORY_MODULE = "energy_trading.infrastructure.vector_store.qdrant.client"

FORBIDDEN_EAGER_COMMANDS = (
    "get_collections",
    "collection_exists",
    "get_collection",
    "create_collection",
    "upsert",
    "query_points",
    "retrieve",
    "health",
)


@pytest.fixture(autouse=True)
def clear_qdrant_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "QDRANT_HOST",
        "QDRANT_PORT",
        "QDRANT_HTTPS",
        "QDRANT_API_KEY",
        "QDRANT_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)


def _settings(**overrides: object) -> QdrantSettings:
    payload: dict[str, object] = {
        "host": "qdrant.example.invalid",
        "port": 6333,
        "https": False,
        "timeout_seconds": 5,
    }
    payload.update(overrides)
    return QdrantSettings(_env_file=None, **payload)


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


async def test_factory_returns_async_qdrant_client_without_network_command() -> None:
    client = create_qdrant_client(_settings())
    try:
        assert isinstance(client, AsyncQdrantClient)
        assert type(client) is AsyncQdrantClient
    finally:
        await client.close()


def test_factory_is_not_async() -> None:
    assert inspect.iscoroutinefunction(create_qdrant_client) is False


async def test_constructor_kwargs_propagate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: list[dict[str, Any]] = []
    real_cls = AsyncQdrantClient

    def spy(*args: object, **kwargs: object) -> AsyncQdrantClient:
        recorded.append(dict(kwargs))
        return real_cls(*args, **kwargs)

    monkeypatch.setattr(f"{FACTORY_MODULE}.AsyncQdrantClient", spy)
    client = create_qdrant_client(
        _settings(
            host="vectors.internal",
            port=7333,
            https=True,
            api_key=SENTINEL_API_KEY,
            timeout_seconds=11,
        )
    )
    try:
        assert recorded[0]["host"] == "vectors.internal"
        assert recorded[0]["port"] == 7333
        assert recorded[0]["https"] is True
        assert recorded[0]["api_key"] == SENTINEL_API_KEY
        assert recorded[0]["timeout"] == 11
        assert recorded[0]["prefer_grpc"] is False
        assert recorded[0]["cloud_inference"] is False
        assert recorded[0]["check_compatibility"] is False
        assert "url" not in recorded[0]
        assert "location" not in recorded[0]
        assert "path" not in recorded[0]
        assert ":memory:" not in str(recorded[0])
    finally:
        await client.close()


async def test_optional_api_key_none_is_propagated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: list[dict[str, Any]] = []
    real_cls = AsyncQdrantClient

    def spy(*args: object, **kwargs: object) -> AsyncQdrantClient:
        recorded.append(dict(kwargs))
        return real_cls(*args, **kwargs)

    monkeypatch.setattr(f"{FACTORY_MODULE}.AsyncQdrantClient", spy)
    client = create_qdrant_client(_settings())
    try:
        assert recorded[0]["api_key"] is None
    finally:
        await client.close()


async def test_repeated_factory_calls_create_distinct_clients() -> None:
    first = create_qdrant_client(_settings())
    second = create_qdrant_client(_settings())
    try:
        assert first is not second
    finally:
        await first.close()
        await second.close()


async def test_factory_does_not_close_returned_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_calls = 0
    real_close = AsyncQdrantClient.close

    async def spy_close(self: AsyncQdrantClient, *args: object, **kwargs: object) -> None:
        nonlocal close_calls
        close_calls += 1
        await real_close(self, *args, **kwargs)

    monkeypatch.setattr(AsyncQdrantClient, "close", spy_close)
    client = create_qdrant_client(_settings())
    try:
        assert close_calls == 0
    finally:
        await client.close()
        assert close_calls == 1


def test_no_module_global_qdrant_client_is_created() -> None:
    client_calls = _module_level_call_names(CLIENT_PATH)
    package_calls = _module_level_call_names(PACKAGE_INIT_PATH)
    forbidden = {"AsyncQdrantClient", "create_qdrant_client", "QdrantClient"}
    assert client_calls.isdisjoint(forbidden)
    assert package_calls.isdisjoint(forbidden)


def test_factory_source_has_no_eager_commands_or_inference() -> None:
    source = CLIENT_PATH.read_text(encoding="utf-8")
    for name in FORBIDDEN_EAGER_COMMANDS:
        assert name not in source
    assert "cloud_inference=False" in source
    assert "prefer_grpc=False" in source
    assert "check_compatibility=False" in source
    assert "cloud_inference=True" not in source
    assert "prefer_grpc=True" not in source
    assert 'location=":memory:"' not in source
    assert "FastEmbed" not in source
    assert "models.Document" not in source
    assert "print(" not in source
    assert SENTINEL_API_KEY not in source
    assert "get_secret_value()" in source
