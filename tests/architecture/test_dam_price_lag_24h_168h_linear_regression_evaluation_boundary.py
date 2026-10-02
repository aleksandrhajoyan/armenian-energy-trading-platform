"""DAM Price 24h+168h OLS MAE evaluator stays a narrow offline ML evaluation artifact."""

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
EVALUATION_MODULE = DAM_ML_ROOT / "lag_24h_168h_linear_regression_evaluation.py"
PREDICTION_MODULE = DAM_ML_ROOT / "lag_24h_168h_linear_regression_prediction.py"
COMPARISON_MODULE = DAM_ML_ROOT / "lag_24h_vs_lag_24h_168h_ols_comparison.py"
PERSISTENCE_COMPARISON_MODULE = DAM_ML_ROOT / "persistence_vs_lag_24h_168h_ols_comparison.py"
THREE_WAY_COMPARISON_MODULE = (
    DAM_ML_ROOT / "persistence_vs_lag_24h_vs_lag_24h_168h_ols_comparison.py"
)
# Explicit allowlist of downstream modules permitted to consume the evaluator:
# only the Chunk 184 one-feature versus two-feature comparison, the Chunk 185
# persistence versus two-feature comparison, and the Chunk 186 three-way
# persistence versus one-feature versus two-feature comparison.
EVALUATOR_CONSUMER_MODULES = frozenset(
    {COMPARISON_MODULE, PERSISTENCE_COMPARISON_MODULE, THREE_WAY_COMPARISON_MODULE}
)
DAM_PRICE_PORT_MODULE = PRODUCTION_ROOT / "application" / "ports" / "dam_price_forecast_model.py"
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
INFRASTRUCTURE_ROOT = PRODUCTION_ROOT / "infrastructure"

MODULE_NAME = "lag_24h_168h_linear_regression_evaluation"
PREDICTION_MODULE_PATH = "energy_trading.ml.dam_price.lag_24h_168h_linear_regression_prediction"
RESULT_CLASS = "DAMPriceLag24h168hLinearRegressionMAEResult"
EVALUATOR = "evaluate_dam_price_lag_24h_168h_linear_regression_mae"
PREDICTION_CLASS = "DAMPriceLag24h168hLinearRegressionPrediction"
PREDICTOR = "predict_dam_price_lag_24h_168h_linear_regression"

UPSTREAM_EXECUTION_NAMES = (
    PREDICTOR,
    "DAMPriceLag24h168hFeatureRow",
    "build_dam_price_lag_24h_168h_feature_rows",
    "DAMPriceLag24h168hChronologicalFeatureSplit",
    "split_dam_price_lag_24h_168h_feature_rows_chronologically",
    "DAMPriceLag24h168hLinearRegressionFit",
    "fit_dam_price_lag_24h_168h_linear_regression",
    "DAMPriceLag24hFeatureRow",
    "build_dam_price_lag_24h_feature_rows",
    "DAMPriceChronologicalFeatureSplit",
    "split_dam_price_feature_rows_chronologically",
    "DAMPriceLag24hLinearRegressionFit",
    "fit_dam_price_lag_24h_linear_regression",
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
    "MarketPriceRecord",
    "EnergyPrice",
    "PriceForecastPoint",
    "DAMPriceForecastModelRequest",
    "DAMPriceForecastModelPort",
    "DAMPriceForecastAgent",
)

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.infrastructure",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.application.ports",
    "energy_trading.ml.common",
    "energy_trading.ml.consumer_load",
    "energy_trading.ml.dam_price.lag_24h_168h_features",
    "energy_trading.ml.dam_price.lag_24h_168h_chronological_feature_split",
    "energy_trading.ml.dam_price.lag_24h_168h_linear_regression",
    "energy_trading.ml.dam_price.lag_24h_features",
    "energy_trading.ml.dam_price.chronological_feature_split",
    "energy_trading.ml.dam_price.lag_24h_linear_regression",
    "energy_trading.ml.dam_price.lag_24h_linear_regression_prediction",
    "energy_trading.ml.dam_price.lag_24h_linear_regression_evaluation",
    "energy_trading.ml.dam_price.persistence_vs_trained_ols_comparison",
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
    "json",
    "logging",
    "datetime",
    "asyncio",
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "decimal",
        "energy_trading.application.errors",
        "energy_trading.domain.value_objects.quantities",
        PREDICTION_MODULE_PATH,
    }
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
        "Metric",
        "Evaluator",
        "Scorer",
        "ModelPort",
        "ForecastingExecutionPort",
        "WorkflowState",
        *UPSTREAM_EXECUTION_NAMES,
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
    "median",
    "max_error",
    "residual",
    "percentage",
    "directional",
    "standard_deviation",
    "std_dev",
    "variance",
)

REPAIR_TOKENS = (
    "sorted(",
    ".sort(",
    "reverse",
    "reversed",
    "shuffle",
    "groupby",
    "drop_duplicates",
    "deduplicat",
    "truncat",
    "intersection",
    "skip",
    "realign",
    "zip(",
    "continue",
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


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _class_def(path: Path, class_name: str) -> ast.ClassDef:
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    msg = f"class {class_name!r} not found in {path}"
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


def _annassign_items(class_def: ast.ClassDef) -> list[ast.AnnAssign]:
    return [
        item
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    ]


def _field_name(item: ast.AnnAssign) -> str:
    assert isinstance(item.target, ast.Name)
    return item.target.id


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

    The module docstring deliberately names what this evaluator does not do,
    so forbidden-token checks must run on executable code only.
    """

    tree = _tree(path)
    holders = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if not isinstance(node, holders) or not node.body:
            continue
        first = node.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            del node.body[0]
            if not node.body:
                node.body.append(ast.Pass())
    return ast.unparse(tree)


def _flattened_source(path: Path) -> str:
    """Return source with quotes removed and whitespace collapsed."""

    return " ".join(path.read_text(encoding="utf-8").replace('"', "").split())


def test_evaluator_lives_under_dam_price_ml_package() -> None:
    assert EVALUATION_MODULE.parent == DAM_ML_ROOT
    assert EVALUATION_MODULE.name == f"{MODULE_NAME}.py"
    assert _module_class_names(EVALUATION_MODULE) == [RESULT_CLASS]
    assert _public_function_names(EVALUATION_MODULE) == [EVALUATOR]
    assert _class_def(EVALUATION_MODULE, RESULT_CLASS).bases == []


def test_result_dataclass_is_frozen_slotted_and_exactly_three_fields() -> None:
    class_def = _class_def(EVALUATION_MODULE, RESULT_CLASS)
    assert _dataclass_keywords(class_def) == {"frozen": True, "slots": True}
    items = _annassign_items(class_def)
    assert tuple(_field_name(item) for item in items) == RESULT_FIELDS
    annotations = {_field_name(item): ast.unparse(item.annotation) for item in items}
    assert annotations == RESULT_ANNOTATIONS
    assert all(item.value is None for item in items)


def test_result_exposes_no_other_metric_identity_or_payload_field() -> None:
    names = {
        _field_name(item) for item in _annassign_items(_class_def(EVALUATION_MODULE, RESULT_CLASS))
    }
    assert names == set(RESULT_FIELDS)
    for forbidden in (
        *OTHER_METRIC_TOKENS,
        "market_id",
        "target_timestamp",
        "model_name",
        "model_version",
        "provider",
        "forecast_run_id",
        "generated_at",
        "metadata",
        "winner",
        "champion",
        "improvement",
    ):
        assert forbidden not in names


def test_evaluator_is_synchronous_keyword_only_and_returns_result() -> None:
    evaluator = next(
        node
        for node in _tree(EVALUATION_MODULE).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == EVALUATOR
    )
    assert isinstance(evaluator, ast.FunctionDef)
    assert evaluator.args.posonlyargs == []
    assert evaluator.args.args == []
    assert tuple(arg.arg for arg in evaluator.args.kwonlyargs) == ("predictions",)
    assert evaluator.args.vararg is None
    assert evaluator.args.kwarg is None
    assert evaluator.args.kw_defaults == [None]
    annotation = evaluator.args.kwonlyargs[0].annotation
    assert annotation is not None
    assert ast.unparse(annotation) == f"tuple[{PREDICTION_CLASS}, ...]"
    assert evaluator.returns is not None
    assert ast.unparse(evaluator.returns) == RESULT_CLASS


def test_evaluator_consumes_prediction_artifact_type_but_never_the_predictor() -> None:
    names = imported_names(EVALUATION_MODULE)
    assert PREDICTION_CLASS in names
    assert PREDICTION_MODULE_PATH in imported_modules(EVALUATION_MODULE)
    source = EVALUATION_MODULE.read_text(encoding="utf-8")
    assert PREDICTOR not in source
    assert PREDICTOR not in _identifier_names(EVALUATION_MODULE)
    calls = _call_names(_tree(EVALUATION_MODULE))
    assert PREDICTOR not in calls
    # Already-produced artifacts are scored; none are constructed here.
    assert PREDICTION_CLASS not in calls


def test_evaluator_has_no_upstream_execution_or_sibling_dependency() -> None:
    names = imported_names(EVALUATION_MODULE)
    identifiers = _identifier_names(EVALUATION_MODULE)
    for forbidden in UPSTREAM_EXECUTION_NAMES:
        assert forbidden not in names
        assert forbidden not in identifiers


def test_evaluator_depends_only_on_allowed_inward_contracts() -> None:
    modules = imported_modules(EVALUATION_MODULE)
    assert sorted(module for module in modules if is_forbidden(module, FORBIDDEN_PREFIXES)) == []
    assert modules == ALLOWED_MODULE_IMPORTS
    names = imported_names(EVALUATION_MODULE)
    for required in (
        "dataclass",
        "Decimal",
        "DecimalException",
        "InvalidRequestError",
        "CurrencyCode",
        "FiniteDecimal",
        PREDICTION_CLASS,
    ):
        assert required in names
    leaked_types = sorted(
        name for name in annotation_type_names(EVALUATION_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_metric_is_mean_absolute_error_over_supplied_predictions() -> None:
    code = _code_source(EVALUATION_MODULE)
    assert "total_abs_error / len(predictions)" in code
    assert "+=" in code
    assert "case_count=len(predictions)" in code
    assert "currency=currency" in code
    assert "mae_amount_per_mwh=mae_amount_per_mwh" in code
    identifiers = _identifier_names(EVALUATION_MODULE)
    assert "sum" not in identifiers
    assert "mean" not in identifiers
    assert "abs" in identifiers
    assert "len" in identifiers


def test_absolute_value_is_used_only_for_the_error_difference() -> None:
    abs_calls = [
        node
        for node in ast.walk(_tree(EVALUATION_MODULE))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "abs"
    ]
    # One call seeds the accumulator; the other adds each remaining prediction.
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


def test_result_currency_is_copied_from_cohort_and_never_used_in_arithmetic() -> None:
    code = _code_source(EVALUATION_MODULE)
    assert "currency = _require_single_currency(predictions)" in code
    assert "currencies = {prediction.currency for prediction in predictions}" in code
    assert "next(iter(currencies))" in code
    for node in ast.walk(_tree(EVALUATION_MODULE)):
        if not isinstance(node, ast.BinOp):
            continue
        for operand in (node.left, node.right):
            assert not (isinstance(operand, ast.Name) and operand.id == "currency")
            assert not (isinstance(operand, ast.Attribute) and operand.attr == "currency")


def test_supplied_chronology_is_validated_and_never_repaired() -> None:
    code = _code_source(EVALUATION_MODULE)
    assert "previous.target_timestamp == current.target_timestamp" in code
    assert "previous.target_timestamp > current.target_timestamp" in code
    for token in REPAIR_TOKENS:
        assert token not in code
    calls = _call_names(_tree(EVALUATION_MODULE))
    for forbidden in ("sorted", "sort", "reverse", "reversed", "shuffle", "sample", "zip"):
        assert forbidden not in calls


def test_evaluator_uses_canonical_decimal_arithmetic_only() -> None:
    code = _code_source(EVALUATION_MODULE)
    for forbidden in (
        "float(",
        "round(",
        "quantize",
        "normalize",
        "standardize",
        "scale",
        "clip(",
        "clamp",
        "floor(",
        "ceil(",
        "Decimal(",
        "sqrt(",
        "**",
        "//",
        "max(",
        "min(",
    ):
        assert forbidden not in code
    identifiers = _identifier_names(EVALUATION_MODULE)
    for forbidden in ("float", "round", "quantize", "isfinite", "sqrt", "fsum"):
        assert forbidden not in identifiers
    assert ".is_finite()" in code
    assert "total_abs_error.is_finite()" in code
    assert "mae_amount_per_mwh.is_finite()" in code


def test_only_narrowed_decimal_exception_handling_is_used() -> None:
    handlers = [
        node for node in ast.walk(_tree(EVALUATION_MODULE)) if isinstance(node, ast.ExceptHandler)
    ]
    assert len(handlers) == 2
    for handler in handlers:
        assert isinstance(handler.type, ast.Name)
        assert handler.type.id == "DecimalException"
    source = EVALUATION_MODULE.read_text(encoding="utf-8")
    assert source.count("raise InvalidRequestError(msg) from error") == 2


def test_evaluator_fails_closed_with_sanitized_static_messages() -> None:
    source = EVALUATION_MODULE.read_text(encoding="utf-8")
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
    tree = _tree(EVALUATION_MODULE)
    assert not any(isinstance(node, ast.JoinedStr) for node in ast.walk(tree))
    calls = _call_names(tree)
    for forbidden in ("format", "repr", "str"):
        assert forbidden not in calls


def test_evaluator_has_no_other_metric_comparison_or_selection() -> None:
    code = _code_source(EVALUATION_MODULE).lower()
    identifiers = {name.lower() for name in _identifier_names(EVALUATION_MODULE)}
    for token in OTHER_METRIC_TOKENS:
        assert token not in code
        assert token not in identifiers
    for forbidden in (
        "champion",
        "winner",
        "rank",
        "improvement",
        "relative",
        "compare",
        "persistence",
        "one_feature",
        "selection",
        "threshold",
        "fx",
        "exchange",
        "convert",
        "weight",
        "volume",
    ):
        assert forbidden not in code


def test_no_generic_metric_framework_is_introduced() -> None:
    class_names = [name for path in ML_ROOT.rglob("*.py") for name in _module_class_names(path)]
    assert sorted(name for name in class_names if name in GENERIC_METRIC_NAMES) == []
    identifiers = _identifier_names(EVALUATION_MODULE)
    assert sorted(name for name in identifiers if name in GENERIC_METRIC_NAMES) == []
    # ``ml/common`` exists from bootstrap history; only usage is forbidden here.
    assert not any(
        module.startswith("energy_trading.ml.common")
        for module in imported_modules(EVALUATION_MODULE)
    )
    assert "ml.common" not in EVALUATION_MODULE.read_text(encoding="utf-8")


def test_evaluator_has_no_io_clock_randomness_or_environment_access() -> None:
    code = _code_source(EVALUATION_MODULE)
    for forbidden in (
        "datetime",
        "utcnow",
        "uuid",
        "random",
        "open(",
        "Path(",
        "environ",
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


def test_existing_dam_price_modules_remain_unaware_of_the_evaluator() -> None:
    others = [
        path
        for path in sorted(DAM_ML_ROOT.rglob("*.py"))
        if path not in {EVALUATION_MODULE, *EVALUATOR_CONSUMER_MODULES}
    ]
    assert PREDICTION_MODULE in others
    for path in others:
        source = path.read_text(encoding="utf-8")
        assert RESULT_CLASS not in source
        assert EVALUATOR not in source
        assert MODULE_NAME not in source
    port_source = DAM_PRICE_PORT_MODULE.read_text(encoding="utf-8")
    assert RESULT_CLASS not in port_source
    assert EVALUATOR not in port_source


def test_evaluator_consumers_are_exactly_the_three_comparisons() -> None:
    # The Chunk 184, Chunk 185, and Chunk 186 comparisons are the only
    # authorized downstream consumers of the evaluator. Each imports the
    # evaluator function, never the result type, and invokes it exactly once.
    assert EVALUATOR_CONSUMER_MODULES == frozenset(
        {COMPARISON_MODULE, PERSISTENCE_COMPARISON_MODULE, THREE_WAY_COMPARISON_MODULE}
    )
    assert COMPARISON_MODULE.parent == DAM_ML_ROOT
    assert COMPARISON_MODULE.name == "lag_24h_vs_lag_24h_168h_ols_comparison.py"
    assert PERSISTENCE_COMPARISON_MODULE.parent == DAM_ML_ROOT
    assert PERSISTENCE_COMPARISON_MODULE.name == "persistence_vs_lag_24h_168h_ols_comparison.py"
    assert THREE_WAY_COMPARISON_MODULE.parent == DAM_ML_ROOT
    assert THREE_WAY_COMPARISON_MODULE.name == (
        "persistence_vs_lag_24h_vs_lag_24h_168h_ols_comparison.py"
    )
    for consumer in sorted(EVALUATOR_CONSUMER_MODULES):
        assert consumer.is_file()
        names = imported_names(consumer)
        assert EVALUATOR in names
        assert RESULT_CLASS not in names
        assert f"energy_trading.ml.dam_price.{MODULE_NAME}" in imported_modules(consumer)
        source = consumer.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(consumer))
        call_names: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name):
                call_names.append(func.id)
            elif isinstance(func, ast.Attribute):
                call_names.append(func.attr)
        assert call_names.count(EVALUATOR) == 1
        assert PREDICTOR not in call_names


def test_application_agents_do_not_import_the_evaluator() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert RESULT_CLASS not in source
        assert EVALUATOR not in source
        assert MODULE_NAME not in source


def test_orchestration_and_langgraph_do_not_import_the_evaluator() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert RESULT_CLASS not in source
        assert EVALUATOR not in source
        assert MODULE_NAME not in source
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in imported_modules(GRAPH_MODULE)
    )


def test_api_composition_and_create_app_do_not_import_or_call_the_evaluator() -> None:
    assert collect_import_violations(API_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert RESULT_CLASS not in source
        assert EVALUATOR not in source
        assert MODULE_NAME not in source
    create_app = next(
        node
        for node in _tree(API_APP).body
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )
    calls = _call_names(create_app)
    assert EVALUATOR not in calls
    assert RESULT_CLASS not in calls


def test_infrastructure_does_not_import_the_evaluator() -> None:
    for path in sorted(INFRASTRUCTURE_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert EVALUATOR not in source
        assert MODULE_NAME not in source


def test_workflow_state_shape_is_unchanged() -> None:
    items = _annassign_items(_class_def(STATE_MODULE, "WorkflowState"))
    assert tuple(_field_name(item) for item in items) == WORKFLOW_STATE_FIELDS
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert RESULT_CLASS not in source
    assert EVALUATOR not in source
    assert MODULE_NAME not in source
    assert "dam_price" not in source
