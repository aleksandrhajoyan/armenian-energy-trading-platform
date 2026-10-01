"""Aligned DAM Price persistence-versus-trained OLS comparison stays a narrow ML artifact."""

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
COMPARISON_MODULE = DAM_ML_ROOT / "persistence_vs_trained_ols_comparison.py"
PERSISTENCE_EVALUATION_MODULE = DAM_ML_ROOT / "previous_day_persistence_evaluation.py"
TRAINED_EVALUATION_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression_evaluation.py"
PERSISTENCE_BACKTEST_MODULE = DAM_ML_ROOT / "previous_day_persistence_backtest.py"
PREDICTION_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression_prediction.py"
FEATURES_MODULE = DAM_ML_ROOT / "lag_24h_features.py"
SPLIT_MODULE = DAM_ML_ROOT / "chronological_feature_split.py"
FIT_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression.py"
LIVE_ADAPTER_MODULE = DAM_ML_ROOT / "previous_day_persistence.py"
DAM_PRICE_PORT_MODULE = PRODUCTION_ROOT / "application" / "ports" / "dam_price_forecast_model.py"
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

COMPARISON_CLASS = "DAMPricePersistenceVsTrainedOLSMAEComparison"
COMPARISON_FUNCTION = "compare_dam_price_persistence_vs_trained_ols_mae"
PERSISTENCE_EVALUATOR = "evaluate_previous_day_persistence_mae"
TRAINED_EVALUATOR = "evaluate_dam_price_lag_24h_linear_regression_mae"
PERSISTENCE_CASE_CLASS = "PreviousDayPersistenceBacktestCase"
TRAINED_PREDICTION_CLASS = "DAMPriceLag24hLinearRegressionPrediction"
PERSISTENCE_RESULT_CLASS = "PreviousDayPersistenceMAEResult"
TRAINED_RESULT_CLASS = "DAMPriceLag24hLinearRegressionMAEResult"
BACKTEST_BUILDER = "build_previous_day_persistence_backtest_cases"
FEATURE_BUILDER = "build_dam_price_lag_24h_feature_rows"
SPLITTER = "split_dam_price_feature_rows_chronologically"
FITTER = "fit_dam_price_lag_24h_linear_regression"
PREDICTOR = "predict_dam_price_lag_24h_linear_regression"

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.infrastructure",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.application.ports",
    "energy_trading.ml.common",
    "energy_trading.ml.consumer_load",
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
        "Trainer",
        "Estimator",
        "Predictor",
        "Comparator",
        "Ranking",
        "Ranker",
        "Champion",
        "ChampionSelector",
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
        "DAMPriceChronologicalFeatureSplit",
        "DAMPriceLag24hFeatureRow",
        "DAMPriceLag24hLinearRegressionFit",
        "WorkflowState",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "energy_trading.application.errors",
        "energy_trading.domain.value_objects.quantities",
        "energy_trading.ml.dam_price.lag_24h_linear_regression_evaluation",
        "energy_trading.ml.dam_price.lag_24h_linear_regression_prediction",
        "energy_trading.ml.dam_price.previous_day_persistence_backtest",
        "energy_trading.ml.dam_price.previous_day_persistence_evaluation",
    }
)

GENERIC_COMPARISON_NAMES = frozenset(
    {
        "Comparator",
        "Comparer",
        "Metric",
        "Metrics",
        "MetricPort",
        "MetricRegistry",
        "Evaluator",
        "EvaluatorPort",
        "Scorer",
        "ScorePort",
        "ModelRegistry",
        "ModelSelector",
        "Ranking",
        "Ranker",
        "Champion",
        "ChampionSelector",
        "AgentFactory",
        "ServiceLocator",
        "Backtester",
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

SELECTION_TOKENS = (
    "winner",
    "champion",
    "preferred",
    "threshold",
    "improvement",
    "ranking",
    "rank(",
    "better",
    "best_model",
    "select_model",
)

REALIGNMENT_TOKENS = (
    "zip(",
    "sorted(",
    ".sort(",
    "reverse",
    "shuffle",
    "intersection",
    "intersect",
    "set(",
    "deduplicat",
    "groupby",
    "truncat",
    "tolerance",
)

RESULT_FIELDS = (
    "case_count",
    "currency",
    "persistence_mae_amount_per_mwh",
    "trained_ols_mae_amount_per_mwh",
)

RESULT_ANNOTATIONS = {
    "case_count": "int",
    "currency": "CurrencyCode",
    "persistence_mae_amount_per_mwh": "FiniteDecimal",
    "trained_ols_mae_amount_per_mwh": "FiniteDecimal",
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
    PERSISTENCE_BACKTEST_MODULE,
    PERSISTENCE_EVALUATION_MODULE,
    FEATURES_MODULE,
    SPLIT_MODULE,
    FIT_MODULE,
    PREDICTION_MODULE,
    TRAINED_EVALUATION_MODULE,
    LIVE_ADAPTER_MODULE,
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

    The module docstring deliberately names what this comparison does not do
    (winner, champion, percentage change, acceptance threshold, MAE
    recalculation), so forbidden-token checks must run on executable code only.
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


def _function_def(path: Path, function_name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return node
    msg = f"function {function_name!r} not found in {path}"
    raise AssertionError(msg)


def _function_body_source(path: Path, function_name: str) -> str:
    """Return only the unparsed body of one function.

    Import statements legitimately contain evaluator names, so delegation
    ordering assertions must be scoped to the executable body rather than the
    whole module.
    """

    function = _function_def(path, function_name)
    module = ast.Module(body=list(function.body), type_ignores=[])
    return ast.unparse(ast.fix_missing_locations(module))


def _call_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.append(func.id)
        elif isinstance(func, ast.Attribute):
            names.append(func.attr)
    return names


def test_comparison_lives_under_dam_price_ml_package() -> None:
    assert COMPARISON_MODULE.is_relative_to(DAM_ML_ROOT)
    assert COMPARISON_MODULE.name == "persistence_vs_trained_ols_comparison.py"
    assert _module_class_names(COMPARISON_MODULE) == [COMPARISON_CLASS]
    assert _public_function_names(COMPARISON_MODULE) == [COMPARISON_FUNCTION]
    assert _base_names(_class_def(COMPARISON_MODULE, COMPARISON_CLASS)) == set()


def test_comparison_result_is_frozen_slotted_and_exactly_four_fields() -> None:
    class_def = _class_def(COMPARISON_MODULE, COMPARISON_CLASS)
    keywords = _dataclass_keywords(class_def)
    assert keywords == {"frozen": True, "slots": True}
    assert _annassign_field_names(COMPARISON_MODULE, COMPARISON_CLASS) == RESULT_FIELDS
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


def test_comparison_result_exposes_no_winner_or_extra_metric_field() -> None:
    names = set(_annassign_field_names(COMPARISON_MODULE, COMPARISON_CLASS))
    assert names == set(RESULT_FIELDS)
    for token in OTHER_METRIC_TOKENS:
        assert token not in names
    for identity in (
        "market_id",
        "winner",
        "champion",
        "preferred_model",
        "improvement",
        "absolute_improvement",
        "percentage_improvement",
        "ratio",
        "threshold",
        "status",
        "confidence",
        "model_name",
        "model_version",
        "provider",
        "metadata",
        "forecast_run_id",
        "generated_at",
    ):
        assert identity not in names


def test_comparison_is_synchronous_keyword_only_and_returns_result() -> None:
    tree = ast.parse(COMPARISON_MODULE.read_text(encoding="utf-8"), filename=str(COMPARISON_MODULE))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == COMPARISON_FUNCTION
    )
    assert not isinstance(function, ast.AsyncFunctionDef)
    assert tuple(arg.arg for arg in function.args.args) == ()
    assert tuple(arg.arg for arg in function.args.kwonlyargs) == (
        "persistence_cases",
        "trained_predictions",
    )
    assert function.args.vararg is None
    assert function.args.kwarg is None
    assert function.args.kw_defaults == [None, None]
    cases_arg = function.args.kwonlyargs[0]
    assert cases_arg.annotation is not None
    assert ast.unparse(cases_arg.annotation) == f"tuple[{PERSISTENCE_CASE_CLASS}, ...]"
    predictions_arg = function.args.kwonlyargs[1]
    assert predictions_arg.annotation is not None
    assert ast.unparse(predictions_arg.annotation) == f"tuple[{TRAINED_PREDICTION_CLASS}, ...]"
    assert function.returns is not None
    assert ast.unparse(function.returns) == COMPARISON_CLASS


def test_comparison_consumes_only_aligned_source_artifacts() -> None:
    names = imported_names(COMPARISON_MODULE)
    assert PERSISTENCE_CASE_CLASS in names
    assert TRAINED_PREDICTION_CLASS in names
    assert PERSISTENCE_EVALUATOR in names
    assert TRAINED_EVALUATOR in names
    for forbidden in (
        BACKTEST_BUILDER,
        FEATURE_BUILDER,
        SPLITTER,
        FITTER,
        PREDICTOR,
        PERSISTENCE_RESULT_CLASS,
        TRAINED_RESULT_CLASS,
        "PreviousDayPersistenceDAMPriceForecastModel",
        "DAMPriceForecastModelRequest",
        "DAMPriceForecastModelPort",
        "DAMPriceForecastAgent",
        "MarketPriceRecord",
        "EnergyPrice",
        "PriceForecastPoint",
    ):
        assert forbidden not in names
    modules = imported_modules(COMPARISON_MODULE)
    assert "energy_trading.ml.dam_price.previous_day_persistence_backtest" in modules
    assert "energy_trading.ml.dam_price.lag_24h_linear_regression_prediction" in modules
    assert "energy_trading.ml.dam_price.previous_day_persistence_evaluation" in modules
    assert "energy_trading.ml.dam_price.lag_24h_linear_regression_evaluation" in modules
    for forbidden in (
        "energy_trading.ml.dam_price.lag_24h_features",
        "energy_trading.ml.dam_price.chronological_feature_split",
        "energy_trading.ml.dam_price.lag_24h_linear_regression",
        "energy_trading.ml.dam_price.previous_day_persistence",
        "energy_trading.domain.models.observations",
        "energy_trading.domain.models.forecasting",
        "energy_trading.application.ports",
    ):
        assert forbidden not in modules


def test_comparison_depends_only_on_allowed_inward_contracts() -> None:
    leaked = sorted(
        module
        for module in imported_modules(COMPARISON_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(COMPARISON_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(COMPARISON_MODULE)
    assert "InvalidRequestError" in names
    assert "CurrencyCode" in names
    assert "FiniteDecimal" in names
    assert "dataclass" in names
    leaked_types = sorted(
        name for name in annotation_type_names(COMPARISON_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_comparison_proves_alignment_before_scoring() -> None:
    code = _code_source(COMPARISON_MODULE)
    for required in (
        "if not persistence_cases and (not trained_predictions):",
        "if not persistence_cases:",
        "if not trained_predictions:",
        "if len(persistence_cases) != len(trained_predictions):",
        "case.market_id for case in persistence_cases",
        "prediction.market_id for prediction in trained_predictions",
        "if persistence_markets != trained_markets:",
        "case.predicted_price.currency != case.actual_price.currency",
        "case.actual_price.currency for case in persistence_cases",
        "prediction.currency for prediction in trained_predictions",
        "if persistence_currencies != trained_currencies:",
        "previous.target_timestamp == current.target_timestamp",
        "previous.target_timestamp > current.target_timestamp",
        "persistence_case.target_timestamp != trained_prediction.target_timestamp",
        "persistence_case.actual_price.amount_per_mwh",
        "!= trained_prediction.actual_amount_per_mwh",
    ):
        assert required in code
    # Predicted values are intentionally allowed to differ.
    assert "predicted_price.amount_per_mwh" not in code
    assert "predicted_amount_per_mwh !=" not in code


def test_comparison_uses_explicit_index_alignment_without_truncation() -> None:
    code = _code_source(COMPARISON_MODULE)
    assert "for index in range(len(persistence_cases)):" in code
    assert "persistence_cases[index]" in code
    assert "trained_predictions[index]" in code
    for token in REALIGNMENT_TOKENS:
        assert token not in code
    identifiers = _identifier_names(COMPARISON_MODULE)
    for forbidden in ("zip", "sorted", "sort", "reverse", "shuffle"):
        assert forbidden not in identifiers


def test_comparison_delegates_scoring_to_both_published_evaluators() -> None:
    calls = _call_names(COMPARISON_MODULE)
    assert calls.count(PERSISTENCE_EVALUATOR) == 1
    assert calls.count(TRAINED_EVALUATOR) == 1
    code = _code_source(COMPARISON_MODULE)
    assert f"{PERSISTENCE_EVALUATOR}(cases=persistence_cases)" in code
    assert f"{TRAINED_EVALUATOR}(" in code
    assert "predictions=trained_predictions" in code
    body = _function_body_source(COMPARISON_MODULE, COMPARISON_FUNCTION)
    persistence_call_index = body.index(f"{PERSISTENCE_EVALUATOR}(")
    trained_call_index = body.index(f"{TRAINED_EVALUATOR}(")
    # Every alignment guard must run before either evaluator is invoked.
    for guard_call in (
        "_require_nonempty_equal_cohort(",
        "_require_single_shared_market_and_currency(",
        "_require_persistence_chronology(",
        "_require_trained_chronology(",
        "_require_pairwise_alignment(",
    ):
        guard_index = body.index(guard_call)
        assert guard_index < persistence_call_index
        assert guard_index < trained_call_index
    assert "except " not in body


def test_comparison_does_not_reimplement_mae_arithmetic() -> None:
    code = _code_source(COMPARISON_MODULE)
    assert "abs(" not in code
    assert "total_abs_error" not in code
    assert "+=" not in code
    assert "/ len(" not in code
    assert "sqrt(" not in code
    assert "**" not in code
    identifiers = _identifier_names(COMPARISON_MODULE)
    assert "abs" not in identifiers
    assert "sum" not in identifiers
    assert "mean" not in identifiers


def test_comparison_has_no_model_selection_or_relative_change() -> None:
    code = _code_source(COMPARISON_MODULE).lower()
    for token in SELECTION_TOKENS:
        assert token not in code
    for token in OTHER_METRIC_TOKENS:
        assert token not in code
    lowered_identifiers = {name.lower() for name in _identifier_names(COMPARISON_MODULE)}
    for token in SELECTION_TOKENS:
        assert token not in lowered_identifiers
    assert "min(" not in code
    assert "max(" not in code


def test_comparison_uses_canonical_decimal_equality_only() -> None:
    code = _code_source(COMPARISON_MODULE)
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
    ):
        assert forbidden not in code
    identifiers = _identifier_names(COMPARISON_MODULE)
    assert "float" not in identifiers
    assert "round" not in identifiers
    assert "quantize" not in identifiers
    assert "Decimal" not in identifiers


def test_comparison_has_no_fx_or_price_construction() -> None:
    code = _code_source(COMPARISON_MODULE).lower()
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
    ):
        assert forbidden not in code
    source = COMPARISON_MODULE.read_text(encoding="utf-8")
    assert "EnergyPrice(" not in source
    assert f"{PERSISTENCE_CASE_CLASS}(" not in source
    assert f"{TRAINED_PREDICTION_CLASS}(" not in source


def test_comparison_fails_closed_with_sanitized_messages() -> None:
    source = COMPARISON_MODULE.read_text(encoding="utf-8")
    assert source.count("InvalidRequestError") >= 16
    for message_name in (
        "_EMPTY_BOTH_MESSAGE",
        "_EMPTY_PERSISTENCE_MESSAGE",
        "_EMPTY_TRAINED_MESSAGE",
        "_UNEQUAL_LENGTH_MESSAGE",
        "_MIXED_PERSISTENCE_MARKET_MESSAGE",
        "_MIXED_TRAINED_MARKET_MESSAGE",
        "_MARKET_MISMATCH_MESSAGE",
        "_PERSISTENCE_CURRENCY_COHERENCE_MESSAGE",
        "_MIXED_PERSISTENCE_CURRENCY_MESSAGE",
        "_MIXED_TRAINED_CURRENCY_MESSAGE",
        "_CURRENCY_MISMATCH_MESSAGE",
        "_DUPLICATE_PERSISTENCE_TIMESTAMP_MESSAGE",
        "_DUPLICATE_TRAINED_TIMESTAMP_MESSAGE",
        "_OUT_OF_ORDER_PERSISTENCE_MESSAGE",
        "_OUT_OF_ORDER_TRAINED_MESSAGE",
        "_TIMESTAMP_MISMATCH_MESSAGE",
        "_ACTUAL_MISMATCH_MESSAGE",
    ):
        assert message_name in source
    flattened = _flattened_source(COMPARISON_MODULE)
    for phrase in (
        "requires a non-empty aligned cohort",
        "requires a non-empty persistence cohort",
        "requires a non-empty trained OLS cohort",
        "requires equal persistence and trained case counts",
        "requires persistence cases from exactly one market",
        "requires trained predictions from exactly one market",
        "requires persistence cases and trained predictions from the same market",
        "requires matching predicted and actual persistence currency",
        "requires persistence cases in exactly one currency",
        "requires trained predictions in exactly one currency",
        "requires persistence cases and trained predictions in the same currency",
        "requires unique persistence target timestamps",
        "requires unique trained target timestamps",
        "requires strictly increasing persistence target timestamps",
        "requires strictly increasing trained target timestamps",
        "requires matching target timestamps at each aligned index",
        "requires matching actual price amounts at each aligned index",
    ):
        assert phrase in flattened
    for leak in ("AMD", "EUR", "market-alpha", "market-beta", "111.11", "222.22"):
        assert leak not in source


def test_no_generic_comparison_framework_exists() -> None:
    class_names = [name for path in ML_ROOT.rglob("*.py") for name in _module_class_names(path)]
    leaked_classes = sorted(name for name in class_names if name in GENERIC_COMPARISON_NAMES)
    assert leaked_classes == []
    identifiers = _identifier_names(COMPARISON_MODULE)
    leaked_ids = sorted(name for name in identifiers if name in GENERIC_COMPARISON_NAMES)
    assert leaked_ids == []
    code = _code_source(COMPARISON_MODULE)
    assert "energy_trading.ml.common" not in code
    assert not any(
        module.startswith("energy_trading.ml.common") for module in ALLOWED_MODULE_IMPORTS
    )


def test_comparison_has_no_io_clock_or_environment_access() -> None:
    code = _code_source(COMPARISON_MODULE)
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
    modules = imported_modules(COMPARISON_MODULE)
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


def test_published_dam_price_modules_remain_unaware_of_the_comparison() -> None:
    for path in UNAWARE_MODULES:
        source = path.read_text(encoding="utf-8")
        assert COMPARISON_CLASS not in source
        assert COMPARISON_FUNCTION not in source
        assert "persistence_vs_trained_ols_comparison" not in source
        names = imported_names(path)
        assert COMPARISON_CLASS not in names
        assert COMPARISON_FUNCTION not in names


def test_application_agents_do_not_import_the_comparison() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert COMPARISON_CLASS not in names
        assert COMPARISON_FUNCTION not in names
        source = path.read_text(encoding="utf-8")
        assert "persistence_vs_trained_ols_comparison" not in source


def test_orchestration_and_langgraph_do_not_import_the_comparison() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert COMPARISON_CLASS not in names
        assert COMPARISON_FUNCTION not in names
        source = path.read_text(encoding="utf-8")
        assert "persistence_vs_trained_ols_comparison" not in source
    graph_modules = imported_modules(GRAPH_MODULE)
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in graph_modules
    )


def test_api_composition_does_not_import_or_construct_the_comparison() -> None:
    assert collect_import_violations(API_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert COMPARISON_CLASS not in names
        assert COMPARISON_FUNCTION not in names
        source = path.read_text(encoding="utf-8")
        assert "persistence_vs_trained_ols_comparison" not in source
    app_source = API_APP.read_text(encoding="utf-8")
    assert COMPARISON_FUNCTION not in app_source
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
    assert COMPARISON_FUNCTION not in call_names
    assert COMPARISON_CLASS not in call_names


def test_workflow_state_shape_is_unchanged() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert COMPARISON_CLASS not in names
    assert COMPARISON_FUNCTION not in names
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "persistence_vs_trained_ols_comparison" not in source
    assert "dam_price" not in source
