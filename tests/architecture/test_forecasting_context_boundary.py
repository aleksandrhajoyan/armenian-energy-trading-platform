"""Forecasting workflow-context Protocol stays typed, application-only, and unwired."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    collect_http_api_import_violations,
    collect_import_violations,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
CONTEXT_MODULE = ORCHESTRATION_ROOT / "forecasting_context.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
API_ROOT = PRODUCTION_ROOT / "api"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
    "energy_trading.application.ports",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.orchestration.forecasting_execution",
    "energy_trading.domain.models.forecasting",
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
    "asyncio",
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
        "Optional",
        "Session",
        "AsyncSession",
        "Engine",
        "Connection",
        "Redis",
        "RedisClient",
        "StateGraph",
        "CompiledStateGraph",
        "Send",
        "RetryPolicy",
        "FailurePolicyPort",
        "FailurePolicyContext",
        "AgentPort",
        "AgentName",
        "ConsumerLoadForecastAgent",
        "DAMPriceForecastAgent",
        "ConsumerLoadForecastModelPort",
        "DAMPriceForecastModelPort",
        "ConsumerLoadForecastModelRequest",
        "DAMPriceForecastModelRequest",
        "LoadForecastPoint",
        "PriceForecastPoint",
        "ForecastingExecutionPort",
        "ForecastingResult",
        "ForecastingOutcome",
        "WorkflowContextPort",
        "ContextPort",
        "ExecutionContext",
        "ModelPort",
        "MLPort",
        "ForecastModelPort",
        "ExecutionPort",
        "WorkflowExecutionPort",
        "ForecastExecutionPort",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "dict",
        "Mapping",
        "MutableMapping",
        "TypedDict",
        "Callable",
        "Exception",
        "Optional",
        "redis_get",
        "db_load",
        "insert",
        "commit",
        "save_row",
        "Session",
        "AsyncSession",
        "Redis",
        "StateGraph",
        "CompiledStateGraph",
        "Send",
        "TaskGroup",
        "gather",
        "create_task",
        "AgentFactory",
        "AgentRegistry",
        "ServiceLocator",
        "WorkflowContextPort",
        "ContextPort",
        "ExecutionContext",
        "ForecastingExecutionPort",
    }
)

MODULE_FORBIDDEN_CLASS_NAMES = frozenset(
    {
        "ForecastingExecutor",
        "ConcurrentForecastingExecutor",
        "SequentialForecastingExecutor",
        "ForecastingWorkflowStep",
        "ForecastingWorkflowNodeAdapter",
        "InMemoryForecastingWorkflowContext",
        "RedisForecastingWorkflowContext",
        "PostgresForecastingWorkflowContext",
        "ForecastingExecutionPort",
        "ForecastingResult",
        "ForecastingOutcome",
        "WorkflowContextPort",
        "ContextPort",
        "ExecutionContext",
        "ExecutionPort",
        "WorkflowExecutionPort",
        "ForecastExecutionPort",
        "ModelPort",
        "MLPort",
        "ForecastModelPort",
        "AgentFactory",
        "AgentRegistry",
        "ServiceLocator",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "typing",
        "energy_trading.application.orchestration.forecasting_plan",
        "energy_trading.application.orchestration.forecasting_success",
        "energy_trading.application.orchestration.state",
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


def _async_method(class_def: ast.ClassDef, method_name: str) -> ast.AsyncFunctionDef:
    for node in class_def.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == method_name:
            return node
    msg = f"async method {method_name!r} not found on {class_def.name}"
    raise AssertionError(msg)


def test_context_module_belongs_to_application_orchestration() -> None:
    assert CONTEXT_MODULE.parent == ORCHESTRATION_ROOT
    assert CONTEXT_MODULE.name == "forecasting_context.py"
    assert CONTEXT_MODULE.exists()


def test_context_module_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(CONTEXT_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(CONTEXT_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(CONTEXT_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(CONTEXT_MODULE)
    assert "Protocol" in names
    assert "WorkflowState" in names
    assert "ForecastingPlan" in names
    assert "ForecastingSuccess" in names
    assert "ForecastingExecutionPort" not in names
    assert "ConsumerLoadForecastAgent" not in names
    assert "DAMPriceForecastAgent" not in names
    assert "ConsumerLoadForecastModelPort" not in names
    assert "DAMPriceForecastModelPort" not in names


def test_context_port_is_nongeneric_protocol_with_exact_async_operations() -> None:
    class_def = _class_def(CONTEXT_MODULE, "ForecastingWorkflowContextPort")
    assert class_def.name == "ForecastingWorkflowContextPort"
    bases = _base_names(class_def)
    assert "Protocol" in bases
    assert "ABC" not in bases
    assert "Generic" not in bases
    assert list(class_def.type_params) == []
    source = CONTEXT_MODULE.read_text(encoding="utf-8")
    assert "abstractmethod" not in source
    assert "runtime_checkable" not in source
    defined_nodes = [
        node for node in class_def.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert [node.name for node in defined_nodes] == ["resolve_plan", "record_success"]
    assert all(isinstance(node, ast.AsyncFunctionDef) for node in defined_nodes)


def test_resolve_plan_annotations_match_workflow_state_and_plan() -> None:
    class_def = _class_def(CONTEXT_MODULE, "ForecastingWorkflowContextPort")
    resolve_fn = _async_method(class_def, "resolve_plan")
    assert tuple(arg.arg for arg in resolve_fn.args.args) == ("self",)
    assert resolve_fn.args.vararg is None
    assert resolve_fn.args.kwarg is None
    assert [arg.arg for arg in resolve_fn.args.kwonlyargs] == ["state"]
    assert resolve_fn.args.kw_defaults == [None]
    assert resolve_fn.args.kwonlyargs[0].annotation is not None
    assert resolve_fn.returns is not None
    assert ast.unparse(resolve_fn.args.kwonlyargs[0].annotation) == "WorkflowState"
    assert ast.unparse(resolve_fn.returns) == "ForecastingPlan"


def test_record_success_annotations_match_workflow_state_and_success() -> None:
    class_def = _class_def(CONTEXT_MODULE, "ForecastingWorkflowContextPort")
    record_fn = _async_method(class_def, "record_success")
    assert tuple(arg.arg for arg in record_fn.args.args) == ("self",)
    assert record_fn.args.vararg is None
    assert record_fn.args.kwarg is None
    assert [arg.arg for arg in record_fn.args.kwonlyargs] == ["state", "success"]
    assert record_fn.args.kw_defaults == [None, None]
    assert record_fn.args.kwonlyargs[0].annotation is not None
    assert record_fn.args.kwonlyargs[1].annotation is not None
    assert record_fn.returns is not None
    assert ast.unparse(record_fn.args.kwonlyargs[0].annotation) == "WorkflowState"
    assert ast.unparse(record_fn.args.kwonlyargs[1].annotation) == "ForecastingSuccess"
    assert ast.unparse(record_fn.returns) == "None"


def test_context_module_exposes_only_the_context_port() -> None:
    class_names = _module_class_names(CONTEXT_MODULE)
    assert class_names == ["ForecastingWorkflowContextPort"]
    leaked_classes = sorted(name for name in class_names if name in MODULE_FORBIDDEN_CLASS_NAMES)
    assert leaked_classes == []
    identifiers = _identifier_names(CONTEXT_MODULE)
    leaked_forbidden = sorted(name for name in identifiers if name in MODULE_FORBIDDEN_CLASS_NAMES)
    assert leaked_forbidden == []


def test_context_public_contract_excludes_generic_storage_and_runtime_types() -> None:
    names = annotation_type_names(CONTEXT_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    identifiers = _identifier_names(CONTEXT_MODULE)
    leaked_identifiers = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked_identifiers == []
    source = CONTEXT_MODULE.read_text(encoding="utf-8")
    assert "langgraph" not in source.lower()
    assert "langchain" not in source.lower()
    assert "redis" not in source.lower()
    assert "sqlalchemy" not in source.lower()
    assert "psycopg" not in source.lower()
    assert "qdrant" not in source.lower()
    assert "openai" not in source.lower()
    assert "fastapi" not in source.lower()
    assert "factory" not in source.lower()
    assert "registry" not in source.lower()
    assert "service locator" not in source.lower()
    assert "asyncio.gather" not in source
    assert "TaskGroup" not in source
    assert "create_task" not in source
    assert ".run(" not in source
    assert ".forecast(" not in source


def test_workflow_state_shape_is_unchanged_and_does_not_import_the_port() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert "ForecastingWorkflowContextPort" not in names
    assert "ForecastingPlan" not in names
    assert "ForecastingSuccess" not in names
    modules = imported_modules(STATE_MODULE)
    assert "energy_trading.application.orchestration.forecasting_context" not in modules
    assert "energy_trading.application.orchestration.forecasting_plan" not in modules
    assert "energy_trading.application.orchestration.forecasting_success" not in modules
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "forecasting_plan" not in source
    assert "forecasting_success" not in source
    assert "ForecastingWorkflowContextPort" not in source


def test_graph_remains_unwired_to_the_forecasting_context_port() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "ForecastingWorkflowContextPort" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "energy_trading.application.orchestration.forecasting_context" not in modules
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "ForecastingWorkflowContextPort" not in source
    assert "forecasting_context" not in source


def test_api_composition_does_not_import_or_construct_forecasting_context_port() -> None:
    forbidden_wiring = ("energy_trading.application.orchestration.forecasting_context",)
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    composition_leaks = collect_import_violations(API_ROOT, forbidden_wiring)
    assert composition_leaks == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "ForecastingWorkflowContextPort" not in names
        source = path.read_text(encoding="utf-8")
        assert "ForecastingWorkflowContextPort" not in source
        assert "forecasting_context" not in source
