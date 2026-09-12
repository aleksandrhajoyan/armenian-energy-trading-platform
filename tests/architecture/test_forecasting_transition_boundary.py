"""Forecasting success transition stays application-owned and LangGraph-free."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    collect_http_api_import_violations,
    http_transport_api_paths,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
TRANSITION_MODULE = ORCHESTRATION_ROOT / "forecasting_transition.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
WORKFLOW_MODULE = ORCHESTRATION_ROOT / "forecasting_workflow.py"
CONTEXT_MODULE = ORCHESTRATION_ROOT / "forecasting_context.py"
EXECUTION_MODULE = ORCHESTRATION_ROOT / "forecasting_execution.py"
PLAN_MODULE = ORCHESTRATION_ROOT / "forecasting_plan.py"
SUCCESS_MODULE = ORCHESTRATION_ROOT / "forecasting_success.py"
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
        "Protocol",
        "ABC",
        "ForecastingPlan",
        "ForecastingSuccess",
        "ForecastingExecutionPort",
        "ForecastingWorkflowContextPort",
        "ForecastingWorkflowStep",
        "ForecastingExecutor",
        "ConsumerLoadForecastAgent",
        "DAMPriceForecastAgent",
        "ConsumerLoadForecastModelPort",
        "DAMPriceForecastModelPort",
        "FailurePolicyPort",
        "FailurePolicyContext",
        "FailureAction",
        "StateGraph",
        "CompiledStateGraph",
        "Send",
        "RetryPolicy",
        "AgentPort",
        "AgentName",
        "WorkflowStep",
        "Transition",
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
        "Protocol",
        "ABC",
        "registry",
        "factory",
        "StateMachine",
        "TransitionTable",
        "ForecastingPlan",
        "ForecastingSuccess",
        "ForecastingExecutionPort",
        "ForecastingWorkflowContextPort",
        "ForecastingWorkflowStep",
        "ForecastingExecutor",
        "fail_forecasting",
        "ConsumerLoadForecastAgent",
        "DAMPriceForecastAgent",
        "ConsumerLoadForecastModelPort",
        "DAMPriceForecastModelPort",
        "FailurePolicyPort",
        "tenacity",
        "backoff",
        "asyncio",
        "TaskGroup",
        "gather",
        "create_task",
        "sleep",
        "retry",
        "fallback",
        "forecast",
        "WorkflowStep",
        "AgentFactory",
        "ServiceLocator",
    }
)

FORBIDDEN_FRAMEWORK_NAMES = (
    "WorkflowTransition",
    "TransitionRegistry",
    "StateMachine",
    "PhaseTransition",
    "GenericTransition",
    "TransitionPort",
    "TransitionFactory",
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "energy_trading.application.errors",
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

FORBIDDEN_STATE_METHODS = frozenset(
    {
        "advance",
        "transition",
        "mark_running",
        "mark_failed",
        "mark_succeeded",
        "next_phase",
        "advance_after_forecasting",
        "fail",
        "fail_forecasting",
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


def _module_class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


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


def _public_function_defs(path: Path) -> list[ast.FunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    ]


def _attr_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return None


def test_transition_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(TRANSITION_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(TRANSITION_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(TRANSITION_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(TRANSITION_MODULE)
    assert "InvalidRequestError" in names
    assert "WorkflowState" in names
    assert "WorkflowPhase" in names
    assert "WorkflowStatus" in names
    assert "replace" in names


def test_transition_module_exposes_exactly_one_public_function() -> None:
    public_functions = _public_function_defs(TRANSITION_MODULE)
    assert [node.name for node in public_functions] == ["advance_after_forecasting"]
    assert _module_class_names(TRANSITION_MODULE) == []
    tree = ast.parse(TRANSITION_MODULE.read_text(encoding="utf-8"), filename=str(TRANSITION_MODULE))
    async_defs = [node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)]
    assert async_defs == []
    production_functions: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if isinstance(node, ast.FunctionDef) and node.name == "advance_after_forecasting":
                production_functions.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_functions == [
        "energy_trading/application/orchestration/forecasting_transition.py"
    ]
    leaked_classes = sorted(
        name
        for name in _module_class_names(TRANSITION_MODULE)
        if name in MODULE_FORBIDDEN_CLASS_NAMES
    )
    assert leaked_classes == []


def test_transition_signature_is_synchronous_workflow_state_to_workflow_state() -> None:
    function = _public_function_defs(TRANSITION_MODULE)[0]
    assert tuple(arg.arg for arg in function.args.args) == ("state",)
    assert function.args.posonlyargs == []
    assert function.args.kwonlyargs == []
    assert function.args.vararg is None
    assert function.args.kwarg is None
    assert function.args.args[0].annotation is not None
    assert function.returns is not None
    assert ast.unparse(function.args.args[0].annotation) == "WorkflowState"
    assert ast.unparse(function.returns) == "WorkflowState"


def test_transition_uses_immutable_replacement_with_canonical_phases() -> None:
    function = _public_function_defs(TRANSITION_MODULE)[0]
    replace_calls = 0
    constructed_states = 0
    replace_kwargs: dict[str, str | None] = {}
    compared_attrs: list[str] = []
    for node in ast.walk(function):
        if isinstance(node, ast.Compare):
            compared_attrs.extend(
                name
                for candidate in (node.left, *node.comparators)
                if (name := _attr_name(candidate)) is not None
            )
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "replace":
            replace_calls += 1
            replace_kwargs = {
                keyword.arg: _attr_name(keyword.value)
                for keyword in node.keywords
                if keyword.arg is not None
            }
        if isinstance(func, ast.Name) and func.id == "WorkflowState":
            constructed_states += 1
        if isinstance(func, ast.Attribute) and func.attr == "replace":
            replace_calls += 1
    assert replace_calls == 1
    assert constructed_states == 0
    assert replace_kwargs == {"phase": "RISK_AND_BID", "status": "RUNNING"}
    assert "FORECASTING" in compared_attrs
    assert "RUNNING" in compared_attrs
    assert "FAILED" not in compared_attrs
    names = annotation_type_names(TRANSITION_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    identifiers = _identifier_names(TRANSITION_MODULE)
    leaked_identifiers = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked_identifiers == []
    source = TRANSITION_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert ".forecast(" not in source
    assert ".run(" not in source
    assert "fail_forecasting" not in source
    for name in FORBIDDEN_FRAMEWORK_NAMES:
        assert name not in source
    class_names = [
        node.name
        for node in ast.walk(ast.parse(source, filename=str(TRANSITION_MODULE)))
        if isinstance(node, ast.ClassDef)
    ]
    assert class_names == []


def test_workflow_state_remains_transition_free() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    class_def = _class_def(STATE_MODULE, "WorkflowState")
    defined = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert defined == ["__post_init__"]
    assert FORBIDDEN_STATE_METHODS.isdisjoint(defined)
    names = imported_names(STATE_MODULE)
    assert "advance_after_forecasting" not in names
    modules = imported_modules(STATE_MODULE)
    assert "energy_trading.application.orchestration.forecasting_transition" not in modules


def test_workflow_step_and_ports_remain_unwired_to_the_transition() -> None:
    for path in (
        WORKFLOW_MODULE,
        CONTEXT_MODULE,
        EXECUTION_MODULE,
        PLAN_MODULE,
        SUCCESS_MODULE,
    ):
        names = imported_names(path)
        assert "advance_after_forecasting" not in names
        modules = imported_modules(path)
        assert "energy_trading.application.orchestration.forecasting_transition" not in modules
        source = path.read_text(encoding="utf-8")
        assert "advance_after_forecasting" not in source
        assert "forecasting_transition" not in source


def test_graph_does_not_import_or_call_the_transition() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "advance_after_forecasting" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "energy_trading.application.orchestration.forecasting_transition" not in modules
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "advance_after_forecasting" not in graph_source
    assert "forecasting_transition" not in graph_source
    transition_source = TRANSITION_MODULE.read_text(encoding="utf-8").lower()
    assert "langgraph" not in transition_source


def test_api_composition_does_not_import_or_construct_the_transition() -> None:
    forbidden_wiring = ("energy_trading.application.orchestration.forecasting_transition",)
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "advance_after_forecasting" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "advance_after_forecasting" not in app_source
    assert "forecasting_transition" not in app_source
