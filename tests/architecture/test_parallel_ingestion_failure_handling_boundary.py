"""Prepared parallel-ingestion failure handling stays application-owned."""

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
HANDLING_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_handling.py"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
DECISION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_decision.py"
CONTEXT_BUILDER_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_context.py"
ACTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_action.py"
FAILURE_TRANSITION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_transition.py"
SUCCESS_TRANSITION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_transition.py"
WORKFLOW_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_workflow.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
EXECUTOR_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_executor.py"
WORKFLOW_CONTEXT_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_context.py"
PLAN_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
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
        "ExceptionGroup",
        "FailureAction",
        "FailurePolicyPort",
        "AdapterDiagnostic",
        "ParallelIngestionPlan",
        "ParallelIngestionSuccess",
        "ParallelIngestionExecutionPort",
        "ParallelIngestionWorkflowContextPort",
        "ConcurrentParallelIngestionExecutor",
        "ParallelIngestionWorkflowStep",
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
        "WorkflowPhase",
        "WorkflowStatus",
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
        "Exception",
        "BaseException",
        "ExceptionGroup",
        "FailureAction",
        "FailurePolicyPort",
        "build_parallel_ingestion_failure_policy_context",
        "fail_parallel_ingestion",
        "advance_after_parallel_ingestion",
        "replace",
        "AdapterDiagnostic",
        "ParallelIngestionPlan",
        "ParallelIngestionSuccess",
        "ParallelIngestionExecutionPort",
        "ParallelIngestionWorkflowContextPort",
        "ConcurrentParallelIngestionExecutor",
        "ParallelIngestionWorkflowStep",
        "registry",
        "factory",
        "StateMachine",
        "tenacity",
        "backoff",
        "asyncio",
        "TaskGroup",
        "create_task",
        "sleep",
        "wait",
        "WorkflowPhase",
        "WorkflowStatus",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.orchestration.failure_policy",
        "energy_trading.application.orchestration.parallel_ingestion_failure_action",
        "energy_trading.application.orchestration.parallel_ingestion_failure_decision",
        "energy_trading.application.orchestration.state",
    }
)

ALLOWED_INIT_ANNOTATIONS = {
    "decision_service": "ParallelIngestionFailureDecisionService",
}


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


def _handle_method(class_def: ast.ClassDef) -> ast.AsyncFunctionDef:
    for node in class_def.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "handle":
            return node
    msg = "async method 'handle' not found on ParallelIngestionFailureHandlingService"
    raise AssertionError(msg)


def test_handling_service_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(HANDLING_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(HANDLING_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(HANDLING_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(HANDLING_MODULE)
    assert "FailurePolicyContext" in names
    assert "WorkflowState" in names
    assert "ParallelIngestionFailureDecisionService" in names
    assert "execute_parallel_ingestion_failure_action" in names
    assert "FailurePolicyPort" not in names
    assert "FailureAction" not in names
    assert "fail_parallel_ingestion" not in names
    assert "build_parallel_ingestion_failure_policy_context" not in names


def test_handling_service_module_exposes_exactly_one_production_class() -> None:
    assert _module_class_names(HANDLING_MODULE) == ["ParallelIngestionFailureHandlingService"]
    class_def = _class_def(HANDLING_MODULE, "ParallelIngestionFailureHandlingService")
    assert _base_names(class_def) == set()
    production_classes: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.ClassDef)
                and node.name == "ParallelIngestionFailureHandlingService"
            ):
                production_classes.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_classes == [
        "energy_trading/application/orchestration/parallel_ingestion_failure_handling.py"
    ]


def test_constructor_injects_exactly_the_published_decision_service() -> None:
    class_def = _class_def(HANDLING_MODULE, "ParallelIngestionFailureHandlingService")
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert tuple(arg.arg for arg in init_fn.args.args) == ("self", "decision_service")
    assert init_fn.args.posonlyargs == []
    assert init_fn.args.kwonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    assert _init_arg_annotations(class_def) == ALLOWED_INIT_ANNOTATIONS


def test_handle_signature_is_async_keyword_only_state_and_context() -> None:
    class_def = _class_def(HANDLING_MODULE, "ParallelIngestionFailureHandlingService")
    handle_fn = _handle_method(class_def)
    assert tuple(arg.arg for arg in handle_fn.args.args) == ("self",)
    assert handle_fn.args.posonlyargs == []
    assert tuple(arg.arg for arg in handle_fn.args.kwonlyargs) == ("state", "context")
    assert handle_fn.args.vararg is None
    assert handle_fn.args.kwarg is None
    assert ast.unparse(handle_fn.args.kwonlyargs[0].annotation) == "WorkflowState"
    assert ast.unparse(handle_fn.args.kwonlyargs[1].annotation) == "FailurePolicyContext"
    assert ast.unparse(handle_fn.returns) == "WorkflowState"
    assert handle_fn.args.kw_defaults == [None, None]
    public_methods = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]
    assert public_methods == ["handle"]


def test_handle_delegates_once_without_branching_or_transition_logic() -> None:
    class_def = _class_def(HANDLING_MODULE, "ParallelIngestionFailureHandlingService")
    handle_fn = _handle_method(class_def)
    control = [
        type(node).__name__
        for node in ast.walk(handle_fn)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try, ast.With))
    ]
    assert control == []
    except_handlers = [node for node in ast.walk(handle_fn) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    decide_calls = 0
    execute_calls = 0
    fail_calls = 0
    replace_calls = 0
    for node in ast.walk(handle_fn):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name: str | None = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name == "decide":
            decide_calls += 1
            assert len(node.args) == 1
            assert isinstance(node.args[0], ast.Name)
            assert node.args[0].id == "context"
        if name == "execute_parallel_ingestion_failure_action":
            execute_calls += 1
            assert node.args == []
            keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in node.keywords}
            assert keywords == {"state": "state", "action": "action"}
        if name == "fail_parallel_ingestion":
            fail_calls += 1
        if name == "replace":
            replace_calls += 1
    assert decide_calls == 1
    assert execute_calls == 1
    assert fail_calls == 0
    assert replace_calls == 0
    identifiers = _identifier_names(HANDLING_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(HANDLING_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    source = HANDLING_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "fail_parallel_ingestion" not in source
    assert "build_parallel_ingestion_failure_policy_context" not in source
    assert "FailurePolicyPort" not in source
    assert "time.sleep" not in lowered
    assert "asyncio.sleep" not in lowered
    assert "asyncio.taskgroup" not in lowered


def test_graph_workflow_and_lower_layers_remain_unwired_to_the_handling_service() -> None:
    for path in (
        GRAPH_MODULE,
        WORKFLOW_MODULE,
        FAILURE_POLICY_MODULE,
        DECISION_MODULE,
        CONTEXT_BUILDER_MODULE,
        ACTION_MODULE,
        FAILURE_TRANSITION_MODULE,
        SUCCESS_TRANSITION_MODULE,
        EXECUTOR_MODULE,
        WORKFLOW_CONTEXT_MODULE,
        PLAN_MODULE,
        STATE_MODULE,
    ):
        names = imported_names(path)
        assert "ParallelIngestionFailureHandlingService" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.parallel_ingestion_failure_handling"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "ParallelIngestionFailureHandlingService" not in source
        assert "parallel_ingestion_failure_handling" not in source
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "add_conditional_edges" not in graph_source


def test_api_composition_does_not_import_or_construct_the_handling_service() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.parallel_ingestion_failure_handling",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "ParallelIngestionFailureHandlingService" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "parallelingestionfailurehandlingservice" not in app_source
    assert "parallel_ingestion_failure_handling" not in app_source
