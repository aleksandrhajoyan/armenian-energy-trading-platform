"""Chunk 68 OpenAI query-embedding adapter stays infrastructure-only."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
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
QUERY_EMBEDDING_PORT = APPLICATION_ROOT / "ports" / "document_query_embedding.py"
ADAPTER_MODULE = PRODUCTION_ROOT / "infrastructure" / "embeddings" / "openai_query_embedding.py"
COMPOSITION_MODULE = API_ROOT / "composition" / "regulatory_intelligence.py"

FORBIDDEN_ADAPTER_PREFIXES = (
    "energy_trading.api",
    "energy_trading.ml",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.application.ports.document_embedding",
    "energy_trading.application.ports.document_vector_search",
    "energy_trading.application.ports.document_vector_index",
    "energy_trading.infrastructure.vector_store",
    "energy_trading.infrastructure.cache",
    "energy_trading.infrastructure.persistence",
    "energy_trading.shared.config",
    "fastapi",
    "starlette",
    "langgraph",
    "langchain",
    "langchain_core",
    "anthropic",
    "google.generativeai",
    "google.genai",
    "litellm",
    "qdrant_client",
    "qdrant",
    "redis",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "numpy",
    "scipy",
    "sklearn",
    "pandas",
    "polars",
    "openpyxl",
    "torch",
    "tensorflow",
    "sentence_transformers",
    "transformers",
    "tenacity",
    "backoff",
    "n8n",
    "os",
    "sys",
)

FORBIDDEN_INNER_OPENAI = (
    "openai",
    "energy_trading.infrastructure.embeddings",
)

ALLOWED_ADAPTER_IMPORTS = {
    "openai",
    "energy_trading.application.errors",
    "energy_trading.application.ports.document_query_embedding",
}

FORBIDDEN_TYPE_NAMES = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "dict",
        "Dict",
        "Mapping",
        "CreateEmbeddingResponse",
        "Embedding",
        "LLMPort",
        "EmbeddingPort",
        "ndarray",
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
        "LiteLLM",
    }
)

RUNTIME_FORBIDDEN_CALLS = frozenset(
    {
        "sleep",
        "AsyncOpenAI",
        "OpenAI",
        "getenv",
        "load_settings",
    }
)


def _module_class_defs(path: Path) -> list[ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node for node in tree.body if isinstance(node, ast.ClassDef)]


def _public_methods(class_def: ast.ClassDef) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        node
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and (not node.name.startswith("_") or node.name == "__init__")
    ]


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


def test_openai_sdk_imports_exist_only_in_the_query_embedding_adapter() -> None:
    leaked: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path.resolve() == ADAPTER_MODULE.resolve():
            continue
        for module in sorted(imported_modules(path)):
            if is_forbidden(module, ("openai",)):
                leaked.append(f"{path.relative_to(SRC_ROOT)} imports {module}")
    assert leaked == []
    adapter_modules = imported_modules(ADAPTER_MODULE)
    assert "openai" in adapter_modules


def test_inner_layers_do_not_import_openai() -> None:
    assert collect_import_violations(DOMAIN_ROOT, FORBIDDEN_INNER_OPENAI) == []
    assert collect_import_violations(APPLICATION_ROOT, FORBIDDEN_INNER_OPENAI) == []
    assert collect_import_violations(API_ROOT, FORBIDDEN_INNER_OPENAI) == []
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, FORBIDDEN_INNER_OPENAI) == []


def test_application_query_embedding_port_is_unchanged() -> None:
    args = async_function_arg_names(QUERY_EMBEDDING_PORT, "embed_query")
    assert args == ("self", "query_text")
    names = imported_names(QUERY_EMBEDDING_PORT)
    assert "openai" not in names
    assert "AsyncOpenAI" not in names
    assert "OpenAIDocumentQueryEmbeddingAdapter" not in names
    source = QUERY_EMBEDDING_PORT.read_text(encoding="utf-8")
    assert "OpenAI" not in source
    assert "text-embedding" not in source


def test_adapter_depends_inward_and_avoids_forbidden_frameworks() -> None:
    leaked = sorted(
        module
        for module in imported_modules(ADAPTER_MODULE)
        if is_forbidden(module, FORBIDDEN_ADAPTER_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(ADAPTER_MODULE) - ALLOWED_ADAPTER_IMPORTS
    stdlib_ok = {"__future__", "collections.abc", "typing"}
    assert extras <= stdlib_ok
    names = imported_names(ADAPTER_MODULE)
    assert "DocumentQueryEmbedding" in names
    assert "DocumentQueryEmbeddingPort" not in names
    assert "AsyncOpenAI" in names
    assert "OpenAIError" in names
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []


def test_adapter_public_surface_is_embed_query_returning_canonical_dto() -> None:
    classes = _module_class_defs(ADAPTER_MODULE)
    assert [node.name for node in classes] == ["OpenAIDocumentQueryEmbeddingAdapter"]
    adapter = classes[0]
    assert adapter.bases == []
    public = _public_methods(adapter)
    assert [node.name for node in public] == ["__init__", "embed_query"]
    init = next(node for node in public if node.name == "__init__")
    assert isinstance(init, ast.FunctionDef)
    assert tuple(arg.arg for arg in init.args.kwonlyargs) == ("client", "model")
    assert [arg.arg for arg in init.args.args] == ["self"]
    embed = next(node for node in public if node.name == "embed_query")
    assert isinstance(embed, ast.AsyncFunctionDef)
    assert [arg.arg for arg in embed.args.args] == ["self", "query_text"]
    assert ast.unparse(embed.returns) == "DocumentQueryEmbedding"
    annotations = annotation_type_names(ADAPTER_MODULE)
    leaked = sorted(name for name in annotations if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    assert "CreateEmbeddingResponse" not in annotations
    assert "Embedding" not in annotations


def test_adapter_calls_only_embeddings_create_with_float_encoding() -> None:
    tree = ast.parse(ADAPTER_MODULE.read_text(encoding="utf-8"), filename=str(ADAPTER_MODULE))
    adapter = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "OpenAIDocumentQueryEmbeddingAdapter"
    )
    embed = next(
        node
        for node in adapter.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "embed_query"
    )
    calls = [node for node in ast.walk(embed) if isinstance(node, ast.Call)]
    named = [_call_name(node) for node in calls]
    assert "create" in named
    assert "chat" not in named
    assert "completions" not in named
    assert "responses" not in named
    encoding: list[str] = []
    for node in calls:
        if _call_name(node) != "create":
            continue
        keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in node.keywords}
        assert keywords["model"] == "self._model"
        assert keywords["input"] == "query_text"
        assert keywords["encoding_format"] == "'float'"
        encoding.append(keywords["encoding_format"])
    assert encoding == ["'float'"]


def test_adapter_has_no_retry_client_construction_or_env_access() -> None:
    source = ADAPTER_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(ADAPTER_MODULE))
    call_names = {_call_name(node) for node in ast.walk(tree) if isinstance(node, ast.Call)}
    leaked_calls = sorted(name for name in call_names if name in RUNTIME_FORBIDDEN_CALLS)
    assert leaked_calls == []
    assert "AsyncOpenAI(" not in source
    assert "os.environ" not in source
    assert "getenv" not in source
    assert "OPENAI_API_KEY" not in source
    assert "time.sleep" not in source
    assert "asyncio.sleep" not in source
    assert "tenacity" not in source
    assert "backoff" not in source
    assert "except BaseException" not in source
    assert "except Exception" not in source
    identifiers = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    leaked_frameworks = sorted(name for name in identifiers if name in GENERIC_FRAMEWORK_NAMES)
    assert leaked_frameworks == []
    assert "query_text.lower(" not in source
    assert ".replace(" not in source
    assert "truncate" not in source.lower()


def test_blank_query_error_does_not_interpolate_query_text() -> None:
    source = ADAPTER_MODULE.read_text(encoding="utf-8")
    assert "InvalidRequestError(_MSG_INVALID_QUERY)" in source
    assert "InvalidRequestError(query_text" not in source
    tree = ast.parse(source, filename=str(ADAPTER_MODULE))
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            for arg in (*node.exc.args, *(kw.value for kw in node.exc.keywords)):
                assert not isinstance(arg, ast.JoinedStr)
                if isinstance(arg, ast.Name):
                    assert arg.id != "query_text"


def test_create_app_and_composition_do_not_construct_openai() -> None:
    forbidden_wiring = (
        "openai",
        "energy_trading.infrastructure.embeddings",
        "energy_trading.infrastructure.embeddings.openai_query_embedding",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "OpenAIDocumentQueryEmbeddingAdapter" not in names
        assert "AsyncOpenAI" not in names
    call_names = _create_app_call_names(API_APP)
    assert "OpenAIDocumentQueryEmbeddingAdapter" not in call_names
    assert "AsyncOpenAI" not in call_names
    composition_source = COMPOSITION_MODULE.read_text(encoding="utf-8")
    assert "openai" not in composition_source.lower()
    assert "OpenAIDocumentQueryEmbeddingAdapter" not in composition_source
    assert "AsyncOpenAI" not in composition_source


def test_graph_remains_unwired_to_openai_query_embedding() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "OpenAIDocumentQueryEmbeddingAdapter" not in names
    assert "AsyncOpenAI" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "openai" not in modules
    assert "energy_trading.infrastructure.embeddings" not in modules
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "openai" not in source.lower()
    assert "OpenAIDocumentQueryEmbeddingAdapter" not in source
