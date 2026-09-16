"""Parallel forecasting executor stays application-owned and LangGraph-free."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_http_api_import_violations,
    collect_import_violations,
    http_transport_api_paths,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
EXECUTOR_MODULE = ORCHESTRATION_ROOT / "forecasting_executor.py"
EXECUTION_PORT_MODULE = ORCHESTRATION_ROOT / "forecasting_execution.py"
PLAN_MODULE = ORCHESTRATION_ROOT / "forecasting_plan.py"
SUCCESS_MODULE = ORCHESTRATION_ROOT / "forecasting_success.py"
CONTEXT_MODULE = ORCHESTRATION_ROOT / "forecasting_context.py"
WORKFLOW_MODULE = ORCHESTRATION_ROOT / "forecasting_workflow.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.orchestration.state",
    "energy_trading.application.orchestration.forecasting_context",
    "energy_trading.application.orchestration.forecasting_workflow",
    "energy_trading.application.orchestration.forecasting_transition",
    "energy_trading.application.orchestration.forecasting_failure_transition",
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
    "concurrent.futures",
    "multiprocessing",
    "threading",
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
        "Exception",
        "BaseException",
        "ExceptionGroup",
        "Optional",
        "WorkflowState",
        "ForecastingWorkflowContextPort",
        "InMemoryForecastingWorkflowContext",
        "FailurePolicyPort",
        "FailurePolicyContext",
        "FailureAction",
        "AgentPort",
        "AgentName",
        "StateGraph",
        "CompiledStateGraph",
        "Send",
        "RetryPolicy",
        "ConsumerLoadForecastModelPort",
        "DAMPriceForecastModelPort",
        "PreviousDayPersistenceConsumerLoadForecastModel",
        "Lag24h168hOLSConsumerLoadForecastModel",
        "AgentFactory",
        "AgentRegistry",
        "ServiceLocator",
        "Repository",
        "UnitOfWork",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "asyncio",
        "energy_trading.application.agents.consumer_load_forecast",
        "energy_trading.application.agents.dam_price_forecast",
        "energy_trading.application.orchestration.forecasting_plan",
        "energy_trading.application.orchestration.forecasting_success",
    }
)

ALLOWED_INIT_ANNOTATIONS = {
    "consumer_load_forecast": "ConsumerLoadForecastAgent",
    "dam_price_forecast": "DAMPriceForecastAgent",
}

FORBIDDEN_CONCURRENCY_TOKENS = (
    "asyncio.gather",
    "asyncio.wait",
    "as_completed",
    "run_in_executor",
    "to_thread",
    "ThreadPoolExecutor",
    "ProcessPoolExecutor",
)

FORBIDDEN_SELECTION_IDENTIFIERS = frozenset(
    {
        "champion",
        "winner",
        "best",
        "selected",
        "ranking",
        "fallback",
        "registry",
        "mae",
        "score",
        "compare",
    }
)

WORKFLOW_STATE_FIELDS = (
    "workflow_id",
    "portfolio_id",
    "delivery_date",
    "correlation_id",
    "phase",
    "status",
    "diagnostics",
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


def _annassign_field_names(path: Path, class_name: str) -> tuple[str, ...]:
    class_def = _class_def(path, class_name)
    names: list[str] = []
    for item in class_def.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            names.append(item.target.id)
    return tuple(names)


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


def test_executor_lives_in_application_orchestration() -> None:
    assert EXECUTOR_MODULE.parent == ORCHESTRATION_ROOT
    assert EXECUTOR_MODULE.name == "forecasting_executor.py"
    assert EXECUTOR_MODULE.exists()


def test_executor_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(EXECUTOR_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(EXECUTOR_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(EXECUTOR_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(EXECUTOR_MODULE)
    assert "ConsumerLoadForecastAgent" in names
    assert "DAMPriceForecastAgent" in names
    assert "ForecastingPlan" in names
    assert "ForecastingSuccess" in names
    assert "ForecastingExecutionPort" not in names
    assert "ForecastingWorkflowContextPort" not in names
    assert "WorkflowState" not in names


def test_executor_module_exposes_exactly_one_concrete_class() -> None:
    assert _module_class_names(EXECUTOR_MODULE) == ["ParallelForecastingExecutionService"]
    production_executors: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if (
                isinstance(node, ast.ClassDef)
                and node.name == "ParallelForecastingExecutionService"
            ):
                production_executors.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_executors == [
        "energy_trading/application/orchestration/forecasting_executor.py"
    ]


def test_executor_is_nongeneric_and_does_not_inherit_protocol() -> None:
    class_def = _class_def(EXECUTOR_MODULE, "ParallelForecastingExecutionService")
    assert list(class_def.type_params) == []
    bases = _base_names(class_def)
    assert "Protocol" not in bases
    assert "ABC" not in bases
    assert "Generic" not in bases
    assert "ForecastingExecutionPort" not in bases
    source = EXECUTOR_MODULE.read_text(encoding="utf-8")
    assert "abstractmethod" not in source
    assert "registry" not in source.lower()
    assert "factory" not in source.lower()


def test_executor_constructor_owns_exactly_the_two_forecast_agents() -> None:
    class_def = _class_def(EXECUTOR_MODULE, "ParallelForecastingExecutionService")
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    arg_names = tuple(arg.arg for arg in init_fn.args.args if arg.arg != "self")
    assert arg_names == ("consumer_load_forecast", "dam_price_forecast")
    assert init_fn.args.kwonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    assert _init_arg_annotations(class_def) == ALLOWED_INIT_ANNOTATIONS


def test_executor_public_operation_is_async_keyword_only_execute() -> None:
    class_def = _class_def(EXECUTOR_MODULE, "ParallelForecastingExecutionService")
    defined = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert defined == ["__init__", "execute"]
    execute_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "execute"
    )
    assert tuple(arg.arg for arg in execute_fn.args.args) == ("self",)
    assert execute_fn.args.posonlyargs == []
    assert tuple(arg.arg for arg in execute_fn.args.kwonlyargs) == ("plan",)
    assert execute_fn.args.vararg is None
    assert execute_fn.args.kwarg is None
    assert execute_fn.args.kw_defaults == [None]
    assert async_function_arg_names(EXECUTOR_MODULE, "execute") == ("self",)
    assert execute_fn.args.kwonlyargs[0].annotation is not None
    assert execute_fn.returns is not None
    assert ast.unparse(execute_fn.args.kwonlyargs[0].annotation) == "ForecastingPlan"
    assert ast.unparse(execute_fn.returns) == "ForecastingSuccess"


def test_executor_uses_taskgroup_and_not_gather() -> None:
    source = EXECUTOR_MODULE.read_text(encoding="utf-8")
    identifiers = _identifier_names(EXECUTOR_MODULE)
    assert "TaskGroup" in identifiers
    assert "create_task" in identifiers
    for token in FORBIDDEN_CONCURRENCY_TOKENS:
        assert token not in source
    tree = ast.parse(source, filename=str(EXECUTOR_MODULE))
    create_task_calls = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "create_task":
            create_task_calls += 1
    assert create_task_calls == 2
    except_handlers = [node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    assert "except*" not in source
    assert "try:" not in source


def test_executor_does_not_own_context_or_workflow_state() -> None:
    identifiers = _identifier_names(EXECUTOR_MODULE)
    assert "ForecastingWorkflowContextPort" not in identifiers
    assert "InMemoryForecastingWorkflowContext" not in identifiers
    assert "resolve_plan" not in identifiers
    assert "record_success" not in identifiers
    assert "WorkflowState" not in identifiers
    assert "advance_after_forecasting" not in identifiers
    assert "fail_after_forecasting" not in identifiers
    source = EXECUTOR_MODULE.read_text(encoding="utf-8")
    assert "resolve_plan" not in source
    assert "record_success" not in source


def test_executor_does_not_import_concrete_ml_or_selection_terms() -> None:
    identifiers = _identifier_names(EXECUTOR_MODULE)
    assert "PreviousDayPersistenceConsumerLoadForecastModel" not in identifiers
    assert "Lag24h168hOLSConsumerLoadForecastModel" not in identifiers
    leaked_selection = sorted(
        name for name in identifiers if name in FORBIDDEN_SELECTION_IDENTIFIERS
    )
    assert leaked_selection == []
    source = EXECUTOR_MODULE.read_text(encoding="utf-8").lower()
    assert "previousdaypersistence" not in source.replace("_", "")
    assert "lag24h168hols" not in source.replace("_", "")
    assert "champion" not in source
    assert "fallback" not in source
    ml_vendor_prefixes = (
        "lightgbm",
        "xgboost",
        "sklearn",
        "numpy",
        "pandas",
        "energy_trading.ml",
    )
    application_leaks = collect_import_violations(APPLICATION_ROOT, ml_vendor_prefixes)
    domain_leaks = collect_import_violations(PRODUCTION_ROOT / "domain", ml_vendor_prefixes)
    assert application_leaks == []
    assert domain_leaks == []


def test_executor_public_contract_excludes_payload_and_runtime_types() -> None:
    names = annotation_type_names(EXECUTOR_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    identifiers = _identifier_names(EXECUTOR_MODULE)
    assert "Any" not in identifiers
    assert "dict" not in identifiers
    assert "Mapping" not in identifiers
    assert "AgentPort" not in identifiers
    assert "FailurePolicyPort" not in identifiers
    assert "WorkflowState" not in identifiers
    assert "ExceptionGroup" not in identifiers
    source = EXECUTOR_MODULE.read_text(encoding="utf-8")
    assert "langgraph" not in source.lower()
    assert "langchain" not in source.lower()
    assert "fastapi" not in source.lower()
    assert "redis" not in source.lower()
    assert "postgres" not in source.lower()
    assert "qdrant" not in source.lower()


def test_published_plan_success_and_port_modules_remain_unchanged() -> None:
    assert _module_class_names(EXECUTION_PORT_MODULE) == ["ForecastingExecutionPort"]
    assert _module_class_names(PLAN_MODULE) == ["ForecastingPlan"]
    assert _module_class_names(SUCCESS_MODULE) == ["ForecastingSuccess"]
    for path in (
        EXECUTION_PORT_MODULE,
        PLAN_MODULE,
        SUCCESS_MODULE,
        CONTEXT_MODULE,
        WORKFLOW_MODULE,
    ):
        names = imported_names(path)
        assert "ParallelForecastingExecutionService" not in names
        modules = imported_modules(path)
        assert "energy_trading.application.orchestration.forecasting_executor" not in modules
        source = path.read_text(encoding="utf-8")
        assert "ParallelForecastingExecutionService" not in source


def test_workflow_state_shape_is_unchanged_by_the_executor() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert "ParallelForecastingExecutionService" not in names
    modules = imported_modules(STATE_MODULE)
    assert "energy_trading.application.orchestration.forecasting_executor" not in modules


def test_graph_remains_unwired_to_the_executor() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "ParallelForecastingExecutionService" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "energy_trading.application.orchestration.forecasting_executor" not in modules
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "ParallelForecastingExecutionService" not in source
    assert "forecasting_executor" not in source


def test_api_composition_does_not_import_or_construct_executor() -> None:
    forbidden_wiring = ("energy_trading.application.orchestration.forecasting_executor",)
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "ParallelForecastingExecutionService" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "parallelforecastingexecutionservice" not in app_source
    assert "forecasting_executor" not in app_source
