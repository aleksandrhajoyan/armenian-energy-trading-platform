"""Alembic foundation tests that do not open a PostgreSQL connection."""

from __future__ import annotations

import ast
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from tests.architecture.import_inspection import SRC_ROOT, is_forbidden

REPO_ROOT = SRC_ROOT.parent
ALEMBIC_INI = REPO_ROOT / "alembic.ini"
ALEMBIC_ENV = REPO_ROOT / "alembic" / "env.py"
VERSIONS_DIR = REPO_ROOT / "alembic" / "versions"
BOOTSTRAP_REVISION = "0001_bootstrap"
BOOTSTRAP_FILE = VERSIONS_DIR / "0001_bootstrap_postgres_timescaledb.py"

FORBIDDEN_ENV_IMPORTS = (
    "fastapi",
    "starlette",
    "energy_trading.api",
    "energy_trading.application",
    "energy_trading.domain",
    "energy_trading.ml",
)

CANONICAL_TABLE_TOKENS = (
    "consumption",
    "weather",
    "hydro",
    "generation",
    "forecast",
    "market_price",
    "market_bid",
    "settlement",
    "regulatory",
    "dlq",
    "outbox",
    "users",
)


def _alembic_config() -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    return config


def _imported_module_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    return imported


def test_alembic_configuration_loads() -> None:
    config = _alembic_config()
    script_location = config.get_main_option("script_location")
    assert script_location is not None
    assert Path(script_location).name == "alembic"


def test_exactly_one_initial_bootstrap_revision_exists() -> None:
    script = ScriptDirectory.from_config(_alembic_config())
    revisions = list(script.walk_revisions())
    assert len(revisions) == 1
    revision = revisions[0]
    assert revision.revision == BOOTSTRAP_REVISION
    assert revision.down_revision is None
    assert script.get_current_head() == BOOTSTRAP_REVISION
    assert BOOTSTRAP_FILE.is_file()


def test_migration_bootstraps_timescaledb_extension() -> None:
    text = BOOTSTRAP_FILE.read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS timescaledb" in text


def test_migration_bootstraps_energy_trading_schema() -> None:
    text = BOOTSTRAP_FILE.read_text(encoding="utf-8")
    assert "CREATE SCHEMA IF NOT EXISTS energy_trading" in text or (
        "CREATE SCHEMA IF NOT EXISTS" in text and "energy_trading" in text
    )


def test_migration_creates_no_canonical_business_tables() -> None:
    text = BOOTSTRAP_FILE.read_text(encoding="utf-8")
    assert "create table" not in text.lower()
    lowered = text.lower()
    for token in CANONICAL_TABLE_TOKENS:
        assert f"create table {token}" not in lowered


def test_downgrade_does_not_drop_timescaledb_extension() -> None:
    text = BOOTSTRAP_FILE.read_text(encoding="utf-8")
    assert "drop extension" not in text.lower()
    tree = ast.parse(text, filename=str(BOOTSTRAP_FILE))
    downgrade = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "downgrade"
    )
    executed: list[str] = []
    for node in ast.walk(downgrade):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else ""
        if name != "execute" or not node.args:
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            executed.append(arg.value)
        elif isinstance(arg, ast.JoinedStr):
            executed.append(
                "".join(part.value if isinstance(part, ast.Constant) else "" for part in arg.values)
            )
    assert executed
    assert all("extension" not in statement.lower() for statement in executed)


def test_migration_files_contain_no_hardcoded_credentials() -> None:
    files = [ALEMBIC_INI, ALEMBIC_ENV, BOOTSTRAP_FILE]
    forbidden_snippets = (
        "ENERGY_DB_PASSWORD=",
        "change-me",
        "postgresql+psycopg://",
    )
    for path in files:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for snippet in forbidden_snippets:
            assert snippet.lower() not in lowered, f"{path} contains {snippet!r}"
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("sqlalchemy.url"):
                _, _, value = stripped.partition("=")
                assert value.strip() == "", f"{path} hardcodes sqlalchemy.url"


def test_alembic_heads_does_not_need_a_database() -> None:
    script = ScriptDirectory.from_config(_alembic_config())
    heads = script.get_heads()
    assert heads == [BOOTSTRAP_REVISION]


def test_alembic_env_does_not_import_api_agents_or_domain() -> None:
    imported = _imported_module_names(ALEMBIC_ENV)
    leaked = sorted(module for module in imported if is_forbidden(module, FORBIDDEN_ENV_IMPORTS))
    assert leaked == []
