"""Exact 24-hour lag DAM Price feature rows stay a narrow ML artifact."""

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
FEATURES_MODULE = DAM_ML_ROOT / "lag_24h_features.py"
BACKTEST_MODULE = DAM_ML_ROOT / "previous_day_persistence_backtest.py"
LIVE_ADAPTER_MODULE = DAM_ML_ROOT / "previous_day_persistence.py"
EVALUATION_MODULE = DAM_ML_ROOT / "previous_day_persistence_evaluation.py"
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

ROW_CLASS = "DAMPriceLag24hFeatureRow"
BUILDER = "build_dam_price_lag_24h_feature_rows"

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
        "PreviousDayPersistenceDAMPriceForecastModel",
        "PreviousDayPersistenceBacktestCase",
        "PreviousDayPersistenceMAEResult",
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
        "FeatureFactory",
        "TrainingRow",
        "TrainingSet",
        "Dataset",
        "DataFrame",
        "ModelRegistry",
        "ModelSelector",
        "AgentFactory",
        "ServiceLocator",
    }
)

FORBIDDEN_FEATURE_TOKENS = (
    "volume",
    "vwap",
    "hour",
    "weekday",
    "month",
    "holiday",
    "weather",
    "generation",
    "hydro",
    "renewable",
    "rolling",
    "volatility",
    "std_dev",
    "spread",
    "residual",
    "lag_168h",
    "hours=168",
    "interpolate",
    "interpolation",
    "resample",
    "ffill",
    "bfill",
    "forward_fill",
    "backward_fill",
    "nearest",
    "tolerance",
    "weekday",
    "session",
    "ZoneInfo",
    "clip",
    "quantize",
    "normalize",
    "standardize",
    "scale",
)

ROW_FIELDS = (
    "market_id",
    "currency",
    "target_timestamp",
    "lag_24h_amount_per_mwh",
    "target_amount_per_mwh",
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

    The module docstring deliberately names the rules this builder rejects
    and the features it does not construct, so forbidden-token checks run on
    code only.
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


def test_feature_builder_lives_under_dam_price_ml_package() -> None:
    assert FEATURES_MODULE.is_relative_to(DAM_ML_ROOT)
    assert FEATURES_MODULE.name == "lag_24h_features.py"
    assert _module_class_names(FEATURES_MODULE) == [ROW_CLASS]
    assert _public_function_names(FEATURES_MODULE) == [BUILDER]
    assert _base_names(_class_def(FEATURES_MODULE, ROW_CLASS)) == set()


def test_row_dataclass_is_frozen_slotted_and_exactly_five_fields() -> None:
    class_def = _class_def(FEATURES_MODULE, ROW_CLASS)
    keywords = _dataclass_keywords(class_def)
    assert keywords == {"frozen": True, "slots": True}
    assert _annassign_field_names(FEATURES_MODULE, ROW_CLASS) == ROW_FIELDS
    annotations = {
        item.target.id: ast.unparse(item.annotation)
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert annotations == {
        "market_id": "EntityId",
        "currency": "CurrencyCode",
        "target_timestamp": "UtcDateTime",
        "lag_24h_amount_per_mwh": "FiniteDecimal",
        "target_amount_per_mwh": "FiniteDecimal",
    }
    leaked = sorted(name for name in annotations if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    defaults = {
        item.target.id: item.value
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert all(value is None for value in defaults.values())


def test_row_exposes_no_extra_engineered_feature() -> None:
    names = set(_annassign_field_names(FEATURES_MODULE, ROW_CLASS))
    assert names == set(ROW_FIELDS)
    for token in FORBIDDEN_FEATURE_TOKENS:
        assert token not in names


def test_builder_is_synchronous_keyword_only_and_returns_row_tuple() -> None:
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


def test_builder_uses_exact_elapsed_twenty_four_hour_lag_only() -> None:
    source = FEATURES_MODULE.read_text(encoding="utf-8")
    code = _code_source(FEATURES_MODULE)
    assert "timedelta(hours=24)" in source
    identifiers = _identifier_names(FEATURES_MODULE)
    assert "timedelta" in identifiers
    assert "_LAG" in identifiers
    for forbidden_rule in (
        "hours=168",
        "days=7",
        "weekday",
        "business_day",
        "nearest",
        "interpolate",
        "interpolation",
        "resample",
        "ffill",
        "bfill",
        "forward_fill",
        "backward_fill",
        "rolling",
        "tolerance",
        "session",
        "ZoneInfo",
    ):
        assert forbidden_rule not in code


def test_builder_sorts_output_chronologically() -> None:
    tree = ast.parse(FEATURES_MODULE.read_text(encoding="utf-8"), filename=str(FEATURES_MODULE))
    builder = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == BUILDER
    )
    calls = [
        node
        for node in ast.walk(builder)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "sorted"
    ]
    assert len(calls) == 1


def test_builder_fails_closed_on_duplicate_mixed_market_and_mixed_currency() -> None:
    source = FEATURES_MODULE.read_text(encoding="utf-8")
    assert source.count("InvalidRequestError") >= 4
    assert "_DUPLICATE_TIMESTAMP_MESSAGE" in source
    assert "_MIXED_MARKET_MESSAGE" in source
    assert "_MIXED_CURRENCY_MESSAGE" in source
    for message in (
        "require history from exactly one market",
        "require history in exactly one currency",
        "require unique historical timestamps",
    ):
        assert message in source
    for leak in ("AMD", "EUR", "market-alpha", "market-beta"):
        assert leak not in source


def test_builder_does_not_depend_on_persistence_artifacts() -> None:
    names = imported_names(FEATURES_MODULE)
    assert "PreviousDayPersistenceDAMPriceForecastModel" not in names
    assert "PreviousDayPersistenceBacktestCase" not in names
    assert "PreviousDayPersistenceMAEResult" not in names
    assert "DAMPriceForecastModelRequest" not in names
    assert "PriceForecastPoint" not in names
    modules = imported_modules(FEATURES_MODULE)
    assert "energy_trading.ml.dam_price.previous_day_persistence" not in modules
    assert "energy_trading.ml.dam_price.previous_day_persistence_backtest" not in modules
    assert "energy_trading.ml.dam_price.previous_day_persistence_evaluation" not in modules
    assert "energy_trading.domain.models.forecasting" not in modules
    source = FEATURES_MODULE.read_text(encoding="utf-8")
    for forbidden in (
        "PreviousDayPersistenceDAMPriceForecastModel",
        "PreviousDayPersistenceBacktestCase",
        "PreviousDayPersistenceMAEResult",
        "build_previous_day_persistence_backtest_cases",
        "evaluate_previous_day_persistence_mae",
    ):
        assert forbidden not in source


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
    assert "MarketPriceRecord" in names
    assert "InvalidRequestError" in names
    assert "CurrencyCode" in names
    assert "EntityId" in names
    assert "FiniteDecimal" in names
    assert "UtcDateTime" in names
    assert "dataclass" in names
    leaked_types = sorted(
        name for name in annotation_type_names(FEATURES_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_builder_has_no_price_transformation_or_extra_feature_arithmetic() -> None:
    code = _code_source(FEATURES_MODULE)
    for forbidden in (
        "float(",
        "Decimal(",
        "round(",
        "abs(",
        "max(",
        "min(",
        "clip(",
        "quantize(",
        "normalize(",
        "standardize(",
        "volume",
        "vwap",
        "residual",
    ):
        assert forbidden not in code
    identifiers = _identifier_names(FEATURES_MODULE)
    assert "Decimal" not in identifiers
    assert "float" not in identifiers
    assert "abs" not in identifiers


def test_builder_accesses_only_canonical_price_amounts() -> None:
    source = FEATURES_MODULE.read_text(encoding="utf-8")
    assert "amount_per_mwh" in source
    assert "volume_mwh" not in source
    # Only the lag and target amounts are read from the price objects.
    assert source.count(".price.amount_per_mwh") == 2


def test_builder_has_no_io_clock_uuid_or_environment_access() -> None:
    source = FEATURES_MODULE.read_text(encoding="utf-8")
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
    modules = imported_modules(FEATURES_MODULE)
    for absent in ("uuid", "random", "secrets", "os", "io", "pathlib", "asyncio", "math"):
        assert absent not in modules


def test_no_generic_feature_framework_exists() -> None:
    class_names = [name for path in ML_ROOT.rglob("*.py") for name in _module_class_names(path)]
    leaked_classes = sorted(name for name in class_names if name in GENERIC_FEATURE_NAMES)
    assert leaked_classes == []
    common_imports = imported_modules(FEATURES_MODULE)
    assert not any(module.startswith("energy_trading.ml.common") for module in common_imports)
    assert "energy_trading.ml.common" in FORBIDDEN_PREFIXES
    identifiers = _identifier_names(FEATURES_MODULE)
    leaked_ids = sorted(name for name in identifiers if name in GENERIC_FEATURE_NAMES)
    assert leaked_ids == []
    source = FEATURES_MODULE.read_text(encoding="utf-8")
    assert "registry" not in source.lower()
    assert "selector" not in source.lower()
    assert "ServiceLocator" not in source
    assert "AgentFactory" not in source


def test_builder_does_not_train_fit_predict_or_score() -> None:
    code = _code_source(FEATURES_MODULE)
    for forbidden in ("fit(", "predict", "score(", "mae", "mse", "rmse", "split", "champion"):
        assert forbidden not in code.lower()
    # "models" is a legitimate domain package segment, so model usage is
    # checked by identifier rather than by substring.
    identifiers = {name.lower() for name in _identifier_names(FEATURES_MODULE)}
    for forbidden in ("fit", "predict", "model", "split", "champion"):
        assert forbidden not in identifiers
    modules = imported_modules(FEATURES_MODULE)
    assert not any(module.endswith(".model") for module in modules)
    assert "energy_trading.ml.dam_price.lag_24h_features" not in modules


def test_persistence_artifacts_remain_unchanged_and_unaware_of_features() -> None:
    for path in (LIVE_ADAPTER_MODULE, BACKTEST_MODULE, EVALUATION_MODULE):
        source = path.read_text(encoding="utf-8")
        assert ROW_CLASS not in source
        assert BUILDER not in source
        assert "lag_24h_features" not in source


def test_application_agents_do_not_import_the_feature_builder() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert ROW_CLASS not in names
        assert BUILDER not in names
        source = path.read_text(encoding="utf-8")
        assert "lag_24h_features" not in source


def test_orchestration_and_langgraph_do_not_import_the_feature_builder() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert ROW_CLASS not in names
        assert BUILDER not in names
        source = path.read_text(encoding="utf-8")
        assert "lag_24h_features" not in source
    graph_modules = imported_modules(GRAPH_MODULE)
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in graph_modules
    )


def test_api_composition_does_not_import_or_construct_the_feature_builder() -> None:
    assert collect_import_violations(API_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert ROW_CLASS not in names
        assert BUILDER not in names
        source = path.read_text(encoding="utf-8")
        assert "lag_24h_features" not in source
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


def test_workflow_state_shape_is_unchanged() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert ROW_CLASS not in names
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "lag_24h_features" not in source
    assert "dam_price" not in source
