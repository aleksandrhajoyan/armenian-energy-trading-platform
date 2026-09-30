"""Lag-24h DAM Price OLS fit stays a narrow ML parameter artifact."""

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
FIT_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression.py"
FEATURES_MODULE = DAM_ML_ROOT / "lag_24h_features.py"
SPLIT_MODULE = DAM_ML_ROOT / "chronological_feature_split.py"
BACKTEST_MODULE = DAM_ML_ROOT / "previous_day_persistence_backtest.py"
LIVE_ADAPTER_MODULE = DAM_ML_ROOT / "previous_day_persistence.py"
EVALUATION_MODULE = DAM_ML_ROOT / "previous_day_persistence_evaluation.py"
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

FIT_CLASS = "DAMPriceLag24hLinearRegressionFit"
FITTER = "fit_dam_price_lag_24h_linear_regression"
ROW_CLASS = "DAMPriceLag24hFeatureRow"
FEATURE_BUILDER = "build_dam_price_lag_24h_feature_rows"
SPLITTER = "split_dam_price_feature_rows_feature_rows_chronologically"
SPLITTER = "split_dam_price_feature_rows_chronologically"
SPLIT_CLASS = "DAMPriceChronologicalFeatureSplit"

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.infrastructure",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.application.ports",
    "energy_trading.ml.common",
    "energy_trading.ml.consumer_load",
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
        "PreviousDayPersistenceDAMPriceForecastModel",
        "PreviousDayPersistenceBacktestCase",
        "PreviousDayPersistenceMAEResult",
        "DAMPriceChronologicalFeatureSplit",
        "WorkflowState",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "decimal",
        "energy_trading.application.errors",
        "energy_trading.domain.value_objects.quantities",
        "energy_trading.ml.dam_price.lag_24h_features",
    }
)

GENERIC_MODEL_NAMES = frozenset(
    {
        "Model",
        "Trainer",
        "Estimator",
        "Regressor",
        "Fitter",
        "Pipeline",
        "ModelRegistry",
        "RegressionRegistry",
        "EstimatorFactory",
        "ModelSelector",
        "AgentFactory",
        "ServiceLocator",
        "Dataset",
        "DatasetSplit",
    }
)

FORBIDDEN_TOKENS = (
    "float(",
    "round(",
    "quantize",
    "normalize",
    "standardize",
    "scale(",
    "clip(",
    "regulariz",
    "lasso",
    "ridge",
    "predict",
    "mae",
    "mse",
    "rmse",
    "r2",
    "residual",
    "volume",
    "sorted(",
    "deduplicat",
    "reverse",
    "shuffle",
    "datetime.now",
    "utcnow",
    "uuid",
    "open(",
    "Path(",
    "os.environ",
    "getenv",
    "print(",
    "logging",
    "** 2",
    "pow(",
    "sqrt",
)

FIT_FIELDS = ("slope", "intercept_amount_per_mwh")

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


def _public_function_names(path: Path) -> list[str]:
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
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


def _annassign_field_names(path: Path, class_name: str) -> tuple[str, ...]:
    class_def = _class_def(path, class_name)
    names: list[str] = []
    for item in class_def.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            names.append(item.target.id)
    return tuple(names)


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
            keyword.arg: (
                keyword.value.value if isinstance(keyword.value, ast.Constant) else keyword.value
            )
            for keyword in call.keywords
            if keyword.arg is not None
        }
    msg = f"dataclass decorator not found on {class_def.name}"
    raise AssertionError(msg)


def _code_source(path: Path) -> str:
    """Return executable source with every docstring removed.

    The module docstring deliberately names what this fitter does not do
    (prediction, metrics, scaling, regularization), so forbidden-token checks
    run on code only.
    """

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
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


def test_fitter_lives_under_dam_price_ml_package() -> None:
    assert FIT_MODULE.is_relative_to(DAM_ML_ROOT)
    assert FIT_MODULE.name == "lag_24h_linear_regression.py"
    assert _module_class_names(FIT_MODULE) == [FIT_CLASS]
    assert _public_function_names(FIT_MODULE) == [FITTER]
    assert _base_names(_class_def(FIT_MODULE, FIT_CLASS)) == set()


def test_fit_result_is_frozen_slotted_and_exactly_two_fields() -> None:
    class_def = _class_def(FIT_MODULE, FIT_CLASS)
    keywords = _dataclass_keywords(class_def)
    assert keywords == {"frozen": True, "slots": True}
    assert _annassign_field_names(FIT_MODULE, FIT_CLASS) == FIT_FIELDS
    annotations = {
        item.target.id: ast.unparse(item.annotation)
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert annotations == {
        "slope": "FiniteDecimal",
        "intercept_amount_per_mwh": "FiniteDecimal",
    }
    defaults = {
        item.target.id: item.value
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert all(value is None for value in defaults.values())


def test_fit_result_exposes_no_identity_metric_or_metadata() -> None:
    names = set(_annassign_field_names(FIT_MODULE, FIT_CLASS))
    assert names == set(FIT_FIELDS)
    for forbidden in (
        "market_id",
        "currency",
        "case_count",
        "row_count",
        "mae",
        "r2",
        "residual",
        "model_name",
        "model_version",
        "timestamp",
    ):
        assert forbidden not in names


def test_fitter_is_synchronous_keyword_only_and_returns_fit() -> None:
    tree = ast.parse(FIT_MODULE.read_text(encoding="utf-8"), filename=str(FIT_MODULE))
    fitter = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == FITTER
    )
    assert not isinstance(fitter, ast.AsyncFunctionDef)
    assert tuple(arg.arg for arg in fitter.args.args) == ()
    assert tuple(arg.arg for arg in fitter.args.kwonlyargs) == ("training_rows",)
    assert fitter.args.vararg is None
    assert fitter.args.kwarg is None
    assert fitter.args.kw_defaults == [None]
    rows_arg = fitter.args.kwonlyargs[0]
    assert rows_arg.annotation is not None
    assert ast.unparse(rows_arg.annotation) == f"tuple[{ROW_CLASS}, ...]"
    assert fitter.returns is not None
    assert ast.unparse(fitter.returns) == FIT_CLASS


def test_ols_formula_is_present() -> None:
    source = FIT_MODULE.read_text(encoding="utf-8")
    # Means, covariance numerator, variance denominator, slope, intercept.
    assert "x_mean" in source
    assert "y_mean" in source
    assert "numerator" in source
    assert "denominator" in source
    assert "slope = numerator / denominator" in source
    assert "intercept = y_mean - slope * x_mean" in source
    assert "lag_24h_amount_per_mwh" in source
    assert "target_amount_per_mwh" in source
    assert "_ZERO_VARIANCE_MESSAGE" in source
    assert "denominator == 0" in source


def test_at_least_two_rows_required() -> None:
    source = FIT_MODULE.read_text(encoding="utf-8")
    assert "len(training_rows) < 2" in source
    assert "_TOO_FEW_ROWS_MESSAGE" in source
    assert "at least two training rows" in source


def test_fitter_fails_closed_with_sanitized_messages() -> None:
    source = FIT_MODULE.read_text(encoding="utf-8")
    assert source.count("InvalidRequestError") >= 8
    for message_name in (
        "_TOO_FEW_ROWS_MESSAGE",
        "_MIXED_MARKET_MESSAGE",
        "_MIXED_CURRENCY_MESSAGE",
        "_DUPLICATE_TIMESTAMP_MESSAGE",
        "_OUT_OF_ORDER_MESSAGE",
        "_ZERO_VARIANCE_MESSAGE",
        "_NON_FINITE_INPUT_MESSAGE",
        "_NON_FINITE_FIT_MESSAGE",
    ):
        assert message_name in source
    for phrase in (
        "requires at least two training rows",
        "requires rows from exactly one market",
        "requires rows in exactly one currency",
        "requires unique target timestamps",
        "requires strictly increasing target timestamps",
        "requires non-zero variance",
        "requires finite feature and target values",
        "requires finite fitted slope and intercept",
    ):
        assert phrase in source
    for leak in ("AMD", "EUR", "market-alpha", "market-beta"):
        assert leak not in source


def test_fitter_does_not_depend_on_the_splitter_or_raw_history() -> None:
    names = imported_names(FIT_MODULE)
    assert ROW_CLASS in names
    assert SPLIT_CLASS not in names
    assert SPLITTER not in names
    assert FEATURE_BUILDER not in names
    assert "MarketPriceRecord" not in names
    modules = imported_modules(FIT_MODULE)
    assert "energy_trading.ml.dam_price.lag_24h_features" in modules
    assert "energy_trading.ml.dam_price.chronological_feature_split" not in modules
    assert "energy_trading.domain.models.observations" not in modules
    source = FIT_MODULE.read_text(encoding="utf-8")
    assert SPLIT_CLASS not in source
    assert SPLITTER not in source
    assert FEATURE_BUILDER not in source
    # The fitter reads canonical amounts but never constructs a price object.
    assert "EnergyPrice(" not in source
    assert "DAMPriceLag24hFeatureRow(" not in source


def test_fitter_does_not_depend_on_persistence_artifacts() -> None:
    names = imported_names(FIT_MODULE)
    for forbidden in (
        "PreviousDayPersistenceDAMPriceForecastModel",
        "PreviousDayPersistenceBacktestCase",
        "PreviousDayPersistenceMAEResult",
        "DAMPriceForecastModelRequest",
        "PriceForecastPoint",
    ):
        assert forbidden not in names
    modules = imported_modules(FIT_MODULE)
    for forbidden in (
        "energy_trading.ml.dam_price.previous_day_persistence",
        "energy_trading.ml.dam_price.previous_day_persistence_backtest",
        "energy_trading.ml.dam_price.previous_day_persistence_evaluation",
        "energy_trading.domain.models.forecasting",
    ):
        assert forbidden not in modules
    source = FIT_MODULE.read_text(encoding="utf-8")
    for forbidden in (
        "PreviousDayPersistenceDAMPriceForecastModel",
        "PreviousDayPersistenceBacktestCase",
        "PreviousDayPersistenceMAEResult",
        "build_previous_day_persistence_backtest_cases",
        "evaluate_previous_day_persistence_mae",
    ):
        assert forbidden not in source


def test_fitter_depends_only_on_allowed_inward_contracts() -> None:
    leaked = sorted(
        module
        for module in imported_modules(FIT_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(FIT_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(FIT_MODULE)
    assert "InvalidRequestError" in names
    assert "FiniteDecimal" in names
    assert "Decimal" in names
    assert "DecimalException" in names
    assert "dataclass" in names
    leaked_types = sorted(
        name for name in annotation_type_names(FIT_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_fitter_uses_decimal_only_arithmetic() -> None:
    code = _code_source(FIT_MODULE)
    for forbidden in (
        "float(",
        "float)",
        "round(",
        "quantize",
        "normalize",
        "standardize",
        "clip(",
        "regulariz",
        "numpy",
        "sklearn",
        "pandas",
    ):
        assert forbidden not in code
    identifiers = _identifier_names(FIT_MODULE)
    assert "float" not in identifiers
    assert "round" not in identifiers
    assert "quantize" not in identifiers
    assert "Decimal" in identifiers
    assert "isfinite" not in identifiers
    # Finiteness is checked with the Decimal-native method.
    assert ".is_finite()" in code


def test_fitter_does_not_sort_or_repair_input() -> None:
    source = FIT_MODULE.read_text(encoding="utf-8")
    code = _code_source(FIT_MODULE)
    for forbidden in ("sorted(", "sort(", "reverse", "shuffle", "deduplicat"):
        assert forbidden not in code
    assert "_DUPLICATE_TIMESTAMP_MESSAGE" in source
    assert "_OUT_OF_ORDER_MESSAGE" in source


def test_fitter_has_no_prediction_metric_or_comparison() -> None:
    code = _code_source(FIT_MODULE).lower()
    for forbidden in (
        "predict",
        "mae",
        "mse",
        "rmse",
        "residual",
        "champion",
        "compare",
        "persistence_vs",
        "forecast_run_id",
        "energyprice",
        "priceforecastpoint",
    ):
        assert forbidden not in code


def test_fitter_uses_only_the_lag_feature_and_target() -> None:
    source = FIT_MODULE.read_text(encoding="utf-8")
    # Only the two canonical amount attributes participate as x and y.
    assert source.count("lag_24h_amount_per_mwh") >= 1
    assert source.count("target_amount_per_mwh") >= 1
    for forbidden in (
        "volume_mwh",
        "target_timestamp.timestamp()",
        "hour",
        "weekday",
        "lag_168h",
        "rolling",
        "diff(",
        "pct_change",
    ):
        assert forbidden not in source


def test_no_generic_model_framework_exists() -> None:
    class_names = [name for path in ML_ROOT.rglob("*.py") for name in _module_class_names(path)]
    leaked_classes = sorted(name for name in class_names if name in GENERIC_MODEL_NAMES)
    assert leaked_classes == []
    identifiers = _identifier_names(FIT_MODULE)
    leaked_ids = sorted(name for name in identifiers if name in GENERIC_MODEL_NAMES)
    assert leaked_ids == []
    common_imports = imported_modules(FIT_MODULE)
    assert not any(module.startswith("energy_trading.ml.common") for module in common_imports)
    assert "energy_trading.ml.common" in FORBIDDEN_PREFIXES
    source = FIT_MODULE.read_text(encoding="utf-8")
    assert "registry" not in source.lower()
    assert "selector" not in source.lower()
    assert "ServiceLocator" not in source
    assert "AgentFactory" not in source


def test_fitter_has_no_io_clock_or_environment_access() -> None:
    source = FIT_MODULE.read_text(encoding="utf-8")
    for forbidden in (
        "datetime.now",
        "utcnow",
        "uuid4",
        "uuid.",
        "Clock",
        "open(",
        "Path(",
        "os.environ",
        "getenv",
        "socket",
        "asyncio.sleep",
        "print(",
        "logging",
    ):
        assert forbidden not in source
    modules = imported_modules(FIT_MODULE)
    for absent in (
        "uuid",
        "random",
        "secrets",
        "os",
        "io",
        "pathlib",
        "asyncio",
        "datetime",
        "math",
    ):
        assert absent not in modules
    # Only DecimalException is translated, never a broad exception.
    code = _code_source(FIT_MODULE)
    assert "except DecimalException" in code
    assert "except Exception" not in code
    assert "except BaseException" not in code


def test_feature_split_and_persistence_modules_remain_unaware_of_the_fit() -> None:
    for path in (
        FEATURES_MODULE,
        SPLIT_MODULE,
        LIVE_ADAPTER_MODULE,
        BACKTEST_MODULE,
        EVALUATION_MODULE,
    ):
        source = path.read_text(encoding="utf-8")
        assert FIT_CLASS not in source
        assert FITTER not in source
        assert "lag_24h_linear_regression" not in source


def test_application_agents_do_not_import_the_fitter() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert FIT_CLASS not in names
        assert FITTER not in names
        source = path.read_text(encoding="utf-8")
        assert "lag_24h_linear_regression" not in source


def test_orchestration_and_langgraph_do_not_import_the_fitter() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert FIT_CLASS not in names
        assert FITTER not in names
        source = path.read_text(encoding="utf-8")
        assert "lag_24h_linear_regression" not in source
    graph_modules = imported_modules(GRAPH_MODULE)
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in graph_modules
    )


def test_api_composition_does_not_import_or_construct_the_fitter() -> None:
    assert collect_import_violations(API_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert FIT_CLASS not in names
        assert FITTER not in names
        source = path.read_text(encoding="utf-8")
        assert "lag_24h_linear_regression" not in source
    app_source = API_APP.read_text(encoding="utf-8")
    assert FITTER not in app_source
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
    assert FITTER not in call_names


def test_workflow_state_shape_is_unchanged() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert FIT_CLASS not in names
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "lag_24h_linear_regression" not in source
    assert "dam_price" not in source
