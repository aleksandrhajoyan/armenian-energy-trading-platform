"""Aligned DAM Price one-feature versus two-feature OLS comparison stays a narrow ML artifact."""

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
COMPARISON_MODULE = DAM_ML_ROOT / "lag_24h_vs_lag_24h_168h_ols_comparison.py"
LAG_24H_PREDICTION_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression_prediction.py"
LAG_24H_EVALUATION_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression_evaluation.py"
LAG_24H_168H_PREDICTION_MODULE = DAM_ML_ROOT / "lag_24h_168h_linear_regression_prediction.py"
LAG_24H_168H_EVALUATION_MODULE = DAM_ML_ROOT / "lag_24h_168h_linear_regression_evaluation.py"
PERSISTENCE_COMPARISON_MODULE = DAM_ML_ROOT / "persistence_vs_trained_ols_comparison.py"
DAM_PRICE_PORT_MODULE = PRODUCTION_ROOT / "application" / "ports" / "dam_price_forecast_model.py"
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
INFRASTRUCTURE_ROOT = PRODUCTION_ROOT / "infrastructure"

MODULE_NAME = "lag_24h_vs_lag_24h_168h_ols_comparison"
COMPARISON_CLASS = "DAMPriceLag24hVsLag24h168hOLSMAEComparison"
COMPARISON_FUNCTION = "compare_dam_price_lag_24h_vs_lag_24h_168h_ols_mae"
LAG_24H_EVALUATOR = "evaluate_dam_price_lag_24h_linear_regression_mae"
LAG_24H_168H_EVALUATOR = "evaluate_dam_price_lag_24h_168h_linear_regression_mae"
LAG_24H_PREDICTION_CLASS = "DAMPriceLag24hLinearRegressionPrediction"
LAG_24H_168H_PREDICTION_CLASS = "DAMPriceLag24h168hLinearRegressionPrediction"
LAG_24H_RESULT_CLASS = "DAMPriceLag24hLinearRegressionMAEResult"
LAG_24H_168H_RESULT_CLASS = "DAMPriceLag24h168hLinearRegressionMAEResult"
LAG_24H_PREDICTOR = "predict_dam_price_lag_24h_linear_regression"
LAG_24H_168H_PREDICTOR = "predict_dam_price_lag_24h_168h_linear_regression"

UPSTREAM_EXECUTION_NAMES = (
    LAG_24H_PREDICTOR,
    LAG_24H_168H_PREDICTOR,
    "build_dam_price_lag_24h_feature_rows",
    "build_dam_price_lag_24h_168h_feature_rows",
    "split_dam_price_feature_rows_chronologically",
    "split_dam_price_lag_24h_168h_feature_rows_chronologically",
    "fit_dam_price_lag_24h_linear_regression",
    "fit_dam_price_lag_24h_168h_linear_regression",
    "build_previous_day_persistence_backtest_cases",
    "evaluate_previous_day_persistence_mae",
    "compare_dam_price_persistence_vs_trained_ols_mae",
    "PreviousDayPersistenceDAMPriceForecastModel",
    "PreviousDayPersistenceBacktestCase",
    LAG_24H_RESULT_CLASS,
    LAG_24H_168H_RESULT_CLASS,
    "DAMPriceForecastModelRequest",
    "DAMPriceForecastModelPort",
    "DAMPriceForecastAgent",
    "MarketPriceRecord",
    "EnergyPrice",
    "PriceForecastPoint",
)

FORBIDDEN_DAM_MODULES = (
    "energy_trading.ml.dam_price.lag_24h_features",
    "energy_trading.ml.dam_price.lag_24h_168h_features",
    "energy_trading.ml.dam_price.chronological_feature_split",
    "energy_trading.ml.dam_price.lag_24h_168h_chronological_feature_split",
    "energy_trading.ml.dam_price.lag_24h_linear_regression",
    "energy_trading.ml.dam_price.lag_24h_168h_linear_regression",
    "energy_trading.ml.dam_price.previous_day_persistence",
    "energy_trading.ml.dam_price.previous_day_persistence_backtest",
    "energy_trading.ml.dam_price.previous_day_persistence_evaluation",
    "energy_trading.ml.dam_price.persistence_vs_trained_ols_comparison",
)

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
        "PreviousDayPersistenceBacktestCase",
        "PreviousDayPersistenceMAEResult",
        "DAMPriceLag24hLinearRegressionMAEResult",
        "DAMPriceLag24h168hLinearRegressionMAEResult",
        "DAMPriceLag24h168hFeatureRow",
        "DAMPriceLag24h168hChronologicalFeatureSplit",
        "DAMPriceLag24h168hLinearRegressionFit",
        "DAMPricePersistenceVsTrainedOLSMAEComparison",
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
        "energy_trading.ml.dam_price.lag_24h_168h_linear_regression_evaluation",
        "energy_trading.ml.dam_price.lag_24h_168h_linear_regression_prediction",
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
    "dict(",
    "deduplicat",
    "groupby",
    "truncat",
    "tolerance",
)

RESULT_FIELDS = (
    "case_count",
    "currency",
    "lag_24h_mae_amount_per_mwh",
    "lag_24h_168h_mae_amount_per_mwh",
)

RESULT_ANNOTATIONS = {
    "case_count": "int",
    "currency": "CurrencyCode",
    "lag_24h_mae_amount_per_mwh": "FiniteDecimal",
    "lag_24h_168h_mae_amount_per_mwh": "FiniteDecimal",
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

ALIGNMENT_GUARDS = (
    "_require_nonempty_equal_cohort(",
    "_require_single_shared_market_and_currency(",
    "_require_lag_24h_chronology(",
    "_require_lag_24h_168h_chronology(",
    "_require_pairwise_alignment(",
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
    assert COMPARISON_MODULE.name == f"{MODULE_NAME}.py"
    assert _module_class_names(COMPARISON_MODULE) == [COMPARISON_CLASS]
    assert _public_function_names(COMPARISON_MODULE) == [COMPARISON_FUNCTION]
    assert _base_names(_class_def(COMPARISON_MODULE, COMPARISON_CLASS)) == set()


def test_comparison_result_is_frozen_slotted_and_exactly_four_fields() -> None:
    class_def = _class_def(COMPARISON_MODULE, COMPARISON_CLASS)
    assert _dataclass_keywords(class_def) == {"frozen": True, "slots": True}
    assert _annassign_field_names(COMPARISON_MODULE, COMPARISON_CLASS) == RESULT_FIELDS
    annotations = {
        item.target.id: ast.unparse(item.annotation)
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert annotations == RESULT_ANNOTATIONS
    defaults = [
        item.value
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    ]
    assert all(value is None for value in defaults)


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
        "better_model",
        "improvement",
        "percentage_improvement",
        "delta",
        "ratio",
        "threshold",
        "rank",
        "score",
        "confidence",
        "significance",
        "metadata",
    ):
        assert identity not in names


def test_comparison_is_synchronous_keyword_only_and_returns_result() -> None:
    tree = ast.parse(COMPARISON_MODULE.read_text(encoding="utf-8"), filename=str(COMPARISON_MODULE))
    function = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == COMPARISON_FUNCTION
    )
    assert isinstance(function, ast.FunctionDef)
    assert tuple(arg.arg for arg in function.args.posonlyargs) == ()
    assert tuple(arg.arg for arg in function.args.args) == ()
    assert tuple(arg.arg for arg in function.args.kwonlyargs) == (
        "lag_24h_predictions",
        "lag_24h_168h_predictions",
    )
    assert function.args.vararg is None
    assert function.args.kwarg is None
    assert function.args.kw_defaults == [None, None]
    lag_24h_arg, lag_24h_168h_arg = function.args.kwonlyargs
    assert lag_24h_arg.annotation is not None
    assert ast.unparse(lag_24h_arg.annotation) == f"tuple[{LAG_24H_PREDICTION_CLASS}, ...]"
    assert lag_24h_168h_arg.annotation is not None
    assert ast.unparse(lag_24h_168h_arg.annotation) == (
        f"tuple[{LAG_24H_168H_PREDICTION_CLASS}, ...]"
    )
    assert function.returns is not None
    assert ast.unparse(function.returns) == COMPARISON_CLASS


def test_comparison_consumes_only_the_two_prediction_dtos_and_two_evaluators() -> None:
    names = imported_names(COMPARISON_MODULE)
    for required in (
        LAG_24H_PREDICTION_CLASS,
        LAG_24H_168H_PREDICTION_CLASS,
        LAG_24H_EVALUATOR,
        LAG_24H_168H_EVALUATOR,
    ):
        assert required in names
    for forbidden in UPSTREAM_EXECUTION_NAMES:
        assert forbidden not in names
    modules = imported_modules(COMPARISON_MODULE)
    for forbidden_module in FORBIDDEN_DAM_MODULES:
        assert forbidden_module not in modules


def test_comparison_never_references_or_invokes_either_predictor() -> None:
    source = COMPARISON_MODULE.read_text(encoding="utf-8")
    calls = _call_names(COMPARISON_MODULE)
    identifiers = _identifier_names(COMPARISON_MODULE)
    for predictor in (LAG_24H_PREDICTOR, LAG_24H_168H_PREDICTOR):
        assert predictor not in source
        assert predictor not in calls
        assert predictor not in identifiers
    # Prediction DTOs are consumed, never constructed.
    assert LAG_24H_PREDICTION_CLASS not in calls
    assert LAG_24H_168H_PREDICTION_CLASS not in calls


def test_comparison_has_no_persistence_or_upstream_stage_dependency() -> None:
    code = _code_source(COMPARISON_MODULE).lower()
    for token in (
        "persistence",
        "backtest",
        "feature_rows",
        "chronologically",
        "fit_dam_price",
        "predict_dam_price",
        "previous_day",
    ):
        assert token not in code


def test_comparison_depends_only_on_allowed_inward_contracts() -> None:
    modules = imported_modules(COMPARISON_MODULE)
    leaked = sorted(module for module in modules if is_forbidden(module, FORBIDDEN_PREFIXES))
    assert leaked == []
    assert modules - ALLOWED_MODULE_IMPORTS == set()
    names = imported_names(COMPARISON_MODULE)
    for required in ("InvalidRequestError", "CurrencyCode", "FiniteDecimal", "dataclass"):
        assert required in names
    leaked_types = sorted(
        name for name in annotation_type_names(COMPARISON_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []
    source = COMPARISON_MODULE.read_text(encoding="utf-8")
    for evasion in ("TYPE_CHECKING", "importlib", "__import__", "getattr(", "globals("):
        assert evasion not in source


def test_comparison_proves_alignment_before_scoring() -> None:
    code = _code_source(COMPARISON_MODULE)
    for required in (
        "if not lag_24h_predictions and (not lag_24h_168h_predictions):",
        "if not lag_24h_predictions:",
        "if not lag_24h_168h_predictions:",
        "if len(lag_24h_predictions) != len(lag_24h_168h_predictions):",
        "prediction.market_id for prediction in lag_24h_predictions",
        "prediction.market_id for prediction in lag_24h_168h_predictions",
        "if len(lag_24h_markets) > 1:",
        "if len(lag_24h_168h_markets) > 1:",
        "if lag_24h_markets != lag_24h_168h_markets:",
        "prediction.currency for prediction in lag_24h_predictions",
        "prediction.currency for prediction in lag_24h_168h_predictions",
        "if len(lag_24h_currencies) > 1:",
        "if len(lag_24h_168h_currencies) > 1:",
        "if lag_24h_currencies != lag_24h_168h_currencies:",
        "previous.target_timestamp == current.target_timestamp",
        "previous.target_timestamp > current.target_timestamp",
        "lag_24h_prediction.target_timestamp != lag_24h_168h_prediction.target_timestamp",
        "lag_24h_prediction.actual_amount_per_mwh != lag_24h_168h_prediction.actual_amount_per_mwh",
    ):
        assert required in code
    # Predicted values are intentionally allowed to differ.
    assert "predicted_amount_per_mwh" not in code


def test_comparison_uses_explicit_index_alignment_without_realignment() -> None:
    code = _code_source(COMPARISON_MODULE)
    assert "for index in range(len(lag_24h_predictions)):" in code
    assert "lag_24h_predictions[index]" in code
    assert "lag_24h_168h_predictions[index]" in code
    for token in REALIGNMENT_TOKENS:
        assert token not in code
    identifiers = _identifier_names(COMPARISON_MODULE)
    for forbidden in ("zip", "sorted", "sort", "reverse", "shuffle", "dict", "enumerate"):
        assert forbidden not in identifiers


def test_comparison_delegates_scoring_once_to_each_evaluator_after_alignment() -> None:
    calls = _call_names(COMPARISON_MODULE)
    assert calls.count(LAG_24H_EVALUATOR) == 1
    assert calls.count(LAG_24H_168H_EVALUATOR) == 1
    body = _function_body_source(COMPARISON_MODULE, COMPARISON_FUNCTION)
    assert f"{LAG_24H_EVALUATOR}(predictions=lag_24h_predictions)" in body
    assert f"{LAG_24H_168H_EVALUATOR}(predictions=lag_24h_168h_predictions)" in body
    lag_24h_call_index = body.index(f"{LAG_24H_EVALUATOR}(")
    lag_24h_168h_call_index = body.index(f"{LAG_24H_168H_EVALUATOR}(")
    for guard_call in ALIGNMENT_GUARDS:
        guard_index = body.index(guard_call)
        assert guard_index < lag_24h_call_index
        assert guard_index < lag_24h_168h_call_index
    code = _code_source(COMPARISON_MODULE)
    assert "except " not in code
    assert "try:" not in code


def test_comparison_does_not_reimplement_mae_arithmetic() -> None:
    code = _code_source(COMPARISON_MODULE)
    for token in ("abs(", "total_abs_error", "+=", " / ", "/ len(", "sqrt(", "**", " - "):
        assert token not in code
    identifiers = _identifier_names(COMPARISON_MODULE)
    for forbidden in ("abs", "sum", "mean", "sqrt", "fsum"):
        assert forbidden not in identifiers


def test_comparison_has_no_model_selection_or_relative_change() -> None:
    code = _code_source(COMPARISON_MODULE).lower()
    for token in SELECTION_TOKENS:
        assert token not in code
    for token in ("best", "percent", "relative", "delta", "ratio"):
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
        "scale(",
        "clamp",
        "floor(",
        "ceil(",
        "Decimal(",
        "isclose",
    ):
        assert forbidden not in code
    identifiers = _identifier_names(COMPARISON_MODULE)
    for forbidden in ("float", "round", "quantize", "Decimal", "localcontext"):
        assert forbidden not in identifiers


def test_comparison_has_no_fx_or_price_construction() -> None:
    code = _code_source(COMPARISON_MODULE).lower()
    for forbidden in ("fx", "exchange", "conversion_rate", "convert_currency", "base_currency"):
        assert forbidden not in code
    source = COMPARISON_MODULE.read_text(encoding="utf-8")
    assert "EnergyPrice(" not in source
    assert "PriceForecastPoint(" not in source


def test_comparison_fails_closed_with_sanitized_messages() -> None:
    source = COMPARISON_MODULE.read_text(encoding="utf-8")
    assert source.count("raise InvalidRequestError(") == 16
    flattened = _flattened_source(COMPARISON_MODULE)
    for phrase in (
        "requires a non-empty aligned cohort",
        "requires a non-empty one-feature cohort",
        "requires a non-empty two-feature cohort",
        "requires equal one-feature and two-feature case counts",
        "requires one-feature predictions from exactly one market",
        "requires two-feature predictions from exactly one market",
        "requires one-feature and two-feature predictions from the same market",
        "requires one-feature predictions in exactly one currency",
        "requires two-feature predictions in exactly one currency",
        "requires one-feature and two-feature predictions in the same currency",
        "requires unique one-feature target timestamps",
        "requires unique two-feature target timestamps",
        "requires strictly increasing one-feature target timestamps",
        "requires strictly increasing two-feature target timestamps",
        "requires matching target timestamps at each aligned index",
        "requires matching actual price amounts at each aligned index",
    ):
        assert phrase in flattened
    code = _code_source(COMPARISON_MODULE)
    assert "JoinedStr" not in ast.dump(ast.parse(code))
    assert ".format(" not in code
    for leak in ("AMD", "EUR", "market-", "111.11", "222.22"):
        assert leak not in source


def test_no_generic_comparison_framework_exists() -> None:
    class_names = [name for path in ML_ROOT.rglob("*.py") for name in _module_class_names(path)]
    leaked_classes = sorted(name for name in class_names if name in GENERIC_COMPARISON_NAMES)
    assert leaked_classes == []
    identifiers = _identifier_names(COMPARISON_MODULE)
    assert sorted(name for name in identifiers if name in GENERIC_COMPARISON_NAMES) == []
    assert not any(
        module.startswith("energy_trading.ml.common") for module in ALLOWED_MODULE_IMPORTS
    )
    assert not any(
        module.startswith("energy_trading.ml.common")
        for module in imported_modules(COMPARISON_MODULE)
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
        "await",
        "print(",
        "logging",
        "json",
        "pickle",
    ):
        assert forbidden not in code
    modules = imported_modules(COMPARISON_MODULE)
    for absent in ("uuid", "random", "secrets", "os", "io", "pathlib", "asyncio", "datetime"):
        assert absent not in modules


def test_other_dam_price_modules_remain_unaware_of_the_comparison() -> None:
    others = [path for path in sorted(DAM_ML_ROOT.rglob("*.py")) if path != COMPARISON_MODULE]
    for required in (
        LAG_24H_PREDICTION_MODULE,
        LAG_24H_EVALUATION_MODULE,
        LAG_24H_168H_PREDICTION_MODULE,
        LAG_24H_168H_EVALUATION_MODULE,
        PERSISTENCE_COMPARISON_MODULE,
    ):
        assert required in others
    for path in [*others, DAM_PRICE_PORT_MODULE]:
        source = path.read_text(encoding="utf-8")
        assert COMPARISON_CLASS not in source
        assert COMPARISON_FUNCTION not in source
        assert MODULE_NAME not in source


def test_application_agents_do_not_import_the_comparison() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert COMPARISON_CLASS not in source
        assert COMPARISON_FUNCTION not in source
        assert MODULE_NAME not in source


def test_orchestration_and_langgraph_do_not_import_the_comparison() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert COMPARISON_CLASS not in source
        assert COMPARISON_FUNCTION not in source
        assert MODULE_NAME not in source
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in imported_modules(GRAPH_MODULE)
    )


def test_api_composition_and_infrastructure_do_not_import_the_comparison() -> None:
    assert collect_import_violations(API_ROOT, ("energy_trading.ml",)) == []
    for root in (API_ROOT, INFRASTRUCTURE_ROOT):
        for path in sorted(root.rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            assert COMPARISON_CLASS not in source
            assert COMPARISON_FUNCTION not in source
            assert MODULE_NAME not in source
    tree = ast.parse(API_APP.read_text(encoding="utf-8"), filename=str(API_APP))
    create_app = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )
    call_names: set[str] = set()
    for node in ast.walk(create_app):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                call_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                call_names.add(func.attr)
    assert COMPARISON_FUNCTION not in call_names
    assert COMPARISON_CLASS not in call_names


def test_workflow_state_shape_is_unchanged() -> None:
    assert _annassign_field_names(STATE_MODULE, "WorkflowState") == WORKFLOW_STATE_FIELDS
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert COMPARISON_CLASS not in source
    assert MODULE_NAME not in source
    assert "dam_price" not in source
