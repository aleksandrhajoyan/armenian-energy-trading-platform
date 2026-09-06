"""Weather agent and source port remain application-owned and provider-neutral."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    collect_import_violations,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
AGENT_MODULE = PRODUCTION_ROOT / "application" / "agents" / "weather_and_renewable_forecast.py"
PORT_MODULE = PRODUCTION_ROOT / "application" / "ports" / "weather_records.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "fastapi",
    "starlette",
    "langgraph",
    "langchain",
    "langchain_core",
    "openai",
    "anthropic",
    "redis",
    "qdrant_client",
    "qdrant",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "httpx",
    "requests",
    "aiohttp",
    "pandas",
    "polars",
    "openpyxl",
    "numpy",
    "sklearn",
    "lightgbm",
    "xgboost",
    "prophet",
    "torch",
    "tensorflow",
    "n8n",
)

FORBIDDEN_TYPE_NAMES = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "dict",
        "Dict",
        "Mapping",
        "MutableMapping",
        "bytes",
        "bytearray",
        "Path",
        "DataFrame",
        "Workbook",
        "Request",
        "Response",
        "RetryPolicy",
        "FailurePolicyPort",
    }
)

ALLOWED_AGENT_IMPORTS = frozenset(
    {
        "dataclasses",
        "datetime",
        "energy_trading.application.agents.base",
        "energy_trading.application.ports.weather_records",
        "energy_trading.domain.models.observations",
        "energy_trading.domain.value_objects.time",
    }
)

ALLOWED_PORT_IMPORTS = frozenset(
    {
        "typing",
        "energy_trading.domain.models.observations",
        "energy_trading.domain.value_objects.quantities",
        "energy_trading.domain.value_objects.time",
    }
)


def _class_def(path: Path, class_name: str) -> ast.ClassDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    msg = f"class {class_name!r} not found in {path}"
    raise AssertionError(msg)


def _annassign_field_names(path: Path, class_name: str) -> tuple[str, ...]:
    class_def = _class_def(path, class_name)
    names: list[str] = []
    for item in class_def.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            names.append(item.target.id)
    return tuple(names)


def _base_names(class_def: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for base in class_def.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
    return names


def _module_class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def test_weather_modules_do_not_import_outer_layers_or_vendors() -> None:
    for path in (AGENT_MODULE, PORT_MODULE):
        leaked = sorted(
            module for module in imported_modules(path) if is_forbidden(module, FORBIDDEN_PREFIXES)
        )
        assert leaked == []
        leaked_names = sorted(name for name in imported_names(path) if name in FORBIDDEN_TYPE_NAMES)
        assert leaked_names == []
    extras_agent = imported_modules(AGENT_MODULE) - ALLOWED_AGENT_IMPORTS
    assert extras_agent == set()
    extras_port = imported_modules(PORT_MODULE) - ALLOWED_PORT_IMPORTS
    assert extras_port == set()


def test_weather_source_port_is_nongeneric_protocol_with_async_fetch() -> None:
    class_def = _class_def(PORT_MODULE, "WeatherRecordSourcePort")
    bases = _base_names(class_def)
    assert "Protocol" in bases
    assert "ABC" not in bases
    assert list(class_def.type_params) == []
    source = PORT_MODULE.read_text(encoding="utf-8")
    assert "abstractmethod" not in source
    defined = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert defined == ["fetch"]
    fetch_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "fetch"
    )
    assert tuple(arg.arg for arg in fetch_fn.args.args) == ("self",)
    assert tuple(arg.arg for arg in fetch_fn.args.kwonlyargs) == (
        "location_id",
        "horizon_start",
        "horizon_end",
    )
    assert fetch_fn.args.vararg is None
    assert fetch_fn.args.kwarg is None
    assert fetch_fn.returns is not None
    assert ast.unparse(fetch_fn.returns) == "tuple[WeatherRecord, ...]"
    names = annotation_type_names(PORT_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    assert "WeatherRecord" in names
    assert "EntityId" in names
    assert "UtcDateTime" in names


def test_weather_source_port_module_has_no_concrete_implementation() -> None:
    assert _module_class_names(PORT_MODULE) == ["WeatherRecordSourcePort"]


def test_weather_agent_public_surface_is_name_and_run() -> None:
    class_def = _class_def(AGENT_MODULE, "WeatherAndRenewableForecastAgent")
    assert _base_names(class_def) == set()
    defined = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert defined == ["__init__", "name", "run"]
    name_fn = next(
        node for node in class_def.body if isinstance(node, ast.FunctionDef) and node.name == "name"
    )
    assert any(
        isinstance(item, ast.Name) and item.id == "property" for item in name_fn.decorator_list
    )
    run_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "run"
    )
    assert tuple(arg.arg for arg in run_fn.args.args) == ("self", "request")
    assert run_fn.args.vararg is None
    assert run_fn.args.kwarg is None
    assert ast.unparse(run_fn.args.args[1].annotation) == "WeatherAndRenewableForecastRequest"
    assert ast.unparse(run_fn.returns) == "WeatherAndRenewableForecastResult"
    names = annotation_type_names(AGENT_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    assert "Any" not in imported_names(AGENT_MODULE)
    assert "dict" not in imported_names(AGENT_MODULE)
    assert "AgentRegistry" not in imported_names(AGENT_MODULE)
    assert "AgentFactory" not in imported_names(AGENT_MODULE)
    assert "FailurePolicyPort" not in imported_names(AGENT_MODULE)


def test_weather_request_and_result_have_exact_fields() -> None:
    assert _annassign_field_names(AGENT_MODULE, "WeatherAndRenewableForecastRequest") == (
        "location_id",
        "horizon_start",
        "horizon_end",
    )
    assert _annassign_field_names(AGENT_MODULE, "WeatherAndRenewableForecastResult") == ("records",)


def test_graph_module_does_not_import_or_invoke_weather_agent() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "WeatherAndRenewableForecastAgent" not in names
    assert "WeatherRecordSourcePort" not in names
    assert "WeatherAndRenewableForecastRequest" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "energy_trading.application.agents.weather_and_renewable_forecast" not in modules
    assert "energy_trading.application.ports.weather_records" not in modules
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "WeatherAndRenewableForecastAgent" not in graph_source
    assert "WeatherRecordSourcePort" not in graph_source


def test_api_composition_does_not_import_or_construct_weather_agent() -> None:
    forbidden_wiring = (
        "energy_trading.application.agents.weather_and_renewable_forecast",
        "energy_trading.application.ports.weather_records",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "WeatherAndRenewableForecastAgent" not in names
        assert "WeatherRecordSourcePort" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "weatherandrenewableforecast" not in app_source
    assert "weatherrecordsourceport" not in app_source
