"""Previous-day persistence DAM Price MAE evaluator stays a narrow ML artifact."""

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
EVALUATION_MODULE = DAM_ML_ROOT / "previous_day_persistence_evaluation.py"
BACKTEST_MODULE = DAM_ML_ROOT / "previous_day_persistence_backtest.py"
LIVE_ADAPTER_MODULE = DAM_ML_ROOT / "previous_day_persistence.py"
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

RESULT_CLASS = "PreviousDayPersistenceMAEResult"
EVALUATOR = "evaluate_previous_day_persistence_mae"
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
        "PreviousDayPersistenceDAMPriceForecastModel",
        "MarketPriceRecord",
        "WorkflowState",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "energy_trading.application.errors",
        "energy_trading.domain.value_objects.quantities",
        "energy_trading.ml.dam_price.previous_day_persistence_backtest",
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

RESULT_FIELDS = ("case_count", "currency", "mae_amount_per_mwh")

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

    The module docstring deliberately names the metric it does not implement
    and the rejected behaviours, so forbidden-token checks run on code only.
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


def test_evaluator_lives_under_dam_price_ml_package() -> None:
    assert EVALUATION_MODULE.is_relative_to(DAM_ML_ROOT)
    assert EVALUATION_MODULE.name == "previous_day_persistence_evaluation.py"
    assert _module_class_names(EVALUATION_MODULE) == [RESULT_CLASS]
    assert _public_function_names(EVALUATION_MODULE) == [EVALUATOR]
    assert _base_names(_class_def(EVALUATION_MODULE, RESULT_CLASS)) == set()


def test_result_dataclass_is_frozen_slotted_and_exactly_three_fields() -> None:
    class_def = _class_def(EVALUATION_MODULE, RESULT_CLASS)
    keywords = _dataclass_keywords(class_def)
    assert keywords == {"frozen": True, "slots": True}
    assert _annassign_field_names(EVALUATION_MODULE, RESULT_CLASS) == RESULT_FIELDS
    annotations = {
        item.target.id: ast.unparse(item.annotation)
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert annotations == {
        "case_count": "int",
        "currency": "CurrencyCode",
        "mae_amount_per_mwh": "FiniteDecimal",
    }
    leaked = sorted(name for name in annotations if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    defaults = {
        item.target.id: item.value
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert all(value is None for value in defaults.values())


def test_result_exposes_no_other_metric_or_identity_field() -> None:
    names = set(_annassign_field_names(EVALUATION_MODULE, RESULT_CLASS))
    assert names == set(RESULT_FIELDS)
    for token in OTHER_METRIC_TOKENS:
        assert token not in names
    for identity in ("market_id", "model_name", "model_version", "provider", "total_amount"):
        assert identity not in names


def test_mae_is_the_only_metric_calculated() -> None:
    code = _code_source(EVALUATION_MODULE)
    lowered = code.lower()
    for token in OTHER_METRIC_TOKENS:
        assert token not in lowered
    assert "sqrt(" not in code
    assert "**" not in code
    identifiers = {name.lower() for name in _identifier_names(EVALUATION_MODULE)}
    for token in OTHER_METRIC_TOKENS:
        assert token not in identifiers


def test_evaluator_is_synchronous_keyword_only_and_returns_result() -> None:
    tree = ast.parse(EVALUATION_MODULE.read_text(encoding="utf-8"), filename=str(EVALUATION_MODULE))
    evaluator = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == EVALUATOR
    )
    assert not isinstance(evaluator, ast.AsyncFunctionDef)
    assert tuple(arg.arg for arg in evaluator.args.args) == ()
    assert tuple(arg.arg for arg in evaluator.args.kwonlyargs) == ("cases",)
    assert evaluator.args.vararg is None
    assert evaluator.args.kwarg is None
    assert evaluator.args.kw_defaults == [None]
    cases_arg = evaluator.args.kwonlyargs[0]
    assert cases_arg.annotation is not None
    assert ast.unparse(cases_arg.annotation) == "tuple[PreviousDayPersistenceBacktestCase, ...]"
    assert evaluator.returns is not None
    assert ast.unparse(evaluator.returns) == RESULT_CLASS


def test_evaluator_consumes_only_backtest_case_artifacts() -> None:
    names = imported_names(EVALUATION_MODULE)
    assert CASE_CLASS in names
    assert BUILDER not in names
    assert "PreviousDayPersistenceDAMPriceForecastModel" not in names
    assert "DAMPriceForecastModelRequest" not in names
    assert "DAMPriceForecastModelPort" not in names
    assert "DAMPriceForecastAgent" not in names
    assert "MarketPriceRecord" not in names
    assert "EnergyPrice" not in names
    modules = imported_modules(EVALUATION_MODULE)
    assert "energy_trading.ml.dam_price.previous_day_persistence_backtest" in modules
    assert "energy_trading.domain.models.observations" not in modules
    assert "energy_trading.application.ports" not in modules
    source = EVALUATION_MODULE.read_text(encoding="utf-8")
    assert f"{BUILDER}(" not in source
    assert "forecast(" not in source
    assert "MarketPriceRecord" not in source


def test_evaluator_depends_only_on_allowed_inward_contracts() -> None:
    leaked = sorted(
        module
        for module in imported_modules(EVALUATION_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(EVALUATION_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(EVALUATION_MODULE)
    assert "InvalidRequestError" in names
    assert "CurrencyCode" in names
    assert "FiniteDecimal" in names
    assert "dataclass" in names
    leaked_types = sorted(
        name for name in annotation_type_names(EVALUATION_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_evaluator_validates_market_currency_and_strict_chronology() -> None:
    source = EVALUATION_MODULE.read_text(encoding="utf-8")
    assert source.count("InvalidRequestError") >= 7
    for message_name in (
        "_EMPTY_CASES_MESSAGE",
        "_MIXED_MARKET_MESSAGE",
        "_MIXED_CURRENCY_MESSAGE",
        "_CASE_CURRENCY_MISMATCH_MESSAGE",
        "_DUPLICATE_TIMESTAMP_MESSAGE",
        "_OUT_OF_ORDER_MESSAGE",
    ):
        assert message_name in source
    # Message literals may be split across adjacent string concatenation, so
    # compare against the source with interior quoting and newlines removed.
    flattened = source.replace('"\n    "', "")
    for phrase in (
        "requires at least one backtest case",
        "requires cases from exactly one market",
        "requires cases in exactly one currency",
        "requires matching predicted and ",
        "requires unique target timestamps",
        "requires strictly increasing target timestamps",
    ):
        assert phrase in flattened
    for leak in ("AMD", "EUR", "market-a", "market-b"):
        assert leak not in source


def test_evaluator_does_not_sort_or_repair_malformed_cohorts() -> None:
    tree = ast.parse(EVALUATION_MODULE.read_text(encoding="utf-8"), filename=str(EVALUATION_MODULE))
    forbidden_calls: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else None
        if name is None and isinstance(func, ast.Attribute):
            name = func.attr
        if name in {"sorted", "sort", "reverse", "deduplicate", "set"}:
            forbidden_calls.append(name)
    assert forbidden_calls == []
    source = EVALUATION_MODULE.read_text(encoding="utf-8")
    assert "sorted(" not in source


def test_evaluator_uses_canonical_decimal_arithmetic_only() -> None:
    code = _code_source(EVALUATION_MODULE)
    assert "float" not in code
    assert "round(" not in code
    assert "quantize" not in code
    assert "Decimal(" not in code
    assert "abs(" in code
    # MAE accumulates absolute errors explicitly rather than via a builtin
    # aggregate, so the accumulator keeps the canonical Decimal type.
    assert "+=" in code
    identifiers = _identifier_names(EVALUATION_MODULE)
    assert "float" not in identifiers
    assert "round" not in identifiers
    assert "quantize" not in identifiers
    assert "isfinite" not in identifiers
    assert "sum" not in identifiers


def test_absolute_value_is_used_only_for_the_mae_error_difference() -> None:
    tree = ast.parse(EVALUATION_MODULE.read_text(encoding="utf-8"), filename=str(EVALUATION_MODULE))
    abs_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "abs"
    ]
    # One call seeds the accumulator from the first case; the other adds each
    # remaining case inside the MAE loop.
    assert len(abs_calls) == 2
    for abs_call in abs_calls:
        assert len(abs_call.args) == 1
        argument = abs_call.args[0]
        assert isinstance(argument, ast.BinOp)
        assert isinstance(argument.op, ast.Sub)
        assert isinstance(argument.left, ast.Attribute)
        assert isinstance(argument.right, ast.Attribute)
        assert argument.left.attr == "amount_per_mwh"
        assert argument.right.attr == "amount_per_mwh"


def test_evaluator_has_no_fx_volume_or_pnl_arithmetic() -> None:
    source = EVALUATION_MODULE.read_text(encoding="utf-8")
    for forbidden in (
        "fx",
        "exchange_rate",
        "convert",
        "converted",
        "volume",
        "revenue",
        "profit",
        "p_and_l",
        "pnl",
        "weight",
        "total_amount",
    ):
        assert forbidden not in source
    # The evaluator scores canonical prices; it never constructs a new
    # canonical price or money object of its own.
    assert "EnergyPrice(" not in source
    assert "MoneyAmount(" not in source
    identifiers = _identifier_names(EVALUATION_MODULE)
    assert "EnergyPrice" not in identifiers
    assert "MoneyAmount" not in identifiers


def test_no_generic_metric_framework_exists() -> None:
    class_names = [name for path in ML_ROOT.rglob("*.py") for name in _module_class_names(path)]
    leaked_classes = sorted(name for name in class_names if name in GENERIC_METRIC_NAMES)
    assert leaked_classes == []
    identifiers = _identifier_names(EVALUATION_MODULE)
    leaked_ids = sorted(name for name in identifiers if name in GENERIC_METRIC_NAMES)
    assert leaked_ids == []
    source = EVALUATION_MODULE.read_text(encoding="utf-8")
    assert "registry" not in source.lower()
    assert "selector" not in source.lower()
    assert "ServiceLocator" not in source
    assert "AgentFactory" not in source
    assert "Dataclass" not in source


def test_evaluator_has_no_io_clock_or_environment_access() -> None:
    source = EVALUATION_MODULE.read_text(encoding="utf-8")
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
    modules = imported_modules(EVALUATION_MODULE)
    for absent in (
        "uuid",
        "random",
        "secrets",
        "os",
        "io",
        "pathlib",
        "asyncio",
        "datetime",
        "math",
    ):
        assert absent not in modules


def test_backtest_builder_remains_unchanged_and_unaware_of_evaluation() -> None:
    builder_source = BACKTEST_MODULE.read_text(encoding="utf-8")
    # The builder legitimately calls its output "evaluation cases"; what must
    # be absent is any reference to the scoring slice.
    assert RESULT_CLASS not in builder_source
    assert EVALUATOR not in builder_source
    assert "mae" not in builder_source.lower()
    assert "previous_day_persistence_evaluation" not in builder_source
    assert "FiniteDecimal" not in builder_source


def test_live_adapter_remains_unchanged_and_unaware_of_evaluation() -> None:
    live_source = LIVE_ADAPTER_MODULE.read_text(encoding="utf-8")
    assert RESULT_CLASS not in live_source
    assert EVALUATOR not in live_source
    assert "mae" not in live_source.lower()


def test_application_agents_do_not_import_the_evaluator() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert RESULT_CLASS not in names
        assert EVALUATOR not in names
        source = path.read_text(encoding="utf-8")
        assert "previous_day_persistence_evaluation" not in source


def test_orchestration_and_langgraph_do_not_import_the_evaluator() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert RESULT_CLASS not in names
        assert EVALUATOR not in names
        source = path.read_text(encoding="utf-8")
        assert "previous_day_persistence_evaluation" not in source
    graph_modules = imported_modules(GRAPH_MODULE)
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in graph_modules
    )


def test_api_composition_does_not_import_or_construct_the_evaluator() -> None:
    assert collect_import_violations(API_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert RESULT_CLASS not in names
        assert EVALUATOR not in names
        source = path.read_text(encoding="utf-8")
        assert "previous_day_persistence_evaluation" not in source
    app_source = API_APP.read_text(encoding="utf-8")
    assert EVALUATOR not in app_source
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
    assert EVALUATOR not in call_names


def test_workflow_state_shape_is_unchanged() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert RESULT_CLASS not in names
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "previous_day_persistence_evaluation" not in source
    assert "dam_price" not in source
