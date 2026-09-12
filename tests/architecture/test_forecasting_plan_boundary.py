"""Forecasting plan stays typed, application-only, and LangGraph-free."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    collect_http_api_import_violations,
    collect_import_violations,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
PLAN_MODULE = ORCHESTRATION_ROOT / "forecasting_plan.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
API_ROOT = PRODUCTION_ROOT / "api"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
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
        "ForecastingExecutionPort",
        "ForecastingSuccess",
        "ForecastingResult",
        "ForecastingOutcome",
        "ModelPort",
        "MLPort",
        "ForecastModelPort",
        "Optional",
        "Protocol",
    }
)

FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "payload",
        "data",
        "context",
        "metadata",
        "artifacts",
        "callback",
        "on_complete",
        "exception",
        "error",
        "diagnostics",
        "results",
        "outcome",
        "fallback",
        "retry_count",
        "retries",
        "degraded",
        "status",
        "failed",
        "failure",
        "errors",
        "skipped",
        "partial",
        "provider",
        "persistence",
        "graph",
        "runtime",
        "state",
        "portfolio_id",
        "workflow_id",
        "model",
        "features",
        "registry",
    }
)

ALLOWED_PLAN_FIELDS = (
    "consumer_load_request",
    "dam_price_request",
)

ALLOWED_PLAN_ANNOTATIONS = {
    "consumer_load_request": "ConsumerLoadForecastModelRequest",
    "dam_price_request": "DAMPriceForecastModelRequest",
}

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "energy_trading.application.ports.consumer_load_forecast_model",
        "energy_trading.application.ports.dam_price_forecast_model",
    }
)

MODULE_FORBIDDEN_CLASS_NAMES = frozenset(
    {
        "ForecastingExecutionPort",
        "ForecastingSuccess",
        "ForecastingResult",
        "ForecastingOutcome",
        "ModelPort",
        "MLPort",
        "ForecastModelPort",
        "AgentFactory",
        "AgentRegistry",
        "ServiceLocator",
    }
)

GENERIC_MODEL_PORT_NAMES = frozenset({"ModelPort", "MLPort", "ForecastModelPort"})

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


def _annassign_field_annotations(path: Path, class_name: str) -> dict[str, str]:
    class_def = _class_def(path, class_name)
    annotations: dict[str, str] = {}
    for item in class_def.body:
        if (
            isinstance(item, ast.AnnAssign)
            and isinstance(item.target, ast.Name)
            and item.annotation is not None
        ):
            annotations[item.target.id] = ast.unparse(item.annotation)
    return annotations


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


def _dataclass_keywords(class_def: ast.ClassDef) -> dict[str, object]:
    for decorator in class_def.decorator_list:
        call = decorator if isinstance(decorator, ast.Call) else None
        if call is None:
            continue
        func = call.func
        name = func.id if isinstance(func, ast.Name) else None
        if name != "dataclass":
            continue
        return {
            keyword.arg: ast.literal_eval(keyword.value)
            for keyword in call.keywords
            if keyword.arg is not None
        }
    msg = f"dataclass decorator not found on {class_def.name}"
    raise AssertionError(msg)


def test_forecasting_plan_lives_in_application_orchestration() -> None:
    assert PLAN_MODULE.is_relative_to(ORCHESTRATION_ROOT)
    assert PLAN_MODULE.name == "forecasting_plan.py"
    assert PLAN_MODULE.exists()


def test_forecasting_plan_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(PLAN_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(PLAN_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(PLAN_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []


def test_forecasting_plan_is_frozen_slotted_dataclass_with_exactly_two_typed_fields() -> None:
    class_def = _class_def(PLAN_MODULE, "ForecastingPlan")
    assert list(class_def.type_params) == []
    assert _base_names(class_def) == set()
    keywords = _dataclass_keywords(class_def)
    assert keywords == {"frozen": True, "slots": True}
    fields = _annassign_field_names(PLAN_MODULE, "ForecastingPlan")
    assert fields == ALLOWED_PLAN_FIELDS
    leaked = sorted(name for name in fields if name in FORBIDDEN_FIELD_NAMES)
    assert leaked == []
    annotations = _annassign_field_annotations(PLAN_MODULE, "ForecastingPlan")
    assert annotations == ALLOWED_PLAN_ANNOTATIONS
    leaked_types = sorted(name for name in annotations.values() if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    result_types = {
        "LoadForecastPoint",
        "PriceForecastPoint",
        "ConsumerLoadForecastResult",
        "DAMPriceForecastResult",
        "ForecastingSuccess",
        "ForecastingResult",
    }
    assert result_types.isdisjoint(annotations.values())
    defined = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert defined == ["__post_init__"]
    assert not any(isinstance(node, ast.AsyncFunctionDef) for node in ast.walk(class_def))


def test_forecasting_plan_module_exposes_only_the_plan_contract() -> None:
    class_names = _module_class_names(PLAN_MODULE)
    assert class_names == ["ForecastingPlan"]
    tree = ast.parse(PLAN_MODULE.read_text(encoding="utf-8"), filename=str(PLAN_MODULE))
    protocols = [
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef) and "Protocol" in _base_names(node)
    ]
    assert protocols == []
    leaked_classes = sorted(name for name in class_names if name in MODULE_FORBIDDEN_CLASS_NAMES)
    assert leaked_classes == []
    identifiers = _identifier_names(PLAN_MODULE)
    leaked_forbidden = sorted(name for name in identifiers if name in MODULE_FORBIDDEN_CLASS_NAMES)
    assert leaked_forbidden == []
    leaked_generics = sorted(name for name in identifiers if name in GENERIC_MODEL_PORT_NAMES)
    assert leaked_generics == []


def test_forecasting_plan_public_contract_excludes_payload_runtime_and_execution() -> None:
    names = annotation_type_names(PLAN_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    identifiers = _identifier_names(PLAN_MODULE)
    assert "Any" not in identifiers
    assert "dict" not in identifiers
    assert "Mapping" not in identifiers
    assert "Callable" not in identifiers
    assert "Protocol" not in identifiers
    assert "WorkflowState" not in identifiers
    assert "AgentPort" not in identifiers
    assert "asyncio" not in identifiers
    assert "gather" not in identifiers
    assert "TaskGroup" not in identifiers
    assert "ForecastingExecutionPort" not in identifiers
    assert "ForecastingSuccess" not in identifiers
    assert "ForecastingResult" not in identifiers
    assert "ForecastingOutcome" not in identifiers
    assert "ModelPort" not in identifiers
    assert "MLPort" not in identifiers
    assert "ForecastModelPort" not in identifiers
    assert "create_task" not in identifiers
    source = PLAN_MODULE.read_text(encoding="utf-8")
    assert "langgraph" not in source.lower()
    assert "langchain" not in source.lower()
    assert "asyncio.gather" not in source
    assert "TaskGroup" not in source
    assert ".run(" not in source
    assert ".forecast(" not in source


def test_workflow_state_shape_is_unchanged_by_the_plan() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    leaked = sorted(name for name in fields if name in ALLOWED_PLAN_FIELDS)
    assert leaked == []
    names = imported_names(STATE_MODULE)
    assert "ForecastingPlan" not in names
    modules = imported_modules(STATE_MODULE)
    assert "energy_trading.application.orchestration.forecasting_plan" not in modules
    state_source = STATE_MODULE.read_text(encoding="utf-8")
    assert "ForecastingPlan" not in state_source


def test_graph_remains_unwired_to_the_forecasting_plan() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "ForecastingPlan" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "energy_trading.application.orchestration.forecasting_plan" not in modules
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "ForecastingPlan" not in source
    assert "forecasting_plan" not in source


def test_api_composition_does_not_import_or_construct_forecasting_plan() -> None:
    forbidden_wiring = ("energy_trading.application.orchestration.forecasting_plan",)
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    composition_leaks = collect_import_violations(API_ROOT, forbidden_wiring)
    assert composition_leaks == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "ForecastingPlan" not in names
        source = path.read_text(encoding="utf-8")
        assert "ForecastingPlan" not in source
        assert "forecasting_plan" not in source


def test_forecasting_plan_stays_isolated_from_ml_implementations() -> None:
    modules = imported_modules(PLAN_MODULE)
    assert "energy_trading.ml" not in modules
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in modules
    )
    identifiers = _identifier_names(PLAN_MODULE)
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
