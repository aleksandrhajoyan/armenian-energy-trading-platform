"""Parallel-ingestion attempt-number source stays a Protocol-only application boundary."""

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
ATTEMPT_NUMBER_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_attempt_number.py"
SELECTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_selection.py"
FACT_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_fact.py"
CLASSIFICATION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_classification.py"
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
APPLICATION_ROOT = PRODUCTION_ROOT / "application"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
    "energy_trading.application.errors",
    "energy_trading.application.orchestration.state",
    "energy_trading.application.orchestration.failure_policy",
    "energy_trading.application.orchestration.graph",
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
    "pathlib",
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
        "ABC",
        "Exception",
        "BaseException",
        "ExceptionGroup",
        "BaseExceptionGroup",
        "ApplicationError",
        "InvalidRequestError",
        "TracebackType",
        "WorkflowState",
        "WorkflowPhase",
        "WorkflowStatus",
        "FailurePolicyContext",
        "FailurePolicyPort",
        "FailureAction",
        "ParallelIngestionFailureFact",
        "ParallelIngestionFailureSelectionPort",
        "ParallelIngestionFailureDecisionService",
        "ParallelIngestionFailureHandlingService",
        "ParallelIngestionAgentFailure",
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
        "Path",
        "PurePath",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "dict",
        "Mapping",
        "ABC",
        "traceback",
        "exc_info",
        "ApplicationError",
        "InvalidRequestError",
        "ExceptionGroup",
        "BaseExceptionGroup",
        "WorkflowState",
        "WorkflowPhase",
        "WorkflowStatus",
        "FailurePolicyContext",
        "FailurePolicyPort",
        "FailureAction",
        "ParallelIngestionFailureFact",
        "ParallelIngestionFailureSelectionPort",
        "build_parallel_ingestion_failure_policy_context",
        "execute_parallel_ingestion_failure_action",
        "ParallelIngestionFailureDecisionService",
        "ParallelIngestionFailureHandlingService",
        "fail_parallel_ingestion",
        "advance_after_parallel_ingestion",
        "extract_parallel_ingestion_agent_failures",
        "classify_parallel_ingestion_agent_failure",
        "classify_parallel_ingestion_agent_failures",
        "ParallelIngestionAgentFailure",
        "ConcurrentParallelIngestionExecutor",
        "ParallelIngestionWorkflowStep",
        "registry",
        "factory",
        "visitor",
        "tenacity",
        "backoff",
        "TaskGroup",
        "sleep",
        "retry",
        "fallback",
        "increment",
        "reset",
        "Path",
        "open",
        "Redis",
        "Engine",
        "Session",
        "__cause__",
        "__context__",
        "__traceback__",
    }
)

FORBIDDEN_MUTATION_NAMES = frozenset(
    {
        "increment",
        "increment_attempt",
        "next_attempt",
        "reset",
        "reset_attempt",
        "set_attempt",
        "record_attempt",
        "begin_attempt",
        "complete_attempt",
        "next",
        "set",
        "record",
        "begin",
        "complete",
    }
)

FORBIDDEN_IMPLEMENTATION_NAMES = frozenset(
    {
        "InMemoryParallelIngestionAttemptNumber",
        "RedisParallelIngestionAttemptNumber",
        "PostgresParallelIngestionAttemptNumber",
        "DefaultParallelIngestionAttemptNumber",
        "ParallelIngestionAttemptTracker",
        "AttemptNumberCounter",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset({"typing"})

UNWIRED_MODULES = (
    GRAPH_MODULE,
    WORKFLOW_MODULE,
    EXECUTOR_MODULE,
    EXTRACTION_MODULE,
    CLASSIFICATION_MODULE,
    FACT_MODULE,
    AGENT_FAILURE_MODULE,
    FAILURE_POLICY_MODULE,
    DECISION_MODULE,
    CONTEXT_BUILDER_MODULE,
    ACTION_MODULE,
    HANDLING_MODULE,
    SELECTION_MODULE,
    STATE_MODULE,
)

STORAGE_SUBSTRINGS = (
    "redis",
    "postgres",
    "postgresql",
    "sqlalchemy",
    "filesystem",
    "pathlib",
    "database",
    "persistence",
    "compare-and-set",
    "compare_and_set",
)


def _class_def(path: Path, class_name: str) -> ast.ClassDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    msg = f"class {class_name!r} not found in {path}"
    raise AssertionError(msg)


def _module_class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def _public_function_defs(path: Path) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]


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


def _async_method(class_def: ast.ClassDef, method_name: str) -> ast.AsyncFunctionDef:
    for node in class_def.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == method_name:
            return node
    msg = f"async method {method_name!r} not found on {class_def.name}"
    raise AssertionError(msg)


def test_attempt_number_module_belongs_to_application_orchestration() -> None:
    assert ATTEMPT_NUMBER_MODULE.parent == ORCHESTRATION_ROOT
    assert ATTEMPT_NUMBER_MODULE.exists()


def test_attempt_number_module_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(ATTEMPT_NUMBER_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(ATTEMPT_NUMBER_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(ATTEMPT_NUMBER_MODULE)
    assert "Protocol" in names
    assert "ApplicationError" not in names
    assert "WorkflowState" not in names
    assert "WorkflowPhase" not in names
    assert "WorkflowStatus" not in names
    assert "FailurePolicyContext" not in names
    assert "FailurePolicyPort" not in names
    assert "FailureAction" not in names
    assert "ParallelIngestionFailureFact" not in names
    assert "ParallelIngestionFailureSelectionPort" not in names
    assert "ParallelIngestionFailureDecisionService" not in names
    assert "ParallelIngestionFailureHandlingService" not in names
    assert "build_parallel_ingestion_failure_policy_context" not in names
    assert "execute_parallel_ingestion_failure_action" not in names
    assert "extract_parallel_ingestion_agent_failures" not in names
    assert "classify_parallel_ingestion_agent_failure" not in names
    assert "classify_parallel_ingestion_agent_failures" not in names
    assert "ParallelIngestionAgentFailure" not in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_attempt_number_module_exposes_exactly_one_nongeneric_protocol() -> None:
    public_functions = _public_function_defs(ATTEMPT_NUMBER_MODULE)
    assert public_functions == []
    assert _module_class_names(ATTEMPT_NUMBER_MODULE) == ["ParallelIngestionAttemptNumberPort"]
    class_def = _class_def(ATTEMPT_NUMBER_MODULE, "ParallelIngestionAttemptNumberPort")
    bases = _base_names(class_def)
    assert "Protocol" in bases
    assert "ABC" not in bases
    assert "Generic" not in bases
    assert list(class_def.type_params) == []
    source = ATTEMPT_NUMBER_MODULE.read_text(encoding="utf-8")
    assert "abstractmethod" not in source
    assert "runtime_checkable" not in source
    leaked_implementations = sorted(
        name
        for name in _module_class_names(ATTEMPT_NUMBER_MODULE)
        if name in FORBIDDEN_IMPLEMENTATION_NAMES
    )
    assert leaked_implementations == []


def test_get_attempt_number_is_the_only_public_operation() -> None:
    class_def = _class_def(ATTEMPT_NUMBER_MODULE, "ParallelIngestionAttemptNumberPort")
    defined_nodes = [
        node for node in class_def.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert [node.name for node in defined_nodes] == ["get_attempt_number"]
    assert all(isinstance(node, ast.AsyncFunctionDef) for node in defined_nodes)
    method = _async_method(class_def, "get_attempt_number")
    assert tuple(arg.arg for arg in method.args.args) == ("self", "workflow_id")
    assert method.args.posonlyargs == []
    assert method.args.kwonlyargs == []
    assert method.args.vararg is None
    assert method.args.kwarg is None
    assert ast.unparse(method.args.args[1].annotation) == "str"
    assert ast.unparse(method.returns) == "int"
    leaked_mutation = sorted(
        node.name for node in defined_nodes if node.name in FORBIDDEN_MUTATION_NAMES
    )
    assert leaked_mutation == []


def test_attempt_number_module_has_no_tracker_storage_or_mutation_machinery() -> None:
    identifiers = _identifier_names(ATTEMPT_NUMBER_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(ATTEMPT_NUMBER_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    leaked_mutation = sorted(name for name in identifiers if name in FORBIDDEN_MUTATION_NAMES)
    assert leaked_mutation == []
    application_implementations: list[str] = []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if isinstance(node, ast.ClassDef) and node.name in FORBIDDEN_IMPLEMENTATION_NAMES:
                application_implementations.append(node.name)
    assert application_implementations == []
    source = ATTEMPT_NUMBER_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    leaked_storage = sorted(term for term in STORAGE_SUBSTRINGS if term in lowered)
    assert leaked_storage == []
    assert "cache" not in identifiers
    assert "lock" not in identifiers
    assert "FailurePolicyContext" not in source
    assert "WorkflowState" not in source


def test_graph_policy_and_classification_remain_unwired_to_attempt_number() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        assert "ParallelIngestionAttemptNumberPort" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.parallel_ingestion_attempt_number"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "ParallelIngestionAttemptNumberPort" not in source
        assert "parallel_ingestion_attempt_number" not in source
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "add_conditional_edges" not in graph_source


def test_api_composition_does_not_import_or_construct_attempt_number() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.parallel_ingestion_attempt_number",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "ParallelIngestionAttemptNumberPort" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "parallelingestionattemptnumberport" not in app_source
    assert "parallel_ingestion_attempt_number" not in app_source
