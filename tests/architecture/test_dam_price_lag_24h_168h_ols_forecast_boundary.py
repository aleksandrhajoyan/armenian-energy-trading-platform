"""Lag-24h plus lag-168h OLS DAM Price candidate adapter stays a narrow, unwired ML seam."""

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
ADAPTER_MODULE = DAM_ML_ROOT / "lag_24h_168h_ols_forecast.py"
ADAPTER_CLASS = "Lag24h168hOLSDAMPriceForecastModel"
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
INFRASTRUCTURE_ROOT = PRODUCTION_ROOT / "infrastructure"
PORT_MODULE = PRODUCTION_ROOT / "application" / "ports" / "dam_price_forecast_model.py"
FORECAST_POINT_MODULE = PRODUCTION_ROOT / "domain" / "models" / "forecasting.py"
MONEY_MODULE = PRODUCTION_ROOT / "domain" / "value_objects" / "money.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.infrastructure",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.ml.common",
    "energy_trading.ml.consumer_load",
    "energy_trading.ml.dam_price.previous_day_persistence",
    "energy_trading.ml.dam_price.previous_day_persistence_backtest",
    "energy_trading.ml.dam_price.previous_day_persistence_evaluation",
    "energy_trading.ml.dam_price.chronological_feature_split",
    "energy_trading.ml.dam_price.lag_24h_features",
    "energy_trading.ml.dam_price.lag_24h_linear_regression",
    "energy_trading.ml.dam_price.lag_24h_linear_regression_prediction",
    "energy_trading.ml.dam_price.lag_24h_linear_regression_evaluation",
    "energy_trading.ml.dam_price.lag_24h_168h_features",
    "energy_trading.ml.dam_price.lag_24h_168h_chronological_feature_split",
    "energy_trading.ml.dam_price.lag_24h_168h_linear_regression_prediction",
    "energy_trading.ml.dam_price.lag_24h_168h_linear_regression_evaluation",
    "energy_trading.ml.dam_price.persistence_vs_trained_ols_comparison",
    "energy_trading.ml.dam_price.lag_24h_vs_lag_24h_168h_ols_comparison",
    "energy_trading.ml.dam_price.persistence_vs_lag_24h_168h_ols_comparison",
    "energy_trading.ml.dam_price.persistence_vs_lag_24h_vs_lag_24h_168h_ols_comparison",
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
    "pathlib",
    "socket",
    "os",
    "io",
    "json",
    "pickle",
    "logging",
    "time",
    "asyncio",
    "importlib",
    "typing",
    "math",
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "datetime",
        "decimal",
        "energy_trading.application.errors",
        "energy_trading.application.ports.dam_price_forecast_model",
        "energy_trading.domain.models.forecasting",
        "energy_trading.domain.models.observations",
        "energy_trading.domain.value_objects.money",
        "energy_trading.ml.dam_price.lag_24h_168h_linear_regression",
    }
)

ALLOWED_IMPORTED_NAMES = frozenset(
    {
        "datetime",
        "timedelta",
        "DecimalException",
        "InvalidRequestError",
        "DAMPriceForecastModelRequest",
        "PriceForecastPoint",
        "MarketPriceRecord",
        "EnergyPrice",
        "DAMPriceLag24h168hLinearRegressionFit",
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
        "Booster",
        "LGBMRegressor",
        "XGBRegressor",
        "Model",
        "Trainer",
        "Estimator",
        "Predictor",
        "Dataset",
        "ModelPort",
        "ForecastPort",
        "ForecastModelPort",
        "MLPort",
        "BestModel",
        "ChampionModel",
        "SelectedModel",
        "ProductionModel",
        "ComparisonResult",
        "Ranking",
        "ClockPort",
        "UuidFactory",
        "ForecastingExecutionPort",
        "ForecastingWorkflowStep",
        "DAMPriceForecastAgent",
        "DAMPriceForecastModelPort",
        "WorkflowState",
        "DAMPriceLag24h168hFeatureRow",
        "DAMPriceLag24h168hChronologicalFeatureSplit",
        "DAMPriceLag24h168hLinearRegressionPrediction",
        "DAMPriceLag24h168hLinearRegressionMAEResult",
        "DAMPriceLag24hLinearRegressionFit",
        "PreviousDayPersistenceDAMPriceForecastModel",
        "float",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "ModelPort",
        "ForecastPort",
        "ForecastModelPort",
        "MLPort",
        "BestModel",
        "ChampionModel",
        "SelectedModel",
        "ProductionModel",
        "Champion",
        "winner",
        "champion",
        "selected_model",
        "ranking",
        "threshold",
        "registry",
        "factory",
        "uuid4",
        "now",
        "utcnow",
        "today",
        "TYPE_CHECKING",
        "importlib",
        "import_module",
        "__import__",
        "getattr",
        "setattr",
        "globals",
        "locals",
        "eval",
        "exec",
        "ForecastingExecutionPort",
        "DAMPriceForecastAgent",
        "DAMPriceForecastModelPort",
        "build_workflow_graph",
        "create_app",
        "build_dam_price_lag_24h_168h_feature_rows",
        "split_dam_price_lag_24h_168h_feature_rows_chronologically",
        "fit_dam_price_lag_24h_168h_linear_regression",
        "predict_dam_price_lag_24h_168h_linear_regression",
        "evaluate_dam_price_lag_24h_168h_linear_regression_mae",
        "fit_dam_price_lag_24h_linear_regression",
        "predict_dam_price_lag_24h_linear_regression",
        "evaluate_dam_price_lag_24h_linear_regression_mae",
        "build_previous_day_persistence_backtest_cases",
        "evaluate_previous_day_persistence_mae",
        "compare_dam_price_persistence_vs_trained_ols_mae",
        "compare_dam_price_lag_24h_vs_lag_24h_168h_ols_mae",
        "compare_dam_price_persistence_vs_lag_24h_168h_ols_mae",
        "compare_dam_price_persistence_vs_lag_24h_vs_lag_24h_168h_ols_mae",
        "PreviousDayPersistenceDAMPriceForecastModel",
        "volume_mwh",
        "quantize",
        "to_integral_value",
        "to_integral",
        "normalize",
        "clip",
        "clamp",
        "convert",
        "exchange_rate",
        "fx_rate",
    }
)

GENERIC_ML_CLASS_NAMES = frozenset(
    {
        "ModelPort",
        "ForecastModelPort",
        "MLPort",
        "ForecastPort",
        "Predictor",
        "PredictorPort",
        "InferencePort",
        "GenericModelPort",
        "TimeSeriesModelPort",
        "BestModel",
        "ChampionModel",
        "SelectedModel",
        "ProductionModel",
        "ComparisonResult",
        "Ranking",
    }
)

FORBIDDEN_CALL_NAMES = frozenset(
    {
        "abs",
        "max",
        "min",
        "round",
        "float",
        "int",
        "sorted",
        "sort",
        "set",
        "frozenset",
        "dict",
        "fromkeys",
        "reversed",
        "quantize",
        "normalize",
        "floor",
        "ceil",
        "clip",
        "clamp",
        "open",
        "print",
        "getattr",
        "__import__",
        "import_module",
        "to_thread",
        "Decimal",
    }
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


def _module_class_names(path: Path) -> list[str]:
    return [node.name for node in _tree(path).body if isinstance(node, ast.ClassDef)]


def _identifier_names(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.alias):
            names.add(node.name)
            if node.asname is not None:
                names.add(node.asname)
    return names


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _calls(path: Path) -> list[ast.Call]:
    return [node for node in ast.walk(_tree(path)) if isinstance(node, ast.Call)]


def _calls_named(path: Path, name: str) -> list[ast.Call]:
    return [node for node in _calls(path) if _call_name(node) == name]


def _keyword_map(call: ast.Call) -> dict[str, str]:
    return {kw.arg: ast.unparse(kw.value) for kw in call.keywords if kw.arg is not None}


def _annassign_field_names(path: Path, class_name: str) -> tuple[str, ...]:
    class_def = _class_def(path, class_name)
    return tuple(
        item.target.id
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    )


def _function_def(path: Path, name: str) -> ast.FunctionDef:
    for node in _tree(path).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    msg = f"function {name!r} not found in {path}"
    raise AssertionError(msg)


def test_exactly_one_public_class_without_bases_under_ml_dam_price() -> None:
    assert ADAPTER_MODULE.is_relative_to(DAM_ML_ROOT)
    assert _module_class_names(ADAPTER_MODULE) == [ADAPTER_CLASS]
    class_def = _class_def(ADAPTER_MODULE, ADAPTER_CLASS)
    assert class_def.bases == []
    assert class_def.keywords == []
    assert class_def.decorator_list == []
    public_functions = [
        node.name
        for node in _tree(ADAPTER_MODULE).body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and not node.name.startswith("_")
    ]
    assert public_functions == []
    leaked = sorted(_identifier_names(ADAPTER_MODULE) & GENERIC_ML_CLASS_NAMES)
    assert leaked == []


def test_adapter_depends_only_on_allowed_inward_contracts() -> None:
    modules = imported_modules(ADAPTER_MODULE)
    leaked = sorted(module for module in modules if is_forbidden(module, FORBIDDEN_PREFIXES))
    assert leaked == []
    assert modules - ALLOWED_MODULE_IMPORTS == set()
    assert imported_names(ADAPTER_MODULE) == ALLOWED_IMPORTED_NAMES | ALLOWED_MODULE_IMPORTS
    leaked_types = sorted(annotation_type_names(ADAPTER_MODULE) & FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    for node in ast.walk(_tree(ADAPTER_MODULE)):
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0
            for alias in node.names:
                assert alias.asname is None
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.asname is None
        if isinstance(node, ast.If):
            assert "TYPE_CHECKING" not in ast.unparse(node.test)


def test_constructor_is_keyword_only_over_required_chunk_181_fit() -> None:
    class_def = _class_def(ADAPTER_MODULE, ADAPTER_CLASS)
    init_fn = next(
        item
        for item in class_def.body
        if isinstance(item, ast.FunctionDef) and item.name == "__init__"
    )
    assert tuple(arg.arg for arg in init_fn.args.args) == ("self",)
    assert tuple(arg.arg for arg in init_fn.args.kwonlyargs) == ("fit",)
    assert init_fn.args.kw_defaults == [None]
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    annotation = init_fn.args.kwonlyargs[0].annotation
    assert annotation is not None
    assert ast.unparse(annotation) == "DAMPriceLag24h168hLinearRegressionFit"
    init_calls = {_call_name(node) for node in ast.walk(init_fn) if isinstance(node, ast.Call)}
    assert init_calls == {"_require_finite_fit"}


def test_forecast_is_async_keyword_only_and_narrowly_typed() -> None:
    class_def = _class_def(ADAPTER_MODULE, ADAPTER_CLASS)
    operations = [
        item
        for item in class_def.body
        if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
        and not item.name.startswith("_")
    ]
    assert len(operations) == 1
    forecast_fn = operations[0]
    assert isinstance(forecast_fn, ast.AsyncFunctionDef)
    assert forecast_fn.name == "forecast"
    assert tuple(arg.arg for arg in forecast_fn.args.args) == ("self",)
    assert tuple(arg.arg for arg in forecast_fn.args.kwonlyargs) == ("request",)
    assert forecast_fn.args.kw_defaults == [None]
    assert forecast_fn.args.vararg is None
    assert forecast_fn.args.kwarg is None
    annotation = forecast_fn.args.kwonlyargs[0].annotation
    assert annotation is not None
    assert ast.unparse(annotation) == "DAMPriceForecastModelRequest"
    assert forecast_fn.returns is not None
    assert ast.unparse(forecast_fn.returns) == "tuple[PriceForecastPoint, ...]"


def test_requested_targets_are_iterated_directly_without_sort_or_dedup() -> None:
    class_def = _class_def(ADAPTER_MODULE, ADAPTER_CLASS)
    forecast_fn = next(
        item
        for item in class_def.body
        if isinstance(item, ast.AsyncFunctionDef) and item.name == "forecast"
    )
    generators = [
        generator
        for node in ast.walk(forecast_fn)
        if isinstance(node, ast.GeneratorExp)
        for generator in node.generators
    ]
    assert len(generators) == 1
    assert ast.unparse(generators[0].iter) == "request.target_timestamps"
    assert ast.unparse(generators[0].target) == "target"
    assert generators[0].ifs == []
    leaked_calls = sorted(
        {name for node in _calls(ADAPTER_MODULE) if (name := _call_name(node))}
        & FORBIDDEN_CALL_NAMES
    )
    assert leaked_calls == []


def test_exact_24h_and_168h_elapsed_lags_are_declared() -> None:
    hours: list[object] = []
    for call in _calls_named(ADAPTER_MODULE, "timedelta"):
        assert call.args == []
        assert [kw.arg for kw in call.keywords] == ["hours"]
        value = call.keywords[0].value
        assert isinstance(value, ast.Constant)
        hours.append(value.value)
    assert sorted(hours) == [24, 168]  # type: ignore[type-var]
    source = ADAPTER_MODULE.read_text(encoding="utf-8")
    assert "_LAG_24H = timedelta(hours=24)" in source
    assert "_LAG_168H = timedelta(hours=168)" in source
    point_fn = _function_def(ADAPTER_MODULE, "_point_for_target")
    lag_assignments = {
        node.targets[0].id: ast.unparse(node.value)
        for node in ast.walk(point_fn)
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
    }
    assert "target - _LAG_24H" in lag_assignments["lag_24h"]
    assert "target - _LAG_168H" in lag_assignments["lag_168h"]
    assert "_LAG_168H" not in lag_assignments["lag_24h"]
    assert "_LAG_24H" not in lag_assignments["lag_168h"]
    lookup_fn = _function_def(ADAPTER_MODULE, "_unique_lag_observation")
    comparisons = [
        ast.unparse(node) for node in ast.walk(lookup_fn) if isinstance(node, ast.Compare)
    ]
    assert "record.timestamp == reference" in comparisons
    assert not any(
        isinstance(op, ast.Lt | ast.LtE | ast.Gt | ast.GtE)
        for node in ast.walk(lookup_fn)
        if isinstance(node, ast.Compare)
        for op in node.ops
    )


def test_each_coefficient_multiplies_its_own_lag_price_and_intercept_is_added() -> None:
    point_fn = _function_def(ADAPTER_MODULE, "_point_for_target")
    products = {
        ast.unparse(node)
        for node in ast.walk(point_fn)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult)
    }
    assert products == {
        "fit.lag_24h_coefficient * lag_24h.price.amount_per_mwh",
        "fit.lag_168h_coefficient * lag_168h.price.amount_per_mwh",
    }
    raw_assignments = [
        ast.unparse(node.value)
        for node in ast.walk(point_fn)
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "raw_prediction"
    ]
    assert raw_assignments == [
        "fit.lag_24h_coefficient * lag_24h.price.amount_per_mwh"
        " + fit.lag_168h_coefficient * lag_168h.price.amount_per_mwh"
        " + fit.intercept_amount_per_mwh"
    ]
    assert not any(
        isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div | ast.FloorDiv | ast.Pow)
        for node in ast.walk(_tree(ADAPTER_MODULE))
    )


def test_only_decimal_exception_is_translated_and_non_finite_result_rejected() -> None:
    handlers = [
        node for node in ast.walk(_tree(ADAPTER_MODULE)) if isinstance(node, ast.ExceptHandler)
    ]
    assert len(handlers) == 1
    assert handlers[0].type is not None
    assert ast.unparse(handlers[0].type) == "DecimalException"
    raises = [node for node in ast.walk(handlers[0]) if isinstance(node, ast.Raise)]
    assert len(raises) == 1
    assert raises[0].cause is not None
    point_fn = _function_def(ADAPTER_MODULE, "_point_for_target")
    finite_checks = [
        node
        for node in ast.walk(point_fn)
        if isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.Not)
        and ast.unparse(node.operand) == "raw_prediction.is_finite()"
    ]
    assert len(finite_checks) == 1
    fit_check = ast.unparse(_function_def(ADAPTER_MODULE, "_require_finite_fit"))
    for field in ("lag_24h_coefficient", "lag_168h_coefficient", "intercept_amount_per_mwh"):
        assert f"fit.{field}.is_finite()" in fit_check


def test_canonical_price_and_point_are_built_from_request_identity_and_currency() -> None:
    price_calls = _calls_named(ADAPTER_MODULE, "EnergyPrice")
    assert len(price_calls) == 1
    assert price_calls[0].args == []
    assert _keyword_map(price_calls[0]) == {
        "amount_per_mwh": "raw_prediction",
        "currency": "request.currency",
    }
    point_calls = _calls_named(ADAPTER_MODULE, "PriceForecastPoint")
    assert len(point_calls) == 1
    assert point_calls[0].args == []
    point_keywords = _keyword_map(point_calls[0])
    assert point_keywords == {
        "forecast_run_id": "request.forecast_run_id",
        "market_id": "request.market_id",
        "generated_at": "request.generated_at",
        "target_timestamp": "target",
        "price": "EnergyPrice(amount_per_mwh=raw_prediction, currency=request.currency)",
    }
    source = ADAPTER_MODULE.read_text(encoding="utf-8")
    assert "price.currency" not in source


def test_no_clamp_fx_rounding_volume_io_identity_or_dynamic_dependency() -> None:
    identifiers = _identifier_names(ADAPTER_MODULE)
    leaked = sorted(identifiers & FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    tree = _tree(ADAPTER_MODULE)
    zero_comparisons = [
        ast.unparse(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.Compare)
        and any(
            isinstance(operand, ast.Constant) and operand.value == 0
            for operand in (node.left, *node.comparators)
        )
        and "len(" not in ast.unparse(node)
    ]
    assert zero_comparisons == []
    assert not any(isinstance(node, ast.Global | ast.Nonlocal) for node in ast.walk(tree))
    lowered = ADAPTER_MODULE.read_text(encoding="utf-8").lower()
    code_only = "\n".join(
        line for line in lowered.splitlines() if not line.lstrip().startswith(("#", "*"))
    )
    for needle in ("lightgbm", "xgboost", "sklearn", "numpy", "pandas", "scipy", "statsmodels"):
        assert f"import {needle}" not in code_only
        assert f"from {needle}" not in code_only
    for needle in ("open(", "print(", "logger", "logging", "to_thread", "pickle", "json"):
        assert needle not in code_only


def test_application_port_and_domain_output_contracts_are_unchanged() -> None:
    port_source = PORT_MODULE.read_text(encoding="utf-8")
    assert "async def forecast(" in port_source
    assert "request: DAMPriceForecastModelRequest" in port_source
    assert "tuple[PriceForecastPoint, ...]" in port_source
    assert ADAPTER_CLASS not in port_source
    assert _annassign_field_names(PORT_MODULE, "DAMPriceForecastModelRequest") == (
        "forecast_run_id",
        "generated_at",
        "market_id",
        "currency",
        "history",
        "target_timestamps",
    )
    assert _annassign_field_names(FORECAST_POINT_MODULE, "PriceForecastPoint") == (
        "forecast_run_id",
        "market_id",
        "generated_at",
        "target_timestamp",
        "price",
    )
    money_source = MONEY_MODULE.read_text(encoding="utf-8")
    assert "amount_per_mwh: FiniteDecimal" in money_source


def test_application_agents_do_not_import_the_adapter() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        assert ADAPTER_CLASS not in imported_names(path)
        source = path.read_text(encoding="utf-8")
        assert ADAPTER_CLASS not in source
        assert "lag_24h_168h_ols_forecast" not in source


def test_orchestration_and_langgraph_do_not_import_the_adapter() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        assert ADAPTER_CLASS not in imported_names(path)
        source = path.read_text(encoding="utf-8")
        assert ADAPTER_CLASS not in source
        assert "lag_24h_168h_ols_forecast" not in source
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in imported_modules(GRAPH_MODULE)
    )


def test_api_composition_does_not_import_or_construct_the_adapter() -> None:
    for path in sorted(API_ROOT.rglob("*.py")):
        assert ADAPTER_CLASS not in imported_names(path)
        source = path.read_text(encoding="utf-8")
        assert ADAPTER_CLASS not in source
        assert "lag_24h_168h_ols_forecast" not in source
    create_app = _function_def(API_APP, "create_app")
    call_names = {_call_name(node) for node in ast.walk(create_app) if isinstance(node, ast.Call)}
    assert ADAPTER_CLASS not in call_names


def test_infrastructure_does_not_import_the_adapter() -> None:
    for path in sorted(INFRASTRUCTURE_ROOT.rglob("*.py")):
        assert ADAPTER_CLASS not in imported_names(path)
        source = path.read_text(encoding="utf-8")
        assert ADAPTER_CLASS not in source
        assert "lag_24h_168h_ols_forecast" not in source


def test_no_other_production_module_references_the_adapter() -> None:
    referencing = sorted(
        str(path.relative_to(PRODUCTION_ROOT))
        for path in PRODUCTION_ROOT.rglob("*.py")
        if path != ADAPTER_MODULE
        and (
            ADAPTER_CLASS in path.read_text(encoding="utf-8")
            or "lag_24h_168h_ols_forecast" in path.read_text(encoding="utf-8")
        )
    )
    assert referencing == []


def test_workflow_state_shape_is_unchanged() -> None:
    assert _annassign_field_names(STATE_MODULE, "WorkflowState") == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert ADAPTER_CLASS not in names
    assert "PriceForecastPoint" not in names
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "lag_24h_168h_ols_forecast" not in source
