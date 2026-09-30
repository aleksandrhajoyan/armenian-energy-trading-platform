"""DAM Price chronological feature split stays a narrow ML artifact."""

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
SPLIT_MODULE = DAM_ML_ROOT / "chronological_feature_split.py"
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

SPLIT_CLASS = "DAMPriceChronologicalFeatureSplit"
SPLITTER = "split_dam_price_feature_rows_chronologically"
ROW_CLASS = "DAMPriceLag24hFeatureRow"
FEATURE_BUILDER = "build_dam_price_lag_24h_feature_rows"

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
        "MarketPriceRecord",
        "PreviousDayPersistenceDAMPriceForecastModel",
        "PreviousDayPersistenceBacktestCase",
        "PreviousDayPersistenceMAEResult",
        "WorkflowState",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "energy_trading.application.errors",
        "energy_trading.domain.value_objects.time",
        "energy_trading.ml.dam_price.lag_24h_features",
    }
)

GENERIC_DATASET_NAMES = frozenset(
    {
        "Dataset",
        "DatasetSplit",
        "TrainingDataset",
        "EvaluationDataset",
        "Splitter",
        "TrainTestSplit",
        "HoldoutSplit",
        "DataModule",
        "ModelRegistry",
        "ModelSelector",
        "AgentFactory",
        "ServiceLocator",
        "FeaturePipeline",
        "FeatureRegistry",
    }
)

FORBIDDEN_TOKENS = (
    "shuffle",
    "sample",
    "train_test_split",
    "TimeSeriesSplit",
    "cross_val",
    "cross_validation",
    "ratio",
    "percentage",
    "percentile",
    "median",
    "quantile",
    "seed",
    "datetime.now",
    "utcnow",
    "uuid",
    "fit(",
    "train(",
    "predict",
    "score(",
    "mae",
    "mse",
    "rmse",
    "normalize",
    "standardize",
    "scale(",
    "clip(",
    "quantize",
    "convert",
    "exchange_rate",
    "volume",
)

SPLIT_FIELDS = ("training_rows", "evaluation_rows")

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

    The module docstring deliberately names the rules this splitter rejects
    (ratio, shuffled, randomized) and the algorithms it does not use, so
    forbidden-token checks run on code only.
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


def test_splitter_lives_under_dam_price_ml_package() -> None:
    assert SPLIT_MODULE.is_relative_to(DAM_ML_ROOT)
    assert SPLIT_MODULE.name == "chronological_feature_split.py"
    assert _module_class_names(SPLIT_MODULE) == [SPLIT_CLASS]
    assert _public_function_names(SPLIT_MODULE) == [SPLITTER]
    assert _base_names(_class_def(SPLIT_MODULE, SPLIT_CLASS)) == set()


def test_split_result_is_frozen_slotted_and_exactly_two_fields() -> None:
    class_def = _class_def(SPLIT_MODULE, SPLIT_CLASS)
    keywords = _dataclass_keywords(class_def)
    assert keywords == {"frozen": True, "slots": True}
    assert _annassign_field_names(SPLIT_MODULE, SPLIT_CLASS) == SPLIT_FIELDS
    annotations = {
        item.target.id: ast.unparse(item.annotation)
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert annotations == {
        "training_rows": f"tuple[{ROW_CLASS}, ...]",
        "evaluation_rows": f"tuple[{ROW_CLASS}, ...]",
    }
    defaults = {
        item.target.id: item.value
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert all(value is None for value in defaults.values())


def test_split_result_exposes_no_metadata() -> None:
    names = set(_annassign_field_names(SPLIT_MODULE, SPLIT_CLASS))
    assert names == set(SPLIT_FIELDS)
    for forbidden in (
        "cutoff",
        "ratio",
        "percentage",
        "training_count",
        "evaluation_count",
        "market_id",
        "currency",
        "metadata",
        "model_name",
        "model_version",
    ):
        assert forbidden not in names


def test_splitter_is_synchronous_keyword_only_and_returns_split() -> None:
    tree = ast.parse(SPLIT_MODULE.read_text(encoding="utf-8"), filename=str(SPLIT_MODULE))
    splitter = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == SPLITTER
    )
    assert not isinstance(splitter, ast.AsyncFunctionDef)
    assert tuple(arg.arg for arg in splitter.args.args) == ()
    assert tuple(arg.arg for arg in splitter.args.kwonlyargs) == ("rows", "cutoff")
    assert splitter.args.vararg is None
    assert splitter.args.kwarg is None
    assert splitter.args.kw_defaults == [None, None]
    rows_arg = splitter.args.kwonlyargs[0]
    cutoff_arg = splitter.args.kwonlyargs[1]
    assert rows_arg.annotation is not None
    assert cutoff_arg.annotation is not None
    assert ast.unparse(rows_arg.annotation) == f"tuple[{ROW_CLASS}, ...]"
    assert ast.unparse(cutoff_arg.annotation) == "UtcDateTime"
    assert splitter.returns is not None
    assert ast.unparse(splitter.returns) == SPLIT_CLASS


def test_split_rules_are_less_than_and_greater_or_equal() -> None:
    source = SPLIT_MODULE.read_text(encoding="utf-8")
    assert "row.target_timestamp < cutoff" in source
    assert "row.target_timestamp >= cutoff" in source
    tree = ast.parse(source, filename=str(SPLIT_MODULE))
    comparisons = [node for node in ast.walk(tree) if isinstance(node, ast.Compare)]
    operators = {type(op).__name__ for node in comparisons for op in node.ops}
    # Chronology checks use equality and ordering; the partition rules use Lt
    # and GtE.
    assert {"Lt", "GtE", "Eq", "Gt"}.issubset(operators)
    assert {"LtE", "NotEq"}.isdisjoint(operators)
    # Timestamp comparisons are the only value comparisons; the remaining
    # ones are set-cardinality guards via len(...).
    timestamp_comparisons = [
        node
        for node in comparisons
        if isinstance(node.left, ast.Attribute) and node.left.attr == "target_timestamp"
    ]
    assert len(timestamp_comparisons) == 4
    for node in timestamp_comparisons:
        for comparator in node.comparators:
            assert isinstance(comparator, (ast.Attribute, ast.Name))
    # No comparison anywhere reads a price amount.
    for node in comparisons:
        assert "amount_per_mwh" not in ast.unparse(node)


def test_splitter_does_not_derive_the_cutoff() -> None:
    code = _code_source(SPLIT_MODULE)
    identifiers = _identifier_names(SPLIT_MODULE)
    assert "cutoff" in identifiers
    for forbidden in (
        "datetime.now",
        "now(",
        "today(",
        "utcnow",
        "random",
        "seed",
        "median",
        "mean",
        "min(",
        "max(",
        "len(rows)",
        "timedelta",
    ):
        assert forbidden not in code
    # The cutoff is only compared against, never reassigned or recomputed.
    tree = ast.parse(SPLIT_MODULE.read_text(encoding="utf-8"), filename=str(SPLIT_MODULE))
    assigned = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    }
    assert "cutoff" not in assigned


def test_splitter_does_not_sort_reverse_shuffle_or_sample() -> None:
    tree = ast.parse(SPLIT_MODULE.read_text(encoding="utf-8"), filename=str(SPLIT_MODULE))
    forbidden_calls: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else None
        if name is None and isinstance(func, ast.Attribute):
            name = func.attr
        if name in {"sorted", "sort", "reverse", "shuffle", "sample", "choice", "random"}:
            forbidden_calls.append(name)
    assert forbidden_calls == []
    code = _code_source(SPLIT_MODULE)
    for token in ("sorted", "shuffle", "sample", "random", "ratio", "percentage"):
        assert token not in code


def test_splitter_fails_closed_with_sanitized_messages() -> None:
    source = SPLIT_MODULE.read_text(encoding="utf-8")
    assert source.count("InvalidRequestError") >= 7
    for message_name in (
        "_EMPTY_ROWS_MESSAGE",
        "_MIXED_MARKET_MESSAGE",
        "_MIXED_CURRENCY_MESSAGE",
        "_DUPLICATE_TIMESTAMP_MESSAGE",
        "_OUT_OF_ORDER_MESSAGE",
        "_EMPTY_TRAINING_MESSAGE",
        "_EMPTY_EVALUATION_MESSAGE",
    ):
        assert message_name in source
    for phrase in (
        "requires at least one feature row",
        "requires rows from exactly one market",
        "requires rows in exactly one currency",
        "requires unique target timestamps",
        "requires strictly increasing target timestamps",
        "requires a non-empty training partition",
        "requires a non-empty evaluation partition",
    ):
        assert phrase in source
    for leak in ("AMD", "EUR", "market-alpha", "market-beta"):
        assert leak not in source


def test_splitter_depends_only_on_allowed_inward_contracts() -> None:
    leaked = sorted(
        module
        for module in imported_modules(SPLIT_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(SPLIT_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(SPLIT_MODULE)
    assert ROW_CLASS in names
    assert "InvalidRequestError" in names
    assert "UtcDateTime" in names
    assert "dataclass" in names
    assert "MarketPriceRecord" not in names
    assert FEATURE_BUILDER not in names
    leaked_types = sorted(
        name for name in annotation_type_names(SPLIT_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_splitter_does_not_rebuild_features_or_consume_raw_history() -> None:
    source = SPLIT_MODULE.read_text(encoding="utf-8")
    code = _code_source(SPLIT_MODULE)
    assert FEATURE_BUILDER not in source
    # The module docstring states that raw history is not consumed; the check
    # below proves no history type is imported or referenced in code.
    assert "MarketPriceRecord" not in code
    assert "energy_trading.domain.models.observations" not in source
    modules = imported_modules(SPLIT_MODULE)
    assert "energy_trading.domain.models.observations" not in modules
    assert "energy_trading.ml.dam_price.lag_24h_features" in modules
    # No feature row is constructed; the splitter only partitions existing rows.
    assert f"{ROW_CLASS}(" not in code


def test_splitter_does_not_depend_on_persistence_artifacts() -> None:
    names = imported_names(SPLIT_MODULE)
    for forbidden in (
        "PreviousDayPersistenceDAMPriceForecastModel",
        "PreviousDayPersistenceBacktestCase",
        "PreviousDayPersistenceMAEResult",
        "DAMPriceForecastModelRequest",
        "PriceForecastPoint",
    ):
        assert forbidden not in names
    modules = imported_modules(SPLIT_MODULE)
    for forbidden in (
        "energy_trading.ml.dam_price.previous_day_persistence",
        "energy_trading.ml.dam_price.previous_day_persistence_backtest",
        "energy_trading.ml.dam_price.previous_day_persistence_evaluation",
        "energy_trading.domain.models.forecasting",
    ):
        assert forbidden not in modules
    source = SPLIT_MODULE.read_text(encoding="utf-8")
    for forbidden in (
        "PreviousDayPersistenceDAMPriceForecastModel",
        "PreviousDayPersistenceBacktestCase",
        "PreviousDayPersistenceMAEResult",
        "build_previous_day_persistence_backtest_cases",
        "evaluate_previous_day_persistence_mae",
    ):
        assert forbidden not in source


def test_splitter_does_not_manipulate_feature_values() -> None:
    code = _code_source(SPLIT_MODULE)
    for forbidden in (
        "amount_per_mwh",
        "float(",
        "Decimal(",
        "round(",
        "abs(",
        "clip(",
        "quantize",
        "normalize",
        "standardize",
        "pow(",
        "**",
        "sqrt",
    ):
        assert forbidden not in code
    source = SPLIT_MODULE.read_text(encoding="utf-8")
    # The only row attributes inspected are the three partition-relevant ones.
    assert "row.target_timestamp" in source
    assert "row.market_id" in source
    assert "row.currency" in source
    assert "lag_24h_amount_per_mwh" not in source
    assert "target_amount_per_mwh" not in source


def test_no_generic_dataset_framework_or_external_split_tooling_exists() -> None:
    class_names = [name for path in ML_ROOT.rglob("*.py") for name in _module_class_names(path)]
    leaked_classes = sorted(name for name in class_names if name in GENERIC_DATASET_NAMES)
    assert leaked_classes == []
    identifiers = _identifier_names(SPLIT_MODULE)
    leaked_ids = sorted(name for name in identifiers if name in GENERIC_DATASET_NAMES)
    assert leaked_ids == []
    common_imports = imported_modules(SPLIT_MODULE)
    assert not any(module.startswith("energy_trading.ml.common") for module in common_imports)
    assert "energy_trading.ml.common" in FORBIDDEN_PREFIXES
    source = SPLIT_MODULE.read_text(encoding="utf-8")
    assert "registry" not in source.lower()
    assert "selector" not in source.lower()
    assert "ServiceLocator" not in source
    assert "AgentFactory" not in source


def test_splitter_has_no_io_clock_uuid_or_environment_access() -> None:
    source = SPLIT_MODULE.read_text(encoding="utf-8")
    code = _code_source(SPLIT_MODULE)
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
    for forbidden in FORBIDDEN_TOKENS:
        assert forbidden not in code.lower()
    modules = imported_modules(SPLIT_MODULE)
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


def test_feature_builder_and_persistence_modules_remain_unaware_of_the_split() -> None:
    for path in (
        FEATURES_MODULE,
        LIVE_ADAPTER_MODULE,
        BACKTEST_MODULE,
        EVALUATION_MODULE,
    ):
        source = path.read_text(encoding="utf-8")
        assert SPLIT_CLASS not in source
        assert SPLITTER not in source
        assert "chronological_feature_split" not in source


def test_application_agents_do_not_import_the_splitter() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert SPLIT_CLASS not in names
        assert SPLITTER not in names
        source = path.read_text(encoding="utf-8")
        assert "chronological_feature_split" not in source


def test_orchestration_and_langgraph_do_not_import_the_splitter() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert SPLIT_CLASS not in names
        assert SPLITTER not in names
        source = path.read_text(encoding="utf-8")
        assert "chronological_feature_split" not in source
    graph_modules = imported_modules(GRAPH_MODULE)
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in graph_modules
    )


def test_api_composition_does_not_import_or_construct_the_splitter() -> None:
    assert collect_import_violations(API_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert SPLIT_CLASS not in names
        assert SPLITTER not in names
        source = path.read_text(encoding="utf-8")
        assert "chronological_feature_split" not in source
    app_source = API_APP.read_text(encoding="utf-8")
    assert SPLITTER not in app_source
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
    assert SPLITTER not in call_names


def test_workflow_state_shape_is_unchanged() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert SPLIT_CLASS not in names
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "chronological_feature_split" not in source
    assert "dam_price" not in source
