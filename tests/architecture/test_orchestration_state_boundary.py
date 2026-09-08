"""Application orchestration state remains framework-neutral and snapshot-only."""

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

ORCHESTRATION_ROOT = SRC_ROOT / "energy_trading" / "application" / "orchestration"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
AGENTS_ROOT = SRC_ROOT / "energy_trading" / "application" / "agents"
API_ROOT = SRC_ROOT / "energy_trading" / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.application.agents",
    "fastapi",
    "starlette",
    "langgraph",
    "langchain",
    "langchain_core",
    "openai",
    "anthropic",
    "redis",
    "qdrant_client",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "httpx",
    "requests",
    "aiohttp",
    "pandas",
    "openpyxl",
    "numpy",
    "sklearn",
    "lightgbm",
    "xgboost",
    "prophet",
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
        "TypedDict",
    }
)

FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "payload",
        "data",
        "context",
        "metadata",
        "artifacts",
        "current_agent",
        "completed_agents",
        "pending_agents",
        "agent_request",
        "agent_result",
        "messages",
        "route",
        "node",
        "retry_count",
        "retries",
        "fallback",
        "degraded",
        "timeout",
        "lock",
        "cas",
        "version",
        "redis_key",
        "weather_records",
        "hydro_records",
        "generation_records",
        "news_events",
        "market_prices",
        "weather_and_renewable_forecast",
        "hydro_resources",
        "generation_availability",
        "news_intelligence",
        "market_monitoring",
        "parallel_ingestion_plan",
        "parallel_ingestion_success",
        "parallel_ingestion_execution_port",
        "parallel_ingestion_executor",
        "parallel_ingestion_workflow_context_port",
        "parallel_ingestion_context",
        "parallel_ingestion_workflow_step",
        "parallel_ingestion_workflow",
        "attempt_number",
        "selected_fact",
        "facts",
        "failure_facts",
        "policy_context",
        "retry_state",
        "fallback_state",
        "load_forecasts",
        "price_forecasts",
        "risk_assessment",
        "market_bids",
        "settlement_results",
    }
)

ALLOWED_STATE_FIELDS = (
    "workflow_id",
    "portfolio_id",
    "delivery_date",
    "correlation_id",
    "phase",
    "status",
    "diagnostics",
)

ALLOWED_STATE_IMPORTS = frozenset(
    {
        "dataclasses",
        "datetime",
        "enum",
        "energy_trading.domain.models.ingestion",
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


def test_orchestration_state_does_not_import_outer_layers_or_vendors() -> None:
    state_violations = [
        f"{STATE_MODULE.relative_to(SRC_ROOT)} imports {module}"
        for module in sorted(imported_modules(STATE_MODULE))
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    ]
    assert state_violations == []
    package_forbidden = tuple(
        prefix
        for prefix in FORBIDDEN_PREFIXES
        if prefix not in {"langgraph", "energy_trading.application.agents"}
    )
    assert collect_import_violations(ORCHESTRATION_ROOT, package_forbidden) == []
    leaked = sorted(name for name in imported_names(STATE_MODULE) if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    extras = (
        imported_names(STATE_MODULE)
        - ALLOWED_STATE_IMPORTS
        - {
            "StrEnum",
            "date",
            "dataclass",
            "AdapterDiagnostic",
        }
    )
    assert extras == set()


def test_workflow_state_is_not_generic_and_has_no_payload_surface() -> None:
    class_def = _class_def(STATE_MODULE, "WorkflowState")
    assert list(class_def.type_params) == []
    assert _base_names(class_def) == set()
    names = annotation_type_names(STATE_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    assert "AdapterDiagnostic" in names
    assert "WorkflowPhase" in names
    assert "WorkflowStatus" in names
    assert "date" in names


def test_workflow_state_fields_are_exactly_the_snapshot_contract() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == ALLOWED_STATE_FIELDS
    leaked = sorted(name for name in fields if name in FORBIDDEN_FIELD_NAMES)
    assert leaked == []


def test_workflow_state_has_only_construction_validation() -> None:
    class_def = _class_def(STATE_MODULE, "WorkflowState")
    defined = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert defined == ["__post_init__"]
    assert not any(isinstance(node, ast.AsyncFunctionDef) for node in ast.walk(class_def))
    assert {
        "fail",
        "mark_failed",
        "transition",
        "retry",
        "fallback",
        "fail_parallel_ingestion",
        "advance_after_parallel_ingestion",
    }.isdisjoint(defined)
    names = imported_names(STATE_MODULE)
    assert "fail_parallel_ingestion" not in names
    assert "advance_after_parallel_ingestion" not in names
    assert "build_parallel_ingestion_failure_policy_context" not in names
    assert "execute_parallel_ingestion_failure_action" not in names
    assert "ParallelIngestionFailureHandlingService" not in names
    modules = imported_modules(STATE_MODULE)
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_transition"
        not in modules
    )
    assert "energy_trading.application.orchestration.parallel_ingestion_transition" not in modules
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_context" not in modules
    )
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_action" not in modules
    )
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_handling"
        not in modules
    )
    assert "ParallelIngestionFailureContextResolutionService" not in names
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_context_resolution"
        not in modules
    )


def test_orchestration_package_does_not_introduce_concrete_agents() -> None:
    production_agent_modules = sorted(
        path.name for path in AGENTS_ROOT.glob("*.py") if path.name != "__init__.py"
    )
    assert production_agent_modules == [
        "base.py",
        "generation_availability.py",
        "hydro_resources.py",
        "market_monitoring.py",
        "news_intelligence.py",
        "weather_and_renewable_forecast.py",
    ]
    orchestration_classes: list[str] = []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                orchestration_classes.append(node.name)
    assert orchestration_classes == [
        "FailureAction",
        "FailurePolicyContext",
        "FailurePolicyPort",
        "ParallelIngestionPlan",
        "ParallelIngestionSuccess",
        "ParallelIngestionExecutionPort",
        "ParallelIngestionAgentFailure",
        "ParallelIngestionAttemptNumberPort",
        "ParallelIngestionWorkflowContextPort",
        "ConcurrentParallelIngestionExecutor",
        "ParallelIngestionFailureContextResolutionService",
        "ParallelIngestionFailureDecisionService",
        "ParallelIngestionFailureFact",
        "ParallelIngestionFailureHandlingService",
        "ParallelIngestionFailureSelectionPort",
        "InitialParallelIngestionAttemptNumberSource",
        "StrictSingleParallelIngestionFailureSelector",
        "ParallelIngestionWorkflowStep",
        "WorkflowPhase",
        "WorkflowStatus",
        "WorkflowState",
    ]


def test_api_composition_does_not_import_or_construct_orchestration_state() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.state",
        "langgraph",
        "langchain",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "WorkflowState" not in names
        assert "WorkflowPhase" not in names
        assert "WorkflowStatus" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "workflowstate" not in app_source
    assert "workflowphase" not in app_source
    assert "langgraph" not in app_source
