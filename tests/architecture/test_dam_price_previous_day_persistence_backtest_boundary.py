"""Previous-day persistence DAM Price backtest builder stays a narrow ML artifact."""

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
BACKTEST_MODULE = DAM_ML_ROOT / "previous_day_persistence_backtest.py"
LIVE_ADAPTER_MODULE = DAM_ML_ROOT / "previous_day_persistence.py"
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

CASE_CLASS = "PreviousDayPersistenceBacktestCase"
BUILDER = "build_previous_day_persistence_backtest_cases"

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
        "PreviousDayPersistenceDAMPriceForecastModel",
        "WorkflowState",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "datetime",
        "energy_trading.application.errors",
        "energy_trading.domain.models.observations",
        "energy_trading.domain.value_objects.money",
        "energy_trading.domain.value_objects.quantities",
        "energy_trading.domain.value_objects.time",
    }
)

GENERIC_BACKTEST_NAMES = frozenset(
    {
        "BacktestCase",
        "Backtester",
        "BacktestRunner",
        "Dataset",
        "MetricPort",
        "Metrics",
        "Evaluator",
        "EvaluatorPort",
        "ScorePort",
        "ModelRegistry",
        "ModelSelector",
        "AgentFactory",
        "ServiceLocator",
    }
)

METRIC_NAMES = frozenset(
    {
        "mae",
        "mse",
        "rmse",
        "mape",
        "smape",
        "r2",
        "residual",
        "absolute_error",
        "percentage_error",
        "bias",
        "directional_accuracy",
        "price_spread",
    }
)

CASE_FIELDS = ("market_id", "target_timestamp", "predicted_price", "actual_price")

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


def test_backtest_builder_lives_under_dam_price_ml_package() -> None:
    assert BACKTEST_MODULE.is_relative_to(DAM_ML_ROOT)
    assert BACKTEST_MODULE.name == "previous_day_persistence_backtest.py"
    assert _module_class_names(BACKTEST_MODULE) == [CASE_CLASS]
    assert _public_function_names(BACKTEST_MODULE) == [BUILDER]
    assert _base_names(_class_def(BACKTEST_MODULE, CASE_CLASS)) == set()


def test_case_dataclass_is_frozen_slotted_and_exactly_four_fields() -> None:
    class_def = _class_def(BACKTEST_MODULE, CASE_CLASS)
    keywords = _dataclass_keywords(class_def)
    assert keywords == {"frozen": True, "slots": True}
    assert _annassign_field_names(BACKTEST_MODULE, CASE_CLASS) == CASE_FIELDS
    annotations = {
        item.target.id: ast.unparse(item.annotation)
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert annotations == {
        "market_id": "EntityId",
        "target_timestamp": "UtcDateTime",
        "predicted_price": "EnergyPrice",
        "actual_price": "EnergyPrice",
    }
    leaked = sorted(name for name in annotations if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    for metric_name in METRIC_NAMES:
        assert metric_name not in annotations


def test_case_has_no_defaults_or_metric_fields() -> None:
    class_def = _class_def(BACKTEST_MODULE, CASE_CLASS)
    defaults = {
        item.target.id: item.value
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert all(value is None for value in defaults.values())
    source = BACKTEST_MODULE.read_text(encoding="utf-8")
    identifiers = {name.lower() for name in _identifier_names(BACKTEST_MODULE)}
    for metric_name in METRIC_NAMES:
        assert metric_name not in identifiers
    assert "forecast_run_id" not in source
    assert "generated_at" not in source
    assert "model_name" not in source
    assert "model_version" not in source


def _code_source(path: Path) -> str:
    """Return executable source with every docstring removed.

    The module docstring deliberately names the rules this builder rejects
    (interpolation, resampling, weekly lag) so that reviewers can see the
    boundary. Those negated names must not be mistaken for implemented
    behavior, so forbidden-token checks run against code only.
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


def test_builder_is_synchronous_keyword_only_and_returns_case_tuple() -> None:
    tree = ast.parse(BACKTEST_MODULE.read_text(encoding="utf-8"), filename=str(BACKTEST_MODULE))
    builder = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == BUILDER
    )
    assert tuple(arg.arg for arg in builder.args.args) == ()
    assert tuple(arg.arg for arg in builder.args.kwonlyargs) == ("history",)
    assert builder.args.vararg is None
    assert builder.args.kwarg is None
    assert builder.args.kw_defaults == [None]
    history_arg = builder.args.kwonlyargs[0]
    assert history_arg.annotation is not None
    assert ast.unparse(history_arg.annotation) == "tuple[MarketPriceRecord, ...]"
    assert builder.returns is not None
    assert ast.unparse(builder.returns) == "tuple[PreviousDayPersistenceBacktestCase, ...]"


def test_builder_uses_exact_elapsed_twenty_four_hour_lag_only() -> None:
    source = BACKTEST_MODULE.read_text(encoding="utf-8")
    code = _code_source(BACKTEST_MODULE)
    assert "timedelta(hours=24)" in source
    identifiers = _identifier_names(BACKTEST_MODULE)
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
    tree = ast.parse(BACKTEST_MODULE.read_text(encoding="utf-8"), filename=str(BACKTEST_MODULE))
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
    source = BACKTEST_MODULE.read_text(encoding="utf-8")
    assert source.count("InvalidRequestError") >= 4
    assert "_DUPLICATE_TIMESTAMP_MESSAGE" in source
    assert "_MIXED_MARKET_MESSAGE" in source
    assert "_MIXED_CURRENCY_MESSAGE" in source
    for message in (
        "requires history from exactly one market",
        "requires history in exactly one currency",
        "requires unique historical timestamps",
    ):
        assert message in source
    for leak in ("AMD", "EUR", "market-a", "market-b"):
        assert leak not in source


def test_builder_does_not_couple_to_live_inference() -> None:
    names = imported_names(BACKTEST_MODULE)
    assert "PreviousDayPersistenceDAMPriceForecastModel" not in names
    assert "DAMPriceForecastModelRequest" not in names
    assert "DAMPriceForecastModelPort" not in names
    assert "DAMPriceForecastAgent" not in names
    modules = imported_modules(BACKTEST_MODULE)
    assert "energy_trading.application.ports.dam_price_forecast_model" not in modules
    assert "energy_trading.application.ports" not in modules
    source = BACKTEST_MODULE.read_text(encoding="utf-8")
    assert "PreviousDayPersistenceDAMPriceForecastModel" not in source
    assert "DAMPriceForecastModelRequest" not in source
    assert "forecast(" not in source
    assert "previous_day_persistence import" not in source


def test_builder_depends_only_on_allowed_inward_contracts() -> None:
    leaked = sorted(
        module
        for module in imported_modules(BACKTEST_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(BACKTEST_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(BACKTEST_MODULE)
    assert "MarketPriceRecord" in names
    assert "EnergyPrice" in names
    assert "EntityId" in names
    assert "UtcDateTime" in names
    assert "InvalidRequestError" in names
    assert "dataclass" in names
    leaked_types = sorted(
        name for name in annotation_type_names(BACKTEST_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_builder_has_no_price_arithmetic_or_currency_conversion() -> None:
    source = BACKTEST_MODULE.read_text(encoding="utf-8")
    for forbidden in (
        "float(",
        "Decimal(",
        "round(",
        "abs(",
        "max(",
        "min(",
        "convert",
        "fx_",
        "exchange_rate",
        "amount_per_mwh=",
        "volume_mwh",
    ):
        assert forbidden not in source
    identifiers = _identifier_names(BACKTEST_MODULE)
    assert "Decimal" not in identifiers
    assert "float" not in identifiers
    assert not any(isinstance(name, str) and name in {"sum", "mean"} for name in identifiers)


def test_builder_has_no_io_clock_uuid_or_environment_access() -> None:
    source = BACKTEST_MODULE.read_text(encoding="utf-8")
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
    modules = imported_modules(BACKTEST_MODULE)
    assert "uuid" not in modules
    assert "random" not in modules
    assert "secrets" not in modules
    assert "os" not in modules
    assert "io" not in modules
    assert "pathlib" not in modules
    assert "asyncio" not in modules


def test_no_generic_backtest_or_metric_framework_exists() -> None:
    class_names = [name for path in ML_ROOT.rglob("*.py") for name in _module_class_names(path)]
    leaked_classes = sorted(name for name in class_names if name in GENERIC_BACKTEST_NAMES)
    assert leaked_classes == []
    common_imports = imported_modules(BACKTEST_MODULE)
    assert not any(module.startswith("energy_trading.ml.common") for module in common_imports)
    assert "energy_trading.ml.common" in FORBIDDEN_PREFIXES
    identifiers = _identifier_names(BACKTEST_MODULE)
    leaked_ids = sorted(name for name in identifiers if name in GENERIC_BACKTEST_NAMES)
    assert leaked_ids == []
    source = BACKTEST_MODULE.read_text(encoding="utf-8")
    assert "registry" not in source.lower()
    assert "selector" not in source.lower()
    assert "ServiceLocator" not in source
    assert "AgentFactory" not in source


def test_live_adapter_remains_unchanged_and_unaware_of_the_backtest() -> None:
    live_source = LIVE_ADAPTER_MODULE.read_text(encoding="utf-8")
    assert "backtest" not in live_source.lower()
    assert "PreviousDayPersistenceBacktestCase" not in live_source
    assert BUILDER not in live_source


def test_application_agents_do_not_import_the_backtest_builder() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert CASE_CLASS not in names
        assert BUILDER not in names
        source = path.read_text(encoding="utf-8")
        assert "previous_day_persistence_backtest" not in source


def test_orchestration_and_langgraph_do_not_import_the_backtest_builder() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert CASE_CLASS not in names
        assert BUILDER not in names
        source = path.read_text(encoding="utf-8")
        assert "previous_day_persistence_backtest" not in source
    graph_modules = imported_modules(GRAPH_MODULE)
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in graph_modules
    )


def test_api_composition_does_not_import_or_construct_the_backtest_builder() -> None:
    assert collect_import_violations(API_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert CASE_CLASS not in names
        assert BUILDER not in names
        source = path.read_text(encoding="utf-8")
        assert "previous_day_persistence_backtest" not in source
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
    assert CASE_CLASS not in names
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "previous_day_persistence_backtest" not in source
    assert "dam_price" not in source
