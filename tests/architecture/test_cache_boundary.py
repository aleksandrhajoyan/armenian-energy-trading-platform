"""Application cache port must stay vendor-neutral and unwired."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    collect_import_violations,
    imported_names,
)

ROOT = SRC_ROOT.parent
PORTS_ROOT = SRC_ROOT / "energy_trading" / "application" / "ports"
CACHE_PORT = PORTS_ROOT / "cache.py"
API_ROOT = SRC_ROOT / "energy_trading" / "api"
API_APP = API_ROOT / "app.py"
CONFIG_ROOT = SRC_ROOT / "energy_trading" / "shared" / "config"
INFRASTRUCTURE_ROOT = SRC_ROOT / "energy_trading" / "infrastructure"
INFRASTRUCTURE_CACHE = INFRASTRUCTURE_ROOT / "cache"
COMPOSE_FILE = ROOT / "compose.yaml"
PYPROJECT_FILE = ROOT / "pyproject.toml"
LOCK_FILE = ROOT / "uv.lock"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.api",
    "energy_trading.ml",
    "fastapi",
    "starlette",
    "redis",
    "hiredis",
    "aioredis",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "qdrant_client",
    "pandas",
    "polars",
    "openpyxl",
    "requests",
    "httpx",
    "aiohttp",
    "langchain",
    "langchain_core",
    "langgraph",
    "llama_index",
    "openai",
    "xgboost",
    "lightgbm",
    "prophet",
    "sentence_transformers",
    "transformers",
)

FORBIDDEN_TYPE_NAMES = frozenset(
    {
        "Any",
        "bytes",
        "bytearray",
        "memoryview",
        "dict",
        "Dict",
        "Mapping",
        "MutableMapping",
        "Redis",
        "RedisCluster",
        "StrictRedis",
        "ConnectionPool",
        "BlockingConnectionPool",
        "Connection",
        "RedisError",
        "ResponseError",
        "JSON",
        "Json",
        "JsonValue",
        "DataFrame",
        "Path",
        "HttpUrl",
        "URL",
    }
)

REDIS_PACKAGE_NAMES = frozenset({"redis", "hiredis", "aioredis", "redis-py"})


def _async_function(path: Path, function_name: str) -> ast.AsyncFunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name:
            return node
    msg = f"async function {function_name!r} not found in {path}"
    raise AssertionError(msg)


def _class_def(path: Path, class_name: str) -> ast.ClassDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    msg = f"class {class_name!r} not found in {path}"
    raise AssertionError(msg)


def _base_names(class_def: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for base in class_def.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
    return names


def _requirement_name(item: str) -> str:
    name = item.split("[", 1)[0]
    for separator in (">", "<", "=", " "):
        name = name.split(separator, 1)[0]
    return name.strip().lower()


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


def test_cache_port_does_not_import_outer_layers_or_vendors() -> None:
    assert collect_import_violations(CACHE_PORT.parent, FORBIDDEN_PREFIXES) == []
    leaked = sorted(name for name in imported_names(CACHE_PORT) if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []


def test_cache_port_is_generic_protocol_not_abc() -> None:
    class_def = _class_def(CACHE_PORT, "CachePort")
    bases = _base_names(class_def)
    assert "Protocol" in bases
    assert "ABC" not in bases
    assert [param.name for param in class_def.type_params] == ["TValue"]
    source = CACHE_PORT.read_text(encoding="utf-8")
    assert "abstractmethod" not in source


def test_public_cache_annotations_exclude_redis_and_untyped_payloads() -> None:
    names = annotation_type_names(CACHE_PORT)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    assert "timedelta" in names
    assert "TValue" in names
    get_fn = _async_function(CACHE_PORT, "get")
    set_fn = _async_function(CACHE_PORT, "set")
    delete_fn = _async_function(CACHE_PORT, "delete")
    assert tuple(arg.arg for arg in get_fn.args.args) == ("self", "key")
    assert tuple(arg.arg for arg in set_fn.args.args) == ("self", "key", "value")
    assert tuple(arg.arg for arg in set_fn.args.kwonlyargs) == ("ttl",)
    assert tuple(arg.arg for arg in delete_fn.args.args) == ("self", "key")
    for function in (get_fn, set_fn, delete_fn):
        assert function.args.vararg is None
        assert function.args.kwarg is None


def test_no_redis_python_dependency_is_declared() -> None:
    pyproject = tomllib.loads(PYPROJECT_FILE.read_text(encoding="utf-8"))
    declared = [
        *pyproject["project"]["dependencies"],
        *pyproject.get("dependency-groups", {}).get("dev", []),
    ]
    leaked = [
        _requirement_name(item)
        for item in declared
        if _requirement_name(item) in REDIS_PACKAGE_NAMES
    ]
    assert leaked == []
    lock = tomllib.loads(LOCK_FILE.read_text(encoding="utf-8"))
    lock_names = {package["name"].lower() for package in lock.get("package", [])}
    assert lock_names.isdisjoint(REDIS_PACKAGE_NAMES)


def test_compose_has_no_redis_service() -> None:
    text = COMPOSE_FILE.read_text(encoding="utf-8")
    names = _top_level_service_names(text)
    assert "redis" not in names
    assert "redis:" not in text.lower()
    assert "redis/redis" not in text.lower()


def test_api_composition_does_not_import_or_construct_cache() -> None:
    forbidden_wiring = (
        "energy_trading.application.ports.cache",
        "energy_trading.infrastructure.cache",
        "redis",
        "hiredis",
        "aioredis",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "CachePort" not in names
        assert "Redis" not in names
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
    assert "CachePort" not in call_names
    assert "Redis" not in call_names
    lowered = app_source.lower()
    assert "redis" not in lowered
    assert "cacheport" not in lowered


def test_no_concrete_cache_or_redis_settings_implementation() -> None:
    py_files = sorted(INFRASTRUCTURE_CACHE.rglob("*.py"))
    assert py_files == []
    assert collect_import_violations(INFRASTRUCTURE_ROOT, ("redis", "hiredis", "aioredis")) == []
    forbidden_settings = {"RedisSettings", "CacheSettings"}
    hits: list[str] = []
    for path in sorted(CONFIG_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in forbidden_settings:
                hits.append(f"{path.relative_to(SRC_ROOT)}:{node.name}")
    assert hits == []
