"""Forecasting execution port stays typed, application-only, and LangGraph-free."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_http_api_import_violations,
    collect_import_violations,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
EXECUTION_MODULE = ORCHESTRATION_ROOT / "forecasting_execution.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
API_ROOT = PRODUCTION_ROOT / "api"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
    "energy_trading.application.ports",
    "energy_trading.application.orchestration.state",
    "energy_trading.application.orchestration.graph",
    "energy_trading.domain.models.forecasting",
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
    "asyncio",
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
        "ApplicationError",
        "bytes",
        "bytearray",
        "Path",
        "DataFrame",
        "Request",
        "Response",
        "StateGraph",
        "CompiledStateGraph",
        "Send",
        "RetryPolicy",
        "WorkflowState",
        "FailurePolicyPort",
        "FailurePolicyContext",
        "AgentPort",
        "AgentName",
        "ConsumerLoadForecastAgent",
        "DAMPriceForecastAgent",
        "ConsumerLoadForecastModelPort",
        "DAMPriceForecastModelPort",
        "ConsumerLoadForecastModelRequest",
        "DAMPriceForecastModelRequest",
        "LoadForecastPoint",
        "PriceForecastPoint",
        "ForecastingResult",
        "ForecastingOutcome",
        "ModelPort",
        "MLPort",
        "ForecastModelPort",
        "ExecutionPort",
        "WorkflowExecutionPort",
        "ForecastExecutionPort",
        "Optional",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "typing",
        "energy_trading.application.orchestration.forecasting_plan",
        "energy_trading.application.orchestration.forecasting_success",
    }
)

MODULE_FORBIDDEN_CLASS_NAMES = frozenset(
    {
        "ForecastingExecutor",
        "ConcurrentForecastingExecutor",
        "SequentialForecastingExecutor",
        "ForecastingWorkflowContextPort",
        "ForecastingWorkflowStep",
        "ForecastingResult",
        "ForecastingOutcome",
        "ExecutionPort",
        "WorkflowExecutionPort",
        "ForecastExecutionPort",
        "ModelPort",
        "MLPort",
        "ForecastModelPort",
        "AgentFactory",
        "AgentRegistry",
        "ServiceLocator",
    }
)

GENERIC_EXECUTION_NAMES = frozenset(
    {
        "ExecutionPort",
        "WorkflowExecutionPort",
        "ForecastExecutionPort",
        "ModelPort",
        "MLPort",
        "ForecastModelPort",
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


def _annassign_field_names(path: Path, class_name: str) -> tuple[str, ...]:
    class_def = _class_def(path, class_name)
    names: list[str] = []
    for item in class_def.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            names.append(item.target.id)
    return tuple(names)


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


def _module_class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def test_forecasting_execution_lives_in_application_orchestration() -> None:
    assert EXECUTION_MODULE.is_relative_to(ORCHESTRATION_ROOT)
    assert EXECUTION_MODULE.name == "forecasting_execution.py"
    assert EXECUTION_MODULE.exists()


def test_forecasting_execution_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(EXECUTION_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(EXECUTION_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(EXECUTION_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []


def test_forecasting_execution_port_is_nongeneric_protocol_with_async_execute() -> None:
    class_def = _class_def(EXECUTION_MODULE, "ForecastingExecutionPort")
    bases = _base_names(class_def)
    assert "Protocol" in bases
    assert "ABC" not in bases
    assert list(class_def.type_params) == []
    source = EXECUTION_MODULE.read_text(encoding="utf-8")
    assert "abstractmethod" not in source
    assert "@runtime_checkable" not in source
    defined = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert defined == ["execute"]
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
    assert async_function_arg_names(EXECUTION_MODULE, "execute") == ("self",)
    assert execute_fn.args.kwonlyargs[0].annotation is not None
    assert execute_fn.returns is not None
    assert ast.unparse(execute_fn.args.kwonlyargs[0].annotation) == "ForecastingPlan"
    assert ast.unparse(execute_fn.returns) == "ForecastingSuccess"


def test_forecasting_execution_module_exposes_only_the_execution_port() -> None:
    class_names = _module_class_names(EXECUTION_MODULE)
    assert class_names == ["ForecastingExecutionPort"]
    leaked_classes = sorted(name for name in class_names if name in MODULE_FORBIDDEN_CLASS_NAMES)
    assert leaked_classes == []
    identifiers = _identifier_names(EXECUTION_MODULE)
    leaked_forbidden = sorted(name for name in identifiers if name in MODULE_FORBIDDEN_CLASS_NAMES)
    assert leaked_forbidden == []
    leaked_generics = sorted(name for name in identifiers if name in GENERIC_EXECUTION_NAMES)
    assert leaked_generics == []


def test_forecasting_execution_public_contract_excludes_payload_runtime_and_implementation() -> (
    None
):
    names = annotation_type_names(EXECUTION_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    identifiers = _identifier_names(EXECUTION_MODULE)
    assert "Any" not in identifiers
    assert "dict" not in identifiers
    assert "Mapping" not in identifiers
    assert "Callable" not in identifiers
    assert "WorkflowState" not in identifiers
    assert "AgentPort" not in identifiers
    assert "AgentName" not in identifiers
    assert "asyncio" not in identifiers
    assert "gather" not in identifiers
    assert "TaskGroup" not in identifiers
    assert "create_task" not in identifiers
    assert "ForecastingExecutor" not in identifiers
    assert "ConcurrentForecastingExecutor" not in identifiers
    assert "SequentialForecastingExecutor" not in identifiers
    assert "ForecastingWorkflowContextPort" not in identifiers
    assert "ForecastingWorkflowStep" not in identifiers
    assert "ConsumerLoadForecastAgent" not in identifiers
    assert "DAMPriceForecastAgent" not in identifiers
    assert "ConsumerLoadForecastModelPort" not in identifiers
    assert "DAMPriceForecastModelPort" not in identifiers
    source = EXECUTION_MODULE.read_text(encoding="utf-8")
    assert "langgraph" not in source.lower()
    assert "langchain" not in source.lower()
    assert "asyncio.gather" not in source
    assert "TaskGroup" not in source
    assert "create_task" not in source
    assert ".run(" not in source
    assert ".forecast(" not in source


def test_workflow_state_shape_is_unchanged_by_the_execution_port() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert "ForecastingExecutionPort" not in names
    assert "ForecastingPlan" not in names
    assert "ForecastingSuccess" not in names
    modules = imported_modules(STATE_MODULE)
    assert "energy_trading.application.orchestration.forecasting_execution" not in modules
    state_source = STATE_MODULE.read_text(encoding="utf-8")
    assert "ForecastingExecutionPort" not in state_source
    assert "ForecastingPlan" not in state_source
    assert "ForecastingSuccess" not in state_source


def test_graph_remains_unwired_to_the_forecasting_execution_port() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "ForecastingExecutionPort" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "energy_trading.application.orchestration.forecasting_execution" not in modules
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "ForecastingExecutionPort" not in source
    assert "forecasting_execution" not in source


def test_api_composition_does_not_import_or_construct_forecasting_execution_port() -> None:
    forbidden_wiring = ("energy_trading.application.orchestration.forecasting_execution",)
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    composition_leaks = collect_import_violations(API_ROOT, forbidden_wiring)
    assert composition_leaks == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "ForecastingExecutionPort" not in names
        source = path.read_text(encoding="utf-8")
        assert "ForecastingExecutionPort" not in source
        assert "forecasting_execution" not in source


def test_forecasting_execution_stays_isolated_from_ml_implementations() -> None:
    modules = imported_modules(EXECUTION_MODULE)
    assert "energy_trading.ml" not in modules
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in modules
    )
    identifiers = _identifier_names(EXECUTION_MODULE)
    implementation_surface = {
        "train",
        "fit",
        "predict",
        "Booster",
        "XGBRegressor",
        "LGBMRegressor",
        "ModelRegistry",
        "FeatureStore",
        "Hyperparameter",
        "sklearn",
        "lightgbm",
        "xgboost",
        "numpy",
        "pandas",
    }
    leaked_surface = sorted(name for name in identifiers if name in implementation_surface)
    assert leaked_surface == []
    leaked_runtime_fields = sorted(
        name for name in identifiers if name in {"model", "features", "registry", "runtime"}
    )
    assert leaked_runtime_fields == []
    ml_vendor_prefixes = (
        "lightgbm",
        "xgboost",
        "sklearn",
        "numpy",
        "pandas",
        "polars",
        "torch",
        "tensorflow",
        "joblib",
        "onnx",
        "mlflow",
        "optuna",
        "energy_trading.ml",
    )
    application_leaks = collect_import_violations(
        PRODUCTION_ROOT / "application",
        ml_vendor_prefixes,
    )
    domain_leaks = collect_import_violations(PRODUCTION_ROOT / "domain", ml_vendor_prefixes)
    assert application_leaks == []
    assert domain_leaks == []
