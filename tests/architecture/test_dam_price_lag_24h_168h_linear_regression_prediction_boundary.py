"""DAM Price 24h+168h OLS prediction stays a narrow offline ML evaluation artifact."""

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
PREDICTION_MODULE = DAM_ML_ROOT / "lag_24h_168h_linear_regression_prediction.py"
EVALUATION_MODULE = DAM_ML_ROOT / "lag_24h_168h_linear_regression_evaluation.py"
COMPARISON_MODULE = DAM_ML_ROOT / "lag_24h_vs_lag_24h_168h_ols_comparison.py"
PERSISTENCE_COMPARISON_MODULE = DAM_ML_ROOT / "persistence_vs_lag_24h_168h_ols_comparison.py"
THREE_WAY_COMPARISON_MODULE = (
    DAM_ML_ROOT / "persistence_vs_lag_24h_vs_lag_24h_168h_ols_comparison.py"
)
# Explicit allowlist of downstream modules permitted to consume the prediction
# artifact type (never the predictor function): the Chunk 183 evaluator, the
# Chunk 184 one-feature versus two-feature comparison, the Chunk 185
# persistence versus two-feature comparison, and the Chunk 186 three-way
# persistence versus one-feature versus two-feature comparison.
PREDICTION_ARTIFACT_CONSUMER_MODULES = frozenset(
    {
        EVALUATION_MODULE,
        COMPARISON_MODULE,
        PERSISTENCE_COMPARISON_MODULE,
        THREE_WAY_COMPARISON_MODULE,
    }
)
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

MODULE_NAME = "lag_24h_168h_linear_regression_prediction"
PREDICTION_CLASS = "DAMPriceLag24h168hLinearRegressionPrediction"
PREDICTOR = "predict_dam_price_lag_24h_168h_linear_regression"
ROW_CLASS = "DAMPriceLag24h168hFeatureRow"
FIT_CLASS = "DAMPriceLag24h168hLinearRegressionFit"
FEATURE_BUILDER = "build_dam_price_lag_24h_168h_feature_rows"
SPLITTER = "split_dam_price_lag_24h_168h_feature_rows_chronologically"
SPLIT_CLASS = "DAMPriceLag24h168hChronologicalFeatureSplit"
FITTER = "fit_dam_price_lag_24h_168h_linear_regression"
ONE_FEATURE_PREDICTOR = "predict_dam_price_lag_24h_linear_regression"
ONE_FEATURE_PREDICTION_CLASS = "DAMPriceLag24hLinearRegressionPrediction"

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
    "energy_trading.ml.dam_price.lag_24h_linear_regression_prediction",
    "energy_trading.ml.dam_price.lag_24h_linear_regression_evaluation",
    "energy_trading.ml.dam_price.persistence_vs_trained_ols_comparison",
    "energy_trading.ml.dam_price.lag_24h_168h_chronological_feature_split",
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
    "io",
    "time",
    "datetime",
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
        "DAMPriceLag24h168hChronologicalFeatureSplit",
        "DAMPriceLag24hFeatureRow",
        "DAMPriceLag24hLinearRegressionFit",
        "DAMPriceLag24hLinearRegressionPrediction",
        "DAMPriceLag24hLinearRegressionMAEResult",
        "DAMPricePersistenceVsTrainedOLSMAEComparison",
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
        "energy_trading.ml.dam_price.lag_24h_168h_features",
        "energy_trading.ml.dam_price.lag_24h_168h_linear_regression",
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


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _class_def(path: Path, class_name: str) -> ast.ClassDef:
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    msg = f"class {class_name!r} not found in {path}"
    raise AssertionError(msg)


def _function_def(path: Path, function_name: str) -> ast.FunctionDef:
    for node in ast.walk(_tree(path)):
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


def _called_names(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(_tree(path)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
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

    The module docstring deliberately names what this predictor does not do
    (float conversion, clamping, scaling, currency conversion) and which
    canonical types it is not (``EnergyPrice``, ``PriceForecastPoint``), so
    forbidden-token checks must run on executable code only.
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


def _flattened_source(path: Path) -> str:
    """Return source with string quotes removed and whitespace collapsed.

    Ruff format may wrap one long message constant into implicit string
    concatenation across lines, which is a formatting artifact rather than a
    semantic difference.
    """

    return " ".join(path.read_text(encoding="utf-8").replace('"', "").split())


def _assigned_value(path: Path, function_name: str, target_name: str) -> ast.expr:
    for node in ast.walk(_function_def(path, function_name)):
        if not isinstance(node, ast.Assign):
            continue
        targets = node.targets
        if len(targets) == 1 and isinstance(targets[0], ast.Name):
            if targets[0].id == target_name:
                return node.value
    msg = f"assignment to {target_name!r} not found in {function_name!r}"
    raise AssertionError(msg)


def _is_attribute(node: ast.expr, owner: str, attr: str) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == attr
        and isinstance(node.value, ast.Name)
        and node.value.id == owner
    )


def _is_product(node: ast.expr, coefficient: str, feature: str) -> bool:
    return (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Mult)
        and _is_attribute(node.left, "fit", coefficient)
        and _is_attribute(node.right, "row", feature)
    )


def _prediction_call() -> ast.Call:
    for node in ast.walk(_function_def(PREDICTION_MODULE, "_prediction_for_row")):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == PREDICTION_CLASS:
            return node
    msg = f"call to {PREDICTION_CLASS!r} not found"
    raise AssertionError(msg)


def test_predictor_lives_under_dam_price_ml_package() -> None:
    assert PREDICTION_MODULE.is_relative_to(DAM_ML_ROOT)
    assert PREDICTION_MODULE.name == f"{MODULE_NAME}.py"
    assert _module_class_names(PREDICTION_MODULE) == [PREDICTION_CLASS]
    assert _public_function_names(PREDICTION_MODULE) == [PREDICTOR]
    assert _base_names(_class_def(PREDICTION_MODULE, PREDICTION_CLASS)) == set()


def test_prediction_result_is_frozen_slotted_and_exactly_five_required_fields() -> None:
    class_def = _class_def(PREDICTION_MODULE, PREDICTION_CLASS)
    assert _dataclass_keywords(class_def) == {"frozen": True, "slots": True}
    items = _annassign_items(class_def)
    assert tuple(_field_name(item) for item in items) == PREDICTION_FIELDS
    annotations = {_field_name(item): ast.unparse(item.annotation) for item in items}
    assert annotations == PREDICTION_ANNOTATIONS
    assert all(item.value is None for item in items)


def test_predictor_is_synchronous_keyword_only_and_returns_predictions() -> None:
    predictor = next(
        node
        for node in _tree(PREDICTION_MODULE).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == PREDICTOR
    )
    assert isinstance(predictor, ast.FunctionDef)
    assert predictor.args.posonlyargs == []
    assert predictor.args.args == []
    assert tuple(arg.arg for arg in predictor.args.kwonlyargs) == ("fit", "evaluation_rows")
    assert predictor.args.vararg is None
    assert predictor.args.kwarg is None
    assert predictor.args.kw_defaults == [None, None]
    fit_arg, rows_arg = predictor.args.kwonlyargs
    assert fit_arg.annotation is not None
    assert ast.unparse(fit_arg.annotation) == FIT_CLASS
    assert rows_arg.annotation is not None
    assert ast.unparse(rows_arg.annotation) == f"tuple[{ROW_CLASS}, ...]"
    assert predictor.returns is not None
    assert ast.unparse(predictor.returns) == f"tuple[{PREDICTION_CLASS}, ...]"


def test_prediction_is_both_coefficients_times_matching_lags_plus_intercept() -> None:
    value = _assigned_value(
        PREDICTION_MODULE, "_predicted_amount_per_mwh", "predicted_amount_per_mwh"
    )
    assert isinstance(value, ast.BinOp)
    assert isinstance(value.op, ast.Add)
    assert _is_attribute(value.right, "fit", "intercept_amount_per_mwh")
    products = value.left
    assert isinstance(products, ast.BinOp)
    assert isinstance(products.op, ast.Add)
    assert _is_product(products.left, "lag_24h_coefficient", "lag_24h_amount_per_mwh")
    assert _is_product(products.right, "lag_168h_coefficient", "lag_168h_amount_per_mwh")
    # Roles are never swapped anywhere in executable code.
    code = _code_source(PREDICTION_MODULE)
    assert "lag_24h_coefficient * row.lag_168h_amount_per_mwh" not in code
    assert "lag_168h_coefficient * row.lag_24h_amount_per_mwh" not in code


def test_prediction_copies_identity_currency_timestamp_and_actual_from_row() -> None:
    call = _prediction_call()
    values = {keyword.arg: keyword.value for keyword in call.keywords if keyword.arg is not None}
    assert call.args == []
    assert set(values) == set(PREDICTION_FIELDS)
    for field, source_attr in (
        ("market_id", "market_id"),
        ("currency", "currency"),
        ("target_timestamp", "target_timestamp"),
        ("actual_amount_per_mwh", "target_amount_per_mwh"),
    ):
        assert _is_attribute(values[field], "row", source_attr)
    predicted = values["predicted_amount_per_mwh"]
    assert isinstance(predicted, ast.Name)
    assert predicted.id == "predicted_amount_per_mwh"


def test_predictor_iterates_supplied_rows_directly_without_repair() -> None:
    predictor = _function_def(PREDICTION_MODULE, PREDICTOR)
    comprehensions = [
        generator
        for node in ast.walk(predictor)
        if isinstance(node, ast.GeneratorExp)
        for generator in node.generators
    ]
    assert len(comprehensions) == 1
    iterator = comprehensions[0].iter
    assert isinstance(iterator, ast.Name)
    assert iterator.id == "evaluation_rows"
    assert comprehensions[0].ifs == []
    code = _code_source(PREDICTION_MODULE)
    for forbidden in (
        "sorted(",
        ".sort(",
        "reverse",
        "shuffle",
        "sample(",
        "random",
        "deduplicat",
        "groupby",
        "itertools",
        "evaluation_rows[1:]",
        "evaluation_rows[:",
        "continue",
        "break",
    ):
        assert forbidden not in code
    identifiers = _identifier_names(PREDICTION_MODULE)
    for forbidden in ("sorted", "sort", "reverse", "shuffle", "groupby", "filter"):
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
        "abs(",
        "max(",
        "min(",
        "epsilon",
        "regulariz",
        "numpy",
        "sklearn",
        "pandas",
    ):
        assert forbidden not in code
    identifiers = _identifier_names(PREDICTION_MODULE)
    for forbidden in ("float", "round", "quantize", "isfinite", "abs"):
        assert forbidden not in identifiers
    assert "Decimal" in identifiers
    assert "DecimalException" in identifiers
    for expected in (
        "fit.lag_24h_coefficient.is_finite()",
        "fit.lag_168h_coefficient.is_finite()",
        "fit.intercept_amount_per_mwh.is_finite()",
        "row.lag_24h_amount_per_mwh.is_finite()",
        "row.lag_168h_amount_per_mwh.is_finite()",
        "row.target_amount_per_mwh.is_finite()",
        "predicted_amount_per_mwh.is_finite()",
    ):
        assert expected in code


def test_predictor_performs_no_currency_or_unit_conversion() -> None:
    code = _code_source(PREDICTION_MODULE).lower()
    for forbidden in (
        "exchange",
        "fx_rate",
        "fx_conversion",
        "convert",
        "base_currency",
        "conversion_rate",
        "unit_convert",
    ):
        assert forbidden not in code
    # Currency only flows from the row into the result; it never enters arithmetic.
    value = _assigned_value(
        PREDICTION_MODULE, "_predicted_amount_per_mwh", "predicted_amount_per_mwh"
    )
    assert "currency" not in ast.unparse(value)


def test_only_narrowed_decimal_exception_handling_is_used() -> None:
    handlers = [
        node for node in ast.walk(_tree(PREDICTION_MODULE)) if isinstance(node, ast.ExceptHandler)
    ]
    assert len(handlers) == 1
    handler_type = handlers[0].type
    assert isinstance(handler_type, ast.Name)
    assert handler_type.id == "DecimalException"
    code = _code_source(PREDICTION_MODULE)
    assert "except Exception" not in code
    assert "except BaseException" not in code
    assert "except:" not in code
    assert "raise InvalidRequestError(msg) from error" in code
    assert "msg = _NON_FINITE_PREDICTION_MESSAGE" in code


def test_predictor_fails_closed_with_static_sanitized_messages() -> None:
    flattened = _flattened_source(PREDICTION_MODULE)
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
        assert message_name in flattened
    for phrase in (
        "requires at least one evaluation row",
        "requires rows from exactly one market",
        "requires rows in exactly one currency",
        "requires unique target timestamps",
        "requires strictly increasing target timestamps",
        "requires finite fitted coefficients and intercept",
        "requires finite feature and target values",
        "requires finite predicted values",
    ):
        assert phrase in flattened
    # Every raise passes a static module-level message, never an f-string or repr.
    for node in ast.walk(_tree(PREDICTION_MODULE)):
        if isinstance(node, ast.JoinedStr):
            raise AssertionError("formatted strings are not allowed in the predictor")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "InvalidRequestError":
                assert len(node.args) == 1
                argument = node.args[0]
                assert isinstance(argument, ast.Name)
                assert argument.id == "msg" or argument.id.startswith("_")
    assert "repr(" not in _code_source(PREDICTION_MODULE)
    assert "str(" not in _code_source(PREDICTION_MODULE)


def test_predictor_depends_only_on_allowed_inward_contracts() -> None:
    modules = imported_modules(PREDICTION_MODULE)
    assert sorted(module for module in modules if is_forbidden(module, FORBIDDEN_PREFIXES)) == []
    assert modules - ALLOWED_MODULE_IMPORTS == set()
    names = imported_names(PREDICTION_MODULE)
    for expected in (
        "dataclass",
        "Decimal",
        "DecimalException",
        "InvalidRequestError",
        "EntityId",
        "CurrencyCode",
        "FiniteDecimal",
        "UtcDateTime",
        ROW_CLASS,
        FIT_CLASS,
    ):
        assert expected in names
    leaked_types = sorted(
        name for name in annotation_type_names(PREDICTION_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_predictor_does_not_build_split_fit_or_reuse_one_feature_predictor() -> None:
    names = imported_names(PREDICTION_MODULE)
    for forbidden in (
        FEATURE_BUILDER,
        SPLITTER,
        SPLIT_CLASS,
        FITTER,
        ONE_FEATURE_PREDICTOR,
        ONE_FEATURE_PREDICTION_CLASS,
        "MarketPriceRecord",
        "EnergyPrice",
    ):
        assert forbidden not in names
    code = _code_source(PREDICTION_MODULE)
    for forbidden in (
        FEATURE_BUILDER,
        SPLITTER,
        SPLIT_CLASS,
        FITTER,
        ONE_FEATURE_PREDICTOR,
        ONE_FEATURE_PREDICTION_CLASS,
        "training_rows",
        "cutoff",
        f"{FIT_CLASS}(",
        f"{ROW_CLASS}(",
        "slope",
    ):
        assert forbidden not in code
    calls = _called_names(PREDICTION_MODULE)
    assert FITTER not in calls
    assert FEATURE_BUILDER not in calls
    assert SPLITTER not in calls


def test_predictor_does_not_depend_on_persistence_metric_or_comparison() -> None:
    names = imported_names(PREDICTION_MODULE)
    for forbidden in (
        "PreviousDayPersistenceDAMPriceForecastModel",
        "PreviousDayPersistenceBacktestCase",
        "PreviousDayPersistenceMAEResult",
        "DAMPriceLag24hLinearRegressionMAEResult",
        "DAMPricePersistenceVsTrainedOLSMAEComparison",
        "evaluate_previous_day_persistence_mae",
        "evaluate_dam_price_lag_24h_linear_regression_mae",
        "compare_dam_price_persistence_vs_trained_ols_mae",
    ):
        assert forbidden not in names
    code = _code_source(PREDICTION_MODULE).lower()
    for forbidden in (
        "persistence",
        "backtest",
        "mae",
        "mse",
        "rmse",
        "mape",
        "residual",
        "evaluate",
        "compare",
        "comparison",
        "champion",
        "winner",
        "improvement",
        "select",
        "best",
    ):
        assert forbidden not in code


def test_predictor_is_offline_only_and_not_live_inference() -> None:
    code = _code_source(PREDICTION_MODULE)
    lowered = code.lower()
    for forbidden in (
        "priceforecastpoint",
        "energyprice",
        "dampriceforecastmodelrequest",
        "dampriceforecastmodelport",
        "forecastingexecutionport",
        "forecast_run_id",
        "generated_at",
        "async ",
        "await ",
        "registry",
        "pickle",
        "joblib",
        "json",
        "serializ",
        "open(",
        "path(",
        "environ",
        "getenv",
        ".now(",
        "utcnow",
        "uuid",
        "asyncio",
        "print(",
        "logging",
    ):
        assert forbidden not in lowered


def test_no_generic_model_framework_or_ml_common_exists() -> None:
    class_names = [name for path in ML_ROOT.rglob("*.py") for name in _module_class_names(path)]
    assert sorted(name for name in class_names if name in GENERIC_MODEL_NAMES) == []
    identifiers = _identifier_names(PREDICTION_MODULE)
    assert sorted(name for name in identifiers if name in GENERIC_MODEL_NAMES) == []
    assert not any(
        module.startswith("energy_trading.ml.common")
        for module in imported_modules(PREDICTION_MODULE)
    )
    assert "energy_trading.ml.common" in FORBIDDEN_PREFIXES


def test_existing_dam_price_modules_remain_unaware_of_the_predictor() -> None:
    others = [
        path
        for path in sorted(DAM_ML_ROOT.rglob("*.py"))
        if path not in {PREDICTION_MODULE, *PREDICTION_ARTIFACT_CONSUMER_MODULES}
    ]
    assert others
    for path in others:
        source = path.read_text(encoding="utf-8")
        assert PREDICTION_CLASS not in source
        assert PREDICTOR not in source
        assert MODULE_NAME not in source


def test_prediction_artifact_consumers_are_exactly_the_evaluator_and_comparisons() -> None:
    # The Chunk 183 evaluator, the Chunk 184 comparison, the Chunk 185
    # comparison, and the Chunk 186 three-way comparison are the only authorized
    # downstream consumers of the prediction artifact type. Each may import the
    # DTO from the prediction module but must never reference or invoke the
    # predictor function itself.
    assert PREDICTION_ARTIFACT_CONSUMER_MODULES == frozenset(
        {
            EVALUATION_MODULE,
            COMPARISON_MODULE,
            PERSISTENCE_COMPARISON_MODULE,
            THREE_WAY_COMPARISON_MODULE,
        }
    )
    assert EVALUATION_MODULE.parent == DAM_ML_ROOT
    assert EVALUATION_MODULE.name == "lag_24h_168h_linear_regression_evaluation.py"
    assert COMPARISON_MODULE.parent == DAM_ML_ROOT
    assert COMPARISON_MODULE.name == "lag_24h_vs_lag_24h_168h_ols_comparison.py"
    assert PERSISTENCE_COMPARISON_MODULE.parent == DAM_ML_ROOT
    assert PERSISTENCE_COMPARISON_MODULE.name == "persistence_vs_lag_24h_168h_ols_comparison.py"
    assert THREE_WAY_COMPARISON_MODULE.parent == DAM_ML_ROOT
    assert THREE_WAY_COMPARISON_MODULE.name == (
        "persistence_vs_lag_24h_vs_lag_24h_168h_ols_comparison.py"
    )
    for consumer in sorted(PREDICTION_ARTIFACT_CONSUMER_MODULES):
        assert consumer.is_file()
        source = consumer.read_text(encoding="utf-8")
        assert PREDICTOR not in source
        names = imported_names(consumer)
        assert PREDICTION_CLASS in names
        assert PREDICTOR not in names
        assert f"energy_trading.ml.dam_price.{MODULE_NAME}" in imported_modules(consumer)
        tree = ast.parse(source, filename=str(consumer))
        call_names: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name):
                call_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                call_names.add(func.attr)
        assert PREDICTOR not in call_names
        assert PREDICTION_CLASS not in call_names


def test_application_agents_do_not_import_the_predictor() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert PREDICTION_CLASS not in source
        assert PREDICTOR not in source
        assert MODULE_NAME not in source


def test_orchestration_and_langgraph_do_not_import_the_predictor() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert PREDICTION_CLASS not in source
        assert PREDICTOR not in source
        assert MODULE_NAME not in source
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in imported_modules(GRAPH_MODULE)
    )


def test_api_composition_and_create_app_do_not_import_or_call_the_predictor() -> None:
    assert collect_import_violations(API_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert PREDICTION_CLASS not in source
        assert PREDICTOR not in source
        assert MODULE_NAME not in source
    create_app = _function_def(API_APP, "create_app")
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


def test_infrastructure_does_not_import_the_predictor() -> None:
    for path in sorted((PRODUCTION_ROOT / "infrastructure").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert PREDICTOR not in source
        assert MODULE_NAME not in source


def test_workflow_state_shape_is_unchanged() -> None:
    items = _annassign_items(_class_def(STATE_MODULE, "WorkflowState"))
    assert tuple(_field_name(item) for item in items) == WORKFLOW_STATE_FIELDS
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert PREDICTION_CLASS not in source
    assert PREDICTOR not in source
    assert MODULE_NAME not in source
    assert "dam_price" not in source
