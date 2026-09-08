"""Chunk 70 OpenAI client foundation stays outer-layer and unwired."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    REGULATORY_PROVIDER_RUNTIME_RELATIVE,
    SRC_ROOT,
    annotation_type_names,
    collect_import_violations,
    imported_modules,
    imported_names,
    is_forbidden,
    is_regulatory_provider_runtime_module,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
DOMAIN_ROOT = PRODUCTION_ROOT / "domain"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
ML_ROOT = PRODUCTION_ROOT / "ml"
GRAPH_MODULE = APPLICATION_ROOT / "orchestration" / "graph.py"
CONFIG_ROOT = PRODUCTION_ROOT / "shared" / "config"
OPENAI_SETTINGS = CONFIG_ROOT / "openai.py"
CLIENT_ROOT = PRODUCTION_ROOT / "infrastructure" / "openai"
CLIENT_MODULE = CLIENT_ROOT / "client.py"
COMPOSITION_MODULE = API_ROOT / "composition" / "regulatory_intelligence.py"
PROVIDER_RUNTIME_MODULE = API_ROOT / "composition" / "regulatory_intelligence_runtime.py"
QUERY_EMBEDDING_ADAPTER = (
    PRODUCTION_ROOT / "infrastructure" / "embeddings" / "openai_query_embedding.py"
)
INFERENCE_ADAPTER = (
    PRODUCTION_ROOT / "infrastructure" / "regulatory" / "openai_constraint_inference.py"
)

ALLOWED_OPENAI_SDK_MODULES = frozenset(
    {
        QUERY_EMBEDDING_ADAPTER.resolve(),
        INFERENCE_ADAPTER.resolve(),
        CLIENT_MODULE.resolve(),
        PROVIDER_RUNTIME_MODULE.resolve(),
    }
)

FORBIDDEN_INNER_OPENAI = (
    "openai",
    "energy_trading.infrastructure.embeddings",
    "energy_trading.infrastructure.regulatory",
    "energy_trading.infrastructure.openai",
)

FORBIDDEN_SETTINGS_IMPORTS = (
    "openai",
    "energy_trading.infrastructure",
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
    "qdrant_client",
    "qdrant",
)

FORBIDDEN_CLIENT_IMPLEMENTATION = (
    "fastapi",
    "starlette",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "redis",
    "qdrant_client",
    "qdrant",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.application.ports",
    "energy_trading.infrastructure.embeddings",
    "energy_trading.infrastructure.regulatory",
    "energy_trading.infrastructure.vector_store",
    "energy_trading.infrastructure.cache",
    "energy_trading.infrastructure.persistence",
    "langchain",
    "langchain_core",
    "langgraph",
    "pandas",
    "polars",
    "openpyxl",
    "numpy",
    "tenacity",
    "backoff",
    "os",
    "sys",
    "dotenv",
)

ALLOWED_CLIENT_IMPORTS = {
    "openai",
    "energy_trading.shared.config.openai",
}

FORBIDDEN_TYPE_NAMES = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "dict",
        "Dict",
        "Mapping",
        "LLMPort",
        "EmbeddingPort",
        "LLMClientFactory",
        "ProviderRegistry",
        "Container",
    }
)

GENERIC_FRAMEWORK_NAMES = frozenset(
    {
        "LLMPort",
        "EmbeddingPort",
        "LLMClientFactory",
        "ProviderRegistry",
        "ServiceRegistry",
        "AgentFactory",
        "Container",
        "LiteLLM",
        "RAGPort",
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


def test_openai_sdk_imports_exist_only_in_approved_modules() -> None:
    leaked: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path.resolve() in ALLOWED_OPENAI_SDK_MODULES:
            continue
        for module in sorted(imported_modules(path)):
            if is_forbidden(module, ("openai",)):
                leaked.append(f"{path.relative_to(SRC_ROOT)} imports {module}")
    assert leaked == []
    assert "openai" in imported_modules(CLIENT_MODULE)
    assert "openai" not in imported_modules(OPENAI_SETTINGS)
    assert "openai" in imported_modules(PROVIDER_RUNTIME_MODULE)


def test_inner_layers_do_not_import_openai() -> None:
    assert collect_import_violations(DOMAIN_ROOT, FORBIDDEN_INNER_OPENAI) == []
    assert collect_import_violations(APPLICATION_ROOT, FORBIDDEN_INNER_OPENAI) == []
    assert (
        collect_import_violations(
            API_ROOT,
            FORBIDDEN_INNER_OPENAI,
            exclude_relative_prefixes=(REGULATORY_PROVIDER_RUNTIME_RELATIVE,),
        )
        == []
    )
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, FORBIDDEN_INNER_OPENAI) == []


def test_openai_settings_are_runtime_client_free() -> None:
    assert collect_import_violations(OPENAI_SETTINGS.parent, FORBIDDEN_SETTINGS_IMPORTS) == []
    names = imported_names(OPENAI_SETTINGS)
    assert "openai" not in names
    assert "AsyncOpenAI" not in names
    assert "OpenAI" not in names
    assert "create_openai_client" not in names
    annotations = annotation_type_names(OPENAI_SETTINGS)
    assert "AsyncOpenAI" not in annotations
    assert "OpenAI" not in annotations
    source = OPENAI_SETTINGS.read_text(encoding="utf-8")
    assert "api_key" in source
    assert "model" not in _openai_settings_field_names()
    assert "ENERGY_OPENAI_" in source


def _openai_settings_field_names() -> set[str]:
    tree = ast.parse(OPENAI_SETTINGS.read_text(encoding="utf-8"), filename=str(OPENAI_SETTINGS))
    settings = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "OpenAISettings"
    )
    names: set[str] = set()
    for item in settings.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            names.add(item.target.id)
    return names


def test_openai_settings_live_outside_application_and_domain() -> None:
    relative = OPENAI_SETTINGS.relative_to(PRODUCTION_ROOT).as_posix()
    assert relative == "shared/config/openai.py"
    names = imported_names(OPENAI_SETTINGS)
    assert "energy_trading.domain" not in names
    assert "energy_trading.application" not in names
    assert "energy_trading.api" not in names


def test_client_factory_is_infrastructure_owned() -> None:
    relative = CLIENT_MODULE.relative_to(PRODUCTION_ROOT).as_posix()
    assert relative == "infrastructure/openai/client.py"
    leaked = sorted(
        module
        for module in imported_modules(CLIENT_MODULE)
        if is_forbidden(module, FORBIDDEN_CLIENT_IMPLEMENTATION)
    )
    assert leaked == []
    extras = imported_modules(CLIENT_MODULE) - ALLOWED_CLIENT_IMPORTS
    stdlib_ok = {"__future__", "typing"}
    assert extras <= stdlib_ok
    names = imported_names(CLIENT_MODULE)
    assert "AsyncOpenAI" in names
    assert "OpenAISettings" in names
    assert "OpenAIDocumentQueryEmbeddingAdapter" not in names
    assert "OpenAIRegulatoryConstraintInferenceAdapter" not in names
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []


def test_client_factory_has_no_environment_or_retry_loop() -> None:
    source = CLIENT_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(CLIENT_MODULE))
    call_names = {_call_name(node) for node in ast.walk(tree) if isinstance(node, ast.Call)}
    assert "getenv" not in call_names
    assert "sleep" not in call_names
    assert "load_openai_settings" not in call_names
    assert "AsyncOpenAI(" in source
    assert "os.environ" not in source
    assert "getenv" not in source
    assert "OPENAI_API_KEY" not in source
    assert ".env" not in source
    assert "time.sleep" not in source
    assert "asyncio.sleep" not in source
    assert "tenacity" not in source
    assert "backoff" not in source
    identifiers = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    leaked_frameworks = sorted(name for name in identifiers if name in GENERIC_FRAMEWORK_NAMES)
    assert leaked_frameworks == []
    assert "except BaseException" not in source
    assert "except Exception" not in source


def test_client_factory_constructs_async_openai_with_disabled_retries() -> None:
    tree = ast.parse(CLIENT_MODULE.read_text(encoding="utf-8"), filename=str(CLIENT_MODULE))
    create_fn = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "create_openai_client"
    )
    keywords: dict[str, str] = {}
    for node in ast.walk(create_fn):
        if not isinstance(node, ast.Call):
            continue
        if _call_name(node) != "AsyncOpenAI":
            continue
        for keyword in node.keywords:
            if keyword.arg is None:
                continue
            keywords[keyword.arg] = ast.unparse(keyword.value)
    assert keywords["api_key"] == "settings.api_key.get_secret_value()"
    assert keywords["max_retries"] == "0"
    assert "model" not in keywords
    assert "organization" not in keywords
    assert "base_url" not in keywords
    assert "timeout" not in keywords


def test_no_global_async_openai_client() -> None:
    source = CLIENT_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(CLIENT_MODULE))
    assigned: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigned.add(target.id)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assigned.add(node.target.id)
    assert "AsyncOpenAI" not in assigned
    assert "client" not in assigned
    call_names = {
        _call_name(node)
        for node in tree.body
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
        for node in [node.value]
    }
    assert "AsyncOpenAI" not in call_names
    assert "create_openai_client" not in source.split("def create_openai_client")[0]


def test_create_app_and_composition_do_not_construct_openai_client() -> None:
    forbidden_wiring = (
        "openai",
        "energy_trading.infrastructure.openai",
        "energy_trading.infrastructure.openai.client",
        "energy_trading.shared.config.openai",
    )
    assert (
        collect_import_violations(
            API_ROOT,
            forbidden_wiring,
            exclude_relative_prefixes=(REGULATORY_PROVIDER_RUNTIME_RELATIVE,),
        )
        == []
    )
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        if is_regulatory_provider_runtime_module(path):
            assert "AsyncOpenAI" in names
            assert "OpenAISettings" not in names
            assert "create_openai_client" not in names
            assert "load_openai_settings" not in names
            continue
        assert "AsyncOpenAI" not in names
        assert "OpenAISettings" not in names
        assert "create_openai_client" not in names
        assert "load_openai_settings" not in names
    call_names = _create_app_call_names(API_APP)
    assert "create_openai_client" not in call_names
    assert "AsyncOpenAI" not in call_names
    assert "OpenAISettings" not in call_names
    assert "load_openai_settings" not in call_names
    composition_source = COMPOSITION_MODULE.read_text(encoding="utf-8")
    assert "create_openai_client" not in composition_source
    assert "OpenAISettings" not in composition_source
    assert "load_openai_settings" not in composition_source
    assert "AsyncOpenAI" not in composition_source


def test_graph_remains_unwired_to_openai_client() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "create_openai_client" not in names
    assert "OpenAISettings" not in names
    assert "AsyncOpenAI" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "openai" not in modules
    assert "energy_trading.infrastructure.openai" not in modules
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "create_openai_client" not in source
    assert "OpenAISettings" not in source
