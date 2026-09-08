"""Chunk 72 Regulatory runtime settings stay shared, SDK-free, and unwired."""

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
DOMAIN_ROOT = PRODUCTION_ROOT / "domain"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
ML_ROOT = PRODUCTION_ROOT / "ml"
GRAPH_MODULE = APPLICATION_ROOT / "orchestration" / "graph.py"
CONFIG_ROOT = PRODUCTION_ROOT / "shared" / "config"
SETTINGS_MODULE = CONFIG_ROOT / "regulatory_intelligence.py"
PROVIDER_RUNTIME_MODULE = API_ROOT / "composition" / "regulatory_intelligence_runtime.py"
NEUTRAL_BUILDER_MODULE = API_ROOT / "composition" / "regulatory_intelligence.py"

EXPECTED_FIELDS = (
    "query_embedding_model",
    "constraint_inference_model",
    "qdrant_collection_name",
    "qdrant_vector_size",
)
EXPECTED_ENV_NAMES = (
    "ENERGY_REGULATORY_QUERY_EMBEDDING_MODEL",
    "ENERGY_REGULATORY_CONSTRAINT_INFERENCE_MODEL",
    "ENERGY_REGULATORY_QDRANT_COLLECTION_NAME",
    "ENERGY_REGULATORY_QDRANT_VECTOR_SIZE",
)

FORBIDDEN_SETTINGS_IMPORTS = (
    "openai",
    "qdrant_client",
    "qdrant",
    "energy_trading.infrastructure",
    "energy_trading.application",
    "energy_trading.api",
    "energy_trading.ml",
    "energy_trading.domain",
    "fastapi",
    "starlette",
    "redis",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "langchain",
    "langchain_core",
    "langgraph",
    "numpy",
    "pandas",
    "polars",
    "lightgbm",
    "xgboost",
    "prophet",
    "tenacity",
    "backoff",
)

FORBIDDEN_TYPE_NAMES = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "dict",
        "Dict",
        "Mapping",
        "SecretStr",
        "AsyncOpenAI",
        "OpenAI",
        "AsyncQdrantClient",
        "QdrantClient",
        "QdrantDocumentVectorConfig",
        "OpenAIDocumentQueryEmbeddingAdapter",
        "OpenAIRegulatoryConstraintInferenceAdapter",
        "QdrantDocumentVectorSearch",
        "RegulatoryIntelligenceQueryExecutionService",
        "LLMPort",
        "EmbeddingPort",
        "ProviderRegistry",
        "Container",
        "RuntimeSettings",
        "ModelCatalog",
    }
)

GENERIC_FRAMEWORK_NAMES = frozenset(
    {
        "LLMPort",
        "EmbeddingPort",
        "ProviderRegistry",
        "ServiceRegistry",
        "AgentFactory",
        "Container",
        "ModelCatalog",
        "RuntimeSettings",
        "SettingsRegistry",
        "LiteLLM",
        "RAGPort",
    }
)

FORBIDDEN_RUNTIME_CALLS = frozenset(
    {
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "create_openai_client",
        "create_qdrant_client",
        "QdrantDocumentVectorConfig",
        "OpenAIDocumentQueryEmbeddingAdapter",
        "OpenAIRegulatoryConstraintInferenceAdapter",
        "QdrantDocumentVectorSearch",
        "RegulatoryIntelligenceQueryExecutionService",
        "build_regulatory_intelligence_query_execution",
        "build_regulatory_intelligence_provider_runtime",
    }
)


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _create_app_call_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    create_app = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )
    names: set[str] = set()
    for node in ast.walk(create_app):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name is not None:
            names.add(name)
    return names


def _settings_class() -> ast.ClassDef:
    tree = ast.parse(SETTINGS_MODULE.read_text(encoding="utf-8"), filename=str(SETTINGS_MODULE))
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "RegulatoryIntelligenceRuntimeSettings"
    )


def _ann_assign_fields(class_node: ast.ClassDef) -> dict[str, ast.AnnAssign]:
    fields: dict[str, ast.AnnAssign] = {}
    for item in class_node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            fields[item.target.id] = item
    return fields


def test_settings_module_lives_under_shared_config() -> None:
    relative = SETTINGS_MODULE.relative_to(PRODUCTION_ROOT).as_posix()
    assert relative == "shared/config/regulatory_intelligence.py"


def test_exact_class_and_four_fields() -> None:
    settings = _settings_class()
    assert settings.name == "RegulatoryIntelligenceRuntimeSettings"
    fields = _ann_assign_fields(settings)
    assert tuple(fields) == EXPECTED_FIELDS
    assert [ast.unparse(base) for base in settings.bases] == ["BaseSettings"]


def test_dedicated_environment_prefix_and_exact_variable_names() -> None:
    source = SETTINGS_MODULE.read_text(encoding="utf-8")
    assert 'env_prefix="ENERGY_REGULATORY_"' in source
    for name in EXPECTED_ENV_NAMES:
        assert name in source
    assert "ENERGY_OPENAI_" not in source
    assert "ENERGY_MODEL_" not in source
    assert "ENERGY_QDRANT_" not in source


def test_no_default_model_collection_or_vector_size() -> None:
    settings = _settings_class()
    fields = _ann_assign_fields(settings)
    for name in EXPECTED_FIELDS:
        assign = fields[name]
        assert assign.value is not None
        assert isinstance(assign.value, ast.Call)
        assert _call_name(assign.value) == "Field"
        keywords = {keyword.arg for keyword in assign.value.keywords if keyword.arg is not None}
        assert "default" not in keywords
        assert "default_factory" not in keywords
    source = SETTINGS_MODULE.read_text(encoding="utf-8")
    assert "text-embedding" not in source
    assert "gpt-" not in source
    assert "regulatory_docs" not in source


def test_vector_size_is_positive_integer() -> None:
    settings = _settings_class()
    vector_size = _ann_assign_fields(settings)["qdrant_vector_size"]
    assert ast.unparse(vector_size.annotation) == "int"
    assert isinstance(vector_size.value, ast.Call)
    keywords = {
        keyword.arg: ast.unparse(keyword.value)
        for keyword in vector_size.value.keywords
        if keyword.arg is not None
    }
    assert keywords["gt"] == "0"


def test_no_secret_or_api_key_surface() -> None:
    names = imported_names(SETTINGS_MODULE)
    assert "SecretStr" not in names
    fields = _ann_assign_fields(_settings_class())
    assert "api_key" not in fields
    source = SETTINGS_MODULE.read_text(encoding="utf-8")
    assert "SecretStr" not in source
    assert "api_key" not in source


def test_settings_module_is_sdk_and_layer_free() -> None:
    leaked = sorted(
        module
        for module in imported_modules(SETTINGS_MODULE)
        if is_forbidden(module, FORBIDDEN_SETTINGS_IMPORTS)
    )
    assert leaked == []
    names = imported_names(SETTINGS_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    annotations = annotation_type_names(SETTINGS_MODULE)
    leaked_annotations = sorted(name for name in annotations if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_annotations == []


def test_inner_layers_do_not_import_regulatory_runtime_settings() -> None:
    forbidden = ("energy_trading.shared.config.regulatory_intelligence",)
    assert collect_import_violations(DOMAIN_ROOT, forbidden) == []
    assert collect_import_violations(APPLICATION_ROOT, forbidden) == []
    assert collect_import_violations(API_ROOT, forbidden) == []
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, forbidden) == []


def test_no_runtime_objects_or_generic_frameworks() -> None:
    source = SETTINGS_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SETTINGS_MODULE))
    call_names = {_call_name(node) for node in ast.walk(tree) if isinstance(node, ast.Call)}
    leaked_calls = sorted(name for name in call_names if name in FORBIDDEN_RUNTIME_CALLS)
    assert leaked_calls == []
    identifiers = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    leaked_frameworks = sorted(name for name in identifiers if name in GENERIC_FRAMEWORK_NAMES)
    assert leaked_frameworks == []
    class_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
    assert class_names == {"RegulatoryIntelligenceRuntimeSettings"}
    assert "await " not in source
    assert "QdrantDocumentVectorConfig" not in source


def test_loader_signature_is_keyword_only_and_uncached() -> None:
    tree = ast.parse(SETTINGS_MODULE.read_text(encoding="utf-8"), filename=str(SETTINGS_MODULE))
    loader = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "load_regulatory_intelligence_runtime_settings"
    )
    assert [arg.arg for arg in loader.args.args] == []
    assert [arg.arg for arg in loader.args.kwonlyargs] == ["env_file"]
    assert ast.unparse(loader.returns) == "RegulatoryIntelligenceRuntimeSettings"
    source = SETTINGS_MODULE.read_text(encoding="utf-8")
    assert "lru_cache" not in source


def test_create_app_remains_unwired() -> None:
    names = imported_names(API_APP)
    assert "RegulatoryIntelligenceRuntimeSettings" not in names
    assert "load_regulatory_intelligence_runtime_settings" not in names
    call_names = _create_app_call_names(API_APP)
    assert "load_regulatory_intelligence_runtime_settings" not in call_names
    assert "RegulatoryIntelligenceRuntimeSettings" not in call_names
    source = API_APP.read_text(encoding="utf-8")
    assert "RegulatoryIntelligenceRuntimeSettings" not in source
    assert "load_regulatory_intelligence_runtime_settings" not in source
    assert "ENERGY_REGULATORY_" not in source


def test_chunk_71_builder_does_not_load_settings() -> None:
    names = imported_names(PROVIDER_RUNTIME_MODULE)
    assert "RegulatoryIntelligenceRuntimeSettings" not in names
    assert "load_regulatory_intelligence_runtime_settings" not in names
    modules = imported_modules(PROVIDER_RUNTIME_MODULE)
    assert "energy_trading.shared.config" not in modules
    assert "energy_trading.shared.config.regulatory_intelligence" not in modules
    source = PROVIDER_RUNTIME_MODULE.read_text(encoding="utf-8")
    assert "RegulatoryIntelligenceRuntimeSettings" not in source
    assert "load_regulatory_intelligence_runtime_settings" not in source
    assert "ENERGY_REGULATORY_" not in source
    tree = ast.parse(source, filename=str(PROVIDER_RUNTIME_MODULE))
    builder = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "build_regulatory_intelligence_provider_runtime"
    )
    assert [arg.arg for arg in builder.args.kwonlyargs] == [
        "openai_client",
        "qdrant_client",
        "qdrant_vector_config",
        "query_embedding_model",
        "constraint_inference_model",
    ]
    neutral_source = NEUTRAL_BUILDER_MODULE.read_text(encoding="utf-8")
    assert "RegulatoryIntelligenceRuntimeSettings" not in neutral_source
    assert "load_regulatory_intelligence_runtime_settings" not in neutral_source


def test_graph_remains_unwired() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "RegulatoryIntelligenceRuntimeSettings" not in names
    assert "load_regulatory_intelligence_runtime_settings" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "energy_trading.shared.config.regulatory_intelligence" not in modules
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "RegulatoryIntelligenceRuntimeSettings" not in source
    assert "ENERGY_REGULATORY_" not in source
