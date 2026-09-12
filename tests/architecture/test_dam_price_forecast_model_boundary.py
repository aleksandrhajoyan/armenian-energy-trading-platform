"""DAM Price Forecast model port stays a narrow application↔ML boundary."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    collect_http_api_import_violations,
    collect_import_violations,
    http_transport_api_paths,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
PORTS_ROOT = PRODUCTION_ROOT / "application" / "ports"
PORT_MODULE = PORTS_ROOT / "dam_price_forecast_model.py"
CONSUMER_PORT_MODULE = PORTS_ROOT / "consumer_load_forecast_model.py"
PORTS_INIT = PORTS_ROOT / "__init__.py"
FORECASTING_MODULE = PRODUCTION_ROOT / "domain" / "models" / "forecasting.py"
OBSERVATIONS_MODULE = PRODUCTION_ROOT / "domain" / "models" / "observations.py"
MONEY_MODULE = PRODUCTION_ROOT / "domain" / "value_objects" / "money.py"
QUANTITIES_MODULE = PRODUCTION_ROOT / "domain" / "value_objects" / "quantities.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"
STATE_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
ML_ROOT = PRODUCTION_ROOT / "ml"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
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
)

FORBIDDEN_TYPE_NAMES = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "dict",
        "Dict",
        "Mapping",
        "MutableMapping",
        "TypedDict",
        "bytes",
        "bytearray",
        "Path",
        "PurePath",
        "DataFrame",
        "ndarray",
        "NDArray",
        "Series",
        "Booster",
        "LGBMRegressor",
        "XGBRegressor",
        "Request",
        "Response",
        "RetryPolicy",
        "FailurePolicyPort",
        "WorkflowState",
    }
)

FORBIDDEN_REQUEST_FIELDS = frozenset(
    {
        "learning_rate",
        "n_estimators",
        "max_depth",
        "model_path",
        "model_file",
        "model_version",
        "provider",
        "hyperparameters",
        "feature_registry",
        "horizon",
        "weather",
        "hydro",
        "news",
        "load",
        "features",
        "metadata",
        "payload",
        "redis_key",
        "database_id",
        "tenant",
        "fx_rate",
        "exchange_rate",
        "converted_currency",
    }
)

GENERIC_ML_CLASS_NAMES = frozenset(
    {
        "ModelPort",
        "ForecastModelPort",
        "MLPort",
        "Predictor",
        "PredictorPort",
        "InferencePort",
        "GenericModelPort",
        "ForecastPort",
        "TimeSeriesModelPort",
        "PriceForecastModelPort",
    }
)

AUTHORIZED_MODEL_PORTS = (
    "ConsumerLoadForecastModelPort",
    "DAMPriceForecastModelPort",
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "datetime",
        "typing",
        "energy_trading.domain.models.forecasting",
        "energy_trading.domain.models.observations",
        "energy_trading.domain.value_objects.quantities",
        "energy_trading.domain.value_objects.time",
    }
)

ALLOWED_REQUEST_FIELDS = {
    "market_id": "EntityId",
    "currency": "CurrencyCode",
    "history": "tuple[MarketPriceRecord, ...]",
    "target_timestamps": "tuple[UtcDateTime, ...]",
}

ALLOWED_CONSUMER_REQUEST_FIELDS = {
    "consumer_id": "EntityId",
    "history": "tuple[ConsumptionRecord, ...]",
    "target_timestamps": "tuple[UtcDateTime, ...]",
}

ALLOWED_STATE_FIELDS = (
    "workflow_id",
    "portfolio_id",
    "delivery_date",
    "correlation_id",
    "phase",
    "status",
    "diagnostics",
)

DAM_PRICE_FORECAST_NAMES = frozenset(
    {
        "DAMPriceForecastModelPort",
        "DAMPriceForecastModelRequest",
        "DAMPriceForecastAgent",
        "DAMPriceForecastPoint",
        "DAMMarketPriceRecord",
    }
)

DUPLICATE_CURRENCY_CLASS_NAMES = frozenset(
    {
        "Currency",
        "IsoCurrency",
        "MarketCurrency",
        "PriceCurrency",
        "CurrencyId",
    }
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


def _annassign_field_annotations(path: Path, class_name: str) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            annotations: dict[str, str] = {}
            for item in node.body:
                if (
                    isinstance(item, ast.AnnAssign)
                    and isinstance(item.target, ast.Name)
                    and item.annotation is not None
                ):
                    annotations[item.target.id] = ast.unparse(item.annotation)
            return annotations
    msg = f"class {class_name!r} not found in {path}"
    raise AssertionError(msg)


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
            keyword.arg: ast.literal_eval(keyword.value)
            for keyword in call.keywords
            if keyword.arg is not None
        }
    msg = f"dataclass decorator not found on {class_def.name}"
    raise AssertionError(msg)


def _production_python_files() -> list[Path]:
    return sorted(path for path in PRODUCTION_ROOT.rglob("*.py") if path.is_file())


def test_dam_price_forecast_model_port_lives_under_application_ports() -> None:
    assert PORT_MODULE.is_relative_to(PORTS_ROOT)
    assert PORT_MODULE.name == "dam_price_forecast_model.py"
    exported = imported_names(PORTS_INIT)
    assert "DAMPriceForecastModelPort" in exported
    assert "DAMPriceForecastModelRequest" in exported


def test_module_defines_exactly_request_and_port() -> None:
    assert _module_class_names(PORT_MODULE) == [
        "DAMPriceForecastModelRequest",
        "DAMPriceForecastModelPort",
    ]
    assert _public_function_names(PORT_MODULE) == []


def test_authorized_model_ports_are_exactly_consumer_load_and_dam_price() -> None:
    protocol_names: list[str] = []
    generic_names: list[str] = []
    for path in sorted(PORTS_ROOT.rglob("*.py")):
        for name in _module_class_names(path):
            if name in GENERIC_ML_CLASS_NAMES:
                generic_names.append(f"{path.name}:{name}")
            if name.endswith("ModelPort") or name in GENERIC_ML_CLASS_NAMES:
                protocol_names.append(name)
    assert protocol_names == list(AUTHORIZED_MODEL_PORTS)
    assert generic_names == []
    production_model_ports = [
        name
        for path in _production_python_files()
        for name in _module_class_names(path)
        if name.endswith("ModelPort") or name in GENERIC_ML_CLASS_NAMES
    ]
    assert production_model_ports == list(AUTHORIZED_MODEL_PORTS)


def test_dam_price_forecast_model_port_does_not_import_forbidden_layers() -> None:
    leaked = sorted(
        module
        for module in imported_modules(PORT_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(PORT_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(PORT_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    application_leaks = collect_import_violations(
        PRODUCTION_ROOT / "application",
        ("energy_trading.ml",),
    )
    domain_leaks = collect_import_violations(
        PRODUCTION_ROOT / "domain",
        ("energy_trading.ml", "energy_trading.application", "energy_trading.infrastructure"),
    )
    assert application_leaks == []
    assert domain_leaks == []


def test_dam_price_forecast_model_port_has_no_generic_payload_types() -> None:
    names = annotation_type_names(PORT_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    assert "MarketPriceRecord" in names
    assert "PriceForecastPoint" in names
    assert "DAMPriceForecastModelRequest" in names
    assert "EntityId" in names
    assert "CurrencyCode" in names
    source = PORT_MODULE.read_text(encoding="utf-8")
    assert "DAMPriceForecastPoint" not in source
    assert "DAMMarketPriceRecord" not in source
    assert "DataFrame" not in source
    assert "ndarray" not in source


def test_forecast_is_async_and_narrowly_typed() -> None:
    class_def = _class_def(PORT_MODULE, "DAMPriceForecastModelPort")
    bases = _base_names(class_def)
    assert bases == {"Protocol"}
    assert "ABC" not in bases
    assert [param.name for param in class_def.type_params] == []
    source = PORT_MODULE.read_text(encoding="utf-8")
    assert "abstractmethod" not in source
    assert "TypeVar" not in source
    assert "Generic[" not in source
    operations = [
        item for item in class_def.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert len(operations) == 1
    forecast_fn = operations[0]
    assert isinstance(forecast_fn, ast.AsyncFunctionDef)
    assert forecast_fn.name == "forecast"
    assert tuple(arg.arg for arg in forecast_fn.args.args) == ("self",)
    assert tuple(arg.arg for arg in forecast_fn.args.kwonlyargs) == ("request",)
    assert forecast_fn.args.vararg is None
    assert forecast_fn.args.kwarg is None
    request_arg = forecast_fn.args.kwonlyargs[0]
    assert request_arg.annotation is not None
    assert forecast_fn.returns is not None
    assert ast.unparse(request_arg.annotation) == "DAMPriceForecastModelRequest"
    assert ast.unparse(forecast_fn.returns) == "tuple[PriceForecastPoint, ...]"


def test_request_contains_only_market_currency_canonical_history_and_explicit_targets() -> None:
    request_def = _class_def(PORT_MODULE, "DAMPriceForecastModelRequest")
    keywords = _dataclass_keywords(request_def)
    assert keywords == {"frozen": True, "slots": True}
    annotations = _annassign_field_annotations(PORT_MODULE, "DAMPriceForecastModelRequest")
    assert annotations == ALLOWED_REQUEST_FIELDS
    assert tuple(annotations) == ("market_id", "currency", "history", "target_timestamps")
    leaked = sorted(name for name in annotations if name in FORBIDDEN_REQUEST_FIELDS)
    assert leaked == []
    assert "horizon" not in annotations
    imported = imported_names(PORT_MODULE)
    assert "EntityId" in imported
    assert "CurrencyCode" in imported
    assert "MarketPriceRecord" in imported
    assert "UtcDateTime" in imported
    assert "PriceForecastPoint" in imported
    modules = imported_modules(PORT_MODULE)
    assert "energy_trading.domain.value_objects.quantities" in modules
    quantities = QUANTITIES_MODULE.read_text(encoding="utf-8")
    assert "CurrencyCode" in quantities
    money = MONEY_MODULE.read_text(encoding="utf-8")
    assert "currency: CurrencyCode" in money


def test_historical_market_price_and_forecast_types_are_reused_not_duplicated() -> None:
    imported = imported_names(PORT_MODULE)
    assert "MarketPriceRecord" in imported
    assert "PriceForecastPoint" in imported
    assert "EntityId" in imported
    assert "CurrencyCode" in imported
    production_observation_classes = _module_class_names(OBSERVATIONS_MODULE)
    assert "MarketPriceRecord" in production_observation_classes
    duplicated_history = [
        f"{path.relative_to(PRODUCTION_ROOT)}:{name}"
        for path in _production_python_files()
        if path != OBSERVATIONS_MODULE
        for name in _module_class_names(path)
        if name in {"MarketPriceRecord", "DAMMarketPriceRecord"}
    ]
    assert duplicated_history == []
    duplicated_forecast_point = [
        f"{path.relative_to(PRODUCTION_ROOT)}:{name}"
        for path in _production_python_files()
        if path != FORECASTING_MODULE
        for name in _module_class_names(path)
        if name in {"PriceForecastPoint", "DAMPriceForecastPoint"}
    ]
    assert duplicated_forecast_point == []
    duplicated_ids = [
        f"{path.relative_to(PRODUCTION_ROOT)}:{name}"
        for path in _production_python_files()
        for name in _module_class_names(path)
        if name in {"MarketId", "MarketIdentifier", *DUPLICATE_CURRENCY_CLASS_NAMES}
    ]
    assert duplicated_ids == []
    assert "MarketId" not in imported


def test_no_currency_conversion_or_alternate_currency_framework() -> None:
    source = PORT_MODULE.read_text(encoding="utf-8")
    assert "item.price.currency" in source
    assert "exchange_rate" not in source
    assert "fx_rate" not in source
    assert "convert_currency" not in source
    assert "asyncio.to_thread" not in source
    names = imported_names(PORT_MODULE)
    assert "EnergyPrice" not in names
    money_modules = imported_modules(PORT_MODULE)
    assert "energy_trading.domain.value_objects.money" not in money_modules
    conversion_classes = [
        f"{path.relative_to(PRODUCTION_ROOT)}:{name}"
        for path in _production_python_files()
        for name in _module_class_names(path)
        if name in {"CurrencyConverter", "FxService", "ExchangeRatePort"}
    ]
    assert conversion_classes == []


def test_domain_forecast_output_reuses_energy_price() -> None:
    leaked = sorted(
        module
        for module in imported_modules(FORECASTING_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    source = FORECASTING_MODULE.read_text(encoding="utf-8")
    assert "class PriceForecastPoint" in source
    assert "price: EnergyPrice" in source
    observations = OBSERVATIONS_MODULE.read_text(encoding="utf-8")
    assert "class MarketPriceRecord" in observations
    assert "price: EnergyPrice" in observations
    assert "market_id: EntityId" in observations


def test_graph_and_workflow_state_remain_unaware_of_dam_price_forecast() -> None:
    graph_names = imported_names(GRAPH_MODULE)
    graph_modules = imported_modules(GRAPH_MODULE)
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "DAMPriceForecastModelPort" not in graph_names
    assert "DAMPriceForecastModelRequest" not in graph_names
    assert "DAMPriceForecastAgent" not in graph_names
    assert "PriceForecastPoint" not in graph_names
    assert "energy_trading.application.ports.dam_price_forecast_model" not in graph_modules
    assert "DAMPriceForecast" not in graph_source
    state_fields = tuple(
        item.target.id
        for item in _class_def(STATE_MODULE, "WorkflowState").body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    )
    assert state_fields == ALLOWED_STATE_FIELDS
    state_names = imported_names(STATE_MODULE)
    assert "DAMPriceForecastModelPort" not in state_names
    assert "PriceForecastPoint" not in state_names
    assert "MarketPriceRecord" not in state_names


def test_api_composition_remains_unaware_of_dam_price_forecast_model_port() -> None:
    forbidden_wiring = (
        "energy_trading.application.ports.dam_price_forecast_model",
        "energy_trading.ml",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    app_names = imported_names(API_APP)
    assert "DAMPriceForecastModelPort" not in app_names
    assert "DAMPriceForecastModelRequest" not in app_names
    assert "build_workflow_graph" not in app_names
    api_leaks: list[str] = []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        modules = imported_modules(path)
        if DAM_PRICE_FORECAST_NAMES & names:
            api_leaks.append(path.name)
        if "energy_trading.application.ports.dam_price_forecast_model" in modules:
            api_leaks.append(path.name)
    assert api_leaks == []
    transport_leaks: list[str] = []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        if DAM_PRICE_FORECAST_NAMES & names:
            transport_leaks.append(path.name)
    assert transport_leaks == []


def test_no_production_dam_price_forecast_model_adapter() -> None:
    production_impls: list[str] = []
    for path in _production_python_files():
        if path == PORT_MODULE:
            continue
        for name in _module_class_names(path):
            if name in {
                "DAMPriceForecastModelPort",
                "DAMPriceForecastPoint",
                "DAMMarketPriceRecord",
            } or name.endswith("DAMPriceForecastModel"):
                production_impls.append(f"{path.relative_to(PRODUCTION_ROOT)}:{name}")
    assert production_impls == []
    if ML_ROOT.exists():
        ml_files = sorted(path.name for path in ML_ROOT.rglob("*.py"))
        assert ml_files == []
    port_classes = set(_module_class_names(PORT_MODULE))
    assert port_classes == {
        "DAMPriceForecastModelRequest",
        "DAMPriceForecastModelPort",
    }


def test_consumer_load_forecast_port_contract_remains_unchanged() -> None:
    annotations = _annassign_field_annotations(
        CONSUMER_PORT_MODULE, "ConsumerLoadForecastModelRequest"
    )
    assert annotations == ALLOWED_CONSUMER_REQUEST_FIELDS
    class_def = _class_def(CONSUMER_PORT_MODULE, "ConsumerLoadForecastModelPort")
    operations = [
        item for item in class_def.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert len(operations) == 1
    forecast_fn = operations[0]
    assert isinstance(forecast_fn, ast.AsyncFunctionDef)
    assert forecast_fn.name == "forecast"
    assert ast.unparse(forecast_fn.returns) == "tuple[LoadForecastPoint, ...]"
    assert ast.unparse(forecast_fn.args.kwonlyargs[0].annotation) == (
        "ConsumerLoadForecastModelRequest"
    )


def test_application_and_domain_do_not_import_production_ml_packages() -> None:
    ml_vendor_prefixes = (
        "lightgbm",
        "xgboost",
        "sklearn",
        "numpy",
        "pandas",
        "polars",
        "torch",
        "tensorflow",
        "joblib",
        "onnx",
        "mlflow",
        "optuna",
        "energy_trading.ml",
    )
    application_leaks = collect_import_violations(
        PRODUCTION_ROOT / "application",
        ml_vendor_prefixes,
    )
    domain_leaks = collect_import_violations(PRODUCTION_ROOT / "domain", ml_vendor_prefixes)
    assert application_leaks == []
    assert domain_leaks == []
