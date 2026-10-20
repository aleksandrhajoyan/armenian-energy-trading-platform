"""Forecasting-success read Protocol stays typed, read-only, application-only, and unwired."""

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
READ_MODULE = ORCHESTRATION_ROOT / "forecasting_success_read.py"
CONTEXT_MODULE = ORCHESTRATION_ROOT / "forecasting_context.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
API_ROOT = PRODUCTION_ROOT / "api"
APP_MODULE = API_ROOT / "app.py"
IN_MEMORY_CONTEXT_MODULE = (
    PRODUCTION_ROOT / "infrastructure" / "orchestration" / "forecasting_context.py"
)
READ_MODULE_NAME = "energy_trading.application.orchestration.forecasting_success_read"

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "typing",
        "energy_trading.application.orchestration.forecasting_success",
    }
)

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
    "energy_trading.application.ports",
    "energy_trading.application.errors",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.orchestration.state",
    "energy_trading.application.orchestration.forecasting_context",
    "energy_trading.application.orchestration.forecasting_execution",
    "energy_trading.application.orchestration.forecasting_executor",
    "energy_trading.application.orchestration.forecasting_workflow",
    "energy_trading.application.orchestration.forecasting_transition",
    "energy_trading.application.orchestration.forecasting_failure_runtime_handling",
    "energy_trading.application.orchestration.forecasting_failure_handling",
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
    "numpy",
    "sklearn",
    "lightgbm",
    "xgboost",
    "prophet",
    "n8n",
    "tenacity",
    "backoff",
    "asyncio",
    "functools",
    "logging",
    "pathlib",
    "datetime",
    "time",
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
        "Optional",
        "Union",
        "None",
        "WorkflowState",
        "ForecastingPlan",
        "ForecastingWorkflowContextPort",
        "ForecastingExecutionPort",
        "ForecastingWorkflowStep",
        "LoadForecastPoint",
        "PriceForecastPoint",
        "ConsumerLoadForecastAgent",
        "DAMPriceForecastAgent",
        "ConsumerLoadForecastModelPort",
        "DAMPriceForecastModelPort",
        "StateGraph",
        "CompiledStateGraph",
        "Redis",
        "Session",
        "AsyncSession",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "dict",
        "Mapping",
        "Optional",
        "lru_cache",
        "cache",
        "Lock",
        "TaskGroup",
        "gather",
        "create_task",
        "sleep",
        "retry",
        "fallback",
        "save",
        "store",
        "record_success",
        "resolve_plan",
        "set_success",
        "delete",
        "clear",
        "advance_after_forecasting",
        "ForecastingSuccess_empty",
        "Repository",
        "UnitOfWork",
        "ServiceLocator",
        "AgentRegistry",
        "AgentFactory",
        "StateGraph",
        "logger",
        "getLogger",
        "open",
        "now",
        "utcnow",
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


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _class_def(path: Path, class_name: str) -> ast.ClassDef:
    for node in ast.walk(_tree(path)):
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
    names: set[str] = set()
    for node in ast.walk(_tree(path)):
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
    return [
        node.name
        for node in class_def.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and not node.name.startswith("_")
    ]


def _annassign_field_names(path: Path, class_name: str) -> tuple[str, ...]:
    class_def = _class_def(path, class_name)
    return tuple(
        item.target.id
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    )


def test_read_module_belongs_to_application_orchestration() -> None:
    assert READ_MODULE.parent == ORCHESTRATION_ROOT
    assert READ_MODULE.name == "forecasting_success_read.py"
    assert READ_MODULE.exists()


def test_read_module_exposes_exactly_one_public_protocol() -> None:
    tree = _tree(READ_MODULE)
    class_names = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    assert class_names == ["ForecastingSuccessReadPort"]
    module_functions = [
        node.name for node in tree.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert module_functions == []
    module_assignments = [
        node for node in tree.body if isinstance(node, ast.Assign | ast.AnnAssign)
    ]
    assert module_assignments == []


def test_read_port_is_nongeneric_protocol_with_one_async_operation() -> None:
    class_def = _class_def(READ_MODULE, "ForecastingSuccessReadPort")
    assert _base_names(class_def) == {"Protocol"}
    assert list(class_def.type_params) == []
    assert class_def.decorator_list == []
    assert _public_methods(class_def) == ["get_success"]
    methods = [
        node for node in class_def.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert len(methods) == 1
    assert isinstance(methods[0], ast.AsyncFunctionDef)
    assert not any(isinstance(node, ast.Assign | ast.AnnAssign) for node in class_def.body)
    source = READ_MODULE.read_text(encoding="utf-8")
    assert "abstractmethod" not in source
    assert "runtime_checkable" not in source


def test_get_success_requires_keyword_only_str_workflow_id_and_returns_success() -> None:
    class_def = _class_def(READ_MODULE, "ForecastingSuccessReadPort")
    get_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_success"
    )
    assert tuple(arg.arg for arg in get_fn.args.args) == ("self",)
    assert get_fn.args.posonlyargs == []
    assert get_fn.args.defaults == []
    assert get_fn.args.vararg is None
    assert get_fn.args.kwarg is None
    assert [arg.arg for arg in get_fn.args.kwonlyargs] == ["workflow_id"]
    assert get_fn.args.kw_defaults == [None]
    annotation = get_fn.args.kwonlyargs[0].annotation
    assert annotation is not None
    assert ast.unparse(annotation) == "str"
    assert get_fn.returns is not None
    assert ast.unparse(get_fn.returns) == "ForecastingSuccess"
    assert get_fn.decorator_list == []


def test_get_success_body_has_no_implementation_or_fallback_result() -> None:
    class_def = _class_def(READ_MODULE, "ForecastingSuccessReadPort")
    get_fn = next(node for node in class_def.body if isinstance(node, ast.AsyncFunctionDef))
    body = list(get_fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        if isinstance(body[0].value.value, str):
            body = body[1:]
    assert len(body) == 1
    assert isinstance(body[0], ast.Expr)
    assert isinstance(body[0].value, ast.Constant)
    assert body[0].value.value is Ellipsis
    for node in ast.walk(_tree(READ_MODULE)):
        assert not isinstance(node, ast.Call)
        assert not isinstance(node, ast.Return | ast.Raise | ast.Try | ast.Await)


def test_read_module_imports_only_protocol_and_forecasting_success() -> None:
    modules = imported_modules(READ_MODULE)
    assert modules == ALLOWED_MODULE_IMPORTS
    leaked = sorted(module for module in modules if is_forbidden(module, FORBIDDEN_PREFIXES))
    assert leaked == []
    assert imported_names(READ_MODULE) - ALLOWED_MODULE_IMPORTS == {
        "Protocol",
        "ForecastingSuccess",
    }
    source = READ_MODULE.read_text(encoding="utf-8")
    assert "TYPE_CHECKING" not in source
    assert "importlib" not in source
    assert "__import__" not in source


def test_read_contract_excludes_generic_payload_storage_and_runtime_types() -> None:
    names = annotation_type_names(READ_MODULE)
    assert names <= {"Protocol", "str", "ForecastingSuccess"}
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    identifiers = _identifier_names(READ_MODULE)
    leaked_identifiers = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked_identifiers == []
    code_only = " ".join(sorted(identifiers | imported_modules(READ_MODULE))).lower()
    for token in (
        "langgraph",
        "langchain",
        "fastapi",
        "redis",
        "sqlalchemy",
        "psycopg",
        "qdrant",
        "openai",
        "anthropic",
        "n8n",
        "registry",
        "factory",
        "repository",
        "cache",
        "lock",
        "retry",
        "fallback",
    ):
        assert token not in code_only


def test_workflow_state_keeps_seven_canonical_fields_and_ignores_read_port() -> None:
    assert _annassign_field_names(STATE_MODULE, "WorkflowState") == WORKFLOW_STATE_FIELDS
    assert READ_MODULE_NAME not in imported_modules(STATE_MODULE)
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "ForecastingSuccessReadPort" not in source
    assert "forecasting_success_read" not in source


def test_forecasting_context_port_keeps_published_two_method_contract() -> None:
    class_def = _class_def(CONTEXT_MODULE, "ForecastingWorkflowContextPort")
    assert _public_methods(class_def) == ["resolve_plan", "record_success"]
    assert READ_MODULE_NAME not in imported_modules(CONTEXT_MODULE)
    assert "ForecastingSuccessReadPort" not in CONTEXT_MODULE.read_text(encoding="utf-8")


def test_in_memory_forecasting_context_remains_unchanged_and_unaware() -> None:
    class_def = _class_def(IN_MEMORY_CONTEXT_MODULE, "InMemoryForecastingWorkflowContext")
    assert _public_methods(class_def) == ["resolve_plan", "record_success"]
    assert "get_success" not in _public_methods(class_def)
    assert READ_MODULE_NAME not in imported_modules(IN_MEMORY_CONTEXT_MODULE)
    assert "ForecastingSuccessReadPort" not in imported_names(IN_MEMORY_CONTEXT_MODULE)
    assert "ForecastingSuccessReadPort" not in IN_MEMORY_CONTEXT_MODULE.read_text(encoding="utf-8")


def test_graph_remains_unaware_of_the_read_port() -> None:
    assert READ_MODULE_NAME not in imported_modules(GRAPH_MODULE)
    assert "ForecastingSuccessReadPort" not in imported_names(GRAPH_MODULE)
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "ForecastingSuccessReadPort" not in source
    assert "forecasting_success_read" not in source
    assert "get_success" not in source


def test_create_app_and_api_remain_unaware_of_the_read_port() -> None:
    assert READ_MODULE_NAME not in imported_modules(APP_MODULE)
    assert "ForecastingSuccessReadPort" not in APP_MODULE.read_text(encoding="utf-8")
    assert collect_import_violations(API_ROOT, (READ_MODULE_NAME,)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "ForecastingSuccessReadPort" not in source
        assert "forecasting_success_read" not in source


def test_no_production_module_implements_or_imports_the_read_port_yet() -> None:
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path == READ_MODULE:
            continue
        assert READ_MODULE_NAME not in imported_modules(path), path
        assert "ForecastingSuccessReadPort" not in imported_names(path), path
