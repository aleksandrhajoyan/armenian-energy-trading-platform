"""DAM Price 24h+168h chronological feature split stays a narrow ML artifact."""

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
SPLIT_MODULE = DAM_ML_ROOT / "lag_24h_168h_chronological_feature_split.py"
FEATURES_MODULE = DAM_ML_ROOT / "lag_24h_168h_features.py"
ONE_FEATURE_MODULE = DAM_ML_ROOT / "lag_24h_features.py"
ONE_FEATURE_SPLIT_MODULE = DAM_ML_ROOT / "chronological_feature_split.py"
FIT_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression.py"
PREDICTION_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression_prediction.py"
TRAINED_EVALUATION_MODULE = DAM_ML_ROOT / "lag_24h_linear_regression_evaluation.py"
COMPARISON_MODULE = DAM_ML_ROOT / "persistence_vs_trained_ols_comparison.py"
LIVE_ADAPTER_MODULE = DAM_ML_ROOT / "previous_day_persistence.py"
BACKTEST_MODULE = DAM_ML_ROOT / "previous_day_persistence_backtest.py"
PERSISTENCE_EVALUATION_MODULE = DAM_ML_ROOT / "previous_day_persistence_evaluation.py"
DAM_ML_INIT = DAM_ML_ROOT / "__init__.py"
DAM_PRICE_PORT_MODULE = PRODUCTION_ROOT / "application" / "ports" / "dam_price_forecast_model.py"
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

SPLIT_CLASS = "DAMPriceLag24h168hChronologicalFeatureSplit"
SPLITTER = "split_dam_price_lag_24h_168h_feature_rows_chronologically"
SPLIT_MODULE_NAME = "lag_24h_168h_chronological_feature_split"
ROW_CLASS = "DAMPriceLag24h168hFeatureRow"
FEATURE_BUILDER = "build_dam_price_lag_24h_168h_feature_rows"
ONE_FEATURE_SPLIT_CLASS = "DAMPriceChronologicalFeatureSplit"
ONE_FEATURE_SPLITTER = "split_dam_price_feature_rows_chronologically"

AMOUNT_FIELDS = (
    "lag_24h_amount_per_mwh",
    "lag_168h_amount_per_mwh",
    "target_amount_per_mwh",
)

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.infrastructure",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.application.ports",
    "energy_trading.domain.models",
    "energy_trading.domain.value_objects.money",
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
    "statistics",
    "itertools",
    "time",
    "datetime",
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
        "EnergyPrice",
        "DAMPriceLag24hFeatureRow",
        "DAMPriceChronologicalFeatureSplit",
        "DAMPriceLag24hLinearRegressionFit",
        "DAMPriceLag24hLinearRegressionPrediction",
        "DAMPriceLag24hLinearRegressionMAEResult",
        "DAMPricePersistenceVsTrainedOLSMAEComparison",
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
        "energy_trading.ml.dam_price.lag_24h_168h_features",
    }
)

ALLOWED_IMPORTED_NAMES = frozenset(
    {
        "dataclass",
        "InvalidRequestError",
        "UtcDateTime",
        ROW_CLASS,
    }
)

GENERIC_DATASET_NAMES = frozenset(
    {
        "Dataset",
        "DatasetSplit",
        "TrainingDataset",
        "ValidationDataset",
        "EvaluationDataset",
        "Splitter",
        "FeatureSplit",
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
    "timeseriessplit",
    "kfold",
    "cross_val",
    "cross_validation",
    "stratif",
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
    "champion",
    "winner",
)

SPLIT_FIELDS = ("training_rows", "evaluation_rows")

UNAWARE_MODULES = (
    FEATURES_MODULE,
    ONE_FEATURE_MODULE,
    ONE_FEATURE_SPLIT_MODULE,
    FIT_MODULE,
    PREDICTION_MODULE,
    TRAINED_EVALUATION_MODULE,
    COMPARISON_MODULE,
    LIVE_ADAPTER_MODULE,
    BACKTEST_MODULE,
    PERSISTENCE_EVALUATION_MODULE,
    DAM_PRICE_PORT_MODULE,
    DAM_ML_INIT,
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


def _splitter_def() -> ast.FunctionDef:
    return next(
        node
        for node in _tree(SPLIT_MODULE).body
        if isinstance(node, ast.FunctionDef) and node.name == SPLITTER
    )


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


def _annassign_field_names(path: Path, class_name: str) -> tuple[str, ...]:
    class_def = _class_def(path, class_name)
    return tuple(
        item.target.id
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    )


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

    The module docstring deliberately names the rules this splitter rejects
    (ratio, shuffled, randomized) and the artifacts it does not depend on, so
    forbidden-token checks run on code only.
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


def _call_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def _attribute_reads(path: Path) -> set[str]:
    return {node.attr for node in ast.walk(_tree(path)) if isinstance(node, ast.Attribute)}


# --- public surface -------------------------------------------------------


def test_splitter_lives_under_dam_price_ml_package() -> None:
    assert SPLIT_MODULE.is_relative_to(DAM_ML_ROOT)
    assert SPLIT_MODULE.name == f"{SPLIT_MODULE_NAME}.py"
    assert _module_class_names(SPLIT_MODULE) == [SPLIT_CLASS]
    assert _public_function_names(SPLIT_MODULE) == [SPLITTER]
    assert _base_names(_class_def(SPLIT_MODULE, SPLIT_CLASS)) == set()


def test_split_result_is_frozen_slotted_and_exactly_two_fields() -> None:
    class_def = _class_def(SPLIT_MODULE, SPLIT_CLASS)
    assert _dataclass_keywords(class_def) == {"frozen": True, "slots": True}
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
    defaults = [
        item.value
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    ]
    assert defaults == [None, None]


def test_split_result_exposes_no_metadata() -> None:
    names = set(_annassign_field_names(SPLIT_MODULE, SPLIT_CLASS))
    assert names == set(SPLIT_FIELDS)
    for forbidden in (
        "cutoff",
        "ratio",
        "percentage",
        "training_count",
        "evaluation_count",
        "case_count",
        "market_id",
        "currency",
        "target_timestamp",
        "metadata",
        "diagnostics",
        "seed",
        "model_name",
        "model_version",
        "feature_names",
    ):
        assert forbidden not in names


def test_splitter_is_synchronous_keyword_only_and_returns_split() -> None:
    splitter = _splitter_def()
    assert not isinstance(splitter, ast.AsyncFunctionDef)
    assert splitter.args.posonlyargs == []
    assert splitter.args.args == []
    assert tuple(arg.arg for arg in splitter.args.kwonlyargs) == ("rows", "cutoff")
    assert splitter.args.vararg is None
    assert splitter.args.kwarg is None
    assert splitter.args.kw_defaults == [None, None]
    rows_arg, cutoff_arg = splitter.args.kwonlyargs
    assert rows_arg.annotation is not None
    assert cutoff_arg.annotation is not None
    assert ast.unparse(rows_arg.annotation) == f"tuple[{ROW_CLASS}, ...]"
    assert ast.unparse(cutoff_arg.annotation) == "UtcDateTime"
    assert splitter.returns is not None
    assert ast.unparse(splitter.returns) == SPLIT_CLASS


def test_split_contract_is_distinct_from_the_one_feature_split() -> None:
    source = SPLIT_MODULE.read_text(encoding="utf-8")
    code = _code_source(SPLIT_MODULE)
    assert ONE_FEATURE_SPLIT_CLASS not in code
    assert ONE_FEATURE_SPLITTER not in source
    assert "energy_trading.ml.dam_price.chronological_feature_split" not in imported_modules(
        SPLIT_MODULE
    )
    one_feature_names = _module_class_names(ONE_FEATURE_SPLIT_MODULE)
    assert one_feature_names == [ONE_FEATURE_SPLIT_CLASS]
    assert _public_function_names(ONE_FEATURE_SPLIT_MODULE) == [ONE_FEATURE_SPLITTER]


# --- partition rule -------------------------------------------------------


def test_partition_rules_are_less_than_and_greater_or_equal() -> None:
    splitter = _splitter_def()
    partition_compares: list[tuple[str, str, str]] = []
    for node in ast.walk(splitter):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1:
            continue
        left = ast.unparse(node.left)
        right = ast.unparse(node.comparators[0])
        if right == "cutoff":
            partition_compares.append((left, type(node.ops[0]).__name__, right))
    assert sorted(partition_compares) == [
        ("row.target_timestamp", "GtE", "cutoff"),
        ("row.target_timestamp", "Lt", "cutoff"),
    ]
    source = SPLIT_MODULE.read_text(encoding="utf-8")
    assert "training_rows = tuple(row for row in rows if row.target_timestamp < cutoff)" in source
    assert (
        "evaluation_rows = tuple(row for row in rows if row.target_timestamp >= cutoff)" in source
    )


def test_cutoff_equality_belongs_only_to_evaluation() -> None:
    tree = _tree(SPLIT_MODULE)
    operators = {
        type(op).__name__
        for node in ast.walk(tree)
        if isinstance(node, ast.Compare)
        for op in node.ops
    }
    # Chronology checks use equality and ordering; the partition rules use Lt
    # and GtE, so equality to the cutoff can only fall into evaluation.
    assert {"Lt", "GtE", "Eq", "Gt"}.issubset(operators)
    assert {"LtE", "NotEq"}.isdisjoint(operators)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        uses_cutoff = "cutoff" in ast.unparse(node)
        if uses_cutoff:
            assert all(type(op).__name__ in {"Lt", "GtE"} for op in node.ops)


# --- chronology -----------------------------------------------------------


def test_input_chronology_is_validated_as_strictly_ascending() -> None:
    chronology = next(
        node
        for node in _tree(SPLIT_MODULE).body
        if isinstance(node, ast.FunctionDef) and node.name == "_require_strict_chronology"
    )
    rendered = {
        (ast.unparse(node.left), type(node.ops[0]).__name__, ast.unparse(node.comparators[0]))
        for node in ast.walk(chronology)
        if isinstance(node, ast.Compare)
    }
    assert rendered == {
        ("previous.target_timestamp", "Eq", "current.target_timestamp"),
        ("previous.target_timestamp", "Gt", "current.target_timestamp"),
    }
    assert "_require_strict_chronology" in _call_names(_splitter_def())


def test_splitter_does_not_sort_reverse_shuffle_sample_or_group() -> None:
    forbidden_calls = _call_names(_tree(SPLIT_MODULE)) & {
        "sorted",
        "sort",
        "reverse",
        "reversed",
        "shuffle",
        "sample",
        "choice",
        "choices",
        "random",
        "groupby",
        "dedup",
        "deduplicate",
        "unique",
        "dict",
        "fromkeys",
    }
    assert forbidden_calls == set()
    code = _code_source(SPLIT_MODULE).lower()
    for token in (
        "sorted",
        ".sort",
        "reverse",
        "shuffle",
        "sample",
        "random",
        "dedup",
        "groupby",
        "group_by",
        "[::-1]",
    ):
        assert token not in code


# --- no derived cutoff ----------------------------------------------------


def test_splitter_does_not_derive_the_cutoff() -> None:
    code = _code_source(SPLIT_MODULE)
    assert "cutoff" in _identifier_names(SPLIT_MODULE)
    for forbidden in (
        "datetime.now",
        "now(",
        "today(",
        "utcnow",
        "time.time",
        "random",
        "seed",
        "median",
        "mean",
        "min(",
        "max(",
        "len(rows)",
        "timedelta",
        "//",
        " / ",
        " * ",
    ):
        assert forbidden not in code
    assigned = {
        node.id
        for node in ast.walk(_tree(SPLIT_MODULE))
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    }
    assert "cutoff" not in assigned


# --- feature values opaque ------------------------------------------------


def test_executable_code_reads_only_partition_relevant_row_attributes() -> None:
    code = _code_source(SPLIT_MODULE)
    for field in AMOUNT_FIELDS:
        assert field not in code
    assert "amount_per_mwh" not in code
    row_attribute_reads = {
        node.attr
        for node in ast.walk(_tree(SPLIT_MODULE))
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id in {"row", "previous", "current"}
    }
    assert row_attribute_reads == {"target_timestamp", "market_id", "currency"}
    assert set(AMOUNT_FIELDS).isdisjoint(_attribute_reads(SPLIT_MODULE))


def test_splitter_does_not_manipulate_feature_values() -> None:
    code = _code_source(SPLIT_MODULE)
    for forbidden in (
        "float(",
        "Decimal(",
        "round(",
        "abs(",
        "clip(",
        "clamp",
        "quantize",
        "normalize",
        "standardize",
        "scale",
        "pow(",
        "**",
        "sqrt",
    ):
        assert forbidden not in code


# --- no row reconstruction -----------------------------------------------


def test_splitter_does_not_construct_rows() -> None:
    code = _code_source(SPLIT_MODULE)
    assert f"{ROW_CLASS}(" not in code
    assert ROW_CLASS not in _call_names(_tree(SPLIT_MODULE))
    for forbidden in ("replace(", "copy(", "deepcopy", "asdict", "astuple"):
        assert forbidden not in code
    # Existing row objects flow straight into the result tuples.
    constructor_calls = [
        node
        for node in ast.walk(_splitter_def())
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == SPLIT_CLASS
    ]
    assert len(constructor_calls) == 1
    keywords = {
        keyword.arg: ast.unparse(keyword.value) for keyword in constructor_calls[0].keywords
    }
    assert keywords == {"training_rows": "training_rows", "evaluation_rows": "evaluation_rows"}


def test_splitter_fails_closed_with_sanitized_messages() -> None:
    source = SPLIT_MODULE.read_text(encoding="utf-8")
    assert source.count("raise InvalidRequestError(") == 7
    for message_name in (
        "_EMPTY_ROWS_MESSAGE",
        "_MIXED_MARKET_MESSAGE",
        "_MIXED_CURRENCY_MESSAGE",
        "_DUPLICATE_TIMESTAMP_MESSAGE",
        "_OUT_OF_ORDER_MESSAGE",
        "_EMPTY_TRAINING_MESSAGE",
        "_EMPTY_EVALUATION_MESSAGE",
    ):
        assert f"raise InvalidRequestError({message_name})" in source
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
    for leak in ("AMD", "EUR", "USD", "market-alpha", "market-beta", "%s", ".format("):
        assert leak not in source
    # Messages are static constants; no f-string can interpolate an identity.
    assert not any(isinstance(node, ast.JoinedStr) for node in ast.walk(_tree(SPLIT_MODULE)))


# --- dependency boundary --------------------------------------------------


def test_splitter_depends_only_on_allowed_inward_contracts() -> None:
    modules = imported_modules(SPLIT_MODULE)
    leaked = sorted(module for module in modules if is_forbidden(module, FORBIDDEN_PREFIXES))
    assert leaked == []
    assert modules == ALLOWED_MODULE_IMPORTS
    assert imported_names(SPLIT_MODULE) == ALLOWED_IMPORTED_NAMES | ALLOWED_MODULE_IMPORTS
    leaked_types = sorted(
        name for name in annotation_type_names(SPLIT_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_splitter_does_not_rebuild_features_or_consume_raw_history() -> None:
    source = SPLIT_MODULE.read_text(encoding="utf-8")
    code = _code_source(SPLIT_MODULE)
    assert FEATURE_BUILDER not in source
    assert "MarketPriceRecord" not in code
    assert "EnergyPrice" not in code
    assert "history" not in code
    modules = imported_modules(SPLIT_MODULE)
    assert "energy_trading.domain.models.observations" not in modules
    assert "energy_trading.domain.value_objects.money" not in modules
    assert "energy_trading.ml.dam_price.lag_24h_168h_features" in modules


def test_splitter_does_not_depend_on_other_dam_price_artifacts() -> None:
    names = imported_names(SPLIT_MODULE)
    for forbidden in (
        "DAMPriceLag24hFeatureRow",
        "build_dam_price_lag_24h_feature_rows",
        ONE_FEATURE_SPLIT_CLASS,
        ONE_FEATURE_SPLITTER,
        "DAMPriceLag24hLinearRegressionFit",
        "fit_dam_price_lag_24h_linear_regression",
        "DAMPriceLag24hLinearRegressionPrediction",
        "predict_dam_price_lag_24h_linear_regression",
        "DAMPriceLag24hLinearRegressionMAEResult",
        "evaluate_dam_price_lag_24h_linear_regression_mae",
        "DAMPricePersistenceVsTrainedOLSMAEComparison",
        "compare_dam_price_persistence_vs_trained_ols_mae",
        "PreviousDayPersistenceDAMPriceForecastModel",
        "PreviousDayPersistenceBacktestCase",
        "build_previous_day_persistence_backtest_cases",
        "PreviousDayPersistenceMAEResult",
        "evaluate_previous_day_persistence_mae",
        "DAMPriceForecastModelRequest",
        "PriceForecastPoint",
    ):
        assert forbidden not in names
    code = _code_source(SPLIT_MODULE)
    for forbidden in ("previous_day_persistence", "linear_regression", "comparison", "consumer"):
        assert forbidden not in code


def test_no_generic_dataset_framework_or_external_split_tooling_exists() -> None:
    class_names = [name for path in ML_ROOT.rglob("*.py") for name in _module_class_names(path)]
    leaked_classes = sorted(name for name in class_names if name in GENERIC_DATASET_NAMES)
    assert leaked_classes == []
    leaked_ids = sorted(
        name for name in _identifier_names(SPLIT_MODULE) if name in GENERIC_DATASET_NAMES
    )
    assert leaked_ids == []
    assert not any(
        module.startswith("energy_trading.ml.common") for module in imported_modules(SPLIT_MODULE)
    )
    source = SPLIT_MODULE.read_text(encoding="utf-8").lower()
    assert "registry" not in source
    assert "selector" not in source
    assert "servicelocator" not in source
    assert "agentfactory" not in source
    assert "protocol" not in source


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
        "asyncio",
        "await",
        "print(",
        "logging",
    ):
        assert forbidden not in source
    for forbidden in FORBIDDEN_TOKENS:
        assert forbidden not in code.lower()


# --- unwired status -------------------------------------------------------


def test_published_dam_price_modules_remain_unaware_of_the_two_lag_split() -> None:
    for path in UNAWARE_MODULES:
        source = path.read_text(encoding="utf-8")
        assert SPLIT_CLASS not in source
        assert SPLITTER not in source
        assert SPLIT_MODULE_NAME not in source
        names = imported_names(path)
        assert SPLIT_CLASS not in names
        assert SPLITTER not in names


def test_application_agents_do_not_import_the_two_lag_split() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert SPLIT_CLASS not in names
        assert SPLITTER not in names
        assert SPLIT_MODULE_NAME not in path.read_text(encoding="utf-8")


def test_orchestration_and_langgraph_do_not_import_the_two_lag_split() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert SPLIT_CLASS not in names
        assert SPLITTER not in names
        assert SPLIT_MODULE_NAME not in path.read_text(encoding="utf-8")
    graph_modules = imported_modules(GRAPH_MODULE)
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in graph_modules
    )


def test_api_composition_does_not_import_or_construct_the_two_lag_split() -> None:
    assert collect_import_violations(API_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert SPLIT_CLASS not in names
        assert SPLITTER not in names
        assert SPLIT_MODULE_NAME not in path.read_text(encoding="utf-8")
    app_source = API_APP.read_text(encoding="utf-8")
    assert SPLITTER not in app_source
    create_app = next(
        node
        for node in _tree(API_APP).body
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )
    call_names = _call_names(create_app)
    assert SPLITTER not in call_names
    assert SPLIT_CLASS not in call_names


def test_workflow_state_shape_is_unchanged() -> None:
    assert _annassign_field_names(STATE_MODULE, "WorkflowState") == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert SPLIT_CLASS not in names
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert SPLIT_MODULE_NAME not in source
    assert "dam_price" not in source
