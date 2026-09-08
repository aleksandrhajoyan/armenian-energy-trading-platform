"""Initial Phase 2 attempt-number source stays application-owned and stateless."""

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
SOURCE_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_initial_attempt_number_source.py"
ATTEMPT_NUMBER_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_attempt_number.py"
SELECTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_selection.py"
SELECTOR_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_strict_single_failure_selector.py"
FACT_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_fact.py"
CLASSIFICATION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_classification.py"
AGENT_FAILURE_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_agent_failure.py"
EXTRACTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_exception_group.py"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
DECISION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_decision.py"
CONTEXT_BUILDER_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_context.py"
RESOLUTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_context_resolution.py"
ACTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_action.py"
HANDLING_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_handling.py"
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
    "energy_trading.application.errors",
    "energy_trading.application.orchestration",
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
    "sqlite3",
    "json",
    "random",
    "hashlib",
    "time",
    "datetime",
    "uuid",
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
        "BaseExceptionGroup",
        "ApplicationError",
        "InvalidRequestError",
        "TracebackType",
        "WorkflowState",
        "WorkflowPhase",
        "WorkflowStatus",
        "FailureAction",
        "FailurePolicyContext",
        "FailurePolicyPort",
        "ParallelIngestionFailureFact",
        "ParallelIngestionFailureSelectionPort",
        "ParallelIngestionAttemptNumberPort",
        "ParallelIngestionFailureDecisionService",
        "ParallelIngestionFailureHandlingService",
        "ParallelIngestionFailureContextResolutionService",
        "StrictSingleParallelIngestionFailureSelector",
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
        "AgentName",
        "AgentPort",
        "Path",
        "PurePath",
        "ClassVar",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "dict",
        "Mapping",
        "set",
        "list",
        "Counter",
        "Protocol",
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
        "FailureAction",
        "FailurePolicyContext",
        "FailurePolicyPort",
        "build_parallel_ingestion_failure_policy_context",
        "execute_parallel_ingestion_failure_action",
        "ParallelIngestionFailureDecisionService",
        "ParallelIngestionFailureHandlingService",
        "ParallelIngestionFailureContextResolutionService",
        "ParallelIngestionAttemptNumberPort",
        "StrictSingleParallelIngestionFailureSelector",
        "ParallelIngestionFailureFact",
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
        "tenacity",
        "backoff",
        "asyncio",
        "TaskGroup",
        "sleep",
        "retry",
        "fallback",
        "increment",
        "reset",
        "hash",
        "random",
        "time",
        "datetime",
        "uuid",
        "cache",
        "lock",
        "Lock",
        "Redis",
        "Engine",
        "Session",
        "open",
        "Path",
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
        "__init__",
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
        "AttemptRepository",
        "AttemptNumberStore",
    }
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
    "sqlite",
    "json",
    "qdrant",
    "checkpointer",
)

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
    RESOLUTION_MODULE,
    ACTION_MODULE,
    HANDLING_MODULE,
    FAILURE_TRANSITION_MODULE,
    SUCCESS_TRANSITION_MODULE,
    WORKFLOW_CONTEXT_MODULE,
    PLAN_MODULE,
    STATE_MODULE,
    SELECTION_MODULE,
    SELECTOR_MODULE,
    ATTEMPT_NUMBER_MODULE,
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


def _public_function_defs(path: Path) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
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


def _async_method(class_def: ast.ClassDef, method_name: str) -> ast.AsyncFunctionDef:
    for node in class_def.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == method_name:
            return node
    msg = f"async method {method_name!r} not found on {class_def.name}"
    raise AssertionError(msg)


def test_source_module_belongs_to_application_orchestration() -> None:
    assert SOURCE_MODULE.parent == ORCHESTRATION_ROOT
    assert SOURCE_MODULE.exists()


def test_source_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(SOURCE_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    assert imported_modules(SOURCE_MODULE) == set()
    leaked_names = sorted(
        name for name in imported_names(SOURCE_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(SOURCE_MODULE)
    assert "ParallelIngestionAttemptNumberPort" not in names
    assert "Protocol" not in names
    assert "WorkflowState" not in names
    assert "FailurePolicyContext" not in names
    assert "FailurePolicyPort" not in names
    assert "FailureAction" not in names
    assert "ParallelIngestionFailureContextResolutionService" not in names
    assert "StrictSingleParallelIngestionFailureSelector" not in names
    assert "ParallelIngestionFailureFact" not in names


def test_source_module_exposes_exactly_one_production_class() -> None:
    assert _public_function_defs(SOURCE_MODULE) == []
    assert _module_class_names(SOURCE_MODULE) == ["InitialParallelIngestionAttemptNumberSource"]
    class_def = _class_def(SOURCE_MODULE, "InitialParallelIngestionAttemptNumberSource")
    assert _base_names(class_def) == set()
    production_classes: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.ClassDef)
                and node.name == "InitialParallelIngestionAttemptNumberSource"
            ):
                production_classes.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_classes == [
        "energy_trading/application/orchestration/parallel_ingestion_initial_attempt_number_source.py"
    ]
    leaked_implementations = sorted(
        name
        for name in _module_class_names(SOURCE_MODULE)
        if name in FORBIDDEN_IMPLEMENTATION_NAMES
    )
    assert leaked_implementations == []


def test_get_attempt_number_is_the_only_public_operation() -> None:
    class_def = _class_def(SOURCE_MODULE, "InitialParallelIngestionAttemptNumberSource")
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


def test_get_attempt_number_returns_literal_integer_one() -> None:
    class_def = _class_def(SOURCE_MODULE, "InitialParallelIngestionAttemptNumberSource")
    method = _async_method(class_def, "get_attempt_number")
    returns = [node for node in ast.walk(method) if isinstance(node, ast.Return)]
    assert len(returns) == 1
    value = returns[0].value
    assert isinstance(value, ast.Constant)
    assert value.value == 1
    assert not any(isinstance(node, ast.BinOp) for node in ast.walk(method))
    assert not any(isinstance(node, ast.Call) for node in ast.walk(method))
    assert not any(
        isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)) for node in ast.walk(method)
    )
    control = [
        type(node).__name__
        for node in ast.walk(method)
        if isinstance(node, (ast.For, ast.While, ast.Match, ast.Try, ast.With, ast.If, ast.IfExp))
    ]
    assert control == []
    identifiers = _identifier_names(SOURCE_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(SOURCE_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    leaked_mutation = sorted(name for name in identifiers if name in FORBIDDEN_MUTATION_NAMES)
    assert leaked_mutation == []
    source = SOURCE_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    leaked_storage = sorted(term for term in STORAGE_SUBSTRINGS if term in lowered)
    assert leaked_storage == []
    assert "WorkflowState" not in source
    assert "FailurePolicyContext" not in source


def test_graph_policy_and_lower_layers_remain_unwired_to_the_source() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        assert "InitialParallelIngestionAttemptNumberSource" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.parallel_ingestion_initial_attempt_number_source"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "InitialParallelIngestionAttemptNumberSource" not in source
        assert "parallel_ingestion_initial_attempt_number_source" not in source


def test_api_composition_does_not_import_or_construct_the_source() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.parallel_ingestion_initial_attempt_number_source",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "InitialParallelIngestionAttemptNumberSource" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "initialparallelingestionattemptnumbersource" not in app_source
    assert "parallel_ingestion_initial_attempt_number_source" not in app_source
