"""Forecasting workflow step stays application-owned and LangGraph-free."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_http_api_import_violations,
    http_transport_api_paths,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
WORKFLOW_MODULE = ORCHESTRATION_ROOT / "forecasting_workflow.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
EXECUTION_MODULE = ORCHESTRATION_ROOT / "forecasting_execution.py"
CONTEXT_MODULE = ORCHESTRATION_ROOT / "forecasting_context.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
    "energy_trading.application.ports",
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
        "Optional",
        "FailurePolicyPort",
        "FailurePolicyContext",
        "FailureAction",
        "ForecastingExecutor",
        "ConcurrentForecastingExecutor",
        "SequentialForecastingExecutor",
        "ConsumerLoadForecastAgent",
        "DAMPriceForecastAgent",
        "ConsumerLoadForecastModelPort",
        "DAMPriceForecastModelPort",
        "StateGraph",
        "CompiledStateGraph",
        "Send",
        "RetryPolicy",
        "AgentPort",
        "AgentName",
        "WorkflowStep",
        "ExecutionService",
        "AgentFactory",
        "ServiceLocator",
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
        "Callable",
        "FailurePolicyPort",
        "ForecastingExecutor",
        "ConcurrentForecastingExecutor",
        "SequentialForecastingExecutor",
        "ConsumerLoadForecastAgent",
        "DAMPriceForecastAgent",
        "ConsumerLoadForecastModelPort",
        "DAMPriceForecastModelPort",
        "tenacity",
        "backoff",
        "sleep",
        "wait",
        "retry",
        "fallback",
        "Timeout",
        "asyncio",
        "TaskGroup",
        "gather",
        "create_task",
        "replace",
        "forecast",
        "WorkflowStep",
        "AgentFactory",
        "ServiceLocator",
        "advance_after_forecasting",
        "complete_forecasting",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.orchestration.forecasting_context",
        "energy_trading.application.orchestration.forecasting_execution",
        "energy_trading.application.orchestration.state",
    }
)

ALLOWED_INIT_ANNOTATIONS = {
    "context": "ForecastingWorkflowContextPort",
    "executor": "ForecastingExecutionPort",
}

WORKFLOW_STATE_FIELDS = (
    "workflow_id",
    "portfolio_id",
    "delivery_date",
    "correlation_id",
    "phase",
    "status",
    "diagnostics",
)

MODULE_FORBIDDEN_CLASS_NAMES = frozenset(
    {
        "ForecastingExecutor",
        "ConcurrentForecastingExecutor",
        "SequentialForecastingExecutor",
        "ForecastingWorkflowNodeAdapter",
        "InMemoryForecastingWorkflowContext",
        "RedisForecastingWorkflowContext",
        "PostgresForecastingWorkflowContext",
        "WorkflowStep",
        "AgentFactory",
        "ServiceLocator",
    }
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


def _module_class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def _annassign_field_names(path: Path, class_name: str) -> tuple[str, ...]:
    class_def = _class_def(path, class_name)
    names: list[str] = []
    for item in class_def.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            names.append(item.target.id)
    return tuple(names)


def _init_arg_annotations(class_def: ast.ClassDef) -> dict[str, str]:
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    annotations: dict[str, str] = {}
    for arg in (*init_fn.args.args, *init_fn.args.kwonlyargs):
        if arg.arg == "self" or arg.annotation is None:
            continue
        annotations[arg.arg] = ast.unparse(arg.annotation)
    return annotations


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


def _run_method(class_def: ast.ClassDef) -> ast.AsyncFunctionDef:
    for node in class_def.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "run":
            return node
    msg = "async method 'run' not found on ForecastingWorkflowStep"
    raise AssertionError(msg)


def _awaited_call_attrs(run_fn: ast.AsyncFunctionDef) -> list[tuple[str, tuple[str, ...]]]:
    awaited: list[tuple[str, tuple[str, ...]]] = []
    for node in run_fn.body:
        expr = node.value if isinstance(node, ast.Assign) else node
        if isinstance(expr, ast.Expr):
            expr = expr.value
        if not isinstance(expr, ast.Await):
            continue
        call = expr.value
        if not isinstance(call, ast.Call):
            continue
        if not isinstance(call.func, ast.Attribute):
            continue
        keywords = tuple(keyword.arg for keyword in call.keywords if keyword.arg is not None)
        awaited.append((call.func.attr, keywords))
    return awaited


def test_workflow_step_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(WORKFLOW_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(WORKFLOW_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(WORKFLOW_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []


def test_workflow_module_exposes_exactly_one_concrete_class() -> None:
    assert _module_class_names(WORKFLOW_MODULE) == ["ForecastingWorkflowStep"]
    production_steps: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "ForecastingWorkflowStep":
                production_steps.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_steps == ["energy_trading/application/orchestration/forecasting_workflow.py"]
    leaked_classes = sorted(
        name
        for name in _module_class_names(WORKFLOW_MODULE)
        if name in MODULE_FORBIDDEN_CLASS_NAMES
    )
    assert leaked_classes == []


def test_workflow_step_is_nongeneric_concrete_class() -> None:
    class_def = _class_def(WORKFLOW_MODULE, "ForecastingWorkflowStep")
    assert list(class_def.type_params) == []
    bases = _base_names(class_def)
    assert "Protocol" not in bases
    assert "ABC" not in bases
    assert "Generic" not in bases
    source = WORKFLOW_MODULE.read_text(encoding="utf-8")
    assert "abstractmethod" not in source
    assert "registry" not in source.lower()
    assert "factory" not in source.lower()


def test_workflow_step_constructor_owns_exactly_the_two_ports() -> None:
    class_def = _class_def(WORKFLOW_MODULE, "ForecastingWorkflowStep")
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    arg_names = tuple(arg.arg for arg in init_fn.args.args if arg.arg != "self")
    assert arg_names == ("context", "executor")
    assert init_fn.args.kwonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    assert _init_arg_annotations(class_def) == ALLOWED_INIT_ANNOTATIONS


def test_workflow_step_public_operation_is_async_run() -> None:
    class_def = _class_def(WORKFLOW_MODULE, "ForecastingWorkflowStep")
    defined = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert defined == ["__init__", "run"]
    run_fn = _run_method(class_def)
    assert tuple(arg.arg for arg in run_fn.args.args) == ("self", "state")
    assert run_fn.args.vararg is None
    assert run_fn.args.kwarg is None
    assert run_fn.args.kwonlyargs == []
    assert async_function_arg_names(WORKFLOW_MODULE, "run") == ("self", "state")
    assert run_fn.args.args[1].annotation is not None
    assert run_fn.returns is not None
    assert ast.unparse(run_fn.args.args[1].annotation) == "WorkflowState"
    assert ast.unparse(run_fn.returns) == "WorkflowState"


def test_run_composes_resolve_execute_record_without_retry_or_transition() -> None:
    class_def = _class_def(WORKFLOW_MODULE, "ForecastingWorkflowStep")
    run_fn = _run_method(class_def)
    assert not any(isinstance(node, ast.Try) for node in ast.walk(run_fn))
    assert _awaited_call_attrs(run_fn) == [
        ("resolve_plan", ("state",)),
        ("execute", ("plan",)),
        ("record_success", ("state", "success")),
    ]


def test_workflow_step_public_contract_excludes_payload_and_runtime_types() -> None:
    names = annotation_type_names(WORKFLOW_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    identifiers = _identifier_names(WORKFLOW_MODULE)
    leaked_identifiers = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked_identifiers == []
    source = WORKFLOW_MODULE.read_text(encoding="utf-8")
    assert "langgraph" not in source.lower()
    assert "langchain" not in source.lower()
    assert ".forecast(" not in source
    assert ".run(" not in source
    assert "TaskGroup" not in source
    assert "asyncio.gather" not in source
    assert "create_task" not in source
    assert "advance_after_forecasting" not in source
    assert "complete_forecasting" not in source


def test_run_does_not_construct_replace_or_mutate_workflow_state() -> None:
    class_def = _class_def(WORKFLOW_MODULE, "ForecastingWorkflowStep")
    run_fn = _run_method(class_def)
    state_param = run_fn.args.args[1].arg
    constructed: list[str] = []
    mutated: list[str] = []
    for node in ast.walk(run_fn):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in {"WorkflowState", "replace"}:
                constructed.append(func.id)
            elif isinstance(func, ast.Attribute) and func.attr == "replace":
                constructed.append(func.attr)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == state_param
                ):
                    mutated.append(target.attr)
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Attribute):
            if isinstance(node.target.value, ast.Name) and node.target.value.id == state_param:
                mutated.append(node.target.attr)
    assert constructed == []
    assert mutated == []
    returns = [node for node in ast.walk(run_fn) if isinstance(node, ast.Return)]
    assert len(returns) == 1
    assert isinstance(returns[0].value, ast.Name)
    assert returns[0].value.id == state_param


def test_workflow_state_shape_is_unchanged_by_the_workflow_step() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert "ForecastingWorkflowStep" not in names
    modules = imported_modules(STATE_MODULE)
    assert "energy_trading.application.orchestration.forecasting_workflow" not in modules


def test_context_and_execution_ports_remain_unwired_to_the_workflow_step() -> None:
    for path in (EXECUTION_MODULE, CONTEXT_MODULE):
        names = imported_names(path)
        assert "ForecastingWorkflowStep" not in names
        modules = imported_modules(path)
        assert "energy_trading.application.orchestration.forecasting_workflow" not in modules
        source = path.read_text(encoding="utf-8")
        assert "ForecastingWorkflowStep" not in source
    graph_names = imported_names(GRAPH_MODULE)
    assert "ForecastingWorkflowStep" in graph_names
    assert "ForecastingWorkflowContextPort" not in graph_names
    assert "ForecastingExecutionPort" not in graph_names
    graph_modules = imported_modules(GRAPH_MODULE)
    assert "energy_trading.application.orchestration.forecasting_workflow" in graph_modules
    assert "energy_trading.application.orchestration.forecasting_context" not in graph_modules
    assert "energy_trading.application.orchestration.forecasting_execution" not in graph_modules
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "ForecastingWorkflowStep" in graph_source
    assert "forecasting_workflow" in graph_source
    assert "ForecastingWorkflowContextPort" not in graph_source
    assert "ForecastingExecutionPort" not in graph_source
    assert "advance_after_forecasting" not in graph_source


def test_api_composition_does_not_import_or_construct_workflow_step() -> None:
    forbidden_wiring = ("energy_trading.application.orchestration.forecasting_workflow",)
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "ForecastingWorkflowStep" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "forecastingworkflowstep" not in app_source
    assert "forecasting_workflow" not in app_source
