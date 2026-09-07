"""Parallel-ingestion terminal FAIL action execution stays application-owned."""

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
ACTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_action.py"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
DECISION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_decision.py"
CONTEXT_BUILDER_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_context.py"
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
        "FailurePolicyContext",
        "FailurePolicyPort",
        "ParallelIngestionFailureDecisionService",
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
        "FailurePolicyContext",
        "FailurePolicyPort",
        "ParallelIngestionFailureDecisionService",
        "build_parallel_ingestion_failure_policy_context",
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
        "sleep",
        "wait",
        "WorkflowPhase",
        "WorkflowStatus",
    }
)

FORBIDDEN_FRAMEWORK_NAMES = (
    "FailureActionExecutor",
    "ActionHandler",
    "CommandBus",
    "StateMachine",
    "RetryPolicy",
    "FallbackExecutor",
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.errors",
        "energy_trading.application.orchestration.failure_policy",
        "energy_trading.application.orchestration.parallel_ingestion_failure_transition",
        "energy_trading.application.orchestration.state",
    }
)


def _module_class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def _public_function_defs(path: Path) -> list[ast.FunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    ]


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


def test_action_executor_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(ACTION_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(ACTION_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(ACTION_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(ACTION_MODULE)
    assert "FailureAction" in names
    assert "WorkflowState" in names
    assert "fail_parallel_ingestion" in names
    assert "InvalidRequestError" in names
    assert "FailurePolicyContext" not in names
    assert "FailurePolicyPort" not in names
    assert "ParallelIngestionFailureDecisionService" not in names
    assert "build_parallel_ingestion_failure_policy_context" not in names
    assert "advance_after_parallel_ingestion" not in names
    assert "AdapterDiagnostic" not in names


def test_action_executor_module_exposes_exactly_one_public_function() -> None:
    public_functions = _public_function_defs(ACTION_MODULE)
    assert [node.name for node in public_functions] == ["execute_parallel_ingestion_failure_action"]
    assert _module_class_names(ACTION_MODULE) == []
    tree = ast.parse(ACTION_MODULE.read_text(encoding="utf-8"), filename=str(ACTION_MODULE))
    async_functions = [node.name for node in tree.body if isinstance(node, ast.AsyncFunctionDef)]
    assert async_functions == []
    production_functions: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "execute_parallel_ingestion_failure_action"
            ):
                production_functions.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_functions == [
        "energy_trading/application/orchestration/parallel_ingestion_failure_action.py"
    ]


def test_action_executor_signature_is_keyword_only_state_and_action() -> None:
    function = _public_function_defs(ACTION_MODULE)[0]
    assert function.args.args == []
    assert function.args.posonlyargs == []
    assert function.args.vararg is None
    assert function.args.kwarg is None
    assert tuple(arg.arg for arg in function.args.kwonlyargs) == ("state", "action")
    assert ast.unparse(function.args.kwonlyargs[0].annotation) == "WorkflowState"
    assert ast.unparse(function.args.kwonlyargs[1].annotation) == "FailureAction"
    assert ast.unparse(function.returns) == "WorkflowState"
    assert function.args.kw_defaults == [None, None]


def test_fail_branch_delegates_once_without_reimplementing_transition() -> None:
    function = _public_function_defs(ACTION_MODULE)[0]
    loops = [
        type(node).__name__
        for node in ast.walk(function)
        if isinstance(node, (ast.For, ast.While, ast.Try, ast.With))
    ]
    assert loops == []
    except_handlers = [node for node in ast.walk(function) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    fail_calls = 0
    replace_calls = 0
    constructed_states = 0
    constructed_diagnostics = 0
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "fail_parallel_ingestion":
            fail_calls += 1
            assert len(node.args) == 1
            assert isinstance(node.args[0], ast.Name)
            assert node.args[0].id == "state"
            assert node.keywords == []
        if isinstance(func, ast.Name) and func.id == "replace":
            replace_calls += 1
        if isinstance(func, ast.Attribute) and func.attr == "replace":
            replace_calls += 1
        if isinstance(func, ast.Name) and func.id == "WorkflowState":
            constructed_states += 1
        if isinstance(func, ast.Name) and func.id == "AdapterDiagnostic":
            constructed_diagnostics += 1
    assert fail_calls == 1
    assert replace_calls == 0
    assert constructed_states == 0
    assert constructed_diagnostics == 0
    identifiers = _identifier_names(ACTION_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(ACTION_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    source = ACTION_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "time.sleep" not in lowered
    assert "asyncio.sleep" not in lowered
    assert "FailurePolicyContext" not in source
    assert "FailurePolicyPort" not in source
    assert "ParallelIngestionFailureDecisionService" not in source
    assert "build_parallel_ingestion_failure_policy_context" not in source
    for name in FORBIDDEN_FRAMEWORK_NAMES:
        assert name not in source


def test_retry_and_fallback_reject_without_execution() -> None:
    source = ACTION_MODULE.read_text(encoding="utf-8")
    assert "Parallel-ingestion retry action is not implemented." in source
    assert "Parallel-ingestion fallback action is not implemented." in source
    tree = ast.parse(source, filename=str(ACTION_MODULE))
    function = _public_function_defs(ACTION_MODULE)[0]
    compared_actions: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Compare):
            for comparator in node.comparators:
                if isinstance(comparator, ast.Attribute):
                    compared_actions.add(comparator.attr)
        if isinstance(node, ast.Match):
            for case in node.cases:
                pattern = case.pattern
                if isinstance(pattern, ast.MatchValue) and isinstance(pattern.value, ast.Attribute):
                    compared_actions.add(pattern.value.attr)
    assert compared_actions == {"FAIL", "RETRY", "FALLBACK"}
    sleep_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "sleep")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "sleep")
        )
    ]
    assert sleep_calls == []


def test_decision_context_and_transition_remain_independent_of_action_execution() -> None:
    for path in (
        DECISION_MODULE,
        CONTEXT_BUILDER_MODULE,
        FAILURE_TRANSITION_MODULE,
        FAILURE_POLICY_MODULE,
        SUCCESS_TRANSITION_MODULE,
        STATE_MODULE,
    ):
        names = imported_names(path)
        assert "execute_parallel_ingestion_failure_action" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.parallel_ingestion_failure_action"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "execute_parallel_ingestion_failure_action" not in source
        assert "parallel_ingestion_failure_action" not in source


def test_graph_workflow_and_executor_remain_unwired_to_action_execution() -> None:
    for path in (
        GRAPH_MODULE,
        WORKFLOW_MODULE,
        EXECUTOR_MODULE,
        WORKFLOW_CONTEXT_MODULE,
        PLAN_MODULE,
    ):
        names = imported_names(path)
        assert "execute_parallel_ingestion_failure_action" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.parallel_ingestion_failure_action"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "execute_parallel_ingestion_failure_action" not in source
        assert "parallel_ingestion_failure_action" not in source
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "add_conditional_edges" not in graph_source
    assert "ParallelIngestionFailureHandlingService" not in graph_source


def test_api_composition_does_not_import_or_construct_the_action_executor() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.parallel_ingestion_failure_action",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "execute_parallel_ingestion_failure_action" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "execute_parallel_ingestion_failure_action" not in app_source
    assert "parallel_ingestion_failure_action" not in app_source
