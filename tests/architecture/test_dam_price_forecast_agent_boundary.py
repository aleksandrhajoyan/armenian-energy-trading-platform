"""DAM Price Forecast Agent stays a thin application↔model-port delegate."""

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
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
AGENT_MODULE = AGENTS_ROOT / "dam_price_forecast.py"
CONSUMER_AGENT_MODULE = AGENTS_ROOT / "consumer_load_forecast.py"
PORT_MODULE = PRODUCTION_ROOT / "application" / "ports" / "dam_price_forecast_model.py"
CONSUMER_PORT_MODULE = PRODUCTION_ROOT / "application" / "ports" / "consumer_load_forecast_model.py"
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
        "AgentFactory",
        "AgentRegistry",
        "ServiceLocator",
        "DAMPriceForecastAgentPort",
        "ForecastAgentPort",
        "MLAgentPort",
    }
)

GENERIC_FRAMEWORK_CLASS_NAMES = frozenset(
    {
        "AgentFactory",
        "AgentRegistry",
        "ServiceLocator",
        "DAMPriceForecastAgentPort",
        "ForecastAgentPort",
        "MLAgentPort",
        "ModelPort",
        "ForecastModelPort",
        "MLPort",
        "Predictor",
        "PredictorPort",
    }
)

ALLOWED_AGENT_IMPORTS = frozenset(
    {
        "energy_trading.application.agents.base",
        "energy_trading.application.ports.dam_price_forecast_model",
        "energy_trading.domain.models.forecasting",
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
        "DAMPriceForecastAgent",
        "DAMPriceForecastModelPort",
        "DAMPriceForecastModelRequest",
        "DAMPriceForecastPoint",
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


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _awaited_call(statement: ast.stmt) -> ast.Call | None:
    value: ast.expr | None = None
    if isinstance(statement, ast.Assign):
        value = statement.value
    elif isinstance(statement, ast.Expr):
        value = statement.value
    elif isinstance(statement, ast.Return):
        value = statement.value
    if isinstance(value, ast.Await) and isinstance(value.value, ast.Call):
        return value.value
    return None


def _production_python_files() -> list[Path]:
    return sorted(path for path in PRODUCTION_ROOT.rglob("*.py") if path.is_file())


def test_dam_price_forecast_agent_lives_under_application_agents() -> None:
    assert AGENT_MODULE.is_relative_to(AGENTS_ROOT)
    assert AGENT_MODULE.name == "dam_price_forecast.py"
    assert AGENT_MODULE.exists()


def test_exactly_one_production_dam_price_forecast_agent_class() -> None:
    production_agents: list[str] = []
    generic_names: list[str] = []
    for path in _production_python_files():
        for name in _module_class_names(path):
            if name == "DAMPriceForecastAgent":
                production_agents.append(path.relative_to(PRODUCTION_ROOT).as_posix())
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        for name in _module_class_names(path):
            if name in GENERIC_FRAMEWORK_CLASS_NAMES:
                generic_names.append(f"{path.name}:{name}")
    assert production_agents == ["application/agents/dam_price_forecast.py"]
    assert generic_names == []
    assert _module_class_names(AGENT_MODULE) == ["DAMPriceForecastAgent"]
    class_def = _class_def(AGENT_MODULE, "DAMPriceForecastAgent")
    assert _base_names(class_def) == set()
    assert list(class_def.type_params) == []


def test_agent_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(AGENT_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(AGENT_MODULE) - ALLOWED_AGENT_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(AGENT_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    imported = imported_names(AGENT_MODULE)
    assert "AgentName" in imported
    assert "DAMPriceForecastModelPort" in imported
    assert "DAMPriceForecastModelRequest" in imported
    assert "PriceForecastPoint" in imported
    assert "AgentFactory" not in imported
    assert "AgentRegistry" not in imported
    assert "ServiceLocator" not in imported
    assert "DAMPriceForecastAgentPort" not in imported


def test_constructor_injects_exactly_the_published_model_port() -> None:
    class_def = _class_def(AGENT_MODULE, "DAMPriceForecastAgent")
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert tuple(arg.arg for arg in init_fn.args.args) == ("self", "model")
    assert init_fn.args.posonlyargs == []
    assert init_fn.args.kwonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    assert init_fn.args.args[1].annotation is not None
    assert ast.unparse(init_fn.args.args[1].annotation) == "DAMPriceForecastModelPort"
    constructed = [_call_name(node) for node in ast.walk(init_fn) if isinstance(node, ast.Call)]
    assert "DAMPriceForecastModelPort" not in constructed
    assert "PriceForecastPoint" not in constructed
    assert "EnergyPrice" not in constructed


def test_run_is_async_and_narrowly_typed() -> None:
    class_def = _class_def(AGENT_MODULE, "DAMPriceForecastAgent")
    defined = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert defined == ["__init__", "name", "run"]
    name_fn = next(
        node for node in class_def.body if isinstance(node, ast.FunctionDef) and node.name == "name"
    )
    assert any(
        isinstance(item, ast.Name) and item.id == "property" for item in name_fn.decorator_list
    )
    assert name_fn.returns is not None
    assert ast.unparse(name_fn.returns) == "AgentName"
    run_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "run"
    )
    assert tuple(arg.arg for arg in run_fn.args.args) == ("self", "request")
    assert run_fn.args.vararg is None
    assert run_fn.args.kwarg is None
    assert run_fn.args.kwonlyargs == []
    assert run_fn.args.args[1].annotation is not None
    assert run_fn.returns is not None
    assert ast.unparse(run_fn.args.args[1].annotation) == "DAMPriceForecastModelRequest"
    assert ast.unparse(run_fn.returns) == "tuple[PriceForecastPoint, ...]"
    names = annotation_type_names(AGENT_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []


def test_run_delegates_exactly_once_to_forecast_without_reconstruction() -> None:
    class_def = _class_def(AGENT_MODULE, "DAMPriceForecastAgent")
    run_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "run"
    )
    control = [
        type(node).__name__
        for node in ast.walk(run_fn)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try, ast.With))
    ]
    assert control == []
    except_handlers = [node for node in ast.walk(run_fn) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    awaited: list[tuple[str | None, dict[str, str], list[str]]] = []
    for statement in run_fn.body:
        call = _awaited_call(statement)
        if call is None:
            continue
        keywords = {
            keyword.arg: ast.unparse(keyword.value)
            for keyword in call.keywords
            if keyword.arg is not None
        }
        args = [ast.unparse(arg) for arg in call.args]
        awaited.append((_call_name(call), keywords, args))
    assert awaited == [("forecast", {"request": "request"}, [])]
    returns = [node for node in ast.walk(run_fn) if isinstance(node, ast.Return)]
    assert len(returns) == 1
    constructed: list[str] = []
    for node in ast.walk(run_fn):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name in {"PriceForecastPoint", "EnergyPrice", "DAMPriceForecastModelRequest", "tuple"}:
            constructed.append(name or "")
    assert constructed == []
    source = AGENT_MODULE.read_text(encoding="utf-8")
    assert "try:" not in source
    assert "except " not in source
    assert "PriceForecastPoint(" not in source
    assert "EnergyPrice(" not in source


def test_chunk_120_port_shape_is_unchanged() -> None:
    annotations = _annassign_field_annotations(PORT_MODULE, "DAMPriceForecastModelRequest")
    assert annotations == ALLOWED_REQUEST_FIELDS
    port_def = _class_def(PORT_MODULE, "DAMPriceForecastModelPort")
    operations = [
        item for item in port_def.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert len(operations) == 1
    forecast_fn = operations[0]
    assert isinstance(forecast_fn, ast.AsyncFunctionDef)
    assert forecast_fn.name == "forecast"
    assert tuple(arg.arg for arg in forecast_fn.args.kwonlyargs) == ("request",)
    assert forecast_fn.returns is not None
    assert ast.unparse(forecast_fn.returns) == "tuple[PriceForecastPoint, ...]"


def test_consumer_load_forecast_agent_and_port_remain_unchanged() -> None:
    assert CONSUMER_AGENT_MODULE.exists()
    consumer_agent = _class_def(CONSUMER_AGENT_MODULE, "ConsumerLoadForecastAgent")
    init_fn = next(
        node
        for node in consumer_agent.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert ast.unparse(init_fn.args.args[1].annotation) == "ConsumerLoadForecastModelPort"
    run_fn = next(
        node
        for node in consumer_agent.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "run"
    )
    assert ast.unparse(run_fn.args.args[1].annotation) == "ConsumerLoadForecastModelRequest"
    assert ast.unparse(run_fn.returns) == "tuple[LoadForecastPoint, ...]"
    annotations = _annassign_field_annotations(
        CONSUMER_PORT_MODULE, "ConsumerLoadForecastModelRequest"
    )
    assert annotations == ALLOWED_CONSUMER_REQUEST_FIELDS
    port_def = _class_def(CONSUMER_PORT_MODULE, "ConsumerLoadForecastModelPort")
    operations = [
        item for item in port_def.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert len(operations) == 1
    forecast_fn = operations[0]
    assert isinstance(forecast_fn, ast.AsyncFunctionDef)
    assert forecast_fn.name == "forecast"
    assert ast.unparse(forecast_fn.returns) == "tuple[LoadForecastPoint, ...]"


def test_graph_and_workflow_state_remain_unaware_of_the_agent() -> None:
    graph_names = imported_names(GRAPH_MODULE)
    graph_modules = imported_modules(GRAPH_MODULE)
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "DAMPriceForecastAgent" not in graph_names
    assert "DAMPriceForecastModelPort" not in graph_names
    assert "energy_trading.application.agents.dam_price_forecast" not in graph_modules
    assert "DAMPriceForecastAgent" not in graph_source
    state_fields = tuple(
        item.target.id
        for item in _class_def(STATE_MODULE, "WorkflowState").body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    )
    assert state_fields == ALLOWED_STATE_FIELDS
    state_names = imported_names(STATE_MODULE)
    assert "DAMPriceForecastAgent" not in state_names
    assert "PriceForecastPoint" not in state_names


def test_api_composition_remains_unaware_of_the_agent() -> None:
    forbidden_wiring = (
        "energy_trading.application.agents.dam_price_forecast",
        "energy_trading.application.ports.dam_price_forecast_model",
        "energy_trading.ml",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    app_names = imported_names(API_APP)
    assert "DAMPriceForecastAgent" not in app_names
    assert "DAMPriceForecastModelPort" not in app_names
    api_leaks: list[str] = []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        modules = imported_modules(path)
        if DAM_PRICE_FORECAST_NAMES & names:
            api_leaks.append(path.name)
        if "energy_trading.application.agents.dam_price_forecast" in modules:
            api_leaks.append(path.name)
    assert api_leaks == []
    transport_leaks: list[str] = []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        if DAM_PRICE_FORECAST_NAMES & names:
            transport_leaks.append(path.name)
    assert transport_leaks == []


def test_no_production_model_adapter_or_ml_package() -> None:
    production_impls: list[str] = []
    for path in _production_python_files():
        if path == PORT_MODULE:
            continue
        for name in _module_class_names(path):
            if name in {
                "DAMPriceForecastModelPort",
                "DAMPriceForecastPoint",
            } or name.endswith("DAMPriceForecastModel"):
                production_impls.append(f"{path.relative_to(PRODUCTION_ROOT).as_posix()}:{name}")
    assert production_impls == []
    if ML_ROOT.exists():
        ml_files = sorted(path.name for path in ML_ROOT.rglob("*.py"))
        assert ml_files == []
    port_classes = set(_module_class_names(PORT_MODULE))
    assert port_classes == {
        "DAMPriceForecastModelRequest",
        "DAMPriceForecastModelPort",
    }


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
