"""Concrete Redis cache infrastructure must stay outside application."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    collect_import_violations,
    imported_modules,
    imported_names,
)

ROOT = SRC_ROOT.parent
DOMAIN_ROOT = SRC_ROOT / "energy_trading" / "domain"
APPLICATION_ROOT = SRC_ROOT / "energy_trading" / "application"
API_ROOT = SRC_ROOT / "energy_trading" / "api"
API_APP = API_ROOT / "app.py"
ML_ROOT = SRC_ROOT / "energy_trading" / "ml"
CONFIG_ROOT = SRC_ROOT / "energy_trading" / "shared" / "config"
REDIS_SETTINGS = CONFIG_ROOT / "redis.py"
CACHE_ROOT = SRC_ROOT / "energy_trading" / "infrastructure" / "cache"
CODEC = CACHE_ROOT / "codec.py"
COMPOSE_FILE = ROOT / "compose.yaml"
PYPROJECT_FILE = ROOT / "pyproject.toml"

FORBIDDEN_REDIS_LIBRARIES = (
    "redis",
    "hiredis",
    "aioredis",
    "energy_trading.infrastructure.cache",
)

FORBIDDEN_SETTINGS_IMPORTS = (
    "redis",
    "hiredis",
    "aioredis",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "energy_trading.infrastructure",
    "energy_trading.api",
    "energy_trading.application",
    "energy_trading.ml",
    "fastapi",
    "starlette",
)

FORBIDDEN_CACHE_IMPLEMENTATION = (
    "fastapi",
    "starlette",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "qdrant_client",
    "pandas",
    "polars",
    "openpyxl",
    "langchain",
    "langchain_core",
    "langgraph",
    "openai",
    "xgboost",
    "lightgbm",
    "prophet",
    "energy_trading.api",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.ml",
    "energy_trading.infrastructure.adapters",
    "pickle",
    "marshal",
    "shelve",
)

UNSAFE_CODEC_NAMES = frozenset({"pickle", "marshal", "shelve", "eval", "exec", "Redis"})


def _top_level_service_names(text: str) -> list[str]:
    names: list[str] = []
    in_services = False
    for line in text.splitlines():
        if line.startswith("services:"):
            in_services = True
            continue
        if not in_services:
            continue
        if (
            line
            and not line.startswith(" ")
            and not line.startswith("\t")
            and not line.startswith("#")
        ):
            break
        if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":"):
            name = line.strip()[:-1]
            if name and not name.startswith("#"):
                names.append(name)
    return names


def _class_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}


def test_domain_does_not_import_redis_or_cache_infrastructure() -> None:
    assert collect_import_violations(DOMAIN_ROOT, FORBIDDEN_REDIS_LIBRARIES) == []


def test_application_does_not_import_redis_or_cache_infrastructure() -> None:
    assert collect_import_violations(APPLICATION_ROOT, FORBIDDEN_REDIS_LIBRARIES) == []


def test_ml_does_not_import_redis() -> None:
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, FORBIDDEN_REDIS_LIBRARIES) == []


def test_api_does_not_import_or_create_redis() -> None:
    assert collect_import_violations(API_ROOT, FORBIDDEN_REDIS_LIBRARIES) == []
    app_source = API_APP.read_text(encoding="utf-8")
    tree = ast.parse(app_source, filename=str(API_APP))
    create_app = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )
    call_names: set[str] = set()
    for node in ast.walk(create_app):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            call_names.add(func.id)
        elif isinstance(func, ast.Attribute):
            call_names.add(func.attr)
    assert "create_redis_client" not in call_names
    assert "Redis" not in call_names
    assert "RedisCache" not in call_names
    assert "redis" not in app_source.lower()


def test_redis_settings_are_vendor_runtime_free() -> None:
    assert collect_import_violations(REDIS_SETTINGS.parent, FORBIDDEN_SETTINGS_IMPORTS) == []
    names = imported_modules(REDIS_SETTINGS)
    assert "redis" not in names
    assert "Redis" not in imported_names(REDIS_SETTINGS)
    assert "RedisSettings" in _class_names(REDIS_SETTINGS)


def test_redis_cache_infrastructure_forbidden_dependencies() -> None:
    assert collect_import_violations(CACHE_ROOT, FORBIDDEN_CACHE_IMPLEMENTATION) == []


def test_codec_has_no_redis_client_or_unsafe_serializer() -> None:
    names = imported_names(CODEC)
    leaked_imports = sorted(
        name
        for name in names
        if name in UNSAFE_CODEC_NAMES or name in {"redis", "hiredis", "aioredis"}
    )
    assert leaked_imports == []
    tree = ast.parse(CODEC.read_text(encoding="utf-8"), filename=str(CODEC))
    imported_modules_in_file = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules_in_file.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules_in_file.add(node.module.split(".", 1)[0])
    assert imported_modules_in_file.isdisjoint({"pickle", "marshal", "shelve", "redis"})
    eval_hits = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"eval", "exec"}
    ]
    assert eval_hits == []


def test_compose_still_has_no_redis_service() -> None:
    text = COMPOSE_FILE.read_text(encoding="utf-8")
    names = _top_level_service_names(text)
    assert "redis" not in names
    assert "redis:" not in text.lower()


def test_no_redis_live_integration_marker() -> None:
    source = PYPROJECT_FILE.read_text(encoding="utf-8")
    assert "redis_integration" not in source
    assert "ENERGY_RUN_REDIS_INTEGRATION" not in source
