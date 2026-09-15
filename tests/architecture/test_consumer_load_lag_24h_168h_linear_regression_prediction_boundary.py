"""Consumer Load 24h+168h OLS prediction stays a narrow ML evaluation seam."""

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
PREDICTION_MODULE = CONSUMER_LOAD_ML_ROOT / "lag_24h_168h_linear_regression_prediction.py"
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
    "energy_trading.ml.dam",
    "energy_trading.ml.consumer_load.chronological_feature_split",
    "energy_trading.ml.consumer_load.lag_24h_features",
    "energy_trading.ml.consumer_load.lag_24h_linear_regression",
    "energy_trading.ml.consumer_load.lag_24h_linear_regression_prediction",
    "energy_trading.ml.consumer_load.lag_24h_linear_regression_evaluation",
    "energy_trading.ml.consumer_load.lag_24h_168h_chronological_split",
    "energy_trading.ml.consumer_load.persistence_vs_trained_ols_comparison",
    "energy_trading.ml.consumer_load.previous_day_persistence",
    "energy_trading.ml.consumer_load.previous_day_persistence_backtest",
    "energy_trading.ml.consumer_load.previous_day_persistence_evaluation",
    "energy_trading.domain.models.observations",
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
        "LinearModel",
        "RegressionModel",
        "Trainer",
        "Estimator",
        "FitResult",
        "ModelParameters",
        "Predictor",
        "Dataset",
        "TrainingDataset",
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
        "ConsumptionRecord",
        "ConsumerLoadLag24hFeatureRow",
        "ConsumerLoadChronologicalFeatureSplit",
        "ConsumerLoadLag24h168hChronologicalFeatureSplit",
        "ConsumerLoadLag24hLinearRegressionFit",
        "ConsumerLoadLag24hLinearRegressionPrediction",
        "ConsumerLoadLag24hLinearRegressionMAEResult",
        "ConsumerLoadPersistenceVsTrainedOLSMAEComparison",
        "PreviousDayPersistenceBacktestCase",
        "PreviousDayPersistenceMAEResult",
        "PreviousDayPersistenceConsumerLoadForecastModel",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "Model",
        "LinearModel",
        "RegressionModel",
        "Trainer",
        "Estimator",
        "FitResult",
        "ModelParameters",
        "Predictor",
        "Dataset",
        "TrainingDataset",
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
        "PreviousDayPersistenceBacktestCase",
        "build_previous_day_persistence_backtest_cases",
        "PreviousDayPersistenceMAEResult",
        "evaluate_previous_day_persistence_mae",
        "ConsumerLoadChronologicalFeatureSplit",
        "split_consumer_load_feature_rows_chronologically",
        "ConsumerLoadLag24h168hChronologicalFeatureSplit",
        "split_consumer_load_lag_24h_168h_feature_rows_chronologically",
        "build_consumer_load_lag_24h_feature_rows",
        "build_consumer_load_lag_24h_168h_feature_rows",
        "fit_consumer_load_lag_24h_linear_regression",
        "fit_consumer_load_lag_24h_168h_linear_regression",
        "predict_consumer_load_lag_24h_linear_regression",
        "evaluate_consumer_load_lag_24h_linear_regression_mae",
        "compare_consumer_load_persistence_vs_trained_ols_mae",
        "ConsumptionRecord",
        "LoadForecastPoint",
        "build_workflow_graph",
        "create_app",
        "mae",
        "rmse",
        "mape",
        "r2",
        "dump",
        "dumps",
        "pickle",
        "joblib",
        "sorted",
        "sort",
        "max",
        "min",
        "clip",
        "clamp",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "math",
        "energy_trading.application.errors",
        "energy_trading.domain.value_objects.quantities",
        "energy_trading.domain.value_objects.time",
        "energy_trading.ml.consumer_load.lag_24h_168h_features",
        "energy_trading.ml.consumer_load.lag_24h_168h_linear_regression",
    }
)

ALLOWED_RESULT_FIELDS = (
    "consumer_id",
    "target_timestamp",
    "predicted_value_mw",
    "actual_value_mw",
)

ALLOWED_RESULT_ANNOTATIONS = {
    "consumer_id": "EntityId",
    "target_timestamp": "UtcDateTime",
    "predicted_value_mw": "float",
    "actual_value_mw": "NonNegativeMW",
}

GENERIC_ML_CLASS_NAMES = frozenset(
    {
        "Model",
        "LinearModel",
        "RegressionModel",
        "Trainer",
        "Estimator",
        "FitResult",
        "ModelParameters",
        "Predictor",
        "PredictorPort",
        "Dataset",
        "TrainingDataset",
        "ModelPort",
        "ForecastModelPort",
        "MLPort",
        "ForecastPort",
        "Backtester",
        "Evaluator",
        "Metric",
        "ModelRegistry",
    }
)

UNAUTHORIZED_PREDICTION_TOKENS = (
    "sklearn",
    "numpy",
    "pandas",
    "polars",
    "scipy",
    "statsmodels",
    "lightgbm",
    "xgboost",
    "ml/common",
    "energy_trading.ml.common",
    "consumptionrecord",
    "chronological_feature_split",
    "split_consumer_load_feature_rows_chronologically",
    "split_consumer_load_lag_24h_168h_feature_rows_chronologically",
    "fit_consumer_load_lag_24h_linear_regression",
    "fit_consumer_load_lag_24h_168h_linear_regression",
    "build_consumer_load_lag_24h_feature_rows",
    "build_consumer_load_lag_24h_168h_feature_rows",
    "predict_consumer_load_lag_24h_linear_regression",
    "evaluate_consumer_load_lag_24h_linear_regression_mae",
    "compare_consumer_load_persistence_vs_trained_ols_mae",
    "datetime.now",
    "loadforecastpoint",
    "max(0",
    "min(0",
    "clip(",
    "clamp(",
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

FORBIDDEN_CALL_NAMES = frozenset(
    {
        "build_consumer_load_lag_24h_feature_rows",
        "build_consumer_load_lag_24h_168h_feature_rows",
        "split_consumer_load_feature_rows_chronologically",
        "split_consumer_load_lag_24h_168h_feature_rows_chronologically",
        "fit_consumer_load_lag_24h_linear_regression",
        "fit_consumer_load_lag_24h_168h_linear_regression",
        "predict_consumer_load_lag_24h_linear_regression",
        "evaluate_consumer_load_lag_24h_linear_regression_mae",
        "compare_consumer_load_persistence_vs_trained_ols_mae",
        "sorted",
        "sort",
        "max",
        "min",
        "clip",
        "clamp",
        "abs",
    }
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


def _is_attribute(node: ast.AST, *, owner: str, attr: str) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == attr
        and isinstance(node.value, ast.Name)
        and node.value.id == owner
    )


def _has_two_feature_formula(function: ast.FunctionDef) -> bool:
    required = {
        "lag_24h_coefficient",
        "lag_168h_coefficient",
        "intercept_mw",
        "lag_24h_mw",
        "lag_168h_mw",
    }
    found = {node.attr for node in ast.walk(function) if isinstance(node, ast.Attribute)}
    return required <= found


def test_prediction_module_lives_under_ml_consumer_load() -> None:
    assert PREDICTION_MODULE.is_relative_to(CONSUMER_LOAD_ML_ROOT)
    assert PREDICTION_MODULE.name == "lag_24h_168h_linear_regression_prediction.py"
    assert _module_class_names(PREDICTION_MODULE) == [
        "ConsumerLoadLag24h168hLinearRegressionPrediction"
    ]
    assert _module_function_names(PREDICTION_MODULE) == [
        "predict_consumer_load_lag_24h_168h_linear_regression"
    ]


def test_result_is_frozen_slotted_with_evaluation_identity_and_signed_prediction() -> None:
    class_def = _class_def(PREDICTION_MODULE, "ConsumerLoadLag24h168hLinearRegressionPrediction")
    assert _base_names(class_def) == set()
    assert list(class_def.type_params) == []
    assert _dataclass_keywords(class_def) == {"frozen": True, "slots": True}
    assert (
        _annassign_field_names(
            PREDICTION_MODULE, "ConsumerLoadLag24h168hLinearRegressionPrediction"
        )
        == ALLOWED_RESULT_FIELDS
    )
    annotations = _annassign_field_annotations(
        PREDICTION_MODULE,
        "ConsumerLoadLag24h168hLinearRegressionPrediction",
    )
    assert annotations == ALLOWED_RESULT_ANNOTATIONS
    leaked_types = sorted(name for name in annotations.values() if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []


def test_predictor_is_keyword_only_sync_over_fit_and_feature_rows() -> None:
    tree = ast.parse(PREDICTION_MODULE.read_text(encoding="utf-8"), filename=str(PREDICTION_MODULE))
    predictor = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "predict_consumer_load_lag_24h_168h_linear_regression"
    )
    assert not isinstance(predictor, ast.AsyncFunctionDef)
    assert tuple(arg.arg for arg in predictor.args.args) == ()
    assert tuple(arg.arg for arg in predictor.args.kwonlyargs) == ("fit", "evaluation_rows")
    assert predictor.args.vararg is None
    assert predictor.args.kwarg is None
    fit_arg = predictor.args.kwonlyargs[0]
    rows_arg = predictor.args.kwonlyargs[1]
    assert fit_arg.annotation is not None
    assert rows_arg.annotation is not None
    assert predictor.returns is not None
    assert ast.unparse(fit_arg.annotation) == "ConsumerLoadLag24h168hLinearRegressionFit"
    assert ast.unparse(rows_arg.annotation) == "tuple[ConsumerLoadLag24h168hFeatureRow, ...]"
    assert (
        ast.unparse(predictor.returns)
        == "tuple[ConsumerLoadLag24h168hLinearRegressionPrediction, ...]"
    )


def test_prediction_formula_uses_both_coefficients_and_intercept_without_clamping() -> None:
    source = PREDICTION_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(PREDICTION_MODULE))
    helpers = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name
        in {"predict_consumer_load_lag_24h_168h_linear_regression", "_prediction_for_row"}
    ]
    assert any(_has_two_feature_formula(function) for function in helpers)
    assert "fit.lag_24h_coefficient" in source
    assert "fit.lag_168h_coefficient" in source
    assert "fit.intercept_mw" in source
    assert "row.lag_24h_mw" in source
    assert "row.lag_168h_mw" in source
    leaked_tokens = [token for token in ("max(0", "min(0", "clip(", "clamp(") if token in source]
    assert leaked_tokens == []
    leaked_calls = sorted(
        name for name in _called_names(PREDICTION_MODULE) if name in FORBIDDEN_CALL_NAMES
    )
    assert leaked_calls == []


def test_prediction_imports_fit_dto_but_does_not_call_fitter() -> None:
    names = imported_names(PREDICTION_MODULE)
    identifiers = _identifier_names(PREDICTION_MODULE)
    called = _called_names(PREDICTION_MODULE)
    assert "ConsumerLoadLag24h168hLinearRegressionFit" in names
    assert "ConsumerLoadLag24h168hFeatureRow" in names
    assert "fit_consumer_load_lag_24h_168h_linear_regression" not in names
    assert "fit_consumer_load_lag_24h_168h_linear_regression" not in identifiers
    assert "fit_consumer_load_lag_24h_168h_linear_regression" not in called
    assert "isfinite" in identifiers
    assert "isfinite" in names


def test_prediction_depends_only_on_allowed_inward_contracts() -> None:
    leaked = sorted(
        module
        for module in imported_modules(PREDICTION_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(PREDICTION_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(PREDICTION_MODULE)
    assert "ConsumerLoadLag24h168hFeatureRow" in names
    assert "ConsumerLoadLag24h168hLinearRegressionFit" in names
    assert "InvalidRequestError" in names
    assert "isfinite" in names
    assert "EntityId" in names
    assert "NonNegativeMW" in names
    assert "UtcDateTime" in names
    assert "ConsumptionRecord" not in names
    assert "LoadForecastPoint" not in names
    assert "ConsumerLoadLag24h168hChronologicalFeatureSplit" not in names
    assert "split_consumer_load_lag_24h_168h_feature_rows_chronologically" not in names
    assert "fit_consumer_load_lag_24h_linear_regression" not in names
    assert "predict_consumer_load_lag_24h_linear_regression" not in names
    assert "build_consumer_load_lag_24h_168h_feature_rows" not in names
    assert "ConsumerLoadForecastModelPort" not in names
    leaked_types = sorted(
        name for name in annotation_type_names(PREDICTION_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_prediction_does_not_generate_identity_or_use_io() -> None:
    source = PREDICTION_MODULE.read_text(encoding="utf-8")
    assert "datetime.now" not in source
    assert "uuid4" not in source
    assert "open(" not in source
    identifiers = _identifier_names(PREDICTION_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    modules = imported_modules(PREDICTION_MODULE)
    assert "uuid" not in modules
    assert "random" not in modules
    assert "pathlib" not in modules
    assert "socket" not in modules
    assert "os" not in modules
    assert "datetime" not in modules
    assert "pickle" not in modules


def test_prediction_does_not_introduce_generic_trainer_metrics_or_frameworks() -> None:
    class_names = _module_class_names(PREDICTION_MODULE)
    leaked_classes = sorted(name for name in class_names if name in GENERIC_ML_CLASS_NAMES)
    assert leaked_classes == []
    identifiers = _identifier_names(PREDICTION_MODULE)
    leaked_ids = sorted(name for name in identifiers if name in GENERIC_ML_CLASS_NAMES)
    assert leaked_ids == []
    source = PREDICTION_MODULE.read_text(encoding="utf-8").lower()
    leaked_tokens = [token for token in UNAUTHORIZED_PREDICTION_TOKENS if token in source]
    assert leaked_tokens == []
    assert "registry" not in source
    assert "hyperparameter" not in source
    assert "lightgbm" not in source
    assert "xgboost" not in source
    assert "mae" not in identifiers
    assert "rmse" not in identifiers
    assert "sorted" not in identifiers
    assert "sort" not in identifiers


def test_application_agents_do_not_import_the_two_lag_ols_prediction() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "ConsumerLoadLag24h168hLinearRegressionPrediction" not in names
        assert "predict_consumer_load_lag_24h_168h_linear_regression" not in names
        source = path.read_text(encoding="utf-8")
        assert "lag_24h_168h_linear_regression_prediction" not in source


def test_orchestration_and_langgraph_do_not_import_the_two_lag_ols_prediction() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "ConsumerLoadLag24h168hLinearRegressionPrediction" not in names
        assert "predict_consumer_load_lag_24h_168h_linear_regression" not in names
        source = path.read_text(encoding="utf-8")
        assert "lag_24h_168h_linear_regression_prediction" not in source
    graph_modules = imported_modules(GRAPH_MODULE)
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in graph_modules
    )
    graph_names = imported_names(GRAPH_MODULE)
    assert "predict_consumer_load_lag_24h_168h_linear_regression" not in graph_names
    assert "ConsumerLoadLag24h168hLinearRegressionPrediction" not in graph_names
    assert "ForecastingExecutionPort" not in graph_names


def test_api_does_not_reference_the_two_lag_ols_prediction() -> None:
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "ConsumerLoadLag24h168hLinearRegressionPrediction" not in names
        assert "predict_consumer_load_lag_24h_168h_linear_regression" not in names
        source = path.read_text(encoding="utf-8")
        assert "lag_24h_168h_linear_regression_prediction" not in source
    app_source = API_APP.read_text(encoding="utf-8")
    assert "ConsumerLoadLag24h168hLinearRegressionPrediction" not in app_source
    assert "predict_consumer_load_lag_24h_168h_linear_regression" not in app_source


def test_workflow_state_shape_is_unchanged() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert "ConsumerLoadLag24h168hLinearRegressionPrediction" not in names
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "lag_24h_168h_linear_regression_prediction" not in source
    assert "predicted_value_mw" not in source


def test_no_dam_imports_in_two_lag_ols_prediction() -> None:
    names = imported_names(PREDICTION_MODULE)
    source = PREDICTION_MODULE.read_text(encoding="utf-8")
    assert "DAMPriceForecastModelPort" not in names
    assert "DAMPriceForecastAgent" not in names
    assert "MarketPriceRecord" not in names
    assert "PriceForecastPoint" not in names
    assert "dam_price" not in source.lower()
    assert "energy_trading.ml.dam" not in imported_modules(PREDICTION_MODULE)
