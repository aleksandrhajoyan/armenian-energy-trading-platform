"""Previous-day persistence DAM Price baseline stays a narrow ML adapter."""

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
ADAPTER_MODULE = DAM_ML_ROOT / "previous_day_persistence.py"
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

CLASS_NAME = "PreviousDayPersistenceDAMPriceForecastModel"

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.infrastructure",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
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
        "WorkflowState",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "ModelPort",
        "ForecastPort",
        "ForecastModelPort",
        "MLPort",
        "AgentFactory",
        "ServiceLocator",
        "ClockPort",
        "UuidFactory",
        "uuid4",
        "datetime.now",
        "ForecastingExecutionPort",
        "DAMPriceForecastAgent",
        "build_workflow_graph",
        "create_app",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "datetime",
        "energy_trading.application.errors",
        "energy_trading.application.ports.dam_price_forecast_model",
        "energy_trading.domain.models.forecasting",
        "energy_trading.domain.models.observations",
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


def _identifier_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
    return names


def _annassign_field_names(path: Path, class_name: str) -> tuple[str, ...]:
    class_def = _class_def(path, class_name)
    names: list[str] = []
    for item in class_def.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            names.append(item.target.id)
    return tuple(names)


_DOCSTRING_HOLDERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _code_source(path: Path) -> str:
    """Return executable source with every docstring removed.

    The module docstring deliberately names the rules this baseline rejects
    (nearest observation, interpolation, partial success) so that reviewers
    can see the boundary. Those negated names must not be mistaken for
    implemented behavior, so forbidden-token checks run against code only.
    """

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, _DOCSTRING_HOLDERS):
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


def test_baseline_lives_under_dam_price_ml_package() -> None:
    assert ADAPTER_MODULE.is_relative_to(DAM_ML_ROOT)
    assert DAM_ML_ROOT.is_relative_to(ML_ROOT)
    assert ADAPTER_MODULE.name == "previous_day_persistence.py"
    assert _module_class_names(ADAPTER_MODULE) == [CLASS_NAME]
    class_def = _class_def(ADAPTER_MODULE, CLASS_NAME)
    assert _base_names(class_def) == set()
    generic_names = [
        name
        for path in ML_ROOT.rglob("*.py")
        for name in _module_class_names(path)
        if name in GENERIC_ML_CLASS_NAMES
    ]
    assert generic_names == []


def test_baseline_depends_only_on_allowed_inward_contracts() -> None:
    leaked = sorted(
        module
        for module in imported_modules(ADAPTER_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(ADAPTER_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(ADAPTER_MODULE)
    assert "DAMPriceForecastModelRequest" in names
    assert "InvalidRequestError" in names
    assert "PriceForecastPoint" in names
    assert "MarketPriceRecord" in names
    assert "DAMPriceForecastModelPort" not in names
    assert "DAMPriceForecastAgent" not in names
    leaked_types = sorted(
        name for name in annotation_type_names(ADAPTER_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_baseline_exposes_keyword_only_async_forecast() -> None:
    class_def = _class_def(ADAPTER_MODULE, CLASS_NAME)
    operations = [
        item
        for item in class_def.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not item.name.startswith("_")
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


def test_baseline_uses_exact_elapsed_twenty_four_hour_lag() -> None:
    source = ADAPTER_MODULE.read_text(encoding="utf-8")
    code = _code_source(ADAPTER_MODULE)
    assert "timedelta(hours=24)" in source
    identifiers = _identifier_names(ADAPTER_MODULE)
    assert "timedelta" in identifiers
    assert "_LAG" in identifiers
    for forbidden_rule in (
        "hours=168",
        "days=7",
        "weekday",
        "nearest",
        "interpolate",
        "interpolation",
        "resample",
        "ffill",
        "bfill",
        "forward_fill",
        "backward_fill",
        "rolling",
        "cumulative",
        "session",
        "timezone(",
        "ZoneInfo",
    ):
        assert forbidden_rule not in code


def test_baseline_does_not_generate_identity_or_use_clocks() -> None:
    source = ADAPTER_MODULE.read_text(encoding="utf-8")
    assert "datetime.now" not in source
    assert "datetime.utcnow" not in source
    assert "uuid4" not in source
    assert "uuid." not in source
    assert "Clock" not in source
    modules = imported_modules(ADAPTER_MODULE)
    assert "uuid" not in modules
    assert "random" not in modules
    assert "secrets" not in modules
    identifiers = _identifier_names(ADAPTER_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []


def test_baseline_passes_identity_fields_through_without_reconstruction() -> None:
    class_def = _class_def(ADAPTER_MODULE, CLASS_NAME)
    forecast_fn = next(
        item
        for item in class_def.body
        if isinstance(item, ast.AsyncFunctionDef) and item.name == "forecast"
    )
    assert forecast_fn.body is not None
    source = ADAPTER_MODULE.read_text(encoding="utf-8")
    for required in (
        "forecast_run_id=request.forecast_run_id",
        "generated_at=request.generated_at",
        "market_id=request.market_id",
        "price=matching_record.price",
        "target_timestamp=target",
    ):
        assert required in source


def test_baseline_has_no_currency_conversion_or_price_arithmetic() -> None:
    source = ADAPTER_MODULE.read_text(encoding="utf-8")
    for forbidden in (
        "float(",
        "Decimal(",
        "round(",
        "abs(",
        "max(",
        "min(",
        "converted",
        "convert",
        "fx_",
        "exchange_rate",
        "amount_per_mwh=",
    ):
        assert forbidden not in source
    identifiers = _identifier_names(ADAPTER_MODULE)
    assert "Decimal" not in identifiers
    assert "float" not in identifiers


def test_baseline_fails_closed_on_missing_or_duplicate_lag() -> None:
    source = ADAPTER_MODULE.read_text(encoding="utf-8")
    code = _code_source(ADAPTER_MODULE)
    assert "InvalidRequestError" in source
    assert "len(matches) == 0" in source
    assert "len(matches) != 1" in source
    for forbidden in ("continue", "partial", "fallback", "retry", "default_price"):
        assert forbidden not in code.lower()


def test_baseline_does_not_introduce_generic_ml_abstractions() -> None:
    class_names = [name for path in ML_ROOT.rglob("*.py") for name in _module_class_names(path)]
    leaked_classes = sorted(name for name in class_names if name in GENERIC_ML_CLASS_NAMES)
    assert leaked_classes == []
    identifiers = _identifier_names(ADAPTER_MODULE)
    leaked_ids = sorted(name for name in identifiers if name in GENERIC_ML_CLASS_NAMES)
    assert leaked_ids == []
    source = ADAPTER_MODULE.read_text(encoding="utf-8")
    assert "AgentFactory" not in source
    assert "ServiceLocator" not in source
    assert "registry" not in source.lower()
    assert "selector" not in source.lower()
    assert "lightgbm" not in source.lower()
    assert "xgboost" not in source.lower()
    assert "sklearn" not in source.lower()
    assert "numpy" not in source.lower()
    assert "pandas" not in source.lower()


def test_baseline_does_not_perform_io_or_use_environment() -> None:
    source = ADAPTER_MODULE.read_text(encoding="utf-8")
    for forbidden in (
        "open(",
        "Path(",
        "os.environ",
        "getenv",
        "requests.",
        "httpx.",
        "socket",
        "asyncio.sleep",
        "print(",
        "logging",
    ):
        assert forbidden not in source
    modules = imported_modules(ADAPTER_MODULE)
    assert "os" not in modules
    assert "io" not in modules
    assert "pathlib" not in modules
    assert "logging" not in modules


def test_application_agents_do_not_import_the_baseline() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert CLASS_NAME not in names
        source = path.read_text(encoding="utf-8")
        assert CLASS_NAME not in source
        assert "dam_price.previous_day_persistence" not in source
        assert "previous_day_persistence" not in source


def test_orchestration_and_langgraph_do_not_import_the_baseline() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert CLASS_NAME not in names
        source = path.read_text(encoding="utf-8")
        assert CLASS_NAME not in source
        assert "dam_price.previous_day_persistence" not in source
        assert "previous_day_persistence" not in source
    graph_modules = imported_modules(GRAPH_MODULE)
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in graph_modules
    )


def test_api_composition_does_not_import_or_construct_the_baseline() -> None:
    assert collect_import_violations(API_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert CLASS_NAME not in names
        source = path.read_text(encoding="utf-8")
        assert CLASS_NAME not in source
        assert "dam_price.previous_day_persistence" not in source
        assert "previous_day_persistence" not in source
    app_source = API_APP.read_text(encoding="utf-8")
    assert CLASS_NAME not in app_source
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
    assert CLASS_NAME not in call_names


def test_ml_package_initializer_is_minimal() -> None:
    initializer = DAM_ML_ROOT / "__init__.py"
    assert initializer.exists()
    tree = ast.parse(initializer.read_text(encoding="utf-8"), filename=str(initializer))
    assert [node for node in tree.body if isinstance(node, ast.ClassDef)] == []
    callables = (ast.FunctionDef, ast.AsyncFunctionDef)
    assert [node for node in tree.body if isinstance(node, callables)] == []
    assert [node for node in tree.body if isinstance(node, ast.Assign)] == []
    assert [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))] == []


def test_workflow_state_shape_is_unchanged() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert CLASS_NAME not in names
    assert "PriceForecastPoint" not in names
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "previous_day_persistence" not in source
    assert "dam_price" not in source
