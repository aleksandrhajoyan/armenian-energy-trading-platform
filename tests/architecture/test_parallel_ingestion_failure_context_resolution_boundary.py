"""Parallel-ingestion failure-policy context resolution stays application-owned."""

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
RESOLUTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_context_resolution.py"
SELECTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_selection.py"
ATTEMPT_NUMBER_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_attempt_number.py"
FACT_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_fact.py"
CLASSIFICATION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_classification.py"
AGENT_FAILURE_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_agent_failure.py"
EXTRACTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_exception_group.py"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
DECISION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_decision.py"
CONTEXT_BUILDER_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_context.py"
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
APPLICATION_ROOT = PRODUCTION_ROOT / "application"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
    "energy_trading.application.errors",
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
        "WorkflowStatus",
        "FailureAction",
        "FailurePolicyPort",
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
        "BaseException",
        "ExceptionGroup",
        "BaseExceptionGroup",
        "ApplicationError",
        "InvalidRequestError",
        "traceback",
        "exc_info",
        "WorkflowState",
        "WorkflowStatus",
        "FailureAction",
        "FailurePolicyPort",
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
        "StateMachine",
        "tenacity",
        "backoff",
        "asyncio",
        "TaskGroup",
        "create_task",
        "sleep",
        "retry",
        "fallback",
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
    }
)

FORBIDDEN_IMPLEMENTATION_NAMES = frozenset(
    {
        "FirstFailureWinsSelector",
        "LastFailureWinsSelector",
        "PriorityFailureSelector",
        "AgentPrioritySelector",
        "ErrorCodePrioritySelector",
        "DefaultParallelIngestionFailureSelector",
        "ParallelIngestionFailureSelector",
        "FailureFactSelector",
        "InMemoryParallelIngestionAttemptNumber",
        "RedisParallelIngestionAttemptNumber",
        "PostgresParallelIngestionAttemptNumber",
        "DefaultParallelIngestionAttemptNumber",
        "ParallelIngestionAttemptTracker",
        "AttemptNumberCounter",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.orchestration.failure_policy",
        "energy_trading.application.orchestration.parallel_ingestion_attempt_number",
        "energy_trading.application.orchestration.parallel_ingestion_failure_context",
        "energy_trading.application.orchestration.parallel_ingestion_failure_fact",
        "energy_trading.application.orchestration.parallel_ingestion_failure_selection",
        "energy_trading.application.orchestration.state",
    }
)

ALLOWED_INIT_ANNOTATIONS = {
    "selection_port": "ParallelIngestionFailureSelectionPort",
    "attempt_number_port": "ParallelIngestionAttemptNumberPort",
}

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
    FAILURE_TRANSITION_MODULE,
    SUCCESS_TRANSITION_MODULE,
    WORKFLOW_CONTEXT_MODULE,
    PLAN_MODULE,
    STATE_MODULE,
    SELECTION_MODULE,
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


def _resolve_method(class_def: ast.ClassDef) -> ast.AsyncFunctionDef:
    for node in class_def.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "resolve":
            return node
    msg = "async method 'resolve' not found on ParallelIngestionFailureContextResolutionService"
    raise AssertionError(msg)


def _is_positional_index(slice_node: ast.expr) -> bool:
    if isinstance(slice_node, ast.Constant) and slice_node.value in (0, -1):
        return True
    return (
        isinstance(slice_node, ast.UnaryOp)
        and isinstance(slice_node.op, ast.USub)
        and isinstance(slice_node.operand, ast.Constant)
        and slice_node.operand.value == 1
    )


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def test_resolution_module_belongs_to_application_orchestration() -> None:
    assert RESOLUTION_MODULE.parent == ORCHESTRATION_ROOT
    assert RESOLUTION_MODULE.exists()


def test_resolution_service_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(RESOLUTION_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(RESOLUTION_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(RESOLUTION_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(RESOLUTION_MODULE)
    assert "FailurePolicyContext" in names
    assert "WorkflowPhase" in names
    assert "ParallelIngestionFailureFact" in names
    assert "ParallelIngestionFailureSelectionPort" in names
    assert "ParallelIngestionAttemptNumberPort" in names
    assert "build_parallel_ingestion_failure_policy_context" in names
    assert "FailurePolicyPort" not in names
    assert "FailureAction" not in names
    assert "WorkflowState" not in names
    assert "WorkflowStatus" not in names
    assert "ParallelIngestionFailureDecisionService" not in names
    assert "ParallelIngestionFailureHandlingService" not in names
    assert "execute_parallel_ingestion_failure_action" not in names
    assert "fail_parallel_ingestion" not in names
    assert "ParallelIngestionAgentFailure" not in names
    assert "extract_parallel_ingestion_agent_failures" not in names
    assert "classify_parallel_ingestion_agent_failure" not in names
    assert "classify_parallel_ingestion_agent_failures" not in names
    assert "ConcurrentParallelIngestionExecutor" not in names
    assert "ParallelIngestionWorkflowStep" not in names
    assert "ParallelIngestionWorkflowContextPort" not in names


def test_resolution_module_exposes_exactly_one_production_class() -> None:
    assert _public_function_defs(RESOLUTION_MODULE) == []
    assert _module_class_names(RESOLUTION_MODULE) == [
        "ParallelIngestionFailureContextResolutionService"
    ]
    class_def = _class_def(RESOLUTION_MODULE, "ParallelIngestionFailureContextResolutionService")
    assert _base_names(class_def) == set()
    production_classes: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.ClassDef)
                and node.name == "ParallelIngestionFailureContextResolutionService"
            ):
                production_classes.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_classes == [
        "energy_trading/application/orchestration/parallel_ingestion_failure_context_resolution.py"
    ]
    leaked_implementations = sorted(
        name
        for name in _module_class_names(RESOLUTION_MODULE)
        if name in FORBIDDEN_IMPLEMENTATION_NAMES
    )
    assert leaked_implementations == []


def test_constructor_injects_exactly_the_published_selection_and_attempt_ports() -> None:
    class_def = _class_def(RESOLUTION_MODULE, "ParallelIngestionFailureContextResolutionService")
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert tuple(arg.arg for arg in init_fn.args.args) == (
        "self",
        "selection_port",
        "attempt_number_port",
    )
    assert init_fn.args.posonlyargs == []
    assert init_fn.args.kwonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    assert _init_arg_annotations(class_def) == ALLOWED_INIT_ANNOTATIONS


def test_resolve_signature_is_async_keyword_only_workflow_phase_and_facts() -> None:
    class_def = _class_def(RESOLUTION_MODULE, "ParallelIngestionFailureContextResolutionService")
    resolve_fn = _resolve_method(class_def)
    assert tuple(arg.arg for arg in resolve_fn.args.args) == ("self",)
    assert resolve_fn.args.posonlyargs == []
    assert tuple(arg.arg for arg in resolve_fn.args.kwonlyargs) == (
        "workflow_id",
        "phase",
        "facts",
    )
    assert resolve_fn.args.vararg is None
    assert resolve_fn.args.kwarg is None
    assert ast.unparse(resolve_fn.args.kwonlyargs[0].annotation) == "str"
    assert ast.unparse(resolve_fn.args.kwonlyargs[1].annotation) == "WorkflowPhase"
    assert ast.unparse(resolve_fn.args.kwonlyargs[2].annotation) == (
        "tuple[ParallelIngestionFailureFact, ...]"
    )
    assert ast.unparse(resolve_fn.returns) == "FailurePolicyContext"
    assert resolve_fn.args.kw_defaults == [None, None, None]
    public_methods = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]
    assert public_methods == ["resolve"]


def test_resolve_delegates_once_in_order_without_selection_or_tracking_logic() -> None:
    class_def = _class_def(RESOLUTION_MODULE, "ParallelIngestionFailureContextResolutionService")
    resolve_fn = _resolve_method(class_def)
    control = [
        type(node).__name__
        for node in ast.walk(resolve_fn)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try, ast.With))
    ]
    assert control == []
    except_handlers = [node for node in ast.walk(resolve_fn) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    select_calls = 0
    attempt_calls = 0
    builder_calls = 0
    context_calls = 0
    for node in ast.walk(resolve_fn):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name == "select":
            select_calls += 1
            assert len(node.args) == 1
            assert isinstance(node.args[0], ast.Name)
            assert node.args[0].id == "facts"
        if name == "get_attempt_number":
            attempt_calls += 1
            assert len(node.args) == 1
            assert isinstance(node.args[0], ast.Name)
            assert node.args[0].id == "workflow_id"
        if name == "build_parallel_ingestion_failure_policy_context":
            builder_calls += 1
            assert node.args == []
            keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in node.keywords}
            assert keywords == {
                "phase": "phase",
                "error_code": "selected_fact.error_code",
                "attempt_number": "attempt_number",
                "agent_name": "selected_fact.agent_name",
            }
        if name == "FailurePolicyContext":
            context_calls += 1
    assert select_calls == 1
    assert attempt_calls == 1
    assert builder_calls == 1
    assert context_calls == 0
    statements = [node for node in resolve_fn.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 3
    first, second, third = statements
    assert isinstance(first, ast.Assign)
    assert isinstance(first.value, ast.Call)
    assert _call_name(first.value) == "select"
    assert isinstance(second, ast.Assign)
    assert isinstance(second.value, ast.Await)
    assert isinstance(second.value.value, ast.Call)
    assert _call_name(second.value.value) == "get_attempt_number"
    assert isinstance(third, ast.Return)
    assert isinstance(third.value, ast.Call)
    assert _call_name(third.value) == "build_parallel_ingestion_failure_policy_context"
    indexed = [
        ast.unparse(node)
        for node in ast.walk(resolve_fn)
        if isinstance(node, ast.Subscript) and _is_positional_index(node.slice)
    ]
    assert indexed == []
    identifiers = _identifier_names(RESOLUTION_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(RESOLUTION_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    application_implementations: list[str] = []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if isinstance(node, ast.ClassDef) and node.name in FORBIDDEN_IMPLEMENTATION_NAMES:
                application_implementations.append(node.name)
    assert application_implementations == []
    source = RESOLUTION_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "FailurePolicyPort" not in source
    assert "FailureAction" not in source
    assert "WorkflowState" not in source
    assert "time.sleep" not in lowered
    assert "asyncio.sleep" not in lowered
    assert "asyncio.taskgroup" not in lowered
    assert "sorted(" not in source
    assert ".sort(" not in source
    assert "increment" not in lowered
    assert "FailurePolicyContext(" not in source


def test_graph_policy_and_lower_layers_remain_unwired_to_the_resolution_service() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        assert "ParallelIngestionFailureContextResolutionService" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.parallel_ingestion_failure_context_resolution"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "ParallelIngestionFailureContextResolutionService" not in source
        assert "parallel_ingestion_failure_context_resolution" not in source
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "add_conditional_edges" not in graph_source


def test_api_composition_does_not_import_or_construct_the_resolution_service() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.parallel_ingestion_failure_context_resolution",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "ParallelIngestionFailureContextResolutionService" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "parallelingestionfailurecontextresolutionservice" not in app_source
    assert "parallel_ingestion_failure_context_resolution" not in app_source
