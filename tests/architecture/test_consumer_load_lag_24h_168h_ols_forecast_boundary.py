"""Lag-24h plus lag-168h OLS Consumer Load candidate adapter stays a narrow ML seam."""

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
ADAPTER_MODULE = CONSUMER_LOAD_ML_ROOT / "lag_24h_168h_ols_forecast.py"
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
PORT_MODULE = PRODUCTION_ROOT / "application" / "ports" / "consumer_load_forecast_model.py"
FORECAST_POINT_MODULE = PRODUCTION_ROOT / "domain" / "models" / "forecasting.py"
QUANTITIES_MODULE = PRODUCTION_ROOT / "domain" / "value_objects" / "quantities.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.infrastructure",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.ml.common",
    "energy_trading.ml.dam",
    "energy_trading.ml.consumer_load.previous_day_persistence",
    "energy_trading.ml.consumer_load.chronological_feature_split",
    "energy_trading.ml.consumer_load.lag_24h_features",
    "energy_trading.ml.consumer_load.lag_24h_linear_regression",
    "energy_trading.ml.consumer_load.lag_24h_168h_features",
    "energy_trading.ml.consumer_load.lag_24h_168h_chronological_split",
    "energy_trading.ml.consumer_load.lag_24h_168h_linear_regression_prediction",
    "energy_trading.ml.consumer_load.lag_24h_168h_linear_regression_evaluation",
    "energy_trading.ml.consumer_load.persistence_vs_trained_ols_comparison",
    "energy_trading.ml.consumer_load.lag_24h_vs_lag_24h_168h_ols_comparison",
    "energy_trading.ml.consumer_load.persistence_vs_lag_24h_168h_ols_comparison",
    "energy_trading.ml.consumer_load.persistence_vs_lag_24h_vs_lag_24h_168h_ols_comparison",
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
    "scipy",
    "statsmodels",
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
    "pickle",
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
        "Model",
        "Trainer",
        "Estimator",
        "Predictor",
        "Dataset",
        "ModelPort",
        "ForecastPort",
        "ForecastModelPort",
        "MLPort",
        "BestModel",
        "ChampionModel",
        "SelectedModel",
        "ProductionModel",
        "ComparisonResult",
        "Ranking",
        "AgentFactory",
        "ServiceLocator",
        "ClockPort",
        "UuidFactory",
        "ForecastingExecutionPort",
        "ForecastingWorkflowStep",
        "ConsumerLoadForecastAgent",
        "WorkflowState",
        "ConsumerLoadLag24h168hFeatureRow",
        "ConsumerLoadLag24h168hLinearRegressionPrediction",
        "PreviousDayPersistenceConsumerLoadForecastModel",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "ModelPort",
        "ForecastPort",
        "ForecastModelPort",
        "MLPort",
        "BestModel",
        "ChampionModel",
        "SelectedModel",
        "ProductionModel",
        "Champion",
        "winner",
        "champion",
        "selected_model",
        "ranking",
        "uuid4",
        "datetime.now",
        "ForecastingExecutionPort",
        "ConsumerLoadForecastAgent",
        "build_workflow_graph",
        "create_app",
        "fit_consumer_load_lag_24h_168h_linear_regression",
        "predict_consumer_load_lag_24h_168h_linear_regression",
        "build_consumer_load_lag_24h_168h_feature_rows",
        "split_consumer_load_lag_24h_168h_feature_rows_chronologically",
        "evaluate_consumer_load_lag_24h_168h_linear_regression_mae",
        "compare_consumer_load_persistence_vs_trained_ols_mae",
        "compare_consumer_load_lag_24h_vs_lag_24h_168h_ols_mae",
        "compare_consumer_load_persistence_vs_lag_24h_168h_ols_mae",
        "compare_consumer_load_persistence_vs_lag_24h_vs_lag_24h_168h_ols_mae",
        "PreviousDayPersistenceConsumerLoadForecastModel",
        "clip",
        "clamp",
        "abs",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "datetime",
        "math",
        "energy_trading.application.errors",
        "energy_trading.application.ports.consumer_load_forecast_model",
        "energy_trading.domain.models.forecasting",
        "energy_trading.domain.models.observations",
        "energy_trading.ml.consumer_load.lag_24h_168h_linear_regression",
    }
)

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
        "BestModel",
        "ChampionModel",
        "SelectedModel",
        "ProductionModel",
        "ComparisonResult",
        "Ranking",
    }
)

FORBIDDEN_CALL_NAMES = frozenset(
    {
        "abs",
        "clip",
        "clamp",
        "max",
        "min",
        "sorted",
        "sort",
        "fit_consumer_load_lag_24h_168h_linear_regression",
        "predict_consumer_load_lag_24h_168h_linear_regression",
        "build_consumer_load_lag_24h_168h_feature_rows",
        "split_consumer_load_lag_24h_168h_feature_rows_chronologically",
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


def _called_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def test_adapter_lives_under_ml_consumer_load() -> None:
    assert ADAPTER_MODULE.is_relative_to(CONSUMER_LOAD_ML_ROOT)
    assert ADAPTER_MODULE.name == "lag_24h_168h_ols_forecast.py"
    assert _module_class_names(ADAPTER_MODULE) == ["Lag24h168hOLSConsumerLoadForecastModel"]
    class_def = _class_def(ADAPTER_MODULE, "Lag24h168hOLSConsumerLoadForecastModel")
    assert _base_names(class_def) == set()
    leaked_classes = sorted(
        name for name in _module_class_names(ADAPTER_MODULE) if name in GENERIC_ML_CLASS_NAMES
    )
    assert leaked_classes == []


def test_adapter_depends_only_on_allowed_inward_contracts() -> None:
    leaked = sorted(
        module
        for module in imported_modules(ADAPTER_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(ADAPTER_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(ADAPTER_MODULE)
    assert "ConsumerLoadForecastModelRequest" in names
    assert "InvalidRequestError" in names
    assert "LoadForecastPoint" in names
    assert "ConsumptionRecord" in names
    assert "ConsumerLoadLag24h168hLinearRegressionFit" in names
    assert "ConsumerLoadForecastModelPort" not in names
    assert "fit_consumer_load_lag_24h_168h_linear_regression" not in names
    assert "predict_consumer_load_lag_24h_168h_linear_regression" not in names
    leaked_types = sorted(
        name for name in annotation_type_names(ADAPTER_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_adapter_exposes_keyword_only_async_forecast() -> None:
    class_def = _class_def(ADAPTER_MODULE, "Lag24h168hOLSConsumerLoadForecastModel")
    operations = [
        item
        for item in class_def.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not item.name.startswith("_")
    ]
    assert len(operations) == 1
    forecast_fn = operations[0]
    assert isinstance(forecast_fn, ast.AsyncFunctionDef)
    assert forecast_fn.name == "forecast"
    assert tuple(arg.arg for arg in forecast_fn.args.args) == ("self",)
    assert tuple(arg.arg for arg in forecast_fn.args.kwonlyargs) == ("request",)
    assert forecast_fn.args.vararg is None
    assert forecast_fn.args.kwarg is None
    request_arg = forecast_fn.args.kwonlyargs[0]
    assert request_arg.annotation is not None
    assert forecast_fn.returns is not None
    assert ast.unparse(request_arg.annotation) == "ConsumerLoadForecastModelRequest"
    assert ast.unparse(forecast_fn.returns) == "tuple[LoadForecastPoint, ...]"
    init_fn = next(
        item
        for item in class_def.body
        if isinstance(item, ast.FunctionDef) and item.name == "__init__"
    )
    assert tuple(arg.arg for arg in init_fn.args.args) == ("self",)
    assert tuple(arg.arg for arg in init_fn.args.kwonlyargs) == ("fit",)
    assert ast.unparse(init_fn.args.kwonlyargs[0].annotation) == (
        "ConsumerLoadLag24h168hLinearRegressionFit"
    )


def test_adapter_does_not_generate_identity_or_use_io() -> None:
    source = ADAPTER_MODULE.read_text(encoding="utf-8")
    assert "datetime.now" not in source
    assert "uuid4" not in source
    assert "open(" not in source
    identifiers = _identifier_names(ADAPTER_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    modules = imported_modules(ADAPTER_MODULE)
    assert "uuid" not in modules
    assert "random" not in modules
    assert "pathlib" not in modules
    assert "socket" not in modules
    assert "os" not in modules
    assert "pickle" not in modules
    assert "timedelta" in identifiers
    assert "hours" in source
    assert "24" in source
    assert "168" in source


def test_adapter_does_not_introduce_generic_or_selection_frameworks() -> None:
    identifiers = _identifier_names(ADAPTER_MODULE)
    leaked_ids = sorted(name for name in identifiers if name in GENERIC_ML_CLASS_NAMES)
    assert leaked_ids == []
    leaked_calls = sorted(
        name for name in _called_names(ADAPTER_MODULE) if name in FORBIDDEN_CALL_NAMES
    )
    assert leaked_calls == []
    source = ADAPTER_MODULE.read_text(encoding="utf-8")
    assert "AgentFactory" not in source
    assert "ServiceLocator" not in source
    assert "registry" not in source.lower()
    assert "lightgbm" not in source.lower()
    assert "xgboost" not in source.lower()
    assert "sklearn" not in source.lower()
    assert "numpy" not in source.lower()
    assert "pandas" not in source.lower()
    assert "ml/common" not in source


def test_negative_admissibility_is_explicit_before_output_construction() -> None:
    tree = ast.parse(ADAPTER_MODULE.read_text(encoding="utf-8"), filename=str(ADAPTER_MODULE))
    compare_linenos: list[int] = []
    construct_linenos: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            zero_constant = any(
                isinstance(operand, ast.Constant) and operand.value in {0}
                for operand in (node.left, *node.comparators)
            )
            less_than = any(isinstance(op, ast.Lt) for op in node.ops)
            if zero_constant and less_than:
                compare_linenos.append(node.lineno)
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else None
            if name == "LoadForecastPoint":
                construct_linenos.append(node.lineno)
    assert compare_linenos
    assert construct_linenos
    assert min(compare_linenos) < min(construct_linenos)
    assert "abs" not in _called_names(ADAPTER_MODULE)
    assert "clip" not in _called_names(ADAPTER_MODULE)
    assert "clamp" not in _called_names(ADAPTER_MODULE)
    assert "max" not in _called_names(ADAPTER_MODULE)


def test_application_port_and_domain_output_contracts_are_unchanged() -> None:
    port_source = PORT_MODULE.read_text(encoding="utf-8")
    assert "async def forecast(" in port_source
    assert "request: ConsumerLoadForecastModelRequest" in port_source
    assert "tuple[LoadForecastPoint, ...]" in port_source
    assert "Lag24h168hOLSConsumerLoadForecastModel" not in port_source
    forecast_source = FORECAST_POINT_MODULE.read_text(encoding="utf-8")
    assert "value_mw: NonNegativeMW" in forecast_source
    quantities_source = QUANTITIES_MODULE.read_text(encoding="utf-8")
    assert "NonNegativeMW = Annotated[float, Field(ge=0, allow_inf_nan=False)]" in quantities_source


def test_application_agents_do_not_import_the_adapter() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "Lag24h168hOLSConsumerLoadForecastModel" not in names
        source = path.read_text(encoding="utf-8")
        assert "Lag24h168hOLSConsumerLoadForecastModel" not in source
        assert "lag_24h_168h_ols_forecast" not in source


def test_orchestration_and_langgraph_do_not_import_the_adapter() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "Lag24h168hOLSConsumerLoadForecastModel" not in names
        source = path.read_text(encoding="utf-8")
        assert "Lag24h168hOLSConsumerLoadForecastModel" not in source
        assert "lag_24h_168h_ols_forecast" not in source
    graph_modules = imported_modules(GRAPH_MODULE)
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in graph_modules
    )


def test_api_composition_does_not_import_or_construct_the_adapter() -> None:
    assert collect_import_violations(API_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "Lag24h168hOLSConsumerLoadForecastModel" not in names
        source = path.read_text(encoding="utf-8")
        assert "Lag24h168hOLSConsumerLoadForecastModel" not in source
        assert "lag_24h_168h_ols_forecast" not in source
    app_source = API_APP.read_text(encoding="utf-8")
    assert "Lag24h168hOLSConsumerLoadForecastModel" not in app_source
    tree = ast.parse(app_source, filename=str(API_APP))
    create_app = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )
    call_names: set[str] = set()
    for node in ast.walk(create_app):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            call_names.add(func.id)
        elif isinstance(func, ast.Attribute):
            call_names.add(func.attr)
    assert "Lag24h168hOLSConsumerLoadForecastModel" not in call_names


def test_workflow_state_shape_is_unchanged() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert "Lag24h168hOLSConsumerLoadForecastModel" not in names
    assert "LoadForecastPoint" not in names
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "lag_24h_168h_ols_forecast" not in source
    assert "forecast_run_id" not in source
