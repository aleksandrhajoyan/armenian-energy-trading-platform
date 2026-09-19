"""Forecasting failure-context preparation stays application-owned."""

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
PREPARATION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_context_preparation.py"
RESOLUTION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_context_resolution.py"
SELECTION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_selection.py"
ATTEMPT_NUMBER_MODULE = ORCHESTRATION_ROOT / "forecasting_attempt_number.py"
SELECTOR_MODULE = ORCHESTRATION_ROOT / "forecasting_strict_single_failure_selector.py"
FACT_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_fact.py"
CLASSIFICATION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_classification.py"
AGENT_FAILURE_MODULE = ORCHESTRATION_ROOT / "forecasting_agent_failure.py"
EXTRACTION_MODULE = ORCHESTRATION_ROOT / "forecasting_exception_group.py"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
CONTEXT_BUILDER_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_context.py"
FAILURE_TRANSITION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_transition.py"
SUCCESS_TRANSITION_MODULE = ORCHESTRATION_ROOT / "forecasting_transition.py"
WORKFLOW_MODULE = ORCHESTRATION_ROOT / "forecasting_workflow.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
EXECUTOR_MODULE = ORCHESTRATION_ROOT / "forecasting_executor.py"
WORKFLOW_CONTEXT_MODULE = ORCHESTRATION_ROOT / "forecasting_context.py"
PLAN_MODULE = ORCHESTRATION_ROOT / "forecasting_plan.py"
PHASE2_PREPARATION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_context_preparation.py"
PHASE2_RESOLUTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_context_resolution.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
    "energy_trading.application.errors",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.orchestration.forecasting_failure_selection",
    "energy_trading.application.orchestration.forecasting_strict_single_failure_selector",
    "energy_trading.application.orchestration.forecasting_attempt_number",
    "energy_trading.application.orchestration.forecasting_failure_fact",
    "energy_trading.application.orchestration.forecasting_agent_failure",
    "energy_trading.application.orchestration.forecasting_executor",
    "energy_trading.application.orchestration.forecasting_workflow",
    "energy_trading.application.orchestration.forecasting_failure_transition",
    "energy_trading.application.orchestration.parallel_ingestion_failure_context_preparation",
    "energy_trading.application.orchestration.parallel_ingestion_failure_context_resolution",
    "energy_trading.application.orchestration.parallel_ingestion_failure_selection",
    "energy_trading.application.orchestration.parallel_ingestion_attempt_number",
    "energy_trading.application.orchestration.parallel_ingestion_failure_fact",
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
    "os",
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
        "BaseExceptionGroup",
        "ApplicationError",
        "InvalidRequestError",
        "TracebackType",
        "WorkflowState",
        "WorkflowStatus",
        "FailureAction",
        "FailurePolicyPort",
        "ForecastingFailureSelectionPort",
        "ForecastingAttemptNumberPort",
        "StrictSingleForecastingFailureSelector",
        "ForecastingFailureFact",
        "ForecastingAgentFailure",
        "ForecastingPlan",
        "ForecastingSuccess",
        "ForecastingExecutionPort",
        "ForecastingWorkflowContextPort",
        "ParallelForecastingExecutionService",
        "ForecastingWorkflowStep",
        "ParallelIngestionFailureContextPreparationService",
        "ParallelIngestionFailureContextResolutionService",
        "ParallelIngestionFailureFact",
        "ConsumerLoadForecastAgent",
        "DAMPriceForecastAgent",
        "StateGraph",
        "CompiledStateGraph",
        "Send",
        "RetryPolicy",
        "AdapterDiagnostic",
        "AgentPort",
        "AgentName",
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
        "MutableMapping",
        "Callable",
        "Protocol",
        "ABC",
        "Exception",
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
        "ForecastingFailureSelectionPort",
        "ForecastingAttemptNumberPort",
        "StrictSingleForecastingFailureSelector",
        "ForecastingFailureFact",
        "ForecastingAgentFailure",
        "classify_forecasting_agent_failure",
        "fail_after_forecasting",
        "advance_after_forecasting",
        "ParallelForecastingExecutionService",
        "ForecastingWorkflowStep",
        "ParallelIngestionFailureContextPreparationService",
        "ParallelIngestionFailureContextResolutionService",
        "ParallelIngestionFailureFact",
        "build_parallel_ingestion_failure_policy_context",
        "execute_parallel_ingestion_failure_action",
        "ConsumerLoadForecastAgent",
        "DAMPriceForecastAgent",
        "CONSUMER_LOAD_FORECAST",
        "DAM_PRICE_FORECAST",
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
        "Path",
        "open",
        "environ",
        "getenv",
        "__cause__",
        "__context__",
        "__traceback__",
        "exceptions",
        "split",
        "subgroup",
        "derive",
        "select",
        "get_attempt_number",
        "attempt_number",
    }
)

FORBIDDEN_IMPLEMENTATION_NAMES = frozenset(
    {
        "FirstFailureWinsSelector",
        "LastFailureWinsSelector",
        "PriorityFailureSelector",
        "AgentPrioritySelector",
        "ErrorCodePrioritySelector",
        "DefaultForecastingFailureSelector",
        "ForecastingFailureSelector",
        "FailureFactSelector",
        "StrictSingleForecastingFailureSelector",
        "InitialForecastingAttemptNumberSource",
        "InMemoryForecastingAttemptNumber",
        "RedisForecastingAttemptNumber",
        "PostgresForecastingAttemptNumber",
        "DefaultForecastingAttemptNumber",
        "ForecastingAttemptTracker",
        "AttemptNumberCounter",
        "ExceptionGroupPipeline",
        "FailurePreparationPipeline",
        "GenericExceptionGroupPipeline",
        "ParallelIngestionFailureContextPreparationService",
        "ParallelIngestionFailureContextResolutionService",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.orchestration.failure_policy",
        "energy_trading.application.orchestration.forecasting_exception_group",
        "energy_trading.application.orchestration.forecasting_failure_classification",
        "energy_trading.application.orchestration.forecasting_failure_context_resolution",
        "energy_trading.application.orchestration.state",
    }
)

ALLOWED_INIT_ANNOTATIONS = {
    "context_resolution_service": "ForecastingFailureContextResolutionService",
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
    CONTEXT_BUILDER_MODULE,
    FAILURE_TRANSITION_MODULE,
    SUCCESS_TRANSITION_MODULE,
    WORKFLOW_CONTEXT_MODULE,
    PLAN_MODULE,
    STATE_MODULE,
    SELECTION_MODULE,
    ATTEMPT_NUMBER_MODULE,
    SELECTOR_MODULE,
    RESOLUTION_MODULE,
    PHASE2_PREPARATION_MODULE,
    PHASE2_RESOLUTION_MODULE,
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


def _prepare_method(class_def: ast.ClassDef) -> ast.AsyncFunctionDef:
    for node in class_def.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "prepare":
            return node
    msg = "async method 'prepare' not found on ForecastingFailureContextPreparationService"
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


def test_preparation_module_belongs_to_application_orchestration() -> None:
    assert PREPARATION_MODULE.parent == ORCHESTRATION_ROOT
    assert PREPARATION_MODULE.exists()


def test_preparation_service_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(PREPARATION_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(PREPARATION_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(PREPARATION_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(PREPARATION_MODULE)
    assert "FailurePolicyContext" in names
    assert "WorkflowPhase" in names
    assert "extract_forecasting_agent_failures" in names
    assert "classify_forecasting_agent_failures" in names
    assert "ForecastingFailureContextResolutionService" in names
    assert "FailurePolicyPort" not in names
    assert "FailureAction" not in names
    assert "WorkflowState" not in names
    assert "WorkflowStatus" not in names
    assert "ForecastingFailureSelectionPort" not in names
    assert "ForecastingAttemptNumberPort" not in names
    assert "StrictSingleForecastingFailureSelector" not in names
    assert "ForecastingFailureFact" not in names
    assert "ForecastingAgentFailure" not in names
    assert "classify_forecasting_agent_failure" not in names
    assert "ParallelForecastingExecutionService" not in names
    assert "ForecastingWorkflowStep" not in names
    assert "fail_after_forecasting" not in names
    assert "ParallelIngestionFailureContextPreparationService" not in names
    assert "ParallelIngestionFailureContextResolutionService" not in names
    assert "ParallelIngestionFailureFact" not in names
    assert "build_forecasting_failure_policy_context" not in names


def test_preparation_module_exposes_exactly_one_production_class() -> None:
    assert _public_function_defs(PREPARATION_MODULE) == []
    assert _module_class_names(PREPARATION_MODULE) == [
        "ForecastingFailureContextPreparationService"
    ]
    class_def = _class_def(PREPARATION_MODULE, "ForecastingFailureContextPreparationService")
    assert _base_names(class_def) == set()
    production_classes: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.ClassDef)
                and node.name == "ForecastingFailureContextPreparationService"
            ):
                production_classes.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_classes == [
        "energy_trading/application/orchestration/forecasting_failure_context_preparation.py"
    ]
    leaked_implementations = sorted(
        name
        for name in _module_class_names(PREPARATION_MODULE)
        if name in FORBIDDEN_IMPLEMENTATION_NAMES
    )
    assert leaked_implementations == []
    tree = ast.parse(
        PREPARATION_MODULE.read_text(encoding="utf-8"), filename=str(PREPARATION_MODULE)
    )
    protocols = [
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and any(
            (isinstance(base, ast.Name) and base.id == "Protocol")
            or (isinstance(base, ast.Attribute) and base.attr == "Protocol")
            for base in node.bases
        )
    ]
    assert protocols == []
    dataclasses = [
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and any(
            (isinstance(decorator, ast.Name) and decorator.id == "dataclass")
            or (isinstance(decorator, ast.Attribute) and decorator.attr == "dataclass")
            or (
                isinstance(decorator, ast.Call)
                and (
                    (isinstance(decorator.func, ast.Name) and decorator.func.id == "dataclass")
                    or (
                        isinstance(decorator.func, ast.Attribute)
                        and decorator.func.attr == "dataclass"
                    )
                )
            )
            for decorator in node.decorator_list
        )
    ]
    assert dataclasses == []


def test_constructor_injects_exactly_the_published_resolution_service() -> None:
    class_def = _class_def(PREPARATION_MODULE, "ForecastingFailureContextPreparationService")
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert tuple(arg.arg for arg in init_fn.args.args) == (
        "self",
        "context_resolution_service",
    )
    assert init_fn.args.posonlyargs == []
    assert init_fn.args.kwonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    assert _init_arg_annotations(class_def) == ALLOWED_INIT_ANNOTATIONS
    constructed = [_call_name(node) for node in ast.walk(init_fn) if isinstance(node, ast.Call)]
    assert "StrictSingleForecastingFailureSelector" not in constructed
    assert "ForecastingFailureContextResolutionService" not in constructed
    assert "ForecastingFailureSelectionPort" not in constructed
    assert "ForecastingAttemptNumberPort" not in constructed


def test_prepare_signature_is_async_keyword_only_workflow_phase_and_error() -> None:
    class_def = _class_def(PREPARATION_MODULE, "ForecastingFailureContextPreparationService")
    prepare_fn = _prepare_method(class_def)
    assert tuple(arg.arg for arg in prepare_fn.args.args) == ("self",)
    assert prepare_fn.args.posonlyargs == []
    assert tuple(arg.arg for arg in prepare_fn.args.kwonlyargs) == (
        "workflow_id",
        "phase",
        "error",
    )
    assert prepare_fn.args.vararg is None
    assert prepare_fn.args.kwarg is None
    assert ast.unparse(prepare_fn.args.kwonlyargs[0].annotation) == "str"
    assert ast.unparse(prepare_fn.args.kwonlyargs[1].annotation) == "WorkflowPhase"
    assert ast.unparse(prepare_fn.args.kwonlyargs[2].annotation) == "BaseException"
    assert ast.unparse(prepare_fn.returns) == "FailurePolicyContext"
    assert prepare_fn.args.kw_defaults == [None, None, None]
    public_methods = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]
    assert public_methods == ["prepare"]


def test_prepare_delegates_once_in_order_without_duplicate_interpretation() -> None:
    class_def = _class_def(PREPARATION_MODULE, "ForecastingFailureContextPreparationService")
    prepare_fn = _prepare_method(class_def)
    control = [
        type(node).__name__
        for node in ast.walk(prepare_fn)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try, ast.With))
    ]
    assert control == []
    except_handlers = [node for node in ast.walk(prepare_fn) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    arithmetic = [
        type(node).__name__
        for stmt in prepare_fn.body
        for node in ast.walk(stmt)
        if isinstance(node, (ast.BinOp, ast.UnaryOp, ast.AugAssign))
    ]
    assert arithmetic == []
    comprehensions = [
        type(node).__name__
        for node in ast.walk(prepare_fn)
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))
    ]
    assert comprehensions == []
    extract_calls = 0
    classify_calls = 0
    resolve_calls = 0
    fact_calls = 0
    context_calls = 0
    for node in ast.walk(prepare_fn):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name == "extract_forecasting_agent_failures":
            extract_calls += 1
            assert len(node.args) == 1
            assert node.keywords == []
            assert isinstance(node.args[0], ast.Name)
            assert node.args[0].id == "error"
        if name == "classify_forecasting_agent_failures":
            classify_calls += 1
            assert len(node.args) == 1
            assert node.keywords == []
            assert isinstance(node.args[0], ast.Name)
        if name == "resolve":
            resolve_calls += 1
            assert node.args == []
            keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in node.keywords}
            assert keywords["workflow_id"] == "workflow_id"
            assert keywords["phase"] == "phase"
            assert set(keywords) == {"workflow_id", "phase", "facts"}
            facts_expr = next(keyword.value for keyword in node.keywords if keyword.arg == "facts")
            assert isinstance(facts_expr, ast.Name)
        if name == "ForecastingFailureFact":
            fact_calls += 1
        if name == "FailurePolicyContext":
            context_calls += 1
    assert extract_calls == 1
    assert classify_calls == 1
    assert resolve_calls == 1
    assert fact_calls == 0
    assert context_calls == 0
    statements = [node for node in prepare_fn.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 3
    first, second, third = statements
    assert isinstance(first, ast.Assign)
    assert isinstance(first.value, ast.Call)
    assert _call_name(first.value) == "extract_forecasting_agent_failures"
    assert isinstance(second, ast.Assign)
    assert isinstance(second.value, ast.Call)
    assert _call_name(second.value) == "classify_forecasting_agent_failures"
    assert isinstance(third, ast.Return)
    assert isinstance(third.value, ast.Await)
    assert isinstance(third.value.value, ast.Call)
    assert _call_name(third.value.value) == "resolve"
    indexed = [
        ast.unparse(node)
        for node in ast.walk(prepare_fn)
        if isinstance(node, ast.Subscript) and _is_positional_index(node.slice)
    ]
    assert indexed == []
    identifiers = _identifier_names(PREPARATION_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(PREPARATION_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    source = PREPARATION_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "FailurePolicyPort" not in source
    assert "FailureAction" not in source
    assert "WorkflowState" not in source
    assert "WorkflowStatus" not in source
    assert "StrictSingleForecastingFailureSelector" not in source
    assert "ForecastingFailureSelectionPort" not in source
    assert "ForecastingAttemptNumberPort" not in source
    assert "fail_after_forecasting" not in source
    assert "ParallelForecastingExecutionService" not in source
    assert "ForecastingWorkflowStep" not in source
    assert "ParallelIngestionFailureContextPreparationService" not in source
    assert "ParallelIngestionFailureContextResolutionService" not in source
    assert "ParallelIngestionFailureFact" not in source
    assert "time.sleep" not in lowered
    assert "asyncio.sleep" not in lowered
    assert "asyncio.taskgroup" not in lowered
    assert "sorted(" not in source
    assert ".sort(" not in source
    assert "increment" not in lowered
    assert "FailurePolicyContext(" not in source
    assert "ForecastingFailureFact(" not in source
    assert ".exceptions" not in source
    assert "__cause__" not in source
    assert "return 1" not in source
    assert "attempt_number" not in source


def test_graph_policy_and_lower_layers_remain_unwired_to_the_preparation_service() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        assert "ForecastingFailureContextPreparationService" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.forecasting_failure_context_preparation"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "ForecastingFailureContextPreparationService" not in source
        assert "forecasting_failure_context_preparation" not in source


def test_workflow_state_shape_is_unchanged_by_context_preparation() -> None:
    tree = ast.parse(STATE_MODULE.read_text(encoding="utf-8"), filename=str(STATE_MODULE))
    fields: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "WorkflowState":
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.append(item.target.id)
    assert tuple(fields) == (
        "workflow_id",
        "portfolio_id",
        "delivery_date",
        "correlation_id",
        "phase",
        "status",
        "diagnostics",
    )


def test_api_composition_does_not_import_or_construct_the_preparation_service() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.forecasting_failure_context_preparation",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "ForecastingFailureContextPreparationService" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "forecastingfailurecontextpreparationservice" not in app_source
    assert "forecasting_failure_context_preparation" not in app_source
