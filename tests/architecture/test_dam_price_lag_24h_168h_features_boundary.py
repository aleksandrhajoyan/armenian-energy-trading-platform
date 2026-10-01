"""Exact T-24h plus T-168h DAM Price feature rows stay a narrow ML artifact."""

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
FEATURES_MODULE = DAM_ML_ROOT / "lag_24h_168h_features.py"
ONE_FEATURE_MODULE = DAM_ML_ROOT / "lag_24h_features.py"
SPLIT_MODULE = DAM_ML_ROOT / "chronological_feature_split.py"
FIT_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression.py"
PREDICTION_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression_prediction.py"
TRAINED_EVALUATION_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression_evaluation.py"
COMPARISON_MODULE = DAM_ML_ROOT / "persistence_vs_trained_ols_comparison.py"
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

ROW_CLASS = "DAMPriceLag24h168hFeatureRow"
BUILDER = "build_dam_price_lag_24h_168h_feature_rows"
ONE_FEATURE_ROW_CLASS = "DAMPriceLag24hFeatureRow"
ONE_FEATURE_BUILDER = "build_dam_price_lag_24h_feature_rows"
SPLITTER = "split_dam_price_feature_rows_chronologically"
FITTER = "fit_dam_price_lag_24h_linear_regression"
PREDICTOR = "predict_dam_price_lag_24h_linear_regression"
TRAINED_EVALUATOR = "evaluate_dam_price_lag_24h_linear_regression_mae"
COMPARISON_FUNCTION = "compare_dam_price_persistence_vs_trained_ols_mae"
PERSISTENCE_BUILDER = "build_previous_day_persistence_backtest_cases"
PERSISTENCE_EVALUATOR = "evaluate_previous_day_persistence_mae"

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.infrastructure",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.application.ports",
    "energy_trading.ml.common",
    "energy_trading.ml.consumer_load",
    "energy_trading.ml.dam_price.chronological_feature_split",
    "energy_trading.ml.dam_price.lag_24h_features",
    "energy_trading.ml.dam_price.lag_24h_linear_regression",
    "energy_trading.ml.dam_price.lag_24h_linear_regression_prediction",
    "energy_trading.ml.dam_price.lag_24h_linear_regression_evaluation",
    "energy_trading.ml.dam_price.persistence_vs_trained_ols_comparison",
    "energy_trading.ml.dam_price.previous_day_persistence",
    "energy_trading.ml.dam_price.previous_day_persistence_backtest",
    "energy_trading.ml.dam_price.previous_day_persistence_evaluation",
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
        "Fitter",
        "Feature",
        "FeatureVector",
        "FeatureSet",
        "FeatureRegistry",
        "FeaturePipeline",
        "Dataset",
        "TrainingRow",
        "ModelRegistry",
        "ModelSelector",
        "Metric",
        "Evaluator",
        "Comparator",
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
        "EnergyPrice",
        "PreviousDayPersistenceDAMPriceForecastModel",
        "PreviousDayPersistenceBacktestCase",
        "DAMPriceChronologicalFeatureSplit",
        "DAMPriceLag24hFeatureRow",
        "DAMPriceLag24hLinearRegressionFit",
        "DAMPriceLag24hLinearRegressionPrediction",
        "WorkflowState",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "datetime",
        "energy_trading.application.errors",
        "energy_trading.domain.models.observations",
        "energy_trading.domain.value_objects.quantities",
        "energy_trading.domain.value_objects.time",
    }
)

GENERIC_FEATURE_NAMES = frozenset(
    {
        "Feature",
        "Features",
        "FeatureVector",
        "FeatureSet",
        "FeatureRegistry",
        "FeaturePipeline",
        "FeatureStore",
        "FeatureFactory",
        "Dataset",
        "DatasetSplit",
        "TrainingRow",
        "Trainer",
        "Model",
        "ModelRegistry",
        "ModelSelector",
        "AgentFactory",
        "ServiceLocator",
        "Estimator",
        "Pipeline",
    }
)

DERIVED_VALUE_TOKENS = (
    "difference",
    "percent",
    "percentage",
    "return",
    "spread",
    "ratio",
    "momentum",
    "volatility",
    "revenue",
    "profit",
    "vwap",
    "rolling",
    "mean",
    "stddev",
    "std_dev",
    "median",
    "variance",
)

ROW_FIELDS = (
    "market_id",
    "currency",
    "target_timestamp",
    "lag_24h_amount_per_mwh",
    "lag_168h_amount_per_mwh",
    "target_amount_per_mwh",
)

ROW_ANNOTATIONS = {
    "market_id": "EntityId",
    "currency": "CurrencyCode",
    "target_timestamp": "UtcDateTime",
    "lag_24h_amount_per_mwh": "FiniteDecimal",
    "lag_168h_amount_per_mwh": "FiniteDecimal",
    "target_amount_per_mwh": "FiniteDecimal",
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
    ONE_FEATURE_MODULE,
    SPLIT_MODULE,
    FIT_MODULE,
    PREDICTION_MODULE,
    TRAINED_EVALUATION_MODULE,
    COMPARISON_MODULE,
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

    The module docstring deliberately names rejected behaviour (same weekday,
    calendar week, previous trading week, market session, tolerance,
    interpolation, resampling, fill, rolling statistics, returns, spreads, and
    volume), so forbidden-token checks must run on executable code only.
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


def _code_without_module_paths(path: Path) -> str:
    """Return executable source with the package-path token removed.

    ``energy_trading`` legitimately contains the substring ``trading``, so
    semantic token checks must not be confused by import paths.
    """

    return _code_source(path).replace("energy_trading", "")


def _flattened_source(path: Path) -> str:
    """Return source with quotes removed and whitespace collapsed.

    Ruff format may wrap long message constants into implicit string
    concatenation across lines, which is a formatting artifact rather than a
    semantic difference.
    """

    return " ".join(path.read_text(encoding="utf-8").replace('"', "").split())


def _function_def(path: Path, function_name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return node
    msg = f"function {function_name!r} not found in {path}"
    raise AssertionError(msg)


def _module_constant_literals(path: Path) -> list[ast.expr]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    literals: list[ast.expr] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            literals.extend(node.value.elts if isinstance(node.value, ast.Tuple) else [node.value])
    return literals


def test_features_module_lives_under_dam_price_ml_package() -> None:
    assert FEATURES_MODULE.is_relative_to(DAM_ML_ROOT)
    assert FEATURES_MODULE.name == "lag_24h_168h_features.py"
    assert _module_class_names(FEATURES_MODULE) == [ROW_CLASS]
    assert _public_function_names(FEATURES_MODULE) == [BUILDER]
    assert _base_names(_class_def(FEATURES_MODULE, ROW_CLASS)) == set()


def test_row_dataclass_is_frozen_slotted_and_exactly_six_fields() -> None:
    class_def = _class_def(FEATURES_MODULE, ROW_CLASS)
    keywords = _dataclass_keywords(class_def)
    assert keywords == {"frozen": True, "slots": True}
    assert _annassign_field_names(FEATURES_MODULE, ROW_CLASS) == ROW_FIELDS
    annotations = {
        item.target.id: ast.unparse(item.annotation)
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert annotations == ROW_ANNOTATIONS
    leaked = sorted(name for name in annotations if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    defaults = {
        item.target.id: item.value
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert all(value is None for value in defaults.values())


def test_row_exposes_no_volume_derived_metric_or_identity_field() -> None:
    names = set(_annassign_field_names(FEATURES_MODULE, ROW_CLASS))
    assert names == set(ROW_FIELDS)
    for forbidden in (
        "volume",
        "volume_mwh",
        "price_difference",
        "percentage_change",
        "returns",
        "spread",
        "rolling_mean",
        "rolling_stddev",
        "volatility",
        "momentum",
        "hour",
        "day_of_week",
        "holiday",
        "weather",
        "hydro",
        "generation",
        "news",
        "market_session",
        "forecast_run_id",
        "generated_at",
        "model_name",
        "model_version",
        "provider",
        "residual",
        "mse",
        "rmse",
        "mape",
        "r2",
        "metadata",
        "feature_vector",
    ):
        assert forbidden not in names


def test_builder_is_synchronous_keyword_only_and_returns_rows() -> None:
    tree = ast.parse(FEATURES_MODULE.read_text(encoding="utf-8"), filename=str(FEATURES_MODULE))
    builder = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == BUILDER
    )
    assert not isinstance(builder, ast.AsyncFunctionDef)
    assert tuple(arg.arg for arg in builder.args.args) == ()
    assert tuple(arg.arg for arg in builder.args.kwonlyargs) == ("history",)
    assert builder.args.vararg is None
    assert builder.args.kwarg is None
    assert builder.args.kw_defaults == [None]
    history_arg = builder.args.kwonlyargs[0]
    assert history_arg.annotation is not None
    assert ast.unparse(history_arg.annotation) == "tuple[MarketPriceRecord, ...]"
    assert builder.returns is not None
    assert ast.unparse(builder.returns) == f"tuple[{ROW_CLASS}, ...]"


def test_builder_uses_exact_24h_and_168h_lag_constants() -> None:
    literals = [ast.unparse(node) for node in _module_constant_literals(FEATURES_MODULE)]
    assert any("timedelta(hours=24)" in value for value in literals)
    assert any("timedelta(hours=168)" in value for value in literals)
    source = FEATURES_MODULE.read_text(encoding="utf-8")
    assert "_LAG_24H = timedelta(hours=24)" in source
    assert "_LAG_168H = timedelta(hours=168)" in source


def test_builder_requires_both_exact_lags_before_emitting_a_row() -> None:
    code = _code_source(FEATURES_MODULE)
    assert "target - _LAG_24H in by_timestamp" in code
    assert "target - _LAG_168H in by_timestamp" in code
    assert "for target in sorted(by_timestamp)" in code
    assert " and " in code
    assert "_row_for_target(by_timestamp, target)" in code


def test_builder_has_no_approximate_nearest_or_weekday_semantics() -> None:
    code = _code_without_module_paths(FEATURES_MODULE)
    for forbidden in (
        "167",
        "169",
        "weekday",
        "isocalendar",
        "week",
        "business",
        "trading",
        "nearest",
        "tolerance",
        "interpolat",
        "resample",
        "fillna",
        "ffill",
        "bfill",
        "backfill",
        "session",
        "ZoneInfo",
        "calendar",
    ):
        assert forbidden not in code
    identifiers = _identifier_names(FEATURES_MODULE)
    for forbidden in ("ZoneInfo", "calendar", "nearest", "session", "weekday"):
        assert forbidden not in identifiers


def test_row_amounts_come_only_from_the_three_exact_observations() -> None:
    code = _code_source(FEATURES_MODULE)
    assert "lag_24h_record.price.amount_per_mwh" in code
    assert "lag_168h_record.price.amount_per_mwh" in code
    assert "target_record.price.amount_per_mwh" in code
    assert "target_record.market_id" in code
    assert "target_record.price.currency" in code
    assert "target_timestamp=target" in code


def test_builder_performs_no_derived_price_arithmetic() -> None:
    code = _code_source(FEATURES_MODULE)
    for forbidden in ("abs(", "float(", "round(", "quantize"):
        assert forbidden not in code
    # Timestamp lag subtraction is required; price arithmetic is not.
    for forbidden in (
        "amount_per_mwh -",
        "amount_per_mwh +",
        "- record.price",
        "+ record.price",
        "amount_per_mwh *",
        "amount_per_mwh /",
    ):
        assert forbidden not in code
    # Derived-value vocabulary is checked against identifiers: Python
    # keywords such as ``return`` are not identifiers.
    identifiers = {name.lower() for name in _identifier_names(FEATURES_MODULE)}
    for token in DERIVED_VALUE_TOKENS:
        assert token not in identifiers
    assert "abs" not in identifiers
    assert "float" not in identifiers
    assert "round" not in identifiers
    assert "Decimal" not in identifiers


def test_builder_ignores_volume() -> None:
    code = _code_source(FEATURES_MODULE)
    assert "volume" not in code
    identifiers = _identifier_names(FEATURES_MODULE)
    assert "volume_mwh" not in identifiers
    assert "volume" not in identifiers


def test_builder_has_exactly_one_sort_phase() -> None:
    code = _code_source(FEATURES_MODULE)
    assert code.count("sorted(") == 1
    identifiers = _identifier_names(FEATURES_MODULE)
    assert "sorted" in identifiers
    for forbidden in ("sort", "reverse", "shuffle", "sample", "choice"):
        assert forbidden not in identifiers
    for forbidden in (".sort(", "reverse", "shuffle", "deduplicat", "groupby"):
        assert forbidden not in code


def test_builder_depends_only_on_allowed_inward_contracts() -> None:
    leaked = sorted(
        module
        for module in imported_modules(FEATURES_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(FEATURES_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(FEATURES_MODULE)
    assert "InvalidRequestError" in names
    assert "MarketPriceRecord" in names
    assert "CurrencyCode" in names
    assert "EntityId" in names
    assert "FiniteDecimal" in names
    assert "UtcDateTime" in names
    assert "dataclass" in names
    assert "timedelta" in names
    leaked_types = sorted(
        name for name in annotation_type_names(FEATURES_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_builder_does_not_chain_the_one_feature_experiment() -> None:
    names = imported_names(FEATURES_MODULE)
    assert ONE_FEATURE_ROW_CLASS not in names
    assert ONE_FEATURE_BUILDER not in names
    for forbidden in (
        SPLITTER,
        FITTER,
        PREDICTOR,
        TRAINED_EVALUATOR,
        COMPARISON_FUNCTION,
        PERSISTENCE_BUILDER,
        PERSISTENCE_EVALUATOR,
    ):
        assert forbidden not in names
    modules = imported_modules(FEATURES_MODULE)
    assert "energy_trading.ml.dam_price.lag_24h_features" not in modules
    assert "energy_trading.ml.dam_price.chronological_feature_split" not in modules
    assert "energy_trading.ml.dam_price.lag_24h_linear_regression" not in modules
    source = FEATURES_MODULE.read_text(encoding="utf-8")
    for forbidden in (
        ONE_FEATURE_BUILDER,
        SPLITTER,
        FITTER,
        PREDICTOR,
        TRAINED_EVALUATOR,
        COMPARISON_FUNCTION,
        PERSISTENCE_BUILDER,
        PERSISTENCE_EVALUATOR,
    ):
        assert forbidden not in source
    assert f"{ONE_FEATURE_ROW_CLASS}(" not in source
    assert "EnergyPrice(" not in source


def test_builder_fails_closed_with_sanitized_messages() -> None:
    source = FEATURES_MODULE.read_text(encoding="utf-8")
    assert source.count("InvalidRequestError") >= 4
    for message_name in (
        "_MIXED_MARKET_MESSAGE",
        "_MIXED_CURRENCY_MESSAGE",
        "_DUPLICATE_TIMESTAMP_MESSAGE",
    ):
        assert message_name in source
    flattened = _flattened_source(FEATURES_MODULE)
    for phrase in (
        "require history from exactly one market",
        "require history in exactly one currency",
        "require unique historical timestamps",
    ):
        assert phrase in flattened
    for leak in ("AMD", "EUR", "market-alpha", "market-beta"):
        assert leak not in source


def test_no_generic_feature_framework_exists() -> None:
    class_names = [name for path in ML_ROOT.rglob("*.py") for name in _module_class_names(path)]
    leaked_classes = sorted(name for name in class_names if name in GENERIC_FEATURE_NAMES)
    assert leaked_classes == []
    identifiers = _identifier_names(FEATURES_MODULE)
    leaked_ids = sorted(name for name in identifiers if name in GENERIC_FEATURE_NAMES)
    assert leaked_ids == []
    code = _code_source(FEATURES_MODULE)
    assert "energy_trading.ml.common" not in code
    assert not any(
        module.startswith("energy_trading.ml.common") for module in ALLOWED_MODULE_IMPORTS
    )
    source = FEATURES_MODULE.read_text(encoding="utf-8")
    assert "registry" not in source.lower()
    assert "selector" not in source.lower()


def test_builder_has_no_io_clock_or_environment_access() -> None:
    code = _code_source(FEATURES_MODULE)
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
    modules = imported_modules(FEATURES_MODULE)
    for absent in (
        "uuid",
        "random",
        "secrets",
        "os",
        "io",
        "pathlib",
        "asyncio",
        "json",
        "math",
    ):
        assert absent not in modules


def test_published_dam_price_modules_remain_unaware_of_the_two_lag_features() -> None:
    for path in UNAWARE_MODULES:
        source = path.read_text(encoding="utf-8")
        assert ROW_CLASS not in source
        assert BUILDER not in source
        assert "lag_24h_168h_features" not in source
        names = imported_names(path)
        assert ROW_CLASS not in names
        assert BUILDER not in names


def test_application_agents_do_not_import_the_two_lag_features() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert ROW_CLASS not in names
        assert BUILDER not in names
        source = path.read_text(encoding="utf-8")
        assert "lag_24h_168h_features" not in source


def test_orchestration_and_langgraph_do_not_import_the_two_lag_features() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert ROW_CLASS not in names
        assert BUILDER not in names
        source = path.read_text(encoding="utf-8")
        assert "lag_24h_168h_features" not in source
    graph_modules = imported_modules(GRAPH_MODULE)
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in graph_modules
    )


def test_api_composition_does_not_import_or_construct_the_two_lag_features() -> None:
    assert collect_import_violations(API_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert ROW_CLASS not in names
        assert BUILDER not in names
        source = path.read_text(encoding="utf-8")
        assert "lag_24h_168h_features" not in source
    app_source = API_APP.read_text(encoding="utf-8")
    assert BUILDER not in app_source
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
    assert BUILDER not in call_names
    assert ROW_CLASS not in call_names


def test_workflow_state_shape_is_unchanged() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert ROW_CLASS not in names
    assert BUILDER not in names
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "lag_24h_168h_features" not in source
    assert "dam_price" not in source
