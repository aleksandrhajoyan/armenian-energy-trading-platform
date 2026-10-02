"""DAM Price 24h+168h OLS fit stays a narrow Decimal ML parameter artifact."""

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
DAM_ML_ROOT = ML_ROOT / "dam_price"
FIT_MODULE = DAM_ML_ROOT / "lag_24h_168h_linear_regression.py"
FEATURES_MODULE = DAM_ML_ROOT / "lag_24h_168h_features.py"
SPLIT_MODULE = DAM_ML_ROOT / "lag_24h_168h_chronological_feature_split.py"
ONE_FEATURE_MODULE = DAM_ML_ROOT / "lag_24h_features.py"
ONE_FEATURE_SPLIT_MODULE = DAM_ML_ROOT / "chronological_feature_split.py"
ONE_FEATURE_FIT_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression.py"
PREDICTION_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression_prediction.py"
TRAINED_EVALUATION_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression_evaluation.py"
COMPARISON_MODULE = DAM_ML_ROOT / "persistence_vs_trained_ols_comparison.py"
LIVE_ADAPTER_MODULE = DAM_ML_ROOT / "previous_day_persistence.py"
BACKTEST_MODULE = DAM_ML_ROOT / "previous_day_persistence_backtest.py"
PERSISTENCE_EVALUATION_MODULE = DAM_ML_ROOT / "previous_day_persistence_evaluation.py"
DAM_ML_INIT = DAM_ML_ROOT / "__init__.py"
DAM_PRICE_PORT_MODULE = PRODUCTION_ROOT / "application" / "ports" / "dam_price_forecast_model.py"
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

FIT_CLASS = "DAMPriceLag24h168hLinearRegressionFit"
FITTER = "fit_dam_price_lag_24h_168h_linear_regression"
FIT_MODULE_NAME = "lag_24h_168h_linear_regression"
ROW_CLASS = "DAMPriceLag24h168hFeatureRow"
FEATURE_BUILDER = "build_dam_price_lag_24h_168h_feature_rows"
SPLIT_CLASS = "DAMPriceLag24h168hChronologicalFeatureSplit"
SPLITTER = "split_dam_price_lag_24h_168h_feature_rows_chronologically"
ONE_FEATURE_FIT_CLASS = "DAMPriceLag24hLinearRegressionFit"
ONE_FEATURE_FITTER = "fit_dam_price_lag_24h_linear_regression"

FIT_FIELDS = ("lag_24h_coefficient", "lag_168h_coefficient", "intercept_amount_per_mwh")

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.infrastructure",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.application.ports",
    "energy_trading.domain.models",
    "energy_trading.domain.value_objects.money",
    "energy_trading.domain.value_objects.time",
    "energy_trading.ml.common",
    "energy_trading.ml.consumer_load",
    "energy_trading.ml.dam_price.chronological_feature_split",
    "energy_trading.ml.dam_price.lag_24h_168h_chronological_feature_split",
    "energy_trading.ml.dam_price.lag_24h_features",
    "energy_trading.ml.dam_price.lag_24h_linear_regression",
    "energy_trading.ml.dam_price.lag_24h_linear_regression_prediction",
    "energy_trading.ml.dam_price.lag_24h_linear_regression_evaluation",
    "energy_trading.ml.dam_price.persistence_vs_trained_ols_comparison",
    "energy_trading.ml.dam_price.previous_day_persistence",
    "energy_trading.ml.dam_price.previous_day_persistence_backtest",
    "energy_trading.ml.dam_price.previous_day_persistence_evaluation",
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
    "math",
    "statistics",
    "itertools",
    "time",
    "datetime",
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
        "AgentFactory",
        "ServiceLocator",
        "ClockPort",
        "UuidFactory",
        "ForecastingExecutionPort",
        "ForecastingWorkflowStep",
        "DAMPriceForecastAgent",
        "DAMPriceForecastModelRequest",
        "DAMPriceForecastModelPort",
        "PriceForecastPoint",
        "MarketPriceRecord",
        "EnergyPrice",
        "UtcDateTime",
        "DAMPriceLag24hFeatureRow",
        "DAMPriceChronologicalFeatureSplit",
        SPLIT_CLASS,
        ONE_FEATURE_FIT_CLASS,
        "DAMPriceLag24hLinearRegressionPrediction",
        "DAMPriceLag24hLinearRegressionMAEResult",
        "DAMPricePersistenceVsTrainedOLSMAEComparison",
        "PreviousDayPersistenceDAMPriceForecastModel",
        "PreviousDayPersistenceBacktestCase",
        "PreviousDayPersistenceMAEResult",
        "WorkflowState",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "decimal",
        "energy_trading.application.errors",
        "energy_trading.domain.value_objects.quantities",
        "energy_trading.ml.dam_price.lag_24h_168h_features",
    }
)

ALLOWED_IMPORTED_NAMES = frozenset(
    {
        "dataclass",
        "Decimal",
        "DecimalException",
        "InvalidRequestError",
        "FiniteDecimal",
        ROW_CLASS,
    }
)

GENERIC_MODEL_NAMES = frozenset(
    {
        "Model",
        "Trainer",
        "Estimator",
        "Regressor",
        "RegressionModel",
        "Fitter",
        "Pipeline",
        "FeatureMatrix",
        "DesignMatrix",
        "Dataset",
        "DatasetSplit",
        "ModelRegistry",
        "RegressionRegistry",
        "EstimatorFactory",
        "ModelFactory",
        "ModelSelector",
        "AgentFactory",
        "ServiceLocator",
    }
)

FORBIDDEN_CODE_TOKENS = (
    "float(",
    "float)",
    "round(",
    "quantize",
    "normalize",
    "standardize",
    "scale(",
    "scaled",
    "clip(",
    "clamp",
    "max(",
    "min(",
    "abs(",
    "regulariz",
    "ridge",
    "lasso",
    "shrink",
    "epsilon",
    "eps",
    "pinv",
    "pseudo",
    "lstsq",
    "inverse",
    "predict",
    "mae",
    "mse",
    "rmse",
    "r2",
    "residual",
    "champion",
    "winner",
    "compare",
    "comparison",
    "volume",
    "sorted(",
    "sort(",
    "reverse",
    "shuffle",
    "dedup",
    "groupby",
    "group_by",
    "** 2",
    "pow(",
    "sqrt",
    "datetime.now",
    "utcnow",
    "uuid",
    "open(",
    "path(",
    "os.environ",
    "getenv",
    "print(",
    "logging",
    "await",
    "asyncio",
)

UNAWARE_MODULES = (
    FEATURES_MODULE,
    SPLIT_MODULE,
    ONE_FEATURE_MODULE,
    ONE_FEATURE_SPLIT_MODULE,
    ONE_FEATURE_FIT_MODULE,
    PREDICTION_MODULE,
    TRAINED_EVALUATION_MODULE,
    COMPARISON_MODULE,
    LIVE_ADAPTER_MODULE,
    BACKTEST_MODULE,
    PERSISTENCE_EVALUATION_MODULE,
    DAM_PRICE_PORT_MODULE,
    DAM_ML_INIT,
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


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _class_def(path: Path, class_name: str) -> ast.ClassDef:
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    msg = f"class {class_name!r} not found in {path}"
    raise AssertionError(msg)


def _function_def(path: Path, name: str) -> ast.FunctionDef:
    for node in _tree(path).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    msg = f"function {name!r} not found in {path}"
    raise AssertionError(msg)


def _module_class_names(path: Path) -> list[str]:
    return [node.name for node in _tree(path).body if isinstance(node, ast.ClassDef)]


def _public_function_names(path: Path) -> list[str]:
    return [
        node.name
        for node in _tree(path).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]


def _identifier_names(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


def _annassign_field_names(path: Path, class_name: str) -> tuple[str, ...]:
    class_def = _class_def(path, class_name)
    return tuple(
        item.target.id
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    )


def _dataclass_keywords(class_def: ast.ClassDef) -> dict[str, object]:
    for decorator in class_def.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        func = decorator.func
        if not (isinstance(func, ast.Name) and func.id == "dataclass"):
            continue
        return {
            keyword.arg: (
                keyword.value.value if isinstance(keyword.value, ast.Constant) else keyword.value
            )
            for keyword in decorator.keywords
            if keyword.arg is not None
        }
    msg = f"dataclass decorator not found on {class_def.name}"
    raise AssertionError(msg)


def _code_source(path: Path) -> str:
    """Return executable source with every docstring removed.

    The module docstring deliberately names what this fitter does not do
    (prediction, metrics, scaling, regularization, fallback), so
    forbidden-token checks run on code only.
    """

    tree = _tree(path)
    holders = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if not isinstance(node, holders):
            continue
        body = node.body
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            del body[0]
            if not body:
                body.append(ast.Pass())
    return ast.unparse(tree)


def _code_without_messages(path: Path) -> str:
    """Return executable code with docstrings and string constants removed."""

    tree = ast.parse(_code_source(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            node.value = ""
    return ast.unparse(tree)


def _call_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def _assigned_expressions(path: Path) -> dict[str, list[str]]:
    """Map each assigned or augmented name to its unparsed right-hand sides."""

    assignments: dict[str, list[str]] = {}
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments.setdefault(target.id, []).append(ast.unparse(node.value))
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            op = type(node.op).__name__
            assignments.setdefault(node.target.id, []).append(f"{op}:{ast.unparse(node.value)}")
    return assignments


def _normalized(expression: str) -> str:
    return ast.unparse(ast.parse(expression, mode="eval"))


# --- public surface -------------------------------------------------------


def test_fitter_lives_under_dam_price_ml_package() -> None:
    assert FIT_MODULE.is_relative_to(DAM_ML_ROOT)
    assert FIT_MODULE.name == f"{FIT_MODULE_NAME}.py"
    assert _module_class_names(FIT_MODULE) == [FIT_CLASS]
    assert _public_function_names(FIT_MODULE) == [FITTER]
    assert _class_def(FIT_MODULE, FIT_CLASS).bases == []


def test_fit_result_is_frozen_slotted_exact_three_fields_without_defaults() -> None:
    class_def = _class_def(FIT_MODULE, FIT_CLASS)
    assert _dataclass_keywords(class_def) == {"frozen": True, "slots": True}
    assert _annassign_field_names(FIT_MODULE, FIT_CLASS) == FIT_FIELDS
    annotations = {
        item.target.id: ast.unparse(item.annotation)
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert annotations == dict.fromkeys(FIT_FIELDS, "FiniteDecimal")
    assert all(
        item.value is None
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    )


def test_fit_result_exposes_no_identity_metric_or_metadata() -> None:
    names = set(_annassign_field_names(FIT_MODULE, FIT_CLASS))
    for forbidden in (
        "market_id",
        "currency",
        "case_count",
        "row_count",
        "timestamp",
        "cutoff",
        "mae",
        "r2",
        "residuals",
        "model_name",
        "model_version",
        "provider",
        "alpha",
        "feature_names",
        "diagnostics",
    ):
        assert forbidden not in names


def test_fitter_is_synchronous_keyword_only_and_returns_fit() -> None:
    fitter = _function_def(FIT_MODULE, FITTER)
    assert tuple(arg.arg for arg in fitter.args.posonlyargs) == ()
    assert tuple(arg.arg for arg in fitter.args.args) == ()
    assert tuple(arg.arg for arg in fitter.args.kwonlyargs) == ("training_rows",)
    assert fitter.args.vararg is None
    assert fitter.args.kwarg is None
    assert fitter.args.kw_defaults == [None]
    annotation = fitter.args.kwonlyargs[0].annotation
    assert annotation is not None
    assert ast.unparse(annotation) == f"tuple[{ROW_CLASS}, ...]"
    assert fitter.returns is not None
    assert ast.unparse(fitter.returns) == FIT_CLASS
    assert not any(isinstance(node, ast.AsyncFunctionDef) for node in ast.walk(_tree(FIT_MODULE)))


# --- OLS semantics --------------------------------------------------------


def test_both_features_and_target_participate() -> None:
    attributes = {
        node.attr for node in ast.walk(_tree(FIT_MODULE)) if isinstance(node, ast.Attribute)
    }
    for field in ("lag_24h_amount_per_mwh", "lag_168h_amount_per_mwh", "target_amount_per_mwh"):
        assert field in attributes
    for forbidden in ("volume_mwh", "hour", "weekday", "timestamp", "isoweekday"):
        assert forbidden not in attributes


def test_centered_two_feature_aggregates_are_present() -> None:
    assignments = _assigned_expressions(FIT_MODULE)
    for name in ("x1_mean", "x2_mean", "y_mean"):
        assert any(expr.startswith("_mean(") for expr in assignments[name])
    assert _normalized("lag_24h_values[index] - x1_mean") in assignments["dx1"]
    assert _normalized("lag_168h_values[index] - x2_mean") in assignments["dx2"]
    assert _normalized("targets[index] - y_mean") in assignments["dy"]
    assert "Add:dx1 * dx1" in assignments["s11"]
    assert "Add:dx2 * dx2" in assignments["s22"]
    assert "Add:dx1 * dx2" in assignments["s12"]
    assert "Add:dx1 * dy" in assignments["t1"]
    assert "Add:dx2 * dy" in assignments["t2"]


def test_determinant_coefficients_and_intercept_follow_the_normal_equations() -> None:
    assignments = _assigned_expressions(FIT_MODULE)
    assert assignments["determinant"] == [_normalized("s11 * s22 - s12 * s12")]
    assert assignments["lag_24h_coefficient"] == [
        _normalized("(t1 * s22 - t2 * s12) / determinant")
    ]
    assert assignments["lag_168h_coefficient"] == [
        _normalized("(t2 * s11 - t1 * s12) / determinant")
    ]
    assert assignments["intercept"] == [
        _normalized("y_mean - lag_24h_coefficient * x1_mean - lag_168h_coefficient * x2_mean")
    ]


def test_three_row_minimum_is_required() -> None:
    fitter = _function_def(FIT_MODULE, FITTER)
    comparisons = [ast.unparse(node) for node in ast.walk(fitter) if isinstance(node, ast.Compare)]
    assert "len(training_rows) < 3" in comparisons
    assert "at least three training rows" in FIT_MODULE.read_text(encoding="utf-8")


def test_non_positive_determinant_fails_closed_without_stabilization() -> None:
    comparisons = [
        ast.unparse(node) for node in ast.walk(_tree(FIT_MODULE)) if isinstance(node, ast.Compare)
    ]
    assert "determinant <= 0" in comparisons
    assert "_SINGULAR_DESIGN_MESSAGE" in _identifier_names(FIT_MODULE)
    code = _code_without_messages(FIT_MODULE).lower()
    for forbidden in ("epsilon", "eps", "pinv", "pseudo", "ridge", "lasso", "lstsq", "alpha"):
        assert forbidden not in code


def test_singular_design_does_not_fall_back_to_the_one_feature_fitter() -> None:
    names = imported_names(FIT_MODULE)
    assert ONE_FEATURE_FITTER not in names
    assert ONE_FEATURE_FIT_CLASS not in names
    assert "energy_trading.ml.dam_price.lag_24h_linear_regression" not in imported_modules(
        FIT_MODULE
    )
    source = FIT_MODULE.read_text(encoding="utf-8")
    assert ONE_FEATURE_FITTER not in source
    assert ONE_FEATURE_FIT_CLASS not in source
    assert "slope" not in _code_without_messages(FIT_MODULE)


# --- Decimal semantics ----------------------------------------------------


def test_fitter_uses_decimal_only_arithmetic() -> None:
    code = _code_without_messages(FIT_MODULE).lower()
    for forbidden in FORBIDDEN_CODE_TOKENS:
        assert forbidden not in code, forbidden
    identifiers = _identifier_names(FIT_MODULE)
    for forbidden in ("float", "round", "quantize", "normalize", "isfinite", "sum"):
        assert forbidden not in identifiers
    assert "Decimal" in identifiers
    assert "is_finite" in _call_names(_tree(FIT_MODULE))


def test_only_decimal_exception_is_translated() -> None:
    handlers = [node for node in ast.walk(_tree(FIT_MODULE)) if isinstance(node, ast.ExceptHandler)]
    assert handlers
    for handler in handlers:
        assert handler.type is not None
        assert ast.unparse(handler.type) == "DecimalException"
    code = _code_source(FIT_MODULE)
    assert "except Exception" not in code
    assert "except BaseException" not in code
    assert not any(handler.type is None for handler in handlers)


# --- no sort / repair -----------------------------------------------------


def test_fitter_does_not_sort_reverse_shuffle_deduplicate_or_group() -> None:
    calls = _call_names(_tree(FIT_MODULE))
    for forbidden in ("sorted", "sort", "reverse", "reversed", "shuffle", "groupby", "sample"):
        assert forbidden not in calls
    identifiers = _identifier_names(FIT_MODULE)
    assert "_DUPLICATE_TIMESTAMP_MESSAGE" in identifiers
    assert "_OUT_OF_ORDER_MESSAGE" in identifiers


def test_fitter_fails_closed_with_sanitized_static_messages() -> None:
    source = FIT_MODULE.read_text(encoding="utf-8")
    for phrase in (
        "requires at least three training rows",
        "requires rows from exactly one market",
        "requires rows in exactly one currency",
        "requires unique target timestamps",
        "requires strictly increasing target timestamps",
        "requires a full-rank two-feature design",
        "requires finite feature and target values",
        "requires finite fitted coefficients and intercept",
    ):
        assert phrase in source
    for leak in ("AMD", "EUR", "market-alpha", "market-beta"):
        assert leak not in source
    assert not any(isinstance(node, ast.JoinedStr) for node in ast.walk(_tree(FIT_MODULE)))


# --- dependency boundary --------------------------------------------------


def test_fitter_depends_only_on_allowed_inward_contracts() -> None:
    modules = imported_modules(FIT_MODULE)
    leaked = sorted(module for module in modules if is_forbidden(module, FORBIDDEN_PREFIXES))
    assert leaked == []
    assert modules == ALLOWED_MODULE_IMPORTS
    assert imported_names(FIT_MODULE) == ALLOWED_IMPORTED_NAMES | ALLOWED_MODULE_IMPORTS
    leaked_types = sorted(
        name for name in annotation_type_names(FIT_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_fitter_does_not_rebuild_features_split_or_consume_raw_history() -> None:
    source = FIT_MODULE.read_text(encoding="utf-8")
    code = _code_source(FIT_MODULE)
    for forbidden in (FEATURE_BUILDER, SPLITTER, SPLIT_CLASS):
        assert forbidden not in source
    for forbidden in ("MarketPriceRecord", "EnergyPrice", "history", f"{ROW_CLASS}("):
        assert forbidden not in code


def test_fitter_does_not_depend_on_other_dam_price_artifacts() -> None:
    names = imported_names(FIT_MODULE)
    for forbidden in (
        "DAMPriceLag24hFeatureRow",
        "build_dam_price_lag_24h_feature_rows",
        "DAMPriceChronologicalFeatureSplit",
        "split_dam_price_feature_rows_chronologically",
        ONE_FEATURE_FIT_CLASS,
        ONE_FEATURE_FITTER,
        "DAMPriceLag24hLinearRegressionPrediction",
        "predict_dam_price_lag_24h_linear_regression",
        "DAMPriceLag24hLinearRegressionMAEResult",
        "evaluate_dam_price_lag_24h_linear_regression_mae",
        "DAMPricePersistenceVsTrainedOLSMAEComparison",
        "compare_dam_price_persistence_vs_trained_ols_mae",
        "PreviousDayPersistenceDAMPriceForecastModel",
        "PreviousDayPersistenceBacktestCase",
        "build_previous_day_persistence_backtest_cases",
        "PreviousDayPersistenceMAEResult",
        "evaluate_previous_day_persistence_mae",
        "DAMPriceForecastModelRequest",
        "PriceForecastPoint",
    ):
        assert forbidden not in names
    code = _code_without_messages(FIT_MODULE).lower()
    for forbidden in ("previous_day_persistence", "comparison", "consumer", "prediction"):
        assert forbidden not in code


def test_no_generic_ml_framework_exists() -> None:
    class_names = [name for path in ML_ROOT.rglob("*.py") for name in _module_class_names(path)]
    leaked_classes = sorted(name for name in class_names if name in GENERIC_MODEL_NAMES)
    assert leaked_classes == []
    leaked_ids = sorted(
        name for name in _identifier_names(FIT_MODULE) if name in GENERIC_MODEL_NAMES
    )
    assert leaked_ids == []
    assert not any(
        module.startswith("energy_trading.ml.common") for module in imported_modules(FIT_MODULE)
    )
    source = FIT_MODULE.read_text(encoding="utf-8").lower()
    for forbidden in ("registry", "selector", "servicelocator", "agentfactory", "protocol"):
        assert forbidden not in source


# --- unwired status -------------------------------------------------------


def test_published_dam_price_modules_remain_unaware_of_the_two_feature_fit() -> None:
    for path in UNAWARE_MODULES:
        source = path.read_text(encoding="utf-8")
        assert FIT_CLASS not in source
        assert FITTER not in source
        assert FIT_MODULE_NAME not in source
        names = imported_names(path)
        assert FIT_CLASS not in names
        assert FITTER not in names


def test_application_agents_do_not_import_the_two_feature_fit() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert FIT_CLASS not in names
        assert FITTER not in names
        assert FIT_MODULE_NAME not in path.read_text(encoding="utf-8")


def test_orchestration_and_langgraph_do_not_import_the_two_feature_fit() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert FIT_CLASS not in names
        assert FITTER not in names
        assert FIT_MODULE_NAME not in path.read_text(encoding="utf-8")
    graph_modules = imported_modules(GRAPH_MODULE)
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in graph_modules
    )


def test_api_composition_does_not_import_or_construct_the_two_feature_fit() -> None:
    assert collect_import_violations(API_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert FIT_CLASS not in names
        assert FITTER not in names
        assert FIT_MODULE_NAME not in path.read_text(encoding="utf-8")
    create_app = _function_def(API_APP, "create_app")
    call_names = _call_names(create_app)
    assert FITTER not in call_names
    assert FIT_CLASS not in call_names


def test_workflow_state_shape_is_unchanged() -> None:
    assert _annassign_field_names(STATE_MODULE, "WorkflowState") == WORKFLOW_STATE_FIELDS
    assert FIT_CLASS not in imported_names(STATE_MODULE)
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert FIT_MODULE_NAME not in source
    assert "dam_price" not in source
