"""Chunk 11 DLQ persistence must stay behind the application port."""

from __future__ import annotations

import ast

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_import_violations,
    imported_names,
)

PORTS_ROOT = SRC_ROOT / "energy_trading" / "application" / "ports"
DLQ_PORT = PORTS_ROOT / "dlq.py"
PERSISTENCE_ROOT = SRC_ROOT / "energy_trading" / "infrastructure" / "persistence"
PERSISTENCE_DLQ = PERSISTENCE_ROOT / "dlq.py"

FORBIDDEN_PORT_LAYERS = (
    "energy_trading.infrastructure",
    "energy_trading.api",
    "energy_trading.ml",
    "fastapi",
    "starlette",
    "pandas",
    "polars",
    "openpyxl",
    "requests",
    "httpx",
    "aiohttp",
    "sqlalchemy",
    "psycopg",
    "asyncpg",
    "redis",
    "qdrant_client",
)

FORBIDDEN_PORT_TYPES = frozenset(
    {
        "Any",
        "Path",
        "PurePath",
        "PosixPath",
        "WindowsPath",
        "bytes",
        "bytearray",
        "dict",
        "Dict",
        "Mapping",
        "MutableMapping",
        "DataFrame",
        "Workbook",
        "Worksheet",
        "Cell",
        "Connection",
        "Engine",
        "Redis",
    }
)

FORBIDDEN_IMPLEMENTATION_PREFIXES = (
    "fastapi",
    "starlette",
    "pandas",
    "polars",
    "openpyxl",
    "requests",
    "httpx",
    "aiohttp",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "redis",
    "qdrant_client",
    "kafka",
    "aiokafka",
    "confluent_kafka",
    "pika",
    "aio_pika",
    "kombu",
    "langchain",
    "langchain_core",
    "langgraph",
    "openai",
    "xgboost",
    "lightgbm",
    "prophet",
    "energy_trading.api",
    "energy_trading.ml",
    "energy_trading.infrastructure.adapters.structured.csv",
    "energy_trading.infrastructure.adapters.structured.excel",
)

FORBIDDEN_ADAPTER_NAMES = frozenset(
    {
        "ConsumptionCsvAdapter",
        "ConsumptionExcelAdapter",
    }
)


def test_application_dlq_port_does_not_import_infrastructure_or_providers() -> None:
    assert collect_import_violations(PORTS_ROOT, FORBIDDEN_PORT_LAYERS) == []
    names = imported_names(DLQ_PORT)
    leaked = sorted(name for name in names if name in FORBIDDEN_PORT_TYPES)
    assert leaked == []


def test_application_dlq_port_accepts_only_canonical_record() -> None:
    names = annotation_type_names(DLQ_PORT)
    leaked = sorted(name for name in names if name in FORBIDDEN_PORT_TYPES)
    assert leaked == []
    assert "DLQRecord" in names
    assert async_function_arg_names(DLQ_PORT, "enqueue") == ("self", "record")
    tree = ast.parse(DLQ_PORT.read_text(encoding="utf-8"), filename=str(DLQ_PORT))
    enqueue = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "enqueue"
    )
    assert enqueue.args.vararg is None
    assert enqueue.args.kwarg is None


def test_filesystem_dlq_does_not_import_forbidden_providers_or_adapters() -> None:
    assert collect_import_violations(PERSISTENCE_ROOT, FORBIDDEN_IMPLEMENTATION_PREFIXES) == []
    names = imported_names(PERSISTENCE_DLQ)
    leaked = sorted(name for name in names if name in FORBIDDEN_ADAPTER_NAMES)
    assert leaked == []


def test_filesystem_dlq_enqueue_offloads_with_to_thread() -> None:
    tree = ast.parse(PERSISTENCE_DLQ.read_text(encoding="utf-8"), filename=str(PERSISTENCE_DLQ))
    enqueue = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "enqueue"
    )
    calls_to_thread = False
    for node in ast.walk(enqueue):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "to_thread":
                calls_to_thread = True
    assert calls_to_thread


def test_filesystem_dlq_public_enqueue_accepts_only_canonical_record() -> None:
    tree = ast.parse(PERSISTENCE_DLQ.read_text(encoding="utf-8"), filename=str(PERSISTENCE_DLQ))
    cls = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "FilesystemDeadLetterQueue"
    )
    public_methods = [
        node.name
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]
    assert public_methods == ["enqueue"]
    enqueue = next(
        node
        for node in cls.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "enqueue"
    )
    assert [arg.arg for arg in enqueue.args.args] == ["self", "record"]
    assert enqueue.args.vararg is None
    assert enqueue.args.kwarg is None
    names = annotation_type_names(PERSISTENCE_DLQ)
    leaked = sorted(name for name in names if name in FORBIDDEN_PORT_TYPES and name != "Path")
    assert leaked == []
    assert "DLQRecord" in names
    assert "Path" in names
