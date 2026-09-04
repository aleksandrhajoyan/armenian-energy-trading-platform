"""Chunk 5 schema-mapping package must stay a local ACL utility."""

from tests.architecture.import_inspection import SRC_ROOT, collect_import_violations

SCHEMA_MAPPING_ROOT = (
    SRC_ROOT / "energy_trading" / "infrastructure" / "adapters" / "structured" / "schema_mapping"
)

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
    "rapidfuzz",
    "fuzzywuzzy",
    "sentence_transformers",
    "energy_trading.application",
    "energy_trading.api",
    "energy_trading.ml",
    "energy_trading.domain",
    "energy_trading.shared",
)


def test_schema_mapping_does_not_import_providers_file_io_or_outer_layers() -> None:
    violations = collect_import_violations(SCHEMA_MAPPING_ROOT, FORBIDDEN_PREFIXES)
    assert violations == []
