"""Initial parallel-ingestion failure policy stays application-owned and stateless."""

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
POLICY_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_initial_failure_policy.py"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
DECISION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_decision.py"
CONTEXT_BUILDER_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_context.py"
RESOLUTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_context_resolution.py"
PREPARATION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_context_preparation.py"
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
SELECTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_selection.py"
SELECTOR_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_strict_single_failure_selector.py"
ATTEMPT_NUMBER_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_attempt_number.py"
INITIAL_ATTEMPT_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_initial_attempt_number_source.py"
FACT_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_fact.py"
CLASSIFICATION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_classification.py"
AGENT_FAILURE_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_agent_failure.py"
EXTRACTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_exception_group.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
    "energy_trading.application.errors",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.orchestration.state",
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
        "FailurePolicyPort",
        "ParallelIngestionFailureFact",
        "ParallelIngestionFailureSelectionPort",
        "ParallelIngestionAttemptNumberPort",
        "InitialParallelIngestionAttemptNumberSource",
        "StrictSingleParallelIngestionFailureSelector",
        "ParallelIngestionFailureContextResolutionService",
        "ParallelIngestionFailureContextPreparationService",
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
        "AgentName",
        "AgentPort",
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
        "Protocol",
        "ABC",
        "traceback",
        "exc_info",
        "WorkflowState",
        "WorkflowPhase",
        "WorkflowStatus",
        "FailurePolicyPort",
        "execute_parallel_ingestion_failure_action",
        "fail_parallel_ingestion",
        "advance_after_parallel_ingestion",
        "ParallelIngestionFailureDecisionService",
        "ParallelIngestionFailureHandlingService",
        "ParallelIngestionFailureContextResolutionService",
        "ParallelIngestionFailureContextPreparationService",
        "ParallelIngestionAttemptNumberPort",
        "InitialParallelIngestionAttemptNumberSource",
        "StrictSingleParallelIngestionFailureSelector",
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
        "RETRY",
        "FALLBACK",
        "phase",
        "error_code",
        "attempt_number",
        "agent_name",
        "sorted",
        "sort",
        "min",
        "max",
        "increment",
        "reset",
        "__cause__",
        "__context__",
        "__traceback__",
    }
)

FORBIDDEN_IMPLEMENTATION_NAMES = frozenset(
    {
        "DefaultFailurePolicy",
        "RetryAllDependenciesPolicy",
        "ExponentialBackoffPolicy",
        "AgentFailurePolicy",
        "StaticFailurePolicy",
        "ConservativeFailurePolicy",
        "RetryableErrorPolicy",
        "FallbackFailurePolicy",
        "GenericPolicyEngine",
        "FailurePolicyEngine",
        "PolicyRuleTable",
    }
)

CONTEXT_FIELDS = frozenset({"phase", "error_code", "attempt_number", "agent_name"})

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.orchestration.failure_policy",
    }
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
    PREPARATION_MODULE,
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
    INITIAL_ATTEMPT_MODULE,
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


def _decide_method(class_def: ast.ClassDef) -> ast.AsyncFunctionDef:
    for node in class_def.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "decide":
            return node
    msg = "async method 'decide' not found on InitialParallelIngestionFailurePolicy"
    raise AssertionError(msg)


def test_policy_module_belongs_to_application_orchestration() -> None:
    assert POLICY_MODULE.parent == ORCHESTRATION_ROOT
    assert POLICY_MODULE.exists()


def test_policy_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(POLICY_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(POLICY_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(POLICY_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(POLICY_MODULE)
    assert "FailureAction" in names
    assert "FailurePolicyContext" in names
    assert "FailurePolicyPort" not in names
    assert "Protocol" not in names
    assert "WorkflowState" not in names
    assert "WorkflowPhase" not in names
    assert "ParallelIngestionFailureDecisionService" not in names
    assert "ParallelIngestionFailureHandlingService" not in names
    assert "execute_parallel_ingestion_failure_action" not in names
    assert "fail_parallel_ingestion" not in names
    assert "ParallelIngestionFailureContextPreparationService" not in names
    assert "ParallelIngestionFailureContextResolutionService" not in names
    assert "StrictSingleParallelIngestionFailureSelector" not in names
    assert "InitialParallelIngestionAttemptNumberSource" not in names
    assert "ConcurrentParallelIngestionExecutor" not in names
    assert "ParallelIngestionWorkflowStep" not in names


def test_policy_module_exposes_exactly_one_production_class() -> None:
    assert _public_function_defs(POLICY_MODULE) == []
    assert _module_class_names(POLICY_MODULE) == ["InitialParallelIngestionFailurePolicy"]
    class_def = _class_def(POLICY_MODULE, "InitialParallelIngestionFailurePolicy")
    assert _base_names(class_def) == set()
    production_classes: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.ClassDef)
                and node.name == "InitialParallelIngestionFailurePolicy"
            ):
                production_classes.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_classes == [
        "energy_trading/application/orchestration/parallel_ingestion_initial_failure_policy.py"
    ]
    leaked_implementations = sorted(
        name
        for name in _module_class_names(POLICY_MODULE)
        if name in FORBIDDEN_IMPLEMENTATION_NAMES
    )
    assert leaked_implementations == []
    application_implementations: list[str] = []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if isinstance(node, ast.ClassDef) and node.name in FORBIDDEN_IMPLEMENTATION_NAMES:
                application_implementations.append(node.name)
    assert application_implementations == []


def test_decide_is_the_only_public_operation() -> None:
    class_def = _class_def(POLICY_MODULE, "InitialParallelIngestionFailurePolicy")
    defined_nodes = [
        node for node in class_def.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert [node.name for node in defined_nodes] == ["decide"]
    assert all(isinstance(node, ast.AsyncFunctionDef) for node in defined_nodes)
    decide_fn = _decide_method(class_def)
    assert tuple(arg.arg for arg in decide_fn.args.args) == ("self", "context")
    assert decide_fn.args.posonlyargs == []
    assert decide_fn.args.kwonlyargs == []
    assert decide_fn.args.vararg is None
    assert decide_fn.args.kwarg is None
    assert ast.unparse(decide_fn.args.args[1].annotation) == "FailurePolicyContext"
    assert ast.unparse(decide_fn.returns) == "FailureAction"


def test_decide_returns_fail_without_context_branching() -> None:
    class_def = _class_def(POLICY_MODULE, "InitialParallelIngestionFailurePolicy")
    decide_fn = _decide_method(class_def)
    control = [
        type(node).__name__
        for node in ast.walk(decide_fn)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try, ast.With))
    ]
    assert control == []
    except_handlers = [node for node in ast.walk(decide_fn) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    returns = [node for node in ast.walk(decide_fn) if isinstance(node, ast.Return)]
    assert len(returns) == 1
    assert ast.unparse(returns[0].value) == "FailureAction.FAIL"
    accessed_fields = sorted(
        node.attr
        for node in ast.walk(decide_fn)
        if isinstance(node, ast.Attribute) and node.attr in CONTEXT_FIELDS
    )
    assert accessed_fields == []
    assert not any(isinstance(node, ast.BinOp) for node in ast.walk(decide_fn))
    assert not any(isinstance(node, ast.Dict) for node in ast.walk(decide_fn))
    assert not any(isinstance(node, ast.Set) for node in ast.walk(decide_fn))
    assert not any(isinstance(node, ast.List) for node in ast.walk(decide_fn))
    identifiers = _identifier_names(POLICY_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(POLICY_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    source = POLICY_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "FailurePolicyPort" not in source
    assert "WorkflowState" not in source
    assert "FailureAction.RETRY" not in source
    assert "FailureAction.FALLBACK" not in source
    assert "time.sleep" not in lowered
    assert "asyncio.sleep" not in lowered
    assert "sorted(" not in source
    assert ".sort(" not in source


def test_graph_policy_and_lower_layers_remain_unwired_to_the_policy() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        assert "InitialParallelIngestionFailurePolicy" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.parallel_ingestion_initial_failure_policy"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "InitialParallelIngestionFailurePolicy" not in source
        assert "parallel_ingestion_initial_failure_policy" not in source
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "add_conditional_edges" not in graph_source


def test_api_composition_does_not_import_or_construct_the_policy() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.parallel_ingestion_initial_failure_policy",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "InitialParallelIngestionFailurePolicy" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "initialparallelingestionfailurepolicy" not in app_source
    assert "parallel_ingestion_initial_failure_policy" not in app_source
