"""Parallel-ingestion terminal failure transition stays application-owned and LangGraph-free."""

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
FAILURE_TRANSITION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_transition.py"
SUCCESS_TRANSITION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_transition.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
WORKFLOW_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_workflow.py"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
EXECUTOR_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_executor.py"
CONTEXT_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_context.py"
PLAN_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
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
        "Optional",
        "Protocol",
        "ABC",
        "Exception",
        "BaseException",
        "AdapterDiagnostic",
        "ParallelIngestionPlan",
        "ParallelIngestionSuccess",
        "ParallelIngestionExecutionPort",
        "ParallelIngestionWorkflowContextPort",
        "ConcurrentParallelIngestionExecutor",
        "ParallelIngestionWorkflowStep",
        "FailurePolicyPort",
        "FailurePolicyContext",
        "FailureAction",
        "WeatherAndRenewableForecastAgent",
        "HydroResourcesAgent",
        "GenerationAvailabilityAgent",
        "NewsIntelligenceAgent",
        "MarketMonitoringAgent",
        "StateGraph",
        "CompiledStateGraph",
        "Send",
        "RetryPolicy",
        "AgentPort",
        "AgentName",
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
        "AdapterDiagnostic",
        "ParallelIngestionPlan",
        "ParallelIngestionSuccess",
        "ParallelIngestionExecutionPort",
        "ParallelIngestionWorkflowContextPort",
        "ConcurrentParallelIngestionExecutor",
        "ParallelIngestionWorkflowStep",
        "FailurePolicyPort",
        "tenacity",
        "backoff",
        "asyncio",
        "TaskGroup",
        "sleep",
        "retry",
        "fallback",
        "except",
        "execute_parallel_ingestion_failure_action",
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
        "fail",
        "retry",
        "fallback",
        "advance_after_parallel_ingestion",
        "fail_parallel_ingestion",
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


def test_failure_transition_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(FAILURE_TRANSITION_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(FAILURE_TRANSITION_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(FAILURE_TRANSITION_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(FAILURE_TRANSITION_MODULE)
    assert "InvalidRequestError" in names
    assert "WorkflowState" in names
    assert "WorkflowPhase" in names
    assert "WorkflowStatus" in names
    assert "replace" in names
    assert "AdapterDiagnostic" not in names
    assert "FailurePolicyPort" not in names
    assert "advance_after_parallel_ingestion" not in names
    assert "ParallelIngestionFailureDecisionService" not in names
    assert "build_parallel_ingestion_failure_policy_context" not in names
    assert "execute_parallel_ingestion_failure_action" not in names


def test_failure_transition_module_exposes_exactly_one_public_function() -> None:
    public_functions = _public_function_defs(FAILURE_TRANSITION_MODULE)
    assert [node.name for node in public_functions] == ["fail_parallel_ingestion"]
    assert _module_class_names(FAILURE_TRANSITION_MODULE) == []
    tree = ast.parse(
        FAILURE_TRANSITION_MODULE.read_text(encoding="utf-8"),
        filename=str(FAILURE_TRANSITION_MODULE),
    )
    async_defs = [node.name for node in tree.body if isinstance(node, ast.AsyncFunctionDef)]
    assert async_defs == []
    production_functions: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if isinstance(node, ast.FunctionDef) and node.name == "fail_parallel_ingestion":
                production_functions.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_functions == [
        "energy_trading/application/orchestration/parallel_ingestion_failure_transition.py"
    ]


def test_failure_transition_signature_is_synchronous_workflow_state_to_workflow_state() -> None:
    function = _public_function_defs(FAILURE_TRANSITION_MODULE)[0]
    assert tuple(arg.arg for arg in function.args.args) == ("state",)
    assert function.args.posonlyargs == []
    assert function.args.kwonlyargs == []
    assert function.args.vararg is None
    assert function.args.kwarg is None
    assert function.args.args[0].annotation is not None
    assert function.returns is not None
    assert ast.unparse(function.args.args[0].annotation) == "WorkflowState"
    assert ast.unparse(function.returns) == "WorkflowState"


def test_failure_transition_has_no_exception_parameter_or_handlers() -> None:
    function = _public_function_defs(FAILURE_TRANSITION_MODULE)[0]
    arg_names = tuple(arg.arg for arg in function.args.args)
    assert "exception" not in arg_names
    assert "error" not in arg_names
    assert "exc" not in arg_names
    tree = ast.parse(
        FAILURE_TRANSITION_MODULE.read_text(encoding="utf-8"),
        filename=str(FAILURE_TRANSITION_MODULE),
    )
    assert [node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)] == []
    raises = [node for node in ast.walk(function) if isinstance(node, ast.Raise)]
    assert raises


def test_failure_transition_uses_immutable_replacement_and_is_not_a_framework() -> None:
    tree = ast.parse(
        FAILURE_TRANSITION_MODULE.read_text(encoding="utf-8"),
        filename=str(FAILURE_TRANSITION_MODULE),
    )
    function = _public_function_defs(FAILURE_TRANSITION_MODULE)[0]
    replace_calls = 0
    constructed_states = 0
    constructed_diagnostics = 0
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "replace":
            replace_calls += 1
        if isinstance(func, ast.Name) and func.id == "WorkflowState":
            constructed_states += 1
        if isinstance(func, ast.Name) and func.id == "AdapterDiagnostic":
            constructed_diagnostics += 1
        if isinstance(func, ast.Attribute) and func.attr == "replace":
            replace_calls += 1
    assert replace_calls == 1
    assert constructed_states == 0
    assert constructed_diagnostics == 0
    names = annotation_type_names(FAILURE_TRANSITION_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    identifiers = _identifier_names(FAILURE_TRANSITION_MODULE)
    leaked_identifiers = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked_identifiers == []
    source = FAILURE_TRANSITION_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    for name in FORBIDDEN_FRAMEWORK_NAMES:
        assert name not in source
    class_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    assert class_names == []


def test_success_and_failure_transition_modules_remain_separate() -> None:
    success_names = imported_names(SUCCESS_TRANSITION_MODULE)
    failure_names = imported_names(FAILURE_TRANSITION_MODULE)
    assert "fail_parallel_ingestion" not in success_names
    assert "advance_after_parallel_ingestion" not in failure_names
    success_modules = imported_modules(SUCCESS_TRANSITION_MODULE)
    failure_modules = imported_modules(FAILURE_TRANSITION_MODULE)
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_transition"
        not in success_modules
    )
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_transition"
        not in failure_modules
    )
    success_functions = [node.name for node in _public_function_defs(SUCCESS_TRANSITION_MODULE)]
    failure_functions = [node.name for node in _public_function_defs(FAILURE_TRANSITION_MODULE)]
    assert success_functions == ["advance_after_parallel_ingestion"]
    assert failure_functions == ["fail_parallel_ingestion"]


def test_workflow_state_does_not_absorb_the_failure_transition() -> None:
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
    assert "fail_parallel_ingestion" not in names
    assert "advance_after_parallel_ingestion" not in names
    modules = imported_modules(STATE_MODULE)
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_transition"
        not in modules
    )
    assert "energy_trading.application.orchestration.parallel_ingestion_transition" not in modules
    state_source = STATE_MODULE.read_text(encoding="utf-8")
    assert "fail_parallel_ingestion" not in state_source


def test_workflow_step_policy_and_lower_deps_remain_unwired_to_the_failure_transition() -> None:
    for path in (
        WORKFLOW_MODULE,
        EXECUTOR_MODULE,
        FAILURE_POLICY_MODULE,
        PLAN_MODULE,
        CONTEXT_MODULE,
        SUCCESS_TRANSITION_MODULE,
    ):
        names = imported_names(path)
        assert "fail_parallel_ingestion" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.parallel_ingestion_failure_transition"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "fail_parallel_ingestion" not in source
        assert "parallel_ingestion_failure_transition" not in source
        assert "build_parallel_ingestion_failure_policy_context" not in source
        assert "execute_parallel_ingestion_failure_action" not in source
    policy_source = FAILURE_POLICY_MODULE.read_text(encoding="utf-8")
    assert "fail_parallel_ingestion" not in policy_source
    workflow_source = WORKFLOW_MODULE.read_text(encoding="utf-8").lower()
    assert "langgraph" not in workflow_source


def test_graph_does_not_import_or_call_the_failure_transition() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "fail_parallel_ingestion" not in names
    assert "advance_after_parallel_ingestion" in names
    assert "ParallelIngestionFailureDecisionService" not in names
    assert "build_parallel_ingestion_failure_policy_context" not in names
    assert "execute_parallel_ingestion_failure_action" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_transition"
        not in modules
    )
    assert "energy_trading.application.orchestration.parallel_ingestion_transition" in modules
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    parsed = ast.parse(graph_source, filename=str(GRAPH_MODULE))
    string_constants = {
        node.value
        for node in ast.walk(parsed)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "workflow_entry" in string_constants
    assert "parallel_ingestion" in string_constants
    assert "parallel_ingestion_success_transition" in string_constants
    assert "parallel_ingestion_failure_transition" not in string_constants
    add_node_count = 0
    add_edge_count = 0
    success_calls = 0
    failure_calls = 0
    for node in ast.walk(parsed):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name: str | None = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name == "add_node":
            add_node_count += 1
        elif name == "add_edge":
            add_edge_count += 1
        elif name == "advance_after_parallel_ingestion":
            success_calls += 1
        elif name == "fail_parallel_ingestion":
            failure_calls += 1
    assert add_node_count == 3
    assert add_edge_count == 4
    assert success_calls == 1
    assert failure_calls == 0
    assert "add_conditional_edges" not in graph_source
    assert "fail_parallel_ingestion" not in graph_source
    assert "execute_parallel_ingestion_failure_action" not in graph_source
    identifiers = _identifier_names(GRAPH_MODULE)
    assert "replace" not in identifiers
    assert "WorkflowPhase" not in identifiers
    assert "WorkflowStatus" not in identifiers
    assert "execute_parallel_ingestion_failure_action" not in identifiers
    transition_source = FAILURE_TRANSITION_MODULE.read_text(encoding="utf-8").lower()
    assert "langgraph" not in transition_source


def test_api_composition_does_not_import_or_construct_the_failure_transition() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.parallel_ingestion_failure_transition",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "fail_parallel_ingestion" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "fail_parallel_ingestion" not in app_source
    assert "parallel_ingestion_failure_transition" not in app_source
