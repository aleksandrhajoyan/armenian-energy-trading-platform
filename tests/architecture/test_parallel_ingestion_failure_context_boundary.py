"""Parallel-ingestion failure-policy context builder stays application-owned."""

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
CONTEXT_BUILDER_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_context.py"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
DECISION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_decision.py"
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
    "energy_trading.application.agents.weather_and_renewable_forecast",
    "energy_trading.application.agents.hydro_resources",
    "energy_trading.application.agents.generation_availability",
    "energy_trading.application.agents.news_intelligence",
    "energy_trading.application.agents.market_monitoring",
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
    "traceback",
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
        "Exception",
        "BaseException",
        "ExceptionGroup",
        "TracebackType",
        "WorkflowState",
        "FailureAction",
        "FailurePolicyPort",
        "ParallelIngestionPlan",
        "ParallelIngestionSuccess",
        "ParallelIngestionExecutionPort",
        "ParallelIngestionWorkflowContextPort",
        "ConcurrentParallelIngestionExecutor",
        "ParallelIngestionWorkflowStep",
        "ParallelIngestionFailureDecisionService",
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
        "AdapterDiagnostic",
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
        "Exception",
        "BaseException",
        "ExceptionGroup",
        "traceback",
        "exc_info",
        "WorkflowState",
        "FailureAction",
        "FailurePolicyPort",
        "fail_parallel_ingestion",
        "execute_parallel_ingestion_failure_action",
        "advance_after_parallel_ingestion",
        "ParallelIngestionFailureDecisionService",
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
        "retry",
        "fallback",
        "wait",
        "CHIEF_ORCHESTRATOR",
        "MARKET_MONITORING",
        "WEATHER_AND_RENEWABLE_FORECAST",
        "HYDRO_RESOURCES",
        "GENERATION_AVAILABILITY",
        "NEWS_INTELLIGENCE",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.agents.base",
        "energy_trading.application.orchestration.failure_policy",
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


def test_context_builder_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(CONTEXT_BUILDER_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(CONTEXT_BUILDER_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(CONTEXT_BUILDER_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(CONTEXT_BUILDER_MODULE)
    assert "FailurePolicyContext" in names
    assert "WorkflowPhase" in names
    assert "AgentName" in names
    assert "FailureAction" not in names
    assert "FailurePolicyPort" not in names
    assert "WorkflowState" not in names
    assert "Exception" not in names
    assert "BaseException" not in names


def test_context_builder_module_exposes_exactly_one_public_function() -> None:
    public_functions = _public_function_defs(CONTEXT_BUILDER_MODULE)
    assert [node.name for node in public_functions] == [
        "build_parallel_ingestion_failure_policy_context"
    ]
    assert _module_class_names(CONTEXT_BUILDER_MODULE) == []
    tree = ast.parse(
        CONTEXT_BUILDER_MODULE.read_text(encoding="utf-8"),
        filename=str(CONTEXT_BUILDER_MODULE),
    )
    async_functions = [node.name for node in tree.body if isinstance(node, ast.AsyncFunctionDef)]
    assert async_functions == []


def test_builder_signature_is_keyword_only_published_fields() -> None:
    builder = _public_function_defs(CONTEXT_BUILDER_MODULE)[0]
    assert builder.args.args == []
    assert builder.args.posonlyargs == []
    assert builder.args.vararg is None
    assert builder.args.kwarg is None
    assert tuple(arg.arg for arg in builder.args.kwonlyargs) == (
        "phase",
        "error_code",
        "attempt_number",
        "agent_name",
    )
    assert ast.unparse(builder.args.kwonlyargs[0].annotation) == "WorkflowPhase"
    assert ast.unparse(builder.args.kwonlyargs[1].annotation) == "str"
    assert ast.unparse(builder.args.kwonlyargs[2].annotation) == "int"
    assert ast.unparse(builder.args.kwonlyargs[3].annotation) == "AgentName | None"
    assert ast.unparse(builder.returns) == "FailurePolicyContext"
    defaults = builder.args.kw_defaults
    assert defaults[0] is None
    assert defaults[1] is None
    assert defaults[2] is None
    assert isinstance(defaults[3], ast.Constant)
    assert defaults[3].value is None


def test_builder_constructs_published_context_once_without_branching() -> None:
    builder = _public_function_defs(CONTEXT_BUILDER_MODULE)[0]
    control = [
        type(node).__name__
        for node in ast.walk(builder)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try, ast.With))
    ]
    assert control == []
    except_handlers = [node for node in ast.walk(builder) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    constructed = [
        node
        for node in ast.walk(builder)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "FailurePolicyContext"
    ]
    assert len(constructed) == 1
    call = constructed[0]
    assert call.args == []
    keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in call.keywords}
    assert keywords == {
        "phase": "phase",
        "error_code": "error_code",
        "attempt_number": "attempt_number",
        "agent_name": "agent_name",
    }
    identifiers = _identifier_names(CONTEXT_BUILDER_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(CONTEXT_BUILDER_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    source = CONTEXT_BUILDER_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "traceback" not in lowered
    assert "exceptiongroup" not in lowered
    assert "fail_parallel_ingestion" not in source
    assert "execute_parallel_ingestion_failure_action" not in source
    assert "ParallelIngestionFailureDecisionService" not in source
    assert "time.sleep" not in lowered
    assert "asyncio.sleep" not in lowered


def test_failure_policy_contract_remains_unchanged_and_unwired_to_the_builder() -> None:
    names = imported_names(FAILURE_POLICY_MODULE)
    assert "build_parallel_ingestion_failure_policy_context" not in names
    modules = imported_modules(FAILURE_POLICY_MODULE)
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_context" not in modules
    )
    source = FAILURE_POLICY_MODULE.read_text(encoding="utf-8")
    assert "build_parallel_ingestion_failure_policy_context" not in source
    assert "parallel_ingestion_failure_context" not in source


def test_decision_service_does_not_construct_context_via_the_builder() -> None:
    names = imported_names(DECISION_MODULE)
    assert "build_parallel_ingestion_failure_policy_context" not in names
    assert "FailurePolicyContext" in names
    modules = imported_modules(DECISION_MODULE)
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_context" not in modules
    )
    source = DECISION_MODULE.read_text(encoding="utf-8")
    assert "build_parallel_ingestion_failure_policy_context" not in source
    tree = ast.parse(DECISION_MODULE.read_text(encoding="utf-8"), filename=str(DECISION_MODULE))
    constructed = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert "FailurePolicyContext" not in constructed


def test_graph_workflow_and_transitions_remain_unwired_to_the_builder() -> None:
    for path in (
        GRAPH_MODULE,
        WORKFLOW_MODULE,
        FAILURE_TRANSITION_MODULE,
        SUCCESS_TRANSITION_MODULE,
        EXECUTOR_MODULE,
        WORKFLOW_CONTEXT_MODULE,
        PLAN_MODULE,
        STATE_MODULE,
    ):
        names = imported_names(path)
        assert "build_parallel_ingestion_failure_policy_context" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.parallel_ingestion_failure_context"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "build_parallel_ingestion_failure_policy_context" not in source
        assert "parallel_ingestion_failure_context" not in source
        assert "execute_parallel_ingestion_failure_action" not in source
        assert "parallel_ingestion_failure_action" not in source
        assert "ParallelIngestionFailureHandlingService" not in source
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "add_conditional_edges" not in graph_source


def test_api_composition_does_not_import_or_construct_the_builder() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.parallel_ingestion_failure_context",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "build_parallel_ingestion_failure_policy_context" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "build_parallel_ingestion_failure_policy_context" not in app_source
    assert "parallel_ingestion_failure_context" not in app_source
