"""Chunk 8 normalization package must stay a local ACL utility."""

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_import_violations,
)

NORMALIZATION_ROOT = (
    SRC_ROOT / "energy_trading" / "infrastructure" / "adapters" / "structured" / "normalization"
)
INGESTION_PORT = SRC_ROOT / "energy_trading" / "application" / "ports" / "structured_ingestion.py"

FORBIDDEN_PREFIXES = (
    "openai",
    "langchain",
    "langchain_core",
    "langgraph",
    "pandas",
    "polars",
    "openpyxl",
    "fastapi",
    "starlette",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "redis",
    "qdrant_client",
    "httpx",
    "requests",
    "aiohttp",
    "energy_trading.application",
    "energy_trading.api",
    "energy_trading.ml",
    "energy_trading.domain",
    "energy_trading.shared",
)

FORBIDDEN_PORT_TYPES = frozenset(
    {
        "PowerUnit",
        "ZoneInfo",
        "timezone",
        "tzinfo",
        "Path",
        "Workbook",
        "Worksheet",
        "Cell",
        "DataFrame",
        "bytes",
        "dict",
        "Mapping",
        "Any",
        "IntervalGrid",
        "timedelta",
    }
)


def test_normalization_package_does_not_import_outer_layers_or_file_readers() -> None:
    violations = collect_import_violations(NORMALIZATION_ROOT, FORBIDDEN_PREFIXES)
    assert violations == []


def test_structured_ingestion_port_has_no_normalization_config_surface() -> None:
    names = annotation_type_names(INGESTION_PORT)
    violations = sorted(name for name in names if name in FORBIDDEN_PORT_TYPES)
    assert violations == []
    assert async_function_arg_names(INGESTION_PORT, "ingest") == ("self",)
