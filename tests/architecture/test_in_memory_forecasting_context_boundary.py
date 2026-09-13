"""In-memory forecasting workflow context stays infrastructure-local."""

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
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
ORCHESTRATION_ROOT = APPLICATION_ROOT / "orchestration"
CONTEXT_PORT_MODULE = ORCHESTRATION_ROOT / "forecasting_context.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
WORKFLOW_MODULE = ORCHESTRATION_ROOT / "forecasting_workflow.py"
TRANSITION_MODULE = ORCHESTRATION_ROOT / "forecasting_transition.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
ADAPTER_MODULE = PRODUCTION_ROOT / "infrastructure" / "orchestration" / "forecasting_context.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
    "energy_trading.application.ports",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.orchestration.forecasting_execution",
    "energy_trading.application.orchestration.forecasting_workflow",
    "energy_trading.application.orchestration.forecasting_transition",
    "energy_trading.infrastructure.cache",
    "energy_trading.infrastructure.persistence",
    "energy_trading.infrastructure.adapters",
    "energy_trading.infrastructure.vector_store",
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
    "threading",
    "multiprocessing",
    "pathlib",
    "concurrent.futures",
)

FORBIDDEN_TYPE_NAMES = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "MutableMapping",
        "TypedDict",
        "Callable",
        "Optional",
        "Protocol",
        "ABC",
        "CachePort",
        "RedisCache",
        "CacheCodec",
        "Session",
        "AsyncSession",
        "Engine",
        "Redis",
        "Path",
        "StateGraph",
        "CompiledStateGraph",
        "FailurePolicyPort",
        "ForecastingExecutionPort",
        "ForecastingWorkflowStep",
        "ForecastingWorkflowContextPort",
        "ConsumerLoadForecastAgent",
        "DAMPriceForecastAgent",
        "ConsumerLoadForecastModelPort",
        "DAMPriceForecastModelPort",
        "ConsumerLoadForecastModelRequest",
        "DAMPriceForecastModelRequest",
        "AgentPort",
        "Repository",
        "UnitOfWork",
        "WorkflowContextPort",
        "ContextPort",
        "ExecutionContext",
        "TaskGroup",
    }
)

FORBIDDEN_PUBLIC_METHODS = frozenset(
    {
        "get_success",
        "list_successes",
        "prepare_plan",
        "delete",
        "clear",
        "reset",
        "dump",
        "get",
        "list",
        "save",
        "load",
        "execute",
        "forecast",
        "run",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "TaskGroup",
        "gather",
        "create_task",
        "as_completed",
        "wait",
        "to_thread",
        "advance_after_forecasting",
        "ForecastingWorkflowStep",
        "ForecastingExecutionPort",
        "ConsumerLoadForecastAgent",
        "DAMPriceForecastAgent",
        "ConsumerLoadForecastModelPort",
        "DAMPriceForecastModelPort",
        "WorkflowContextPort",
        "ContextPort",
        "ExecutionContext",
        "AgentFactory",
        "ServiceLocator",
        "Repository",
        "UnitOfWork",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "__future__",
        "asyncio",
        "collections.abc",
        "energy_trading.application.errors",
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
    return names


def _public_methods(class_def: ast.ClassDef) -> list[str]:
    names: list[str] = []
    for node in class_def.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith(
            "_"
        ):
            names.append(node.name)
    return names


def _annassign_field_names(path: Path, class_name: str) -> tuple[str, ...]:
    class_def = _class_def(path, class_name)
    names: list[str] = []
    for item in class_def.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            names.append(item.target.id)
    return tuple(names)


def test_adapter_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(ADAPTER_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(ADAPTER_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(ADAPTER_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    identifiers = _identifier_names(ADAPTER_MODULE)
    leaked_identifiers = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked_identifiers == []
    names = imported_names(ADAPTER_MODULE)
    assert "ForecastingPlan" in names
    assert "ForecastingSuccess" in names
    assert "WorkflowState" in names
    assert "ForecastingWorkflowContextPort" not in names
    assert "ForecastingExecutionPort" not in names
    assert "ConsumerLoadForecastAgent" not in names
    assert "DAMPriceForecastAgent" not in names
    assert "advance_after_forecasting" not in names


def test_adapter_exposes_exactly_one_structural_class() -> None:
    tree = ast.parse(ADAPTER_MODULE.read_text(encoding="utf-8"), filename=str(ADAPTER_MODULE))
    class_names = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    assert class_names == ["InMemoryForecastingWorkflowContext"]
    class_def = _class_def(ADAPTER_MODULE, "InMemoryForecastingWorkflowContext")
    assert _base_names(class_def) == set()
    assert "ABC" not in _identifier_names(ADAPTER_MODULE)
    assert "Protocol" not in imported_names(ADAPTER_MODULE)
    assert "ForecastingWorkflowContextPort" not in imported_names(ADAPTER_MODULE)
    assert "WorkflowContextPort" not in _identifier_names(ADAPTER_MODULE)


def test_adapter_constructor_copies_typed_plan_mapping() -> None:
    class_def = _class_def(ADAPTER_MODULE, "InMemoryForecastingWorkflowContext")
    init = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert tuple(arg.arg for arg in init.args.args) == ("self", "plans")
    assert init.args.kwonlyargs == []
    assert init.args.vararg is None
    assert init.args.kwarg is None
    assert init.args.args[1].annotation is not None
    assert ast.unparse(init.args.args[1].annotation) == "Mapping[str, ForecastingPlan]"
    source = ast.unparse(init)
    assert "dict(plans)" in source


def test_adapter_public_operations_match_the_port() -> None:
    class_def = _class_def(ADAPTER_MODULE, "InMemoryForecastingWorkflowContext")
    assert _public_methods(class_def) == ["resolve_plan", "record_success"]
    leaked = sorted(name for name in _public_methods(class_def) if name in FORBIDDEN_PUBLIC_METHODS)
    assert leaked == []
    names = annotation_type_names(ADAPTER_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    resolve_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "resolve_plan"
    )
    record_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "record_success"
    )
    assert tuple(arg.arg for arg in resolve_fn.args.args) == ("self",)
    assert [arg.arg for arg in resolve_fn.args.kwonlyargs] == ["state"]
    assert ast.unparse(resolve_fn.args.kwonlyargs[0].annotation) == "WorkflowState"
    assert ast.unparse(resolve_fn.returns) == "ForecastingPlan"
    assert tuple(arg.arg for arg in record_fn.args.args) == ("self",)
    assert [arg.arg for arg in record_fn.args.kwonlyargs] == ["state", "success"]
    assert ast.unparse(record_fn.args.kwonlyargs[0].annotation) == "WorkflowState"
    assert ast.unparse(record_fn.args.kwonlyargs[1].annotation) == "ForecastingSuccess"
    assert ast.unparse(record_fn.returns) == "None"


def test_adapter_uses_asyncio_lock_and_not_execution_or_durable_stores() -> None:
    identifiers = _identifier_names(ADAPTER_MODULE)
    assert "Lock" in identifiers
    source = ADAPTER_MODULE.read_text(encoding="utf-8")
    assert "asyncio.Lock" in source
    assert "TaskGroup" not in source
    assert "asyncio.gather" not in source
    assert "create_task" not in source
    assert "threading" not in source
    assert "multiprocessing" not in source
    assert "advance_after_forecasting" not in source
    assert ".forecast(" not in source
    assert ".run(" not in source
    lowered = source.lower()
    assert "redis" not in lowered
    assert "postgres" not in lowered
    assert "sqlalchemy" not in lowered
    assert "cacheport" not in lowered
    assert "ttl" not in lowered
    assert "UnitOfWork" not in source
    assert "Repository" not in source


def test_application_context_port_remains_infrastructure_free() -> None:
    modules = imported_modules(CONTEXT_PORT_MODULE)
    assert not any(is_forbidden(module, ("energy_trading.infrastructure",)) for module in modules)
    names = imported_names(CONTEXT_PORT_MODULE)
    assert "InMemoryForecastingWorkflowContext" not in names
    source = CONTEXT_PORT_MODULE.read_text(encoding="utf-8")
    assert "InMemoryForecastingWorkflowContext" not in source
    assert "energy_trading.infrastructure" not in source
    class_names = [
        node.name
        for node in ast.parse(source, filename=str(CONTEXT_PORT_MODULE)).body
        if isinstance(node, ast.ClassDef)
    ]
    assert class_names == ["ForecastingWorkflowContextPort"]


def test_graph_workflow_and_transition_do_not_import_the_adapter() -> None:
    for path in (GRAPH_MODULE, WORKFLOW_MODULE, TRANSITION_MODULE):
        names = imported_names(path)
        assert "InMemoryForecastingWorkflowContext" not in names
        modules = imported_modules(path)
        assert "energy_trading.infrastructure.orchestration" not in modules
        assert "energy_trading.infrastructure.orchestration.forecasting_context" not in modules
        source = path.read_text(encoding="utf-8")
        assert "InMemoryForecastingWorkflowContext" not in source


def test_graph_depends_on_forecasting_step_not_concrete_context() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "ForecastingWorkflowStep" in names
    assert "ForecastingWorkflowContextPort" not in names
    assert "InMemoryForecastingWorkflowContext" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "energy_trading.application.orchestration.forecasting_workflow" in modules
    assert "energy_trading.application.orchestration.forecasting_context" not in modules
    assert "energy_trading.infrastructure.orchestration.forecasting_context" not in modules


def test_workflow_state_shape_is_unchanged() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert "InMemoryForecastingWorkflowContext" not in names
    assert "ForecastingPlan" not in names
    assert "ForecastingSuccess" not in names
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "forecasting_plan" not in source
    assert "forecasting_success" not in source
    assert "InMemoryForecastingWorkflowContext" not in source


def test_api_composition_does_not_import_or_construct_the_adapter() -> None:
    forbidden_wiring = (
        "energy_trading.infrastructure.orchestration",
        "energy_trading.infrastructure.orchestration.forecasting_context",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "InMemoryForecastingWorkflowContext" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "inmemoryforecastingworkflowcontext" not in app_source
    assert "forecasting_context" not in app_source
    tree = ast.parse(API_APP.read_text(encoding="utf-8"), filename=str(API_APP))
    create_app = next(
        node
        for node in tree.body
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
    assert "InMemoryForecastingWorkflowContext" not in call_names
