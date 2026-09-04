"""Chunk 6 CSV adapter must stay a local ACL reader without provider SDKs."""

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_import_violations,
)

CSV_ADAPTER_ROOT = (
    SRC_ROOT / "energy_trading" / "infrastructure" / "adapters" / "structured" / "csv"
)
PORTS_ROOT = SRC_ROOT / "energy_trading" / "application" / "ports"
INGESTION_PORT = PORTS_ROOT / "structured_ingestion.py"

FORBIDDEN_PREFIXES = (
    "pandas",
    "polars",
    "pyarrow",
    "openpyxl",
    "requests",
    "aiohttp",
    "httpx",
    "fastapi",
    "starlette",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "redis",
    "qdrant_client",
    "langchain",
    "langchain_core",
    "langgraph",
    "openai",
    "xgboost",
    "lightgbm",
    "prophet",
    "energy_trading.api",
    "energy_trading.ml",
)

FORBIDDEN_PORT_TYPES = frozenset(
    {
        "Path",
        "PurePath",
        "PosixPath",
        "WindowsPath",
        "TextIO",
        "BinaryIO",
        "csv",
        "DictReader",
        "DataFrame",
        "IntervalGrid",
        "ConsumptionGap",
        "timedelta",
        "bytes",
        "dict",
        "Mapping",
        "Any",
    }
)


def test_csv_adapter_does_not_import_forbidden_providers_or_layers() -> None:
    violations = collect_import_violations(CSV_ADAPTER_ROOT, FORBIDDEN_PREFIXES)
    assert violations == []


def test_structured_ingestion_port_still_has_no_csv_or_path_surface() -> None:
    names = annotation_type_names(INGESTION_PORT)
    violations = sorted(name for name in names if name in FORBIDDEN_PORT_TYPES)
    assert violations == []
    assert async_function_arg_names(INGESTION_PORT, "ingest") == ("self",)
