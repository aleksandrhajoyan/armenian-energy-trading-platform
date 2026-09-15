"""Previous-day persistence backtest cases stay a narrow ML evaluation builder."""

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
ML_ROOT = PRODUCTION_ROOT / "ml"
CONSUMER_LOAD_ML_ROOT = ML_ROOT / "consumer_load"
BACKTEST_MODULE = CONSUMER_LOAD_ML_ROOT / "previous_day_persistence_backtest.py"
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.infrastructure",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.application.ports",
    "energy_trading.ml.common",
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
    "sklearn",
    "lightgbm",
    "xgboost",
    "prophet",
    "torch",
    "tensorflow",
    "joblib",
    "onnx",
    "onnxruntime",
    "mlflow",
    "optuna",
    "n8n",
    "uuid",
    "random",
    "secrets",
    "pathlib",
    "socket",
    "os",
)

FORBIDDEN_TYPE_NAMES = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "Dict",
        "Mapping",
        "MutableMapping",
        "TypedDict",
        "DataFrame",
        "ndarray",
        "NDArray",
        "Booster",
        "LGBMRegressor",
        "XGBRegressor",
        "ModelPort",
        "ForecastPort",
        "ForecastModelPort",
        "MLPort",
        "Backtester",
        "Evaluator",
        "Metric",
        "AgentFactory",
        "ServiceLocator",
        "ClockPort",
        "UuidFactory",
        "ForecastingExecutionPort",
        "ForecastingWorkflowStep",
        "ConsumerLoadForecastAgent",
        "ConsumerLoadForecastModelPort",
        "LoadForecastPoint",
        "WorkflowState",
        "MAE",
        "MSE",
        "RMSE",
        "MAPE",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "ModelPort",
        "ForecastPort",
        "ForecastModelPort",
        "MLPort",
        "Backtester",
        "Evaluator",
        "MetricRegistry",
        "ModelRegistry",
        "AgentFactory",
        "ServiceLocator",
        "ClockPort",
        "UuidFactory",
        "uuid4",
        "datetime.now",
        "ForecastingExecutionPort",
        "ConsumerLoadForecastAgent",
        "ConsumerLoadForecastModelPort",
        "PreviousDayPersistenceConsumerLoadForecastModel",
        "LoadForecastPoint",
        "build_workflow_graph",
        "create_app",
        "mean_absolute_error",
        "mean_squared_error",
        "root_mean_squared_error",
        "mean_absolute_percentage_error",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "datetime",
        "energy_trading.application.errors",
        "energy_trading.domain.models.observations",
        "energy_trading.domain.value_objects.quantities",
        "energy_trading.domain.value_objects.time",
    }
)

ALLOWED_CASE_FIELDS = (
    "consumer_id",
    "target_timestamp",
    "predicted_value_mw",
    "actual_value_mw",
)

ALLOWED_CASE_ANNOTATIONS = {
    "consumer_id": "EntityId",
    "target_timestamp": "UtcDateTime",
    "predicted_value_mw": "NonNegativeMW",
    "actual_value_mw": "NonNegativeMW",
}

GENERIC_ML_CLASS_NAMES = frozenset(
    {
        "ModelPort",
        "ForecastModelPort",
        "MLPort",
        "ForecastPort",
        "Predictor",
        "PredictorPort",
        "InferencePort",
        "GenericModelPort",
        "TimeSeriesModelPort",
        "Backtester",
        "Evaluator",
        "Metric",
        "ModelRegistry",
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


def _module_function_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node.name
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
    return names


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


def test_backtest_module_lives_under_ml_consumer_load() -> None:
    assert BACKTEST_MODULE.is_relative_to(CONSUMER_LOAD_ML_ROOT)
    assert BACKTEST_MODULE.name == "previous_day_persistence_backtest.py"
    assert _module_class_names(BACKTEST_MODULE) == ["PreviousDayPersistenceBacktestCase"]
    assert _module_function_names(BACKTEST_MODULE) == [
        "build_previous_day_persistence_backtest_cases"
    ]
    common_root = ML_ROOT / "common"
    common_python = sorted(common_root.rglob("*.py")) if common_root.exists() else []
    assert common_python == []


def test_case_is_frozen_slotted_with_exactly_four_canonical_fields() -> None:
    class_def = _class_def(BACKTEST_MODULE, "PreviousDayPersistenceBacktestCase")
    assert _base_names(class_def) == set()
    assert list(class_def.type_params) == []
    assert _dataclass_keywords(class_def) == {"frozen": True, "slots": True}
    assert _annassign_field_names(BACKTEST_MODULE, "PreviousDayPersistenceBacktestCase") == (
        ALLOWED_CASE_FIELDS
    )
    annotations = _annassign_field_annotations(
        BACKTEST_MODULE,
        "PreviousDayPersistenceBacktestCase",
    )
    assert annotations == ALLOWED_CASE_ANNOTATIONS
    leaked_types = sorted(name for name in annotations.values() if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []


def test_builder_is_keyword_only_sync_over_consumption_history() -> None:
    tree = ast.parse(BACKTEST_MODULE.read_text(encoding="utf-8"), filename=str(BACKTEST_MODULE))
    builder = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "build_previous_day_persistence_backtest_cases"
    )
    assert not isinstance(builder, ast.AsyncFunctionDef)
    assert tuple(arg.arg for arg in builder.args.args) == ()
    assert tuple(arg.arg for arg in builder.args.kwonlyargs) == ("history",)
    assert builder.args.vararg is None
    assert builder.args.kwarg is None
    history_arg = builder.args.kwonlyargs[0]
    assert history_arg.annotation is not None
    assert builder.returns is not None
    assert ast.unparse(history_arg.annotation) == "tuple[ConsumptionRecord, ...]"
    assert ast.unparse(builder.returns) == "tuple[PreviousDayPersistenceBacktestCase, ...]"


def test_backtest_depends_only_on_allowed_inward_contracts() -> None:
    leaked = sorted(
        module
        for module in imported_modules(BACKTEST_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(BACKTEST_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(BACKTEST_MODULE)
    assert "ConsumptionRecord" in names
    assert "InvalidRequestError" in names
    assert "EntityId" in names
    assert "UtcDateTime" in names
    assert "NonNegativeMW" in names
    assert "LoadForecastPoint" not in names
    assert "ConsumerLoadForecastModelPort" not in names
    assert "ConsumerLoadForecastModelRequest" not in names
    assert "PreviousDayPersistenceConsumerLoadForecastModel" not in names
    leaked_types = sorted(
        name for name in annotation_type_names(BACKTEST_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_backtest_does_not_generate_identity_or_use_io() -> None:
    source = BACKTEST_MODULE.read_text(encoding="utf-8")
    assert "datetime.now" not in source
    assert "uuid4" not in source
    assert "open(" not in source
    identifiers = _identifier_names(BACKTEST_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    modules = imported_modules(BACKTEST_MODULE)
    assert "uuid" not in modules
    assert "random" not in modules
    assert "pathlib" not in modules
    assert "timedelta" in identifiers
    assert "hours" in source
    assert "24" in source


def test_backtest_does_not_introduce_generic_ml_or_metrics() -> None:
    class_names = [name for path in ML_ROOT.rglob("*.py") for name in _module_class_names(path)]
    leaked_classes = sorted(name for name in class_names if name in GENERIC_ML_CLASS_NAMES)
    assert leaked_classes == []
    identifiers = _identifier_names(BACKTEST_MODULE)
    leaked_ids = sorted(name for name in identifiers if name in GENERIC_ML_CLASS_NAMES)
    assert leaked_ids == []
    source = BACKTEST_MODULE.read_text(encoding="utf-8").lower()
    assert "registry" not in source
    assert "lightgbm" not in source
    assert "xgboost" not in source
    assert "sklearn" not in source
    assert "numpy" not in source
    assert "pandas" not in source
    assert "mae" not in source
    assert "rmse" not in source
    assert "mape" not in source
    assert "residual" not in source
    assert "ml/common" not in source
    assert "energy_trading.ml.common" not in source


def test_application_agents_do_not_import_the_backtest_builder() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "PreviousDayPersistenceBacktestCase" not in names
        assert "build_previous_day_persistence_backtest_cases" not in names
        source = path.read_text(encoding="utf-8")
        assert "previous_day_persistence_backtest" not in source


def test_orchestration_and_langgraph_do_not_import_the_backtest_builder() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "PreviousDayPersistenceBacktestCase" not in names
        assert "build_previous_day_persistence_backtest_cases" not in names
        source = path.read_text(encoding="utf-8")
        assert "previous_day_persistence_backtest" not in source
    graph_modules = imported_modules(GRAPH_MODULE)
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in graph_modules
    )
    graph_names = imported_names(GRAPH_MODULE)
    assert "build_previous_day_persistence_backtest_cases" not in graph_names
    assert "PreviousDayPersistenceBacktestCase" not in graph_names


def test_api_composition_does_not_import_or_construct_the_backtest_builder() -> None:
    assert collect_import_violations(API_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "PreviousDayPersistenceBacktestCase" not in names
        assert "build_previous_day_persistence_backtest_cases" not in names
        source = path.read_text(encoding="utf-8")
        assert "previous_day_persistence_backtest" not in source
    app_source = API_APP.read_text(encoding="utf-8")
    assert "PreviousDayPersistenceBacktestCase" not in app_source
    assert "build_previous_day_persistence_backtest_cases" not in app_source


def test_workflow_state_shape_is_unchanged() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert "PreviousDayPersistenceBacktestCase" not in names
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "previous_day_persistence_backtest" not in source
    assert "predicted_value_mw" not in source


def test_no_dam_imports_in_consumer_load_backtest() -> None:
    names = imported_names(BACKTEST_MODULE)
    source = BACKTEST_MODULE.read_text(encoding="utf-8")
    assert "DAMPriceForecastModelPort" not in names
    assert "DAMPriceForecastAgent" not in names
    assert "MarketPriceRecord" not in names
    assert "PriceForecastPoint" not in names
    assert "dam_price" not in source.lower()
    assert "energy_trading.ml.dam" not in imported_modules(BACKTEST_MODULE)
