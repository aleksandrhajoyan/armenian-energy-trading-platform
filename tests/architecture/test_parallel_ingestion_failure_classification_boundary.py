"""Parallel-ingestion tuple-level failure classification stays application-owned."""

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
CLASSIFICATION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_classification.py"
FACT_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_fact.py"
AGENT_FAILURE_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_agent_failure.py"
EXTRACTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_exception_group.py"
EXECUTOR_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_executor.py"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
DECISION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_decision.py"
CONTEXT_BUILDER_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_context.py"
ACTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_action.py"
HANDLING_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_handling.py"
WORKFLOW_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_workflow.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
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
    "energy_trading.application.errors",
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
        "Protocol",
        "ABC",
        "ExceptionGroup",
        "BaseExceptionGroup",
        "TracebackType",
        "ApplicationError",
        "WorkflowState",
        "FailurePolicyContext",
        "FailurePolicyPort",
        "FailureAction",
        "ParallelIngestionFailureDecisionService",
        "ParallelIngestionFailureHandlingService",
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
        "Protocol",
        "ABC",
        "traceback",
        "exc_info",
        "format_exc",
        "format_tb",
        "extract_tb",
        "print_exc",
        "ApplicationError",
        "ExceptionGroup",
        "BaseExceptionGroup",
        "WorkflowState",
        "FailurePolicyContext",
        "FailurePolicyPort",
        "FailureAction",
        "build_parallel_ingestion_failure_policy_context",
        "execute_parallel_ingestion_failure_action",
        "ParallelIngestionFailureDecisionService",
        "ParallelIngestionFailureHandlingService",
        "fail_parallel_ingestion",
        "advance_after_parallel_ingestion",
        "extract_parallel_ingestion_agent_failures",
        "ConcurrentParallelIngestionExecutor",
        "ParallelIngestionWorkflowStep",
        "registry",
        "factory",
        "visitor",
        "tenacity",
        "backoff",
        "asyncio",
        "TaskGroup",
        "sleep",
        "retry",
        "fallback",
        "attempt_number",
        "split",
        "subgroup",
        "derive",
        "sorted",
        "sort",
        "unique",
        "deduplicate",
        "groupby",
        "group",
        "primary",
        "rank",
        "severity",
        "max",
        "min",
        "__cause__",
        "__context__",
        "__traceback__",
        "__name__",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.orchestration.parallel_ingestion_agent_failure",
        "energy_trading.application.orchestration.parallel_ingestion_failure_fact",
    }
)

UNWIRED_MODULES = (
    GRAPH_MODULE,
    WORKFLOW_MODULE,
    EXECUTOR_MODULE,
    EXTRACTION_MODULE,
    FAILURE_POLICY_MODULE,
    DECISION_MODULE,
    CONTEXT_BUILDER_MODULE,
    ACTION_MODULE,
    HANDLING_MODULE,
    STATE_MODULE,
    AGENT_FAILURE_MODULE,
    FACT_MODULE,
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


def _call_names(function: ast.FunctionDef) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def test_classification_module_belongs_to_application_orchestration() -> None:
    assert CLASSIFICATION_MODULE.parent == ORCHESTRATION_ROOT
    assert CLASSIFICATION_MODULE.exists()


def test_classification_module_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(CLASSIFICATION_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(CLASSIFICATION_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(CLASSIFICATION_MODULE)
    assert "ParallelIngestionAgentFailure" in names
    assert "ParallelIngestionFailureFact" in names
    assert "classify_parallel_ingestion_agent_failure" in names
    assert "ApplicationError" not in names
    assert "WorkflowState" not in names
    assert "FailurePolicyContext" not in names
    assert "FailurePolicyPort" not in names
    assert "FailureAction" not in names
    assert "ParallelIngestionFailureDecisionService" not in names
    assert "ParallelIngestionFailureHandlingService" not in names
    assert "build_parallel_ingestion_failure_policy_context" not in names
    assert "execute_parallel_ingestion_failure_action" not in names
    assert "extract_parallel_ingestion_agent_failures" not in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_classification_module_exposes_exactly_one_public_function() -> None:
    public_functions = _public_function_defs(CLASSIFICATION_MODULE)
    assert [node.name for node in public_functions] == [
        "classify_parallel_ingestion_agent_failures"
    ]
    assert _module_class_names(CLASSIFICATION_MODULE) == []
    tree = ast.parse(
        CLASSIFICATION_MODULE.read_text(encoding="utf-8"),
        filename=str(CLASSIFICATION_MODULE),
    )
    async_functions = [node.name for node in tree.body if isinstance(node, ast.AsyncFunctionDef)]
    assert async_functions == []
    protocols = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        and any(
            (isinstance(base, ast.Name) and base.id == "Protocol")
            or (isinstance(base, ast.Attribute) and base.attr == "Protocol")
            for base in node.bases
        )
    ]
    assert protocols == []
    abcs = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        and any(
            (isinstance(base, ast.Name) and base.id == "ABC")
            or (isinstance(base, ast.Attribute) and base.attr == "ABC")
            for base in node.bases
        )
    ]
    assert abcs == []


def test_classifier_signature_is_attributed_tuple_to_fact_tuple() -> None:
    classifier = _public_function_defs(CLASSIFICATION_MODULE)[0]
    assert classifier.name == "classify_parallel_ingestion_agent_failures"
    assert tuple(arg.arg for arg in classifier.args.args) == ("failures",)
    assert classifier.args.posonlyargs == []
    assert classifier.args.kwonlyargs == []
    assert classifier.args.vararg is None
    assert classifier.args.kwarg is None
    assert ast.unparse(classifier.args.args[0].annotation) == (
        "tuple[ParallelIngestionAgentFailure, ...]"
    )
    assert ast.unparse(classifier.returns) == "tuple[ParallelIngestionFailureFact, ...]"


def test_classifier_delegates_without_selection_or_exception_inspection() -> None:
    classifier = _public_function_defs(CLASSIFICATION_MODULE)[0]
    call_names = _call_names(classifier)
    assert "classify_parallel_ingestion_agent_failure" in call_names
    assert "isinstance" not in call_names
    assert "sorted" not in call_names
    assert "set" not in call_names
    assert "ExceptionGroup" not in call_names
    assert "extract_parallel_ingestion_agent_failures" not in call_names
    assert "ParallelIngestionFailureFact" not in call_names
    try_nodes = [node for node in ast.walk(classifier) if isinstance(node, ast.Try)]
    assert try_nodes == []
    if_nodes = [node for node in ast.walk(classifier) if isinstance(node, ast.If)]
    assert if_nodes == []
    match_nodes = [node for node in ast.walk(classifier) if isinstance(node, ast.Match)]
    assert match_nodes == []
    for_nodes = [node for node in ast.walk(classifier) if isinstance(node, ast.For)]
    assert for_nodes == []
    while_nodes = [node for node in ast.walk(classifier) if isinstance(node, ast.While)]
    assert while_nodes == []
    identifiers = _identifier_names(CLASSIFICATION_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(CLASSIFICATION_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    source = CLASSIFICATION_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "traceback" not in lowered
    assert "__cause__" not in source
    assert "__context__" not in source
    assert "__traceback__" not in source
    assert "ApplicationError" not in source
    assert "ExceptionGroup" not in source
    assert "BaseExceptionGroup" not in source
    assert "extract_parallel_ingestion_agent_failures" not in source
    assert "FailurePolicyContext" not in source
    assert "sorted(" not in source
    assert ".sort(" not in source
    assert "time.sleep" not in lowered
    assert "asyncio.sleep" not in lowered
    assert "str(" not in source
    assert "repr(" not in source
    singular_calls = [
        node
        for node in ast.walk(classifier)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "classify_parallel_ingestion_agent_failure"
    ]
    assert len(singular_calls) == 1


def test_graph_policy_extractor_and_executor_remain_unwired_to_tuple_classification() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        assert "classify_parallel_ingestion_agent_failures" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.parallel_ingestion_failure_classification"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "classify_parallel_ingestion_agent_failures" not in source
        assert "parallel_ingestion_failure_classification" not in source
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "add_conditional_edges" not in graph_source


def test_api_composition_does_not_import_or_construct_tuple_classification() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.parallel_ingestion_failure_classification",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "classify_parallel_ingestion_agent_failures" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "classify_parallel_ingestion_agent_failures" not in app_source
    assert "parallel_ingestion_failure_classification" not in app_source
