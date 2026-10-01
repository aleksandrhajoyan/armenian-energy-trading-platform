"""Lag-24h DAM Price OLS MAE evaluator stays a narrow ML evaluation artifact."""

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
EVALUATION_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression_evaluation.py"
PREDICTION_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression_prediction.py"
FEATURES_MODULE = DAM_ML_ROOT / "lag_24h_features.py"
SPLIT_MODULE = DAM_ML_ROOT / "chronological_feature_split.py"
FIT_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression.py"
LIVE_ADAPTER_MODULE = DAM_ML_ROOT / "previous_day_persistence.py"
BACKTEST_MODULE = DAM_ML_ROOT / "previous_day_persistence_backtest.py"
PERSISTENCE_EVALUATION_MODULE = DAM_ML_ROOT / "previous_day_persistence_evaluation.py"
DAM_PRICE_PORT_MODULE = PRODUCTION_ROOT / "application" / "ports" / "dam_price_forecast_model.py"
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

RESULT_CLASS = "DAMPriceLag24hLinearRegressionMAEResult"
EVALUATOR = "evaluate_dam_price_lag_24h_linear_regression_mae"
PREDICTION_CLASS = "DAMPriceLag24hLinearRegressionPrediction"
PREDICTOR = "predict_dam_price_lag_24h_linear_regression"
FIT_CLASS = "DAMPriceLag24hLinearRegressionFit"
FITTER = "fit_dam_price_lag_24h_linear_regression"
ROW_CLASS = "DAMPriceLag24hFeatureRow"
FEATURE_BUILDER = "build_dam_price_lag_24h_feature_rows"
SPLITTER = "split_dam_price_feature_rows_chronologically"

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.infrastructure",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.application.ports",
    "energy_trading.ml.common",
    "energy_trading.ml.consumer_load",
    "energy_trading.ml.dam_price.lag_24h_features",
    "energy_trading.ml.dam_price.chronological_feature_split",
    "energy_trading.ml.dam_price.lag_24h_linear_regression",
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
        "ModelSelector",
        "Metric",
        "MetricPort",
        "Evaluator",
        "EvaluatorPort",
        "Scorer",
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
        "energy_trading.ml.dam_price.lag_24h_linear_regression_prediction",
    }
)

GENERIC_METRIC_NAMES = frozenset(
    {
        "Metric",
        "Metrics",
        "MetricPort",
        "MetricsPort",
        "Evaluator",
        "EvaluatorPort",
        "Scorer",
        "ScorePort",
        "MetricRegistry",
        "ModelRegistry",
        "ModelSelector",
        "AgentFactory",
        "ServiceLocator",
        "Backtester",
        "Champion",
        "ChampionSelector",
    }
)

OTHER_METRIC_TOKENS = (
    "mse",
    "rmse",
    "mape",
    "smape",
    "r2",
    "r_squared",
    "bias",
    "median_absolute_error",
    "max_error",
    "residual",
    "residuals",
    "percentage_error",
    "directional_accuracy",
    "standard_deviation",
    "std_dev",
)

REPAIR_TOKENS = (
    "sorted(",
    ".sort(",
    "reverse",
    "shuffle",
    "groupby",
    "drop_duplicates",
    "deduplicat",
    "truncat",
    "skip",
)

RESULT_FIELDS = ("case_count", "currency", "mae_amount_per_mwh")

RESULT_ANNOTATIONS = {
    "case_count": "int",
    "currency": "CurrencyCode",
    "mae_amount_per_mwh": "FiniteDecimal",
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

UNAWARE_MODULES = (
    FEATURES_MODULE,
    SPLIT_MODULE,
    FIT_MODULE,
    PREDICTION_MODULE,
    LIVE_ADAPTER_MODULE,
    BACKTEST_MODULE,
    PERSISTENCE_EVALUATION_MODULE,
    DAM_PRICE_PORT_MODULE,
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

    The module docstring deliberately names what this evaluator does not do
    (float conversion, rounding, quantizing, clamping, scaling, currency
    conversion, other metrics, persistence comparison), so forbidden-token
    checks must run on executable code only.
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


def _flattened_source(path: Path) -> str:
    """Return source with quotes removed and whitespace collapsed.

    Ruff format may wrap long message constants into implicit string
    concatenation across lines, which is a formatting artifact rather than a
    semantic difference. Removing quote characters and collapsing whitespace
    lets message-phrase checks see the concatenated message text.
    """

    return " ".join(path.read_text(encoding="utf-8").replace('"', "").split())


def test_evaluator_lives_under_dam_price_ml_package() -> None:
    assert EVALUATION_MODULE.is_relative_to(DAM_ML_ROOT)
    assert EVALUATION_MODULE.name == "lag_24h_linear_regression_evaluation.py"
    assert _module_class_names(EVALUATION_MODULE) == [RESULT_CLASS]
    assert _public_function_names(EVALUATION_MODULE) == [EVALUATOR]
    assert _base_names(_class_def(EVALUATION_MODULE, RESULT_CLASS)) == set()


def test_result_dataclass_is_frozen_slotted_and_exactly_three_fields() -> None:
    class_def = _class_def(EVALUATION_MODULE, RESULT_CLASS)
    keywords = _dataclass_keywords(class_def)
    assert keywords == {"frozen": True, "slots": True}
    assert _annassign_field_names(EVALUATION_MODULE, RESULT_CLASS) == RESULT_FIELDS
    annotations = {
        item.target.id: ast.unparse(item.annotation)
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert annotations == RESULT_ANNOTATIONS
    leaked = sorted(name for name in annotations if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    defaults = {
        item.target.id: item.value
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert all(value is None for value in defaults.values())


def test_result_exposes_no_other_metric_identity_or_payload_field() -> None:
    names = set(_annassign_field_names(EVALUATION_MODULE, RESULT_CLASS))
    assert names == set(RESULT_FIELDS)
    for token in OTHER_METRIC_TOKENS:
        assert token not in names
    for identity in (
        "market_id",
        "model_name",
        "model_version",
        "provider",
        "total_amount",
        "target_timestamp",
        "forecast_run_id",
        "generated_at",
        "metadata",
    ):
        assert identity not in names


def test_evaluator_is_synchronous_keyword_only_and_returns_result() -> None:
    tree = ast.parse(EVALUATION_MODULE.read_text(encoding="utf-8"), filename=str(EVALUATION_MODULE))
    evaluator = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == EVALUATOR
    )
    assert not isinstance(evaluator, ast.AsyncFunctionDef)
    assert tuple(arg.arg for arg in evaluator.args.args) == ()
    assert tuple(arg.arg for arg in evaluator.args.kwonlyargs) == ("predictions",)
    assert evaluator.args.vararg is None
    assert evaluator.args.kwarg is None
    assert evaluator.args.kw_defaults == [None]
    predictions_arg = evaluator.args.kwonlyargs[0]
    assert predictions_arg.annotation is not None
    assert ast.unparse(predictions_arg.annotation) == f"tuple[{PREDICTION_CLASS}, ...]"
    assert evaluator.returns is not None
    assert ast.unparse(evaluator.returns) == RESULT_CLASS


def test_evaluator_consumes_only_chunk_176_prediction_artifacts() -> None:
    names = imported_names(EVALUATION_MODULE)
    assert PREDICTION_CLASS in names
    assert PREDICTOR not in names
    assert FIT_CLASS not in names
    assert FITTER not in names
    assert ROW_CLASS not in names
    assert FEATURE_BUILDER not in names
    assert SPLITTER not in names
    assert "DAMPriceChronologicalFeatureSplit" not in names
    assert "PreviousDayPersistenceBacktestCase" not in names
    assert "PreviousDayPersistenceMAEResult" not in names
    assert "MarketPriceRecord" not in names
    assert "EnergyPrice" not in names
    assert "DAMPriceForecastModelRequest" not in names
    assert "DAMPriceForecastModelPort" not in names
    modules = imported_modules(EVALUATION_MODULE)
    assert "energy_trading.ml.dam_price.lag_24h_linear_regression_prediction" in modules
    for forbidden in (
        "energy_trading.ml.dam_price.lag_24h_features",
        "energy_trading.ml.dam_price.chronological_feature_split",
        "energy_trading.ml.dam_price.lag_24h_linear_regression",
        "energy_trading.ml.dam_price.previous_day_persistence",
        "energy_trading.ml.dam_price.previous_day_persistence_backtest",
        "energy_trading.ml.dam_price.previous_day_persistence_evaluation",
        "energy_trading.domain.models.observations",
        "energy_trading.domain.models.forecasting",
        "energy_trading.application.ports",
    ):
        assert forbidden not in modules


def test_evaluator_depends_only_on_allowed_inward_contracts() -> None:
    leaked = sorted(
        module
        for module in imported_modules(EVALUATION_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(EVALUATION_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(EVALUATION_MODULE)
    assert "InvalidRequestError" in names
    assert "CurrencyCode" in names
    assert "FiniteDecimal" in names
    assert "Decimal" in names
    assert "DecimalException" in names
    assert "dataclass" in names
    leaked_types = sorted(
        name for name in annotation_type_names(EVALUATION_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_metric_is_mean_absolute_error_over_supplied_predictions() -> None:
    code = _code_source(EVALUATION_MODULE)
    assert f"{EVALUATOR}(" in code
    assert "total_abs_error" in code
    assert "abs(" in code
    assert "+=" in code
    assert "total_abs_error / len(predictions)" in code
    assert "case_count=len(predictions)" in code
    assert "currency=currency" in code
    assert "mae_amount_per_mwh=mae_amount_per_mwh" in code
    annotations = {
        item.target.id: ast.unparse(item.annotation)
        for item in _class_def(EVALUATION_MODULE, RESULT_CLASS).body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert annotations[RESULT_FIELDS[2]] == "FiniteDecimal"
    identifiers = _identifier_names(EVALUATION_MODULE)
    assert "sum" not in identifiers
    assert "mean" not in identifiers
    assert "abs" in identifiers
    assert "len" in identifiers


def test_absolute_value_is_used_only_for_the_error_difference() -> None:
    tree = ast.parse(EVALUATION_MODULE.read_text(encoding="utf-8"), filename=str(EVALUATION_MODULE))
    abs_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "abs"
    ]
    # One call seeds the accumulator from the first prediction; the other adds
    # each remaining prediction inside the MAE accumulation loop.
    assert len(abs_calls) == 2
    for abs_call in abs_calls:
        assert len(abs_call.args) == 1
        argument = abs_call.args[0]
        assert isinstance(argument, ast.BinOp)
        assert isinstance(argument.op, ast.Sub)
        assert isinstance(argument.left, ast.Attribute)
        assert isinstance(argument.right, ast.Attribute)
        assert argument.left.attr == "predicted_amount_per_mwh"
        assert argument.right.attr == "actual_amount_per_mwh"


def test_result_currency_comes_from_the_supplied_cohort() -> None:
    code = _code_source(EVALUATION_MODULE)
    assert "currency = _require_single_currency(predictions)" in code
    assert "currencies = {prediction.currency for prediction in predictions}" in code
    assert "next(iter(currencies))" in code
    # Currency is identity only and never enters the arithmetic.
    for forbidden in ("currency *", "* currency", "currency /", "/ currency"):
        assert forbidden not in code


def test_evaluator_does_not_sort_or_repair_malformed_cohorts() -> None:
    code = _code_source(EVALUATION_MODULE)
    for token in REPAIR_TOKENS:
        assert token not in code
    tree = ast.parse(EVALUATION_MODULE.read_text(encoding="utf-8"), filename=str(EVALUATION_MODULE))
    forbidden_calls: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else None
        if name is None and isinstance(func, ast.Attribute):
            name = func.attr
        if name in {"sorted", "sort", "reverse", "shuffle", "deduplicate", "sample"}:
            forbidden_calls.append(name)
    assert forbidden_calls == []
    identifiers = _identifier_names(EVALUATION_MODULE)
    for forbidden in ("sorted", "sort", "reverse", "shuffle", "sample"):
        assert forbidden not in identifiers


def test_evaluator_uses_canonical_decimal_arithmetic_only() -> None:
    code = _code_source(EVALUATION_MODULE)
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
        "Decimal(",
        "sqrt(",
        "**",
    ):
        assert forbidden not in code
    identifiers = _identifier_names(EVALUATION_MODULE)
    assert "float" not in identifiers
    assert "round" not in identifiers
    assert "quantize" not in identifiers
    assert "isfinite" not in identifiers
    assert "sum" not in identifiers
    assert "Decimal" in identifiers
    assert "DecimalException" in identifiers
    # Finiteness is checked with the Decimal-native method, not a math helper.
    assert ".is_finite()" in code
    assert "mae_amount_per_mwh.is_finite()" in code


def test_only_narrowed_decimal_exception_handling_is_used() -> None:
    code = _code_source(EVALUATION_MODULE)
    assert "except DecimalException" in code
    assert "except Exception" not in code
    assert "except BaseException" not in code
    assert "except (" not in code
    source = EVALUATION_MODULE.read_text(encoding="utf-8")
    assert source.count("raise InvalidRequestError(msg) from error") == 2
    assert "_NON_FINITE_MAE_MESSAGE" in source


def test_evaluator_fails_closed_with_sanitized_messages() -> None:
    source = EVALUATION_MODULE.read_text(encoding="utf-8")
    assert source.count("InvalidRequestError") >= 9
    for message_name in (
        "_EMPTY_PREDICTIONS_MESSAGE",
        "_MIXED_MARKET_MESSAGE",
        "_MIXED_CURRENCY_MESSAGE",
        "_DUPLICATE_TIMESTAMP_MESSAGE",
        "_OUT_OF_ORDER_MESSAGE",
        "_NON_FINITE_VALUES_MESSAGE",
        "_NON_FINITE_MAE_MESSAGE",
    ):
        assert message_name in source
    flattened = _flattened_source(EVALUATION_MODULE)
    for phrase in (
        "requires at least one prediction",
        "requires predictions from exactly one market",
        "requires predictions in exactly one currency",
        "requires unique target timestamps",
        "requires strictly increasing target timestamps",
        "requires finite predicted and actual values",
        "requires a finite MAE",
    ):
        assert phrase in flattened
    for leak in ("AMD", "EUR", "market-alpha", "market-beta", "111.11", "222.22"):
        assert leak not in source


def test_evaluator_has_no_fx_weighting_or_pnl_arithmetic() -> None:
    code = _code_source(EVALUATION_MODULE).lower()
    for forbidden in (
        "fx",
        "exchange",
        "conversion_rate",
        "convert_currency",
        "base_currency",
        "volume",
        "revenue",
        "profit",
        "pnl",
        "p_and_l",
        "weight",
        "total_amount",
        "return_on",
    ):
        assert forbidden not in code
    source = EVALUATION_MODULE.read_text(encoding="utf-8")
    # The evaluator scores supplied artifacts; it never constructs a new
    # prediction or a canonical price of its own.
    assert f"{PREDICTION_CLASS}(" not in source
    assert "EnergyPrice(" not in source


def test_evaluator_has_no_other_metric_or_comparison() -> None:
    code = _code_source(EVALUATION_MODULE).lower()
    for token in OTHER_METRIC_TOKENS:
        assert token not in code
    identifiers = {name.lower() for name in _identifier_names(EVALUATION_MODULE)}
    for token in OTHER_METRIC_TOKENS:
        assert token not in identifiers
    for forbidden in (
        "champion",
        "winner",
        "improvement",
        "compare",
        "persistence_vs",
        "selection",
    ):
        assert forbidden not in code


def test_no_generic_metric_framework_exists() -> None:
    class_names = [name for path in ML_ROOT.rglob("*.py") for name in _module_class_names(path)]
    leaked_classes = sorted(name for name in class_names if name in GENERIC_METRIC_NAMES)
    assert leaked_classes == []
    identifiers = _identifier_names(EVALUATION_MODULE)
    leaked_ids = sorted(name for name in identifiers if name in GENERIC_METRIC_NAMES)
    assert leaked_ids == []
    code = _code_source(EVALUATION_MODULE)
    assert "energy_trading.ml.common" not in code
    assert not any(
        module.startswith("energy_trading.ml.common") for module in ALLOWED_MODULE_IMPORTS
    )


def test_evaluator_has_no_io_clock_or_environment_access() -> None:
    code = _code_source(EVALUATION_MODULE)
    for forbidden in (
        "datetime.now",
        "utcnow",
        "uuid",
        "open(",
        "Path(",
        "os.environ",
        "getenv",
        "socket",
        "asyncio",
        "print(",
        "logging",
        "json",
        "pickle",
    ):
        assert forbidden not in code
    modules = imported_modules(EVALUATION_MODULE)
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
        "json",
    ):
        assert absent not in modules


def test_published_dam_price_modules_remain_unaware_of_the_evaluator() -> None:
    for path in UNAWARE_MODULES:
        source = path.read_text(encoding="utf-8")
        assert RESULT_CLASS not in source
        assert EVALUATOR not in source
        assert "lag_24h_linear_regression_evaluation" not in source
        names = imported_names(path)
        assert RESULT_CLASS not in names
        assert EVALUATOR not in names
        assert PREDICTION_CLASS not in names
        assert PREDICTOR not in names


def test_application_agents_do_not_import_the_evaluator() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert RESULT_CLASS not in names
        assert EVALUATOR not in names
        source = path.read_text(encoding="utf-8")
        assert "lag_24h_linear_regression_evaluation" not in source


def test_orchestration_and_langgraph_do_not_import_the_evaluator() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert RESULT_CLASS not in names
        assert EVALUATOR not in names
        source = path.read_text(encoding="utf-8")
        assert "lag_24h_linear_regression_evaluation" not in source
    graph_modules = imported_modules(GRAPH_MODULE)
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in graph_modules
    )


def test_api_composition_does_not_import_or_construct_the_evaluator() -> None:
    assert collect_import_violations(API_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert RESULT_CLASS not in names
        assert EVALUATOR not in names
        source = path.read_text(encoding="utf-8")
        assert "lag_24h_linear_regression_evaluation" not in source
    app_source = API_APP.read_text(encoding="utf-8")
    assert EVALUATOR not in app_source
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
    assert EVALUATOR not in call_names
    assert RESULT_CLASS not in call_names


def test_workflow_state_shape_is_unchanged() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert RESULT_CLASS not in names
    assert EVALUATOR not in names
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "lag_24h_linear_regression_evaluation" not in source
    assert "dam_price" not in source
