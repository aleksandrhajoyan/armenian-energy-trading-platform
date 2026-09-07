"""Parallel ingestion plan and success contracts stay typed and LangGraph-free."""

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
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
PLAN_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
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
    "scipy",
    "sklearn",
    "lightgbm",
    "xgboost",
    "prophet",
    "torch",
    "tensorflow",
    "n8n",
    "tenacity",
    "backoff",
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
        "TypedDict",
        "Callable",
        "Exception",
        "BaseException",
        "ApplicationError",
        "bytes",
        "bytearray",
        "Path",
        "DataFrame",
        "Request",
        "Response",
        "StateGraph",
        "CompiledStateGraph",
        "Send",
        "RetryPolicy",
        "WorkflowState",
        "FailurePolicyPort",
        "FailurePolicyContext",
        "AgentPort",
        "AgentName",
        "WeatherAndRenewableForecastAgent",
        "HydroResourcesAgent",
        "GenerationAvailabilityAgent",
        "NewsIntelligenceAgent",
        "MarketMonitoringAgent",
        "ParallelIngestionResult",
        "ParallelIngestionOutcome",
        "ParallelIngestionJoin",
        "ParallelIngestionExecution",
        "Optional",
    }
)

FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "payload",
        "data",
        "context",
        "metadata",
        "artifacts",
        "callback",
        "on_complete",
        "exception",
        "error",
        "diagnostics",
        "results",
        "outcome",
        "fallback",
        "retry_count",
        "retries",
        "degraded",
        "status",
        "failed",
        "failure",
        "errors",
        "skipped",
        "partial",
        "provider",
        "persistence",
        "graph",
        "runtime",
        "state",
        "portfolio_id",
        "workflow_id",
    }
)

ALLOWED_PLAN_FIELDS = (
    "weather_and_renewable_forecast",
    "hydro_resources",
    "generation_availability",
    "news_intelligence",
    "market_monitoring",
)

ALLOWED_PLAN_ANNOTATIONS = {
    "weather_and_renewable_forecast": "WeatherAndRenewableForecastRequest",
    "hydro_resources": "HydroResourcesRequest",
    "generation_availability": "GenerationAvailabilityRequest",
    "news_intelligence": "NewsIntelligenceRequest",
    "market_monitoring": "MarketMonitoringRequest",
}

ALLOWED_SUCCESS_ANNOTATIONS = {
    "weather_and_renewable_forecast": "WeatherAndRenewableForecastResult",
    "hydro_resources": "HydroResourcesResult",
    "generation_availability": "GenerationAvailabilityResult",
    "news_intelligence": "NewsIntelligenceResult",
    "market_monitoring": "MarketMonitoringResult",
}

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "energy_trading.application.agents.generation_availability",
        "energy_trading.application.agents.hydro_resources",
        "energy_trading.application.agents.market_monitoring",
        "energy_trading.application.agents.news_intelligence",
        "energy_trading.application.agents.weather_and_renewable_forecast",
    }
)

WORKFLOW_STATE_FIELDS = (
    "workflow_id",
    "portfolio_id",
    "delivery_date",
    "correlation_id",
    "phase",
    "status",
    "diagnostics",
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


def _annassign_field_annotations(path: Path, class_name: str) -> dict[str, str]:
    class_def = _class_def(path, class_name)
    annotations: dict[str, str] = {}
    for item in class_def.body:
        if (
            isinstance(item, ast.AnnAssign)
            and isinstance(item.target, ast.Name)
            and item.annotation is not None
        ):
            annotations[item.target.id] = ast.unparse(item.annotation)
    return annotations


def _base_names(class_def: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for base in class_def.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
    return names


def _identifier_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
            names.update(param.name for param in node.type_params)
    return names


def _module_class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def test_parallel_ingestion_plan_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(PLAN_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(PLAN_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(PLAN_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []


def test_parallel_ingestion_plan_has_exactly_five_typed_request_fields() -> None:
    class_def = _class_def(PLAN_MODULE, "ParallelIngestionPlan")
    assert list(class_def.type_params) == []
    assert _base_names(class_def) == set()
    fields = _annassign_field_names(PLAN_MODULE, "ParallelIngestionPlan")
    assert fields == ALLOWED_PLAN_FIELDS
    leaked = sorted(name for name in fields if name in FORBIDDEN_FIELD_NAMES)
    assert leaked == []
    annotations = _annassign_field_annotations(PLAN_MODULE, "ParallelIngestionPlan")
    assert annotations == ALLOWED_PLAN_ANNOTATIONS
    leaked_types = sorted(name for name in annotations.values() if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    result_types = {
        "WeatherAndRenewableForecastResult",
        "HydroResourcesResult",
        "GenerationAvailabilityResult",
        "NewsIntelligenceResult",
        "MarketMonitoringResult",
    }
    assert result_types.isdisjoint(annotations.values())


def test_parallel_ingestion_success_has_exactly_five_typed_result_fields() -> None:
    class_def = _class_def(PLAN_MODULE, "ParallelIngestionSuccess")
    assert list(class_def.type_params) == []
    assert _base_names(class_def) == set()
    fields = _annassign_field_names(PLAN_MODULE, "ParallelIngestionSuccess")
    assert fields == ALLOWED_PLAN_FIELDS
    leaked = sorted(name for name in fields if name in FORBIDDEN_FIELD_NAMES)
    assert leaked == []
    annotations = _annassign_field_annotations(PLAN_MODULE, "ParallelIngestionSuccess")
    assert annotations == ALLOWED_SUCCESS_ANNOTATIONS
    leaked_types = sorted(name for name in annotations.values() if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    request_types = {
        "WeatherAndRenewableForecastRequest",
        "HydroResourcesRequest",
        "GenerationAvailabilityRequest",
        "NewsIntelligenceRequest",
        "MarketMonitoringRequest",
    }
    assert request_types.isdisjoint(annotations.values())


def test_parallel_ingestion_plan_public_contract_excludes_payload_and_runtime_types() -> None:
    names = annotation_type_names(PLAN_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    identifiers = _identifier_names(PLAN_MODULE)
    assert "Any" not in identifiers
    assert "dict" not in identifiers
    assert "Mapping" not in identifiers
    assert "Callable" not in identifiers
    assert "Exception" not in identifiers
    assert "StateGraph" not in identifiers
    assert "CompiledStateGraph" not in identifiers
    assert "Send" not in identifiers
    assert "WorkflowState" not in identifiers
    assert "FailurePolicyPort" not in identifiers
    assert "AgentPort" not in identifiers
    assert "asyncio" not in identifiers
    assert "gather" not in identifiers
    assert "TaskGroup" not in identifiers
    assert "Optional" not in identifiers
    assert "ParallelIngestionResult" not in identifiers
    assert "ParallelIngestionOutcome" not in identifiers
    assert "ParallelIngestionJoin" not in identifiers
    source = PLAN_MODULE.read_text(encoding="utf-8")
    assert "langgraph" not in source.lower()
    assert "langchain" not in source.lower()


def test_parallel_ingestion_module_exposes_only_plan_and_success_dtos() -> None:
    assert _module_class_names(PLAN_MODULE) == [
        "ParallelIngestionPlan",
        "ParallelIngestionSuccess",
    ]
    for class_name in ("ParallelIngestionPlan", "ParallelIngestionSuccess"):
        class_def = _class_def(PLAN_MODULE, class_name)
        defined = [
            node.name
            for node in class_def.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assert defined == ["__post_init__"]
        assert not any(isinstance(node, ast.AsyncFunctionDef) for node in ast.walk(class_def))


def test_workflow_state_shape_is_unchanged_by_the_plan() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    leaked = sorted(name for name in fields if name in ALLOWED_PLAN_FIELDS)
    assert leaked == []
    names = imported_names(STATE_MODULE)
    assert "ParallelIngestionPlan" not in names
    assert "ParallelIngestionSuccess" not in names
    modules = imported_modules(STATE_MODULE)
    assert "energy_trading.application.orchestration.parallel_ingestion" not in modules


def test_graph_and_failure_policy_remain_unwired_to_the_plan() -> None:
    for path in (GRAPH_MODULE, FAILURE_POLICY_MODULE):
        names = imported_names(path)
        assert "ParallelIngestionPlan" not in names
        assert "ParallelIngestionSuccess" not in names
        modules = imported_modules(path)
        assert "energy_trading.application.orchestration.parallel_ingestion" not in modules
        source = path.read_text(encoding="utf-8")
        assert "ParallelIngestionPlan" not in source
        assert "ParallelIngestionSuccess" not in source
        assert "asyncio.gather" not in source
        assert "TaskGroup" not in source


def test_api_composition_does_not_import_or_construct_parallel_ingestion_plan() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.parallel_ingestion",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "ParallelIngestionPlan" not in names
        assert "ParallelIngestionSuccess" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "parallelingestionplan" not in app_source
    assert "parallelingestionsuccess" not in app_source
    assert "parallel_ingestion" not in app_source
