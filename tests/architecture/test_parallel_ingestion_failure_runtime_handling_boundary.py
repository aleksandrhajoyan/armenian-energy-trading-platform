"""Parallel-ingestion runtime failure handling stays application-owned."""

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
RUNTIME_HANDLING_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_runtime_handling.py"
PREPARATION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_context_preparation.py"
HANDLING_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_handling.py"
RESOLUTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_context_resolution.py"
SELECTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_selection.py"
STRICT_SELECTOR_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_strict_single_failure_selector.py"
ATTEMPT_NUMBER_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_attempt_number.py"
INITIAL_ATTEMPT_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_initial_attempt_number_source.py"
INITIAL_POLICY_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_initial_failure_policy.py"
FACT_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_fact.py"
CLASSIFICATION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_classification.py"
AGENT_FAILURE_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_agent_failure.py"
EXTRACTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_exception_group.py"
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
APPLICATION_ROOT = PRODUCTION_ROOT / "application"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
    "energy_trading.application.errors",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.orchestration.failure_policy",
    "energy_trading.application.orchestration.parallel_ingestion_failure_decision",
    "energy_trading.application.orchestration.parallel_ingestion_failure_action",
    "energy_trading.application.orchestration.parallel_ingestion_failure_transition",
    "energy_trading.application.orchestration.parallel_ingestion_failure_context",
    "energy_trading.application.orchestration.parallel_ingestion_failure_context_resolution",
    "energy_trading.application.orchestration.parallel_ingestion_failure_selection",
    "energy_trading.application.orchestration.parallel_ingestion_strict_single_failure_selector",
    "energy_trading.application.orchestration.parallel_ingestion_attempt_number",
    "energy_trading.application.orchestration.parallel_ingestion_initial_attempt_number_source",
    "energy_trading.application.orchestration.parallel_ingestion_initial_failure_policy",
    "energy_trading.application.orchestration.parallel_ingestion_exception_group",
    "energy_trading.application.orchestration.parallel_ingestion_failure_classification",
    "energy_trading.application.orchestration.parallel_ingestion_failure_fact",
    "energy_trading.application.orchestration.parallel_ingestion_agent_failure",
    "energy_trading.application.orchestration.parallel_ingestion_executor",
    "energy_trading.application.orchestration.parallel_ingestion_workflow",
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
        "ExceptionGroup",
        "ApplicationError",
        "InvalidRequestError",
        "TracebackType",
        "WorkflowPhase",
        "WorkflowStatus",
        "FailureAction",
        "FailurePolicyContext",
        "FailurePolicyPort",
        "ParallelIngestionFailureDecisionService",
        "ParallelIngestionFailureFact",
        "ParallelIngestionAgentFailure",
        "ParallelIngestionFailureSelectionPort",
        "StrictSingleParallelIngestionFailureSelector",
        "ParallelIngestionAttemptNumberPort",
        "InitialParallelIngestionAttemptNumberSource",
        "InitialParallelIngestionFailurePolicy",
        "ParallelIngestionFailureContextResolutionService",
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
        "Exception",
        "ExceptionGroup",
        "ApplicationError",
        "InvalidRequestError",
        "traceback",
        "exc_info",
        "WorkflowPhase",
        "WorkflowStatus",
        "FailureAction",
        "FailurePolicyContext",
        "FailurePolicyPort",
        "execute_parallel_ingestion_failure_action",
        "ParallelIngestionFailureDecisionService",
        "fail_parallel_ingestion",
        "advance_after_parallel_ingestion",
        "replace",
        "build_parallel_ingestion_failure_policy_context",
        "classify_parallel_ingestion_agent_failure",
        "classify_parallel_ingestion_agent_failures",
        "extract_parallel_ingestion_agent_failures",
        "ParallelIngestionFailureFact",
        "ParallelIngestionAgentFailure",
        "ParallelIngestionFailureSelectionPort",
        "StrictSingleParallelIngestionFailureSelector",
        "ParallelIngestionAttemptNumberPort",
        "InitialParallelIngestionAttemptNumberSource",
        "InitialParallelIngestionFailurePolicy",
        "ParallelIngestionFailureContextResolutionService",
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
        "retry",
        "fallback",
        "RETRY",
        "FALLBACK",
        "wait",
        "sorted",
        "sort",
        "unique",
        "deduplicate",
        "groupby",
        "primary",
        "rank",
        "severity",
        "retryable",
        "min",
        "max",
        "increment",
        "reset",
        "__cause__",
        "__context__",
        "__traceback__",
        "exceptions",
        "split",
        "subgroup",
        "derive",
        "AdapterDiagnostic",
    }
)

FORBIDDEN_IMPLEMENTATION_NAMES = frozenset(
    {
        "GenericFailureRuntime",
        "WorkflowFailureEngine",
        "OrchestratorFailureFramework",
        "GenericPolicyEngine",
        "FailurePolicyEngine",
        "ExceptionGroupPipeline",
        "DefaultFailureRuntime",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.orchestration.parallel_ingestion_failure_context_preparation",
        "energy_trading.application.orchestration.parallel_ingestion_failure_handling",
        "energy_trading.application.orchestration.state",
    }
)

ALLOWED_INIT_ANNOTATIONS = {
    "context_preparation_service": "ParallelIngestionFailureContextPreparationService",
    "failure_handling_service": "ParallelIngestionFailureHandlingService",
}

UNWIRED_MODULES = (
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
    STRICT_SELECTOR_MODULE,
    ATTEMPT_NUMBER_MODULE,
    INITIAL_ATTEMPT_MODULE,
    INITIAL_POLICY_MODULE,
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
    msg = "async method 'handle' not found on ParallelIngestionFailureRuntimeHandlingService"
    raise AssertionError(msg)


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def test_runtime_handling_module_belongs_to_application_orchestration() -> None:
    assert RUNTIME_HANDLING_MODULE.parent == ORCHESTRATION_ROOT
    assert RUNTIME_HANDLING_MODULE.exists()


def test_runtime_handling_service_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(RUNTIME_HANDLING_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(RUNTIME_HANDLING_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(RUNTIME_HANDLING_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(RUNTIME_HANDLING_MODULE)
    assert "WorkflowState" in names
    assert "ParallelIngestionFailureContextPreparationService" in names
    assert "ParallelIngestionFailureHandlingService" in names
    assert "FailurePolicyContext" not in names
    assert "FailurePolicyPort" not in names
    assert "FailureAction" not in names
    assert "ParallelIngestionFailureDecisionService" not in names
    assert "execute_parallel_ingestion_failure_action" not in names
    assert "fail_parallel_ingestion" not in names
    assert "build_parallel_ingestion_failure_policy_context" not in names
    assert "InitialParallelIngestionFailurePolicy" not in names
    assert "StrictSingleParallelIngestionFailureSelector" not in names
    assert "InitialParallelIngestionAttemptNumberSource" not in names
    assert "ParallelIngestionFailureContextResolutionService" not in names
    assert "extract_parallel_ingestion_agent_failures" not in names
    assert "classify_parallel_ingestion_agent_failures" not in names
    assert "classify_parallel_ingestion_agent_failure" not in names
    assert "ParallelIngestionAgentFailure" not in names
    assert "ParallelIngestionFailureFact" not in names
    assert "ConcurrentParallelIngestionExecutor" not in names
    assert "ParallelIngestionWorkflowStep" not in names
    assert "WorkflowPhase" not in names
    assert "WorkflowStatus" not in names


def test_runtime_handling_module_exposes_exactly_one_production_class() -> None:
    assert _public_function_defs(RUNTIME_HANDLING_MODULE) == []
    assert _module_class_names(RUNTIME_HANDLING_MODULE) == [
        "ParallelIngestionFailureRuntimeHandlingService"
    ]
    class_def = _class_def(
        RUNTIME_HANDLING_MODULE, "ParallelIngestionFailureRuntimeHandlingService"
    )
    assert _base_names(class_def) == set()
    production_classes: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.ClassDef)
                and node.name == "ParallelIngestionFailureRuntimeHandlingService"
            ):
                production_classes.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_classes == [
        "energy_trading/application/orchestration/parallel_ingestion_failure_runtime_handling.py"
    ]
    leaked_implementations = sorted(
        name
        for name in _module_class_names(RUNTIME_HANDLING_MODULE)
        if name in FORBIDDEN_IMPLEMENTATION_NAMES
    )
    assert leaked_implementations == []


def test_constructor_injects_exactly_the_published_preparation_and_handling_services() -> None:
    class_def = _class_def(
        RUNTIME_HANDLING_MODULE, "ParallelIngestionFailureRuntimeHandlingService"
    )
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert tuple(arg.arg for arg in init_fn.args.args) == (
        "self",
        "context_preparation_service",
        "failure_handling_service",
    )
    assert init_fn.args.posonlyargs == []
    assert init_fn.args.kwonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    assert _init_arg_annotations(class_def) == ALLOWED_INIT_ANNOTATIONS
    constructed = [_call_name(node) for node in ast.walk(init_fn) if isinstance(node, ast.Call)]
    assert "ParallelIngestionFailureContextPreparationService" not in constructed
    assert "ParallelIngestionFailureHandlingService" not in constructed
    assert "ParallelIngestionFailureDecisionService" not in constructed
    assert "InitialParallelIngestionFailurePolicy" not in constructed
    assert "StrictSingleParallelIngestionFailureSelector" not in constructed
    assert "InitialParallelIngestionAttemptNumberSource" not in constructed


def test_handle_signature_is_async_keyword_only_state_and_failure_group() -> None:
    class_def = _class_def(
        RUNTIME_HANDLING_MODULE, "ParallelIngestionFailureRuntimeHandlingService"
    )
    handle_fn = _handle_method(class_def)
    assert tuple(arg.arg for arg in handle_fn.args.args) == ("self",)
    assert handle_fn.args.posonlyargs == []
    assert tuple(arg.arg for arg in handle_fn.args.kwonlyargs) == ("state", "failure_group")
    assert handle_fn.args.vararg is None
    assert handle_fn.args.kwarg is None
    assert ast.unparse(handle_fn.args.kwonlyargs[0].annotation) == "WorkflowState"
    assert ast.unparse(handle_fn.args.kwonlyargs[1].annotation) == "BaseExceptionGroup"
    assert ast.unparse(handle_fn.returns) == "WorkflowState"
    assert handle_fn.args.kw_defaults == [None, None]
    public_methods = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]
    assert public_methods == ["handle"]


def test_handle_delegates_prepare_then_handle_without_duplicate_logic() -> None:
    class_def = _class_def(
        RUNTIME_HANDLING_MODULE, "ParallelIngestionFailureRuntimeHandlingService"
    )
    handle_fn = _handle_method(class_def)
    control = [
        type(node).__name__
        for node in ast.walk(handle_fn)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try, ast.With))
    ]
    assert control == []
    except_handlers = [node for node in ast.walk(handle_fn) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    prepare_calls = 0
    handle_calls = 0
    decide_calls = 0
    execute_calls = 0
    fail_calls = 0
    replace_calls = 0
    extract_calls = 0
    classify_calls = 0
    for node in ast.walk(handle_fn):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name == "prepare":
            prepare_calls += 1
            assert node.args == []
            keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in node.keywords}
            assert keywords == {
                "workflow_id": "state.workflow_id",
                "phase": "state.phase",
                "failure_group": "failure_group",
            }
        if name == "handle":
            handle_calls += 1
            assert node.args == []
            keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in node.keywords}
            assert keywords == {"state": "state", "context": "context"}
        if name == "decide":
            decide_calls += 1
        if name == "execute_parallel_ingestion_failure_action":
            execute_calls += 1
        if name == "fail_parallel_ingestion":
            fail_calls += 1
        if name == "replace":
            replace_calls += 1
        if name in {
            "extract_parallel_ingestion_agent_failures",
            "classify_parallel_ingestion_agent_failures",
            "classify_parallel_ingestion_agent_failure",
        }:
            extract_calls += 1
            classify_calls += 1
        if name == "WorkflowState":
            replace_calls += 1
    assert prepare_calls == 1
    assert handle_calls == 1
    assert decide_calls == 0
    assert execute_calls == 0
    assert fail_calls == 0
    assert replace_calls == 0
    assert extract_calls == 0
    assert classify_calls == 0
    statements = [node for node in handle_fn.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 2
    first, second = statements
    assert isinstance(first, ast.Assign)
    assert isinstance(first.value, ast.Await)
    assert isinstance(first.value.value, ast.Call)
    assert _call_name(first.value.value) == "prepare"
    assert isinstance(second, ast.Return)
    assert isinstance(second.value, ast.Await)
    assert isinstance(second.value.value, ast.Call)
    assert _call_name(second.value.value) == "handle"
    identifiers = _identifier_names(RUNTIME_HANDLING_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(RUNTIME_HANDLING_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    application_implementations: list[str] = []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if isinstance(node, ast.ClassDef) and node.name in FORBIDDEN_IMPLEMENTATION_NAMES:
                application_implementations.append(node.name)
    assert application_implementations == []
    source = RUNTIME_HANDLING_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "FailurePolicyPort" not in source
    assert "FailureAction" not in source
    assert "fail_parallel_ingestion" not in source
    assert "execute_parallel_ingestion_failure_action" not in source
    assert "build_parallel_ingestion_failure_policy_context" not in source
    assert "WorkflowState(" not in source
    assert "time.sleep" not in lowered
    assert "asyncio.sleep" not in lowered
    assert "asyncio.taskgroup" not in lowered
    assert ".exceptions" not in source
    assert "__cause__" not in source
    assert "FailureAction.RETRY" not in source
    assert "FailureAction.FALLBACK" not in source


def test_graph_policy_and_lower_layers_remain_unwired_to_the_runtime_handling_service() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        assert "ParallelIngestionFailureRuntimeHandlingService" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.parallel_ingestion_failure_runtime_handling"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "ParallelIngestionFailureRuntimeHandlingService" not in source
        assert "parallel_ingestion_failure_runtime_handling" not in source
    graph_names = imported_names(GRAPH_MODULE)
    assert "ParallelIngestionFailureRuntimeHandlingService" in graph_names
    graph_modules = imported_modules(GRAPH_MODULE)
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_runtime_handling"
        in graph_modules
    )
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "ParallelIngestionFailureContextPreparationService" not in graph_source
    assert "ParallelIngestionFailureHandlingService" not in graph_source
    assert "InitialParallelIngestionFailurePolicy" not in graph_source


def test_api_composition_does_not_import_or_construct_the_runtime_handling_service() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.parallel_ingestion_failure_runtime_handling",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "ParallelIngestionFailureRuntimeHandlingService" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "parallelingestionfailureruntimehandlingservice" not in app_source
    assert "parallel_ingestion_failure_runtime_handling" not in app_source
