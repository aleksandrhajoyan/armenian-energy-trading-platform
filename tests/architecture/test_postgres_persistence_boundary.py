"""PostgreSQL persistence foundation must stay an infrastructure concern."""

from __future__ import annotations

import ast

from tests.architecture.import_inspection import (
    SRC_ROOT,
    collect_import_violations,
    imported_modules,
)

DOMAIN_ROOT = SRC_ROOT / "energy_trading" / "domain"
APPLICATION_ROOT = SRC_ROOT / "energy_trading" / "application"
CONFIG_ROOT = SRC_ROOT / "energy_trading" / "shared" / "config"
DATABASE_SETTINGS = CONFIG_ROOT / "database.py"
POSTGRES_ROOT = SRC_ROOT / "energy_trading" / "infrastructure" / "persistence" / "postgres"
API_ROOT = SRC_ROOT / "energy_trading" / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_DB_LIBRARIES = (
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "energy_trading.infrastructure.persistence.postgres",
)

FORBIDDEN_SHARED_SETTINGS = (
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

FORBIDDEN_POSTGRES_IMPLEMENTATION = (
    "fastapi",
    "starlette",
    "langgraph",
    "langchain",
    "langchain_core",
    "openai",
    "pandas",
    "polars",
    "openpyxl",
    "xgboost",
    "lightgbm",
    "prophet",
    "redis",
    "qdrant_client",
    "energy_trading.api",
    "energy_trading.application",
    "energy_trading.ml",
    "energy_trading.infrastructure.adapters",
)


def test_domain_does_not_import_database_libraries() -> None:
    assert collect_import_violations(DOMAIN_ROOT, FORBIDDEN_DB_LIBRARIES) == []


def test_application_does_not_import_database_libraries() -> None:
    assert collect_import_violations(APPLICATION_ROOT, FORBIDDEN_DB_LIBRARIES) == []


def test_database_settings_do_not_import_runtime_or_outer_layers() -> None:
    assert collect_import_violations(CONFIG_ROOT, FORBIDDEN_SHARED_SETTINGS) == []
    names = imported_modules(DATABASE_SETTINGS)
    assert "sqlalchemy" not in names
    assert "psycopg" not in names
    assert "alembic" not in names


def test_postgres_infrastructure_does_not_import_api_agents_or_ml() -> None:
    assert collect_import_violations(POSTGRES_ROOT, FORBIDDEN_POSTGRES_IMPLEMENTATION) == []


def test_api_composition_root_does_not_wire_postgres() -> None:
    assert collect_import_violations(API_ROOT, FORBIDDEN_DB_LIBRARIES) == []
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
    assert "create_postgres_engine" not in call_names
    assert "create_session_factory" not in call_names
    assert "create_async_engine" not in call_names
    assert "postgres" not in app_source.lower()
