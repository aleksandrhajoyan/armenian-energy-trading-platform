"""Lag-24h DAM Price OLS prediction stays a narrow ML evaluation artifact."""

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
PREDICTION_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression_prediction.py"
FEATURES_MODULE = DAM_ML_ROOT / "lag_24h_features.py"
SPLIT_MODULE = DAM_ML_ROOT / "chronological_feature_split.py"
FIT_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression.py"
LIVE_ADAPTER_MODULE = DAM_ML_ROOT / "previous_day_persistence.py"
BACKTEST_MODULE = DAM_ML_ROOT / "previous_day_persistence_backtest.py"
EVALUATION_MODULE = DAM_ML_ROOT / "previous_day_persistence_evaluation.py"
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

PREDICTION_CLASS = "DAMPriceLag24hLinearRegressionPrediction"
PREDICTOR = "predict_dam_price_lag_24h_linear_regression"
ROW_CLASS = "DAMPriceLag24hFeatureRow"
FIT_CLASS = "DAMPriceLag24hLinearRegressionFit"
FEATURE_BUILDER = "build_dam_price_lag_24h_feature_rows"
SPLITTER = "split_dam_price_feature_rows_chronologically"
SPLIT_CLASS = "DAMPriceChronologicalFeatureSplit"
FITTER = "fit_dam_price_lag_24h_linear_regression"

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.infrastructure",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.application.ports",
    "energy_trading.ml.common",
    "energy_trading.ml.consumer_load",
    "energy_trading.ml.dam_price.chronological_feature_split",
    "energy_trading.ml.dam_price.previous_day_persistence",
    "energy_trading.ml.dam_price.previous_day_persistence_backtest",
    "energy_trading.ml.dam_price.previous_day_persistence_evaluation",
    "energy_trading.domain.models.observations",
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
        "Predictor",
        "ModelRegistry",
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
        "energy_trading.domain.value_objects.time",
        "energy_trading.ml.dam_price.lag_24h_features",
        "energy_trading.ml.dam_price.lag_24h_linear_regression",
    }
)

GENERIC_MODEL_NAMES = frozenset(
    {
        "Model",
        "Trainer",
        "Estimator",
        "Regressor",
        "Fitter",
        "Predictor",
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

PREDICTION_FIELDS = (
    "market_id",
    "currency",
    "target_timestamp",
    "predicted_amount_per_mwh",
    "actual_amount_per_mwh",
)

PREDICTION_ANNOTATIONS = {
    "market_id": "EntityId",
    "currency": "CurrencyCode",
    "target_timestamp": "UtcDateTime",
    "predicted_amount_per_mwh": "FiniteDecimal",
    "actual_amount_per_mwh": "FiniteDecimal",
}

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


def _function_def(path: Path, function_name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return node
    msg = f"function {function_name!r} not found in {path}"
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

    The module docstring deliberately names what this predictor does not do
    (float conversion, clamping, scaling, currency conversion) and which
    canonical types it is not (``EnergyPrice``, ``PriceForecastPoint``), so
    forbidden-token checks must run on executable code only.
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


def _assigned_value(path: Path, function_name: str, target_name: str) -> ast.expr:
    function = _function_def(path, function_name)
    for node in ast.walk(function):
        if not isinstance(node, ast.Assign):
            continue
        targets = node.targets
        if len(targets) == 1 and isinstance(targets[0], ast.Name):
            if targets[0].id == target_name:
                return node.value
    msg = f"assignment to {target_name!r} not found in {function_name!r}"
    raise AssertionError(msg)


def _prediction_call(path: Path) -> ast.Call:
    for node in ast.walk(_function_def(path, "_prediction_for_row")):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == PREDICTION_CLASS:
            return node
    msg = f"call to {PREDICTION_CLASS!r} not found"
    raise AssertionError(msg)


def _keyword_nodes(call: ast.Call) -> dict[str, ast.expr]:
    return {keyword.arg: keyword.value for keyword in call.keywords if keyword.arg is not None}


def test_predictor_lives_under_dam_price_ml_package() -> None:
    assert PREDICTION_MODULE.is_relative_to(DAM_ML_ROOT)
    assert PREDICTION_MODULE.name == "lag_24h_linear_regression_prediction.py"
    assert _module_class_names(PREDICTION_MODULE) == [PREDICTION_CLASS]
    assert _public_function_names(PREDICTION_MODULE) == [PREDICTOR]
    assert _base_names(_class_def(PREDICTION_MODULE, PREDICTION_CLASS)) == set()


def test_prediction_result_is_frozen_slotted_and_exactly_five_fields() -> None:
    class_def = _class_def(PREDICTION_MODULE, PREDICTION_CLASS)
    keywords = _dataclass_keywords(class_def)
    assert keywords == {"frozen": True, "slots": True}
    assert _annassign_field_names(PREDICTION_MODULE, PREDICTION_CLASS) == PREDICTION_FIELDS
    annotations = {
        item.target.id: ast.unparse(item.annotation)
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert annotations == PREDICTION_ANNOTATIONS
    defaults = {
        item.target.id: item.value
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert all(value is None for value in defaults.values())


def test_prediction_result_exposes_no_forecast_identity_metric_or_model_metadata() -> None:
    names = set(_annassign_field_names(PREDICTION_MODULE, PREDICTION_CLASS))
    assert names == set(PREDICTION_FIELDS)
    for forbidden in (
        "forecast_run_id",
        "generated_at",
        "model_name",
        "model_version",
        "provider",
        "residual",
        "error",
        "row_index",
        "confidence_interval",
        "metadata",
        "feature_vector",
        "prediction_timestamp",
        "case_count",
        "row_count",
        "mae",
        "mse",
        "rmse",
        "r2",
    ):
        assert forbidden not in names


def test_predictor_is_synchronous_keyword_only_and_returns_predictions() -> None:
    tree = ast.parse(PREDICTION_MODULE.read_text(encoding="utf-8"), filename=str(PREDICTION_MODULE))
    predictor = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == PREDICTOR
    )
    assert not isinstance(predictor, ast.AsyncFunctionDef)
    assert tuple(arg.arg for arg in predictor.args.args) == ()
    assert tuple(arg.arg for arg in predictor.args.kwonlyargs) == ("fit", "evaluation_rows")
    assert predictor.args.vararg is None
    assert predictor.args.kwarg is None
    assert predictor.args.kw_defaults == [None, None]
    fit_arg = predictor.args.kwonlyargs[0]
    assert fit_arg.annotation is not None
    assert ast.unparse(fit_arg.annotation) == FIT_CLASS
    rows_arg = predictor.args.kwonlyargs[1]
    assert rows_arg.annotation is not None
    assert ast.unparse(rows_arg.annotation) == f"tuple[{ROW_CLASS}, ...]"
    assert predictor.returns is not None
    assert ast.unparse(predictor.returns) == f"tuple[{PREDICTION_CLASS}, ...]"


def test_prediction_structure_is_ols_slope_times_lag_plus_intercept() -> None:
    value = _assigned_value(
        PREDICTION_MODULE,
        "_predicted_amount_per_mwh",
        "predicted_amount_per_mwh",
    )
    assert isinstance(value, ast.BinOp)
    assert isinstance(value.op, ast.Add)
    product = value.left
    intercept = value.right
    assert isinstance(product, ast.BinOp)
    assert isinstance(product.op, ast.Mult)
    assert isinstance(product.left, ast.Attribute)
    assert product.left.attr == "slope"
    assert isinstance(product.left.value, ast.Name)
    assert product.left.value.id == "fit"
    assert isinstance(product.right, ast.Attribute)
    assert product.right.attr == "lag_24h_amount_per_mwh"
    assert isinstance(intercept, ast.Attribute)
    assert intercept.attr == "intercept_amount_per_mwh"
    source = PREDICTION_MODULE.read_text(encoding="utf-8")
    for expected in (
        "predicted_amount_per_mwh = (",
        "fit.slope * row.lag_24h_amount_per_mwh + fit.intercept_amount_per_mwh",
        "row.lag_24h_amount_per_mwh.is_finite()",
        "row.target_amount_per_mwh.is_finite()",
        "fit.intercept_amount_per_mwh.is_finite()",
    ):
        assert expected in source


def test_prediction_copies_identity_currency_timestamp_and_actual() -> None:
    values = _keyword_nodes(_prediction_call(PREDICTION_MODULE))
    assert set(values) == set(PREDICTION_FIELDS)
    for field, source_attr in (
        ("market_id", "market_id"),
        ("currency", "currency"),
        ("target_timestamp", "target_timestamp"),
        ("actual_amount_per_mwh", "target_amount_per_mwh"),
    ):
        node = values[field]
        assert isinstance(node, ast.Attribute)
        assert node.attr == source_attr
        assert isinstance(node.value, ast.Name)
        assert node.value.id == "row"
    predicted = values["predicted_amount_per_mwh"]
    assert isinstance(predicted, ast.Name)
    assert predicted.id == "predicted_amount_per_mwh"


def test_predictor_preserves_supplied_row_order_without_repairing_input() -> None:
    source = PREDICTION_MODULE.read_text(encoding="utf-8")
    assert "for row in evaluation_rows" in source
    code = _code_source(PREDICTION_MODULE)
    for forbidden in (
        "sorted(",
        "sort(",
        "reverse",
        "shuffle",
        "sample(",
        "random",
        "deduplicat",
        "evaluation_rows[1:]",
        "rows[1:] +",
    ):
        assert forbidden not in code
    identifiers = _identifier_names(PREDICTION_MODULE)
    for forbidden in ("sorted", "sort", "reverse", "shuffle"):
        assert forbidden not in identifiers


def test_predictor_uses_decimal_only_arithmetic() -> None:
    code = _code_source(PREDICTION_MODULE)
    for forbidden in (
        "float(",
        "float)",
        "round(",
        "quantize",
        "normalize",
        "standardize",
        "scale(",
        "clip(",
        "clamp",
        "floor(",
        "ceil(",
        "regulariz",
        "numpy",
        "sklearn",
        "pandas",
    ):
        assert forbidden not in code
    identifiers = _identifier_names(PREDICTION_MODULE)
    assert "float" not in identifiers
    assert "round" not in identifiers
    assert "quantize" not in identifiers
    assert "Decimal" in identifiers
    assert "DecimalException" in identifiers
    assert "isfinite" not in identifiers
    # Finiteness is checked with the Decimal-native method.
    assert ".is_finite()" in code


def test_predictor_performs_no_currency_or_unit_conversion() -> None:
    code = _code_source(PREDICTION_MODULE).lower()
    for forbidden in (
        "exchange",
        "fx_rate",
        "fx_conversion",
        "convert_currency",
        "base_currency",
        "conversion_rate",
        "unit_convert",
    ):
        assert forbidden not in code
    # Currency is copied as identity only and never enters the computation.
    source = PREDICTION_MODULE.read_text(encoding="utf-8")
    assert "currency=row.currency" in source


def test_only_narrowed_decimal_exception_handling_is_used() -> None:
    code = _code_source(PREDICTION_MODULE)
    assert "except DecimalException" in code
    assert "except Exception" not in code
    assert "except BaseException" not in code
    assert "except (" not in code
    source = PREDICTION_MODULE.read_text(encoding="utf-8")
    assert "_NON_FINITE_PREDICTION_MESSAGE" in source
    assert "raise InvalidRequestError(msg) from error" in source


def _flattened_source(path: Path) -> str:
    """Return source with string literals de-quoted and whitespace collapsed.

    Ruff format may wrap one long message constant into implicit string
    concatenation across lines, which is a formatting artifact rather than a
    semantic difference. Removing quote characters and collapsing whitespace
    lets message-phrase checks see the concatenated message text.
    """

    return " ".join(path.read_text(encoding="utf-8").replace('"', "").split())


def test_predictor_fails_closed_with_sanitized_messages() -> None:
    source = PREDICTION_MODULE.read_text(encoding="utf-8")
    assert source.count("InvalidRequestError") >= 8
    for message_name in (
        "_EMPTY_ROWS_MESSAGE",
        "_MIXED_MARKET_MESSAGE",
        "_MIXED_CURRENCY_MESSAGE",
        "_DUPLICATE_TIMESTAMP_MESSAGE",
        "_OUT_OF_ORDER_MESSAGE",
        "_NON_FINITE_FIT_MESSAGE",
        "_NON_FINITE_INPUT_MESSAGE",
        "_NON_FINITE_PREDICTION_MESSAGE",
    ):
        assert message_name in source
    for phrase in (
        "requires at least one evaluation row",
        "requires rows from exactly one market",
        "requires rows in exactly one currency",
        "requires unique target timestamps",
        "requires strictly increasing target timestamps",
        "requires finite fitted parameters",
        "requires finite feature and target values",
        "requires finite predicted values",
    ):
        assert phrase in _flattened_source(PREDICTION_MODULE)
    for leak in ("AMD", "EUR", "market-alpha", "market-beta"):
        assert leak not in source


def test_predictor_depends_only_on_allowed_inward_contracts() -> None:
    leaked = sorted(
        module
        for module in imported_modules(PREDICTION_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(PREDICTION_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(PREDICTION_MODULE)
    assert "InvalidRequestError" in names
    assert "FiniteDecimal" in names
    assert "EntityId" in names
    assert "CurrencyCode" in names
    assert "UtcDateTime" in names
    assert "Decimal" in names
    assert "DecimalException" in names
    assert "dataclass" in names
    assert ROW_CLASS in names
    assert FIT_CLASS in names
    leaked_types = sorted(
        name for name in annotation_type_names(PREDICTION_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_predictor_does_not_depend_on_the_splitter_or_feature_builder() -> None:
    names = imported_names(PREDICTION_MODULE)
    assert SPLIT_CLASS not in names
    assert SPLITTER not in names
    assert FEATURE_BUILDER not in names
    assert FITTER not in names
    assert "MarketPriceRecord" not in names
    modules = imported_modules(PREDICTION_MODULE)
    assert "energy_trading.ml.dam_price.chronological_feature_split" not in modules
    assert "energy_trading.ml.dam_price.lag_24h_features" in modules
    source = PREDICTION_MODULE.read_text(encoding="utf-8")
    for forbidden in (
        SPLIT_CLASS,
        SPLITTER,
        FEATURE_BUILDER,
        FITTER,
        "build_dam_price_lag_24h_feature_rows(",
    ):
        assert forbidden not in source
    # The predictor never constructs the fit it receives or a price object.
    assert "DAMPriceLag24hLinearRegressionFit(" not in source
    assert "EnergyPrice(" not in source
    assert "DAMPriceLag24hFeatureRow(" not in source


def test_predictor_does_not_depend_on_persistence_artifacts() -> None:
    names = imported_names(PREDICTION_MODULE)
    for forbidden in (
        "PreviousDayPersistenceDAMPriceForecastModel",
        "PreviousDayPersistenceBacktestCase",
        "PreviousDayPersistenceMAEResult",
        "DAMPriceForecastModelRequest",
        "DAMPriceForecastModelPort",
        "PriceForecastPoint",
    ):
        assert forbidden not in names
    modules = imported_modules(PREDICTION_MODULE)
    for forbidden in (
        "energy_trading.ml.dam_price.previous_day_persistence",
        "energy_trading.ml.dam_price.previous_day_persistence_backtest",
        "energy_trading.ml.dam_price.previous_day_persistence_evaluation",
        "energy_trading.domain.models.forecasting",
        "energy_trading.domain.models.observations",
    ):
        assert forbidden not in modules
    source = PREDICTION_MODULE.read_text(encoding="utf-8")
    for forbidden in (
        "PreviousDayPersistenceDAMPriceForecastModel",
        "PreviousDayPersistenceBacktestCase",
        "PreviousDayPersistenceMAEResult",
        "build_previous_day_persistence_backtest_cases",
        "evaluate_previous_day_persistence_mae",
    ):
        assert forbidden not in source


def test_predictor_is_offline_only_and_not_live_inference() -> None:
    code = _code_source(PREDICTION_MODULE).lower()
    for forbidden in (
        "priceforecastpoint",
        "energyprice",
        "dampriceforecastmodelrequest",
        "dampriceforecastmodelport",
        "forecastingexecutionport",
        "forecast_run_id",
        "generated_at",
        "model_registry",
        "pickle",
        "joblib",
        "open(",
        "path(",
        "os.environ",
        "getenv",
        "datetime.now",
        "utcnow",
        "uuid",
        "asyncio",
        "print(",
        "logging",
    ):
        assert forbidden not in code
    source = PREDICTION_MODULE.read_text(encoding="utf-8")
    for forbidden in (
        "DAMPriceForecastModelRequest",
        "DAMPriceForecastModelPort",
        "ForecastingExecutionPort",
        "PriceForecastPoint",
        "EnergyPrice",
    ):
        assert forbidden not in _code_source(PREDICTION_MODULE)
    modules = imported_modules(PREDICTION_MODULE)
    for absent in ("asyncio", "datetime", "uuid", "random", "secrets", "os", "io", "pathlib"):
        assert absent not in modules
    assert "registry" not in source.lower()
    assert "selector" not in source.lower()


def test_predictor_has_no_metric_or_comparison() -> None:
    code = _code_source(PREDICTION_MODULE).lower()
    for forbidden in (
        "mae",
        "mse",
        "rmse",
        "mape",
        "residual",
        "champion",
        "compare",
        "persistence_vs",
        "improvement",
        "winner",
    ):
        assert forbidden not in code


def test_no_generic_model_framework_exists() -> None:
    class_names = [name for path in ML_ROOT.rglob("*.py") for name in _module_class_names(path)]
    leaked_classes = sorted(name for name in class_names if name in GENERIC_MODEL_NAMES)
    assert leaked_classes == []
    identifiers = _identifier_names(PREDICTION_MODULE)
    leaked_ids = sorted(name for name in identifiers if name in GENERIC_MODEL_NAMES)
    assert leaked_ids == []
    common_imports = imported_modules(PREDICTION_MODULE)
    assert not any(module.startswith("energy_trading.ml.common") for module in common_imports)
    assert "energy_trading.ml.common" in FORBIDDEN_PREFIXES


def test_published_dam_price_modules_remain_unaware_of_the_predictor() -> None:
    for path in (
        FEATURES_MODULE,
        SPLIT_MODULE,
        FIT_MODULE,
        LIVE_ADAPTER_MODULE,
        BACKTEST_MODULE,
        EVALUATION_MODULE,
    ):
        source = path.read_text(encoding="utf-8")
        assert PREDICTION_CLASS not in source
        assert PREDICTOR not in source
        assert "lag_24h_linear_regression_prediction" not in source


def test_application_agents_do_not_import_the_predictor() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert PREDICTION_CLASS not in names
        assert PREDICTOR not in names
        source = path.read_text(encoding="utf-8")
        assert "lag_24h_linear_regression_prediction" not in source


def test_orchestration_and_langgraph_do_not_import_the_predictor() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert PREDICTION_CLASS not in names
        assert PREDICTOR not in names
        source = path.read_text(encoding="utf-8")
        assert "lag_24h_linear_regression_prediction" not in source
    graph_modules = imported_modules(GRAPH_MODULE)
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in graph_modules
    )


def test_api_composition_does_not_import_or_construct_the_predictor() -> None:
    assert collect_import_violations(API_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert PREDICTION_CLASS not in names
        assert PREDICTOR not in names
        source = path.read_text(encoding="utf-8")
        assert "lag_24h_linear_regression_prediction" not in source
    app_source = API_APP.read_text(encoding="utf-8")
    assert PREDICTOR not in app_source
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
    assert PREDICTOR not in call_names
    assert PREDICTION_CLASS not in call_names


def test_workflow_state_shape_is_unchanged() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert PREDICTION_CLASS not in names
    assert PREDICTOR not in names
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "lag_24h_linear_regression_prediction" not in source
    assert "dam_price" not in source
