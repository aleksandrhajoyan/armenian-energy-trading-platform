"""Strict single-failure Phase 3 selector stays application-owned and fail-closed."""

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
SELECTOR_MODULE = ORCHESTRATION_ROOT / "forecasting_strict_single_failure_selector.py"
SELECTION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_selection.py"
FACT_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_fact.py"
CLASSIFICATION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_classification.py"
AGENT_FAILURE_MODULE = ORCHESTRATION_ROOT / "forecasting_agent_failure.py"
EXTRACTION_MODULE = ORCHESTRATION_ROOT / "forecasting_exception_group.py"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
FAILURE_TRANSITION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_transition.py"
SUCCESS_TRANSITION_MODULE = ORCHESTRATION_ROOT / "forecasting_transition.py"
WORKFLOW_MODULE = ORCHESTRATION_ROOT / "forecasting_workflow.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
EXECUTOR_MODULE = ORCHESTRATION_ROOT / "forecasting_executor.py"
EXECUTION_MODULE = ORCHESTRATION_ROOT / "forecasting_execution.py"
WORKFLOW_CONTEXT_MODULE = ORCHESTRATION_ROOT / "forecasting_context.py"
PLAN_MODULE = ORCHESTRATION_ROOT / "forecasting_plan.py"
SUCCESS_MODULE = ORCHESTRATION_ROOT / "forecasting_success.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.orchestration.state",
    "energy_trading.application.orchestration.failure_policy",
    "energy_trading.application.orchestration.forecasting_agent_failure",
    "energy_trading.application.orchestration.forecasting_exception_group",
    "energy_trading.application.orchestration.forecasting_failure_classification",
    "energy_trading.application.orchestration.forecasting_failure_selection",
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
        "TracebackType",
        "WorkflowState",
        "WorkflowPhase",
        "WorkflowStatus",
        "FailureAction",
        "FailurePolicyContext",
        "FailurePolicyPort",
        "ForecastingFailureSelectionPort",
        "ForecastingAgentFailure",
        "ForecastingPlan",
        "ForecastingSuccess",
        "ForecastingExecutionPort",
        "ForecastingWorkflowContextPort",
        "ParallelForecastingExecutionService",
        "ForecastingWorkflowStep",
        "ConsumerLoadForecastAgent",
        "DAMPriceForecastAgent",
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
        "Counter",
        "Protocol",
        "ABC",
        "traceback",
        "exc_info",
        "ApplicationError",
        "ExceptionGroup",
        "BaseExceptionGroup",
        "WorkflowState",
        "WorkflowPhase",
        "WorkflowStatus",
        "FailureAction",
        "FailurePolicyContext",
        "FailurePolicyPort",
        "fail_after_forecasting",
        "advance_after_forecasting",
        "extract_forecasting_agent_failures",
        "classify_forecasting_agent_failure",
        "classify_forecasting_agent_failures",
        "ForecastingAgentFailure",
        "ParallelForecastingExecutionService",
        "ForecastingWorkflowStep",
        "registry",
        "factory",
        "tenacity",
        "backoff",
        "asyncio",
        "TaskGroup",
        "sleep",
        "retry",
        "fallback",
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
        "attempt_number",
        "diagnostics",
        "error_code",
        "AgentName",
        "CONSUMER_LOAD_FORECAST",
        "DAM_PRICE_FORECAST",
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
        "DefaultForecastingFailureSelector",
        "ForecastingFailureSelector",
        "FailureFactSelector",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.errors",
        "energy_trading.application.orchestration.forecasting_failure_fact",
    }
)

UNWIRED_MODULES = (
    GRAPH_MODULE,
    WORKFLOW_MODULE,
    EXECUTOR_MODULE,
    EXECUTION_MODULE,
    EXTRACTION_MODULE,
    CLASSIFICATION_MODULE,
    FACT_MODULE,
    AGENT_FAILURE_MODULE,
    FAILURE_POLICY_MODULE,
    FAILURE_TRANSITION_MODULE,
    SUCCESS_TRANSITION_MODULE,
    WORKFLOW_CONTEXT_MODULE,
    PLAN_MODULE,
    SUCCESS_MODULE,
    STATE_MODULE,
    SELECTION_MODULE,
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


def _sync_method(class_def: ast.ClassDef, method_name: str) -> ast.FunctionDef:
    for node in class_def.body:
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return node
    msg = f"method {method_name!r} not found on {class_def.name}"
    raise AssertionError(msg)


def _is_len_facts_one_compare(node: ast.Compare) -> bool:
    if len(node.ops) != 1 or len(node.comparators) != 1:
        return False
    if not isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
        return False
    comparator = node.comparators[0]
    if not isinstance(comparator, ast.Constant) or comparator.value != 1:
        return False
    call = node.left
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
        return False
    if call.func.id != "len" or len(call.args) != 1:
        return False
    argument = call.args[0]
    return isinstance(argument, ast.Name) and argument.id == "facts"


def _is_facts_zero_index(node: ast.Subscript) -> bool:
    if not isinstance(node.value, ast.Name) or node.value.id != "facts":
        return False
    slice_node = node.slice
    return isinstance(slice_node, ast.Constant) and slice_node.value == 0


def test_selector_module_belongs_to_application_orchestration() -> None:
    assert SELECTOR_MODULE.parent == ORCHESTRATION_ROOT
    assert SELECTOR_MODULE.exists()


def test_selector_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(SELECTOR_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(SELECTOR_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(SELECTOR_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(SELECTOR_MODULE)
    assert "InvalidRequestError" in names
    assert "ForecastingFailureFact" in names
    assert "ForecastingFailureSelectionPort" not in names
    assert "Protocol" not in names
    assert "WorkflowState" not in names
    assert "FailurePolicyContext" not in names
    assert "FailurePolicyPort" not in names
    assert "FailureAction" not in names
    assert "ForecastingAgentFailure" not in names
    assert "extract_forecasting_agent_failures" not in names
    assert "classify_forecasting_agent_failure" not in names
    assert "classify_forecasting_agent_failures" not in names
    assert "fail_after_forecasting" not in names
    assert "AgentName" not in names


def test_selector_module_exposes_exactly_one_production_class() -> None:
    assert _public_function_defs(SELECTOR_MODULE) == []
    assert _module_class_names(SELECTOR_MODULE) == ["StrictSingleForecastingFailureSelector"]
    class_def = _class_def(SELECTOR_MODULE, "StrictSingleForecastingFailureSelector")
    assert _base_names(class_def) == set()
    production_classes: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.ClassDef)
                and node.name == "StrictSingleForecastingFailureSelector"
            ):
                production_classes.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_classes == [
        "energy_trading/application/orchestration/forecasting_strict_single_failure_selector.py"
    ]
    leaked_implementations = sorted(
        name
        for name in _module_class_names(SELECTOR_MODULE)
        if name in FORBIDDEN_IMPLEMENTATION_NAMES
    )
    assert leaked_implementations == []


def test_select_is_the_only_public_operation() -> None:
    class_def = _class_def(SELECTOR_MODULE, "StrictSingleForecastingFailureSelector")
    defined_nodes = [
        node for node in class_def.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert [node.name for node in defined_nodes] == ["select"]
    assert all(isinstance(node, ast.FunctionDef) for node in defined_nodes)
    select_fn = _sync_method(class_def, "select")
    assert tuple(arg.arg for arg in select_fn.args.args) == ("self", "facts")
    assert select_fn.args.posonlyargs == []
    assert select_fn.args.kwonlyargs == []
    assert select_fn.args.vararg is None
    assert select_fn.args.kwarg is None
    assert ast.unparse(select_fn.args.args[1].annotation) == ("tuple[ForecastingFailureFact, ...]")
    assert ast.unparse(select_fn.returns) == "ForecastingFailureFact"


def test_select_guards_cardinality_before_returning_the_unique_fact() -> None:
    class_def = _class_def(SELECTOR_MODULE, "StrictSingleForecastingFailureSelector")
    select_fn = _sync_method(class_def, "select")
    cardinality_guards = [
        node
        for node in ast.walk(select_fn)
        if isinstance(node, ast.Compare) and _is_len_facts_one_compare(node)
    ]
    assert len(cardinality_guards) == 1
    unique_returns = [
        node
        for node in ast.walk(select_fn)
        if isinstance(node, ast.Return)
        and isinstance(node.value, ast.Subscript)
        and _is_facts_zero_index(node.value)
    ]
    assert len(unique_returns) == 1
    negative_indexes = [
        ast.unparse(node)
        for node in ast.walk(select_fn)
        if isinstance(node, ast.Subscript)
        and isinstance(node.slice, ast.UnaryOp)
        and isinstance(node.slice.op, ast.USub)
    ]
    assert negative_indexes == []
    raises = [
        node
        for node in ast.walk(select_fn)
        if isinstance(node, ast.Raise)
        and isinstance(node.exc, ast.Call)
        and isinstance(node.exc.func, ast.Name)
        and node.exc.func.id == "InvalidRequestError"
    ]
    assert len(raises) == 1
    control = [
        type(node).__name__
        for node in ast.walk(select_fn)
        if isinstance(node, (ast.For, ast.While, ast.Match, ast.Try, ast.With, ast.IfExp))
    ]
    assert control == []
    identifiers = _identifier_names(SELECTOR_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(SELECTOR_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    source = SELECTOR_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "sorted(" not in source
    assert ".sort(" not in source
    assert "first failure" not in lowered
    assert "last failure" not in lowered
    assert "deduplicat" not in lowered
    assert "WorkflowState" not in source
    assert "FailurePolicyContext" not in source
    assert ".error_code" not in source
    assert "CONSUMER_LOAD_FORECAST" not in source
    assert "DAM_PRICE_FORECAST" not in source
    assert "ExceptionGroup" not in source
    assert "BaseExceptionGroup" not in source
    assert "__cause__" not in source


def test_graph_policy_and_lower_layers_remain_unwired_to_the_selector() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        assert "StrictSingleForecastingFailureSelector" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.forecasting_strict_single_failure_selector"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "StrictSingleForecastingFailureSelector" not in source
        assert "forecasting_strict_single_failure_selector" not in source


def test_selection_port_remains_implementation_neutral() -> None:
    names = imported_names(SELECTION_MODULE)
    modules = imported_modules(SELECTION_MODULE)
    source = SELECTION_MODULE.read_text(encoding="utf-8")
    assert "StrictSingleForecastingFailureSelector" not in names
    assert (
        "energy_trading.application.orchestration.forecasting_strict_single_failure_selector"
        not in modules
    )
    assert "StrictSingleForecastingFailureSelector" not in source
    assert "forecasting_strict_single_failure_selector" not in source
    assert "InvalidRequestError" not in source


def test_api_composition_does_not_import_or_construct_the_selector() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.forecasting_strict_single_failure_selector",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "StrictSingleForecastingFailureSelector" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "strictsingleforecastingfailureselector" not in app_source
    assert "forecasting_strict_single_failure_selector" not in app_source
