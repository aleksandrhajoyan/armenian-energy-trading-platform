"""Prepared forecasting failure handling stays application-owned."""

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
HANDLING_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_handling.py"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
DECISION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_decision.py"
PREPARATION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_context_preparation.py"
RESOLUTION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_context_resolution.py"
ACTION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_action.py"
FAILURE_TRANSITION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_transition.py"
WORKFLOW_MODULE = ORCHESTRATION_ROOT / "forecasting_workflow.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
EXECUTOR_MODULE = ORCHESTRATION_ROOT / "forecasting_executor.py"
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
        "FailureAction",
        "FailurePolicyPort",
        "InitialForecastingFailurePolicy",
        "ForecastingFailureContextPreparationService",
        "ForecastingFailureContextResolutionService",
        "ForecastingFailureSelectionPort",
        "StrictSingleForecastingFailureSelector",
        "ForecastingAttemptNumberPort",
        "InitialForecastingAttemptNumberSource",
        "ForecastingFailureFact",
        "ForecastingAgentFailure",
        "ParallelForecastingExecutionService",
        "ForecastingWorkflowStep",
        "ParallelIngestionFailureHandlingService",
        "ParallelIngestionFailureDecisionService",
        "AdapterDiagnostic",
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
        "FailureAction",
        "FailurePolicyPort",
        "InitialForecastingFailurePolicy",
        "ForecastingFailureContextPreparationService",
        "ForecastingFailureContextResolutionService",
        "ForecastingFailureSelectionPort",
        "StrictSingleForecastingFailureSelector",
        "ForecastingAttemptNumberPort",
        "InitialForecastingAttemptNumberSource",
        "ForecastingFailureFact",
        "ForecastingAgentFailure",
        "ParallelForecastingExecutionService",
        "ForecastingWorkflowStep",
        "ParallelIngestionFailureHandlingService",
        "ParallelIngestionFailureDecisionService",
        "execute_parallel_ingestion_failure_action",
        "fail_after_forecasting",
        "build_forecasting_failure_policy_context",
        "replace",
        "AdapterDiagnostic",
        "registry",
        "factory",
        "StateMachine",
        "tenacity",
        "backoff",
        "asyncio",
        "TaskGroup",
        "create_task",
        "sleep",
        "wait",
        "WorkflowPhase",
        "WorkflowStatus",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.orchestration.failure_policy",
        "energy_trading.application.orchestration.forecasting_failure_action",
        "energy_trading.application.orchestration.forecasting_failure_decision",
        "energy_trading.application.orchestration.state",
    }
)

ALLOWED_INIT_ANNOTATIONS = {
    "decision_service": "ForecastingFailureDecisionService",
}

UNWIRED_MODULES = (
    GRAPH_MODULE,
    WORKFLOW_MODULE,
    EXECUTOR_MODULE,
    PREPARATION_MODULE,
    RESOLUTION_MODULE,
    FAILURE_POLICY_MODULE,
    DECISION_MODULE,
    ACTION_MODULE,
    FAILURE_TRANSITION_MODULE,
    STATE_MODULE,
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


def _public_function_defs(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node.name
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
    msg = "async method 'handle' not found on ForecastingFailureHandlingService"
    raise AssertionError(msg)


def _executable_statements(function: ast.AsyncFunctionDef) -> list[ast.stmt]:
    return [
        node
        for node in function.body
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))
    ]


def test_handling_service_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(HANDLING_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(HANDLING_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(HANDLING_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(HANDLING_MODULE)
    assert "FailurePolicyContext" in names
    assert "WorkflowState" in names
    assert "ForecastingFailureDecisionService" in names
    assert "execute_forecasting_failure_action" in names
    assert "FailurePolicyPort" not in names
    assert "FailureAction" not in names
    assert "fail_after_forecasting" not in names
    assert "InitialForecastingFailurePolicy" not in names
    assert "ParallelIngestionFailureHandlingService" not in names


def test_handling_service_module_exposes_exactly_one_production_class() -> None:
    assert _module_class_names(HANDLING_MODULE) == ["ForecastingFailureHandlingService"]
    assert _public_function_defs(HANDLING_MODULE) == []
    class_def = _class_def(HANDLING_MODULE, "ForecastingFailureHandlingService")
    assert _base_names(class_def) == set()
    assert class_def.decorator_list == []
    assert class_def.type_params == []
    production_classes: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if isinstance(node, ast.ClassDef) and node.name == "ForecastingFailureHandlingService":
                production_classes.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_classes == [
        "energy_trading/application/orchestration/forecasting_failure_handling.py"
    ]


def test_constructor_injects_exactly_the_published_decision_service() -> None:
    class_def = _class_def(HANDLING_MODULE, "ForecastingFailureHandlingService")
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert tuple(arg.arg for arg in init_fn.args.args) == ("self", "decision_service")
    assert init_fn.args.posonlyargs == []
    assert init_fn.args.kwonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    assert _init_arg_annotations(class_def) == ALLOWED_INIT_ANNOTATIONS


def test_handle_signature_is_async_keyword_only_state_and_context() -> None:
    class_def = _class_def(HANDLING_MODULE, "ForecastingFailureHandlingService")
    handle_fn = _handle_method(class_def)
    assert tuple(arg.arg for arg in handle_fn.args.args) == ("self",)
    assert handle_fn.args.posonlyargs == []
    assert tuple(arg.arg for arg in handle_fn.args.kwonlyargs) == ("state", "context")
    assert handle_fn.args.vararg is None
    assert handle_fn.args.kwarg is None
    assert ast.unparse(handle_fn.args.kwonlyargs[0].annotation) == "WorkflowState"
    assert ast.unparse(handle_fn.args.kwonlyargs[1].annotation) == "FailurePolicyContext"
    assert ast.unparse(handle_fn.returns) == "WorkflowState"
    assert handle_fn.args.kw_defaults == [None, None]
    public_methods = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]
    assert public_methods == ["handle"]


def test_handle_delegates_once_without_branching_or_transition_logic() -> None:
    class_def = _class_def(HANDLING_MODULE, "ForecastingFailureHandlingService")
    handle_fn = _handle_method(class_def)
    statements = _executable_statements(handle_fn)
    assert len(statements) == 2
    assert isinstance(statements[0], ast.Assign)
    assert [target.id for target in statements[0].targets if isinstance(target, ast.Name)] == [
        "action"
    ]
    assert isinstance(statements[0].value, ast.Await)
    assert isinstance(statements[1], ast.Return)
    control = [
        type(node).__name__
        for node in ast.walk(handle_fn)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try, ast.With))
    ]
    assert control == []
    except_handlers = [node for node in ast.walk(handle_fn) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    decide_calls = 0
    execute_calls = 0
    fail_calls = 0
    replace_calls = 0
    context_field_reads = 0
    for node in ast.walk(handle_fn):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "context" and node.attr in {
                "phase",
                "error_code",
                "attempt_number",
                "agent_name",
            }:
                context_field_reads += 1
            if node.value.id == "state" and node.attr in {
                "phase",
                "status",
                "diagnostics",
                "workflow_id",
            }:
                context_field_reads += 1
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name: str | None = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name == "decide":
            decide_calls += 1
            assert len(node.args) == 1
            assert isinstance(node.args[0], ast.Name)
            assert node.args[0].id == "context"
        if name == "execute_forecasting_failure_action":
            execute_calls += 1
            assert node.args == []
            keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in node.keywords}
            assert keywords == {"state": "state", "action": "action"}
        if name == "fail_after_forecasting":
            fail_calls += 1
        if name == "replace":
            replace_calls += 1
    assert decide_calls == 1
    assert execute_calls == 1
    assert fail_calls == 0
    assert replace_calls == 0
    assert context_field_reads == 0
    await_nodes = [node for node in ast.walk(handle_fn) if isinstance(node, ast.Await)]
    assert len(await_nodes) == 1
    identifiers = _identifier_names(HANDLING_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(HANDLING_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    source = HANDLING_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "fastapi" not in lowered
    assert "starlette" not in lowered
    assert "fail_after_forecasting" not in source
    assert "FailureAction.FAIL" not in source
    assert "FailureAction.RETRY" not in source
    assert "FailureAction.FALLBACK" not in source
    assert "FailurePolicyPort" not in source
    assert "InitialForecastingFailurePolicy" not in source
    assert "ParallelIngestionFailureHandlingService" not in source
    assert "execute_parallel_ingestion_failure_action" not in source
    assert "time.sleep" not in lowered
    assert "asyncio.sleep" not in lowered
    assert "asyncio.taskgroup" not in lowered


def test_graph_workflow_and_lower_layers_remain_unwired_to_the_handling_service() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        assert "ForecastingFailureHandlingService" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.forecasting_failure_handling" not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "ForecastingFailureHandlingService" not in source
        assert "forecasting_failure_handling" not in source


def test_workflow_state_shape_is_unchanged_by_the_handling_service() -> None:
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


def test_api_composition_does_not_import_or_construct_the_handling_service() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.forecasting_failure_handling",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "ForecastingFailureHandlingService" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "forecastingfailurehandlingservice" not in app_source
    assert "forecasting_failure_handling" not in app_source
