"""Chunk 69 OpenAI regulatory-constraint inference adapter stays infrastructure-only."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES,
    REGULATORY_MANAGED_RUNTIME_RELATIVE,
    REGULATORY_PROVIDER_COMPOSITION_RELATIVES,
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_import_violations,
    imported_modules,
    imported_names,
    is_document_vector_index_provider_composition_module,
    is_forbidden,
    is_regulatory_provider_composition_module,
    is_regulatory_provider_runtime_module,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
DOMAIN_ROOT = PRODUCTION_ROOT / "domain"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
ML_ROOT = PRODUCTION_ROOT / "ml"
GRAPH_MODULE = APPLICATION_ROOT / "orchestration" / "graph.py"
INFERENCE_PORT = APPLICATION_ROOT / "ports" / "regulatory_constraint_inference.py"
ADAPTER_MODULE = (
    PRODUCTION_ROOT / "infrastructure" / "regulatory" / "openai_constraint_inference.py"
)
QUERY_EMBEDDING_ADAPTER_MODULE = (
    PRODUCTION_ROOT / "infrastructure" / "embeddings" / "openai_query_embedding.py"
)
DOCUMENT_EMBEDDING_ADAPTER_MODULE = (
    PRODUCTION_ROOT / "infrastructure" / "embeddings" / "openai_document_embedding.py"
)
CLIENT_FACTORY_MODULE = PRODUCTION_ROOT / "infrastructure" / "openai" / "client.py"
COMPOSITION_MODULE = API_ROOT / "composition" / "regulatory_intelligence.py"
PROVIDER_RUNTIME_MODULE = API_ROOT / "composition" / "regulatory_intelligence_runtime.py"
CONFIGURED_RUNTIME_MODULE = (
    API_ROOT / "composition" / "regulatory_intelligence_configured_runtime.py"
)
INDEX_RUNTIME_MODULE = API_ROOT / "composition" / "document_vector_index_runtime.py"
INDEX_CONFIGURED_RUNTIME_MODULE = (
    API_ROOT / "composition" / "document_vector_index_configured_runtime.py"
)

ALLOWED_OPENAI_ADAPTER_MODULES = frozenset(
    {
        ADAPTER_MODULE.resolve(),
        QUERY_EMBEDDING_ADAPTER_MODULE.resolve(),
        DOCUMENT_EMBEDDING_ADAPTER_MODULE.resolve(),
        CLIENT_FACTORY_MODULE.resolve(),
        PROVIDER_RUNTIME_MODULE.resolve(),
        CONFIGURED_RUNTIME_MODULE.resolve(),
        INDEX_RUNTIME_MODULE.resolve(),
        INDEX_CONFIGURED_RUNTIME_MODULE.resolve(),
    }
)

FORBIDDEN_ADAPTER_PREFIXES = (
    "energy_trading.api",
    "energy_trading.ml",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.application.ports.document_embedding",
    "energy_trading.application.ports.document_query_embedding",
    "energy_trading.application.ports.document_vector_search",
    "energy_trading.application.ports.document_vector_index",
    "energy_trading.infrastructure.vector_store",
    "energy_trading.infrastructure.cache",
    "energy_trading.infrastructure.persistence",
    "energy_trading.infrastructure.embeddings",
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
    "energy_trading.infrastructure.regulatory",
    "energy_trading.infrastructure.openai",
)

ALLOWED_ADAPTER_IMPORTS = {
    "openai",
    "pydantic",
    "energy_trading.application.errors",
    "energy_trading.application.ports.document_extraction",
    "energy_trading.domain.models.regulatory",
}

FORBIDDEN_TYPE_NAMES = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "dict",
        "Dict",
        "Mapping",
        "ParsedResponse",
        "Response",
        "ChatCompletion",
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
        "RAGPort",
        "VectorStore",
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

DAM_RULE_IDENTIFIERS = frozenset(
    {
        "AMD",
        "HOURLY",
        "INTERVAL",
        "GATE_CLOSURE",
        "LOT_SIZE",
        "PRICE_CAP",
        "PRICE_FLOOR",
        "NOMINATION",
        "BALANCING",
        "PENALTY",
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


def test_openai_sdk_imports_exist_only_in_approved_openai_adapters() -> None:
    leaked: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path.resolve() in ALLOWED_OPENAI_ADAPTER_MODULES:
            continue
        for module in sorted(imported_modules(path)):
            if is_forbidden(module, ("openai",)):
                leaked.append(f"{path.relative_to(SRC_ROOT)} imports {module}")
    assert leaked == []
    assert "openai" in imported_modules(ADAPTER_MODULE)
    assert "openai" in imported_modules(QUERY_EMBEDDING_ADAPTER_MODULE)
    assert "openai" in imported_modules(DOCUMENT_EMBEDDING_ADAPTER_MODULE)
    assert "openai" in imported_modules(CLIENT_FACTORY_MODULE)
    assert "openai" in imported_modules(PROVIDER_RUNTIME_MODULE)
    assert "openai" in imported_modules(CONFIGURED_RUNTIME_MODULE)
    assert "openai" in imported_modules(INDEX_RUNTIME_MODULE)
    assert "openai" in imported_modules(INDEX_CONFIGURED_RUNTIME_MODULE)


def test_inner_layers_do_not_import_openai() -> None:
    assert collect_import_violations(DOMAIN_ROOT, FORBIDDEN_INNER_OPENAI) == []
    assert collect_import_violations(APPLICATION_ROOT, FORBIDDEN_INNER_OPENAI) == []
    assert (
        collect_import_violations(
            API_ROOT,
            (
                "openai",
                "energy_trading.infrastructure.embeddings",
                "energy_trading.infrastructure.regulatory",
            ),
            exclude_relative_prefixes=(
                *REGULATORY_PROVIDER_COMPOSITION_RELATIVES,
                *DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES,
            ),
        )
        == []
    )
    assert (
        collect_import_violations(
            API_ROOT,
            ("energy_trading.infrastructure.openai",),
            exclude_relative_prefixes=(REGULATORY_MANAGED_RUNTIME_RELATIVE,),
        )
        == []
    )
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, FORBIDDEN_INNER_OPENAI) == []


def test_application_inference_port_is_unchanged() -> None:
    args = async_function_arg_names(INFERENCE_PORT, "infer")
    assert args == ("self",)
    names = imported_names(INFERENCE_PORT)
    assert "openai" not in names
    assert "AsyncOpenAI" not in names
    assert "OpenAIRegulatoryConstraintInferenceAdapter" not in names
    source = INFERENCE_PORT.read_text(encoding="utf-8")
    assert "OpenAI" not in source
    assert "gpt-" not in source


def test_adapter_depends_inward_and_avoids_forbidden_frameworks() -> None:
    leaked = sorted(
        module
        for module in imported_modules(ADAPTER_MODULE)
        if is_forbidden(module, FORBIDDEN_ADAPTER_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(ADAPTER_MODULE) - ALLOWED_ADAPTER_IMPORTS
    stdlib_ok = {"__future__", "collections.abc", "datetime", "typing"}
    assert extras <= stdlib_ok
    names = imported_names(ADAPTER_MODULE)
    assert "ExtractedDocumentChunk" in names
    assert "RegulatoryConstraint" in names
    assert "RegulatoryConstraintInferencePort" not in names
    assert "AsyncOpenAI" in names
    assert "OpenAIError" in names
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []


def test_adapter_public_surface_is_infer_returning_canonical_constraints() -> None:
    classes = _module_class_defs(ADAPTER_MODULE)
    public_classes = [node.name for node in classes if not node.name.startswith("_")]
    assert public_classes == ["OpenAIRegulatoryConstraintInferenceAdapter"]
    adapter = next(
        node for node in classes if node.name == "OpenAIRegulatoryConstraintInferenceAdapter"
    )
    assert adapter.bases == []
    public = _public_methods(adapter)
    assert [node.name for node in public] == ["__init__", "infer"]
    init = next(node for node in public if node.name == "__init__")
    assert isinstance(init, ast.FunctionDef)
    assert tuple(arg.arg for arg in init.args.kwonlyargs) == ("client", "model")
    assert [arg.arg for arg in init.args.args] == ["self"]
    infer = next(node for node in public if node.name == "infer")
    assert isinstance(infer, ast.AsyncFunctionDef)
    assert [arg.arg for arg in infer.args.args] == ["self"]
    assert tuple(arg.arg for arg in infer.args.kwonlyargs) == ("chunks",)
    assert ast.unparse(infer.returns) == "tuple[RegulatoryConstraint, ...]"
    annotations = annotation_type_names(ADAPTER_MODULE)
    leaked = sorted(name for name in annotations if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    assert "ParsedResponse" not in annotations
    assert "Response" not in annotations


def test_adapter_calls_responses_parse_with_private_text_format() -> None:
    tree = ast.parse(ADAPTER_MODULE.read_text(encoding="utf-8"), filename=str(ADAPTER_MODULE))
    adapter = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "OpenAIRegulatoryConstraintInferenceAdapter"
    )
    infer = next(
        node
        for node in adapter.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "infer"
    )
    calls = [node for node in ast.walk(infer) if isinstance(node, ast.Call)]
    named = [_call_name(node) for node in calls]
    assert "parse" in named
    assert "create" not in named
    assert "chat" not in named
    assert "completions" not in named
    assert "embeddings" not in named
    parse_keywords: list[dict[str, str]] = []
    for node in calls:
        if _call_name(node) != "parse":
            continue
        keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in node.keywords}
        assert keywords["model"] == "self._model"
        assert "text_format" in keywords
        assert keywords["text_format"] == "_ProviderInferenceEnvelope"
        assert "instructions" in keywords
        assert "tools" not in keywords
        parse_keywords.append(keywords)
    assert len(parse_keywords) == 1


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
    assigned = {
        target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    leaked_dam = sorted(name for name in assigned | identifiers if name in DAM_RULE_IDENTIFIERS)
    assert leaked_dam == []
    assert "PSRC" not in source
    assert "Armenian" not in source


def test_errors_do_not_interpolate_chunk_or_provider_text() -> None:
    source = ADAPTER_MODULE.read_text(encoding="utf-8")
    assert "DependencyUnavailableError(_MSG_UNAVAILABLE)" in source
    tree = ast.parse(source, filename=str(ADAPTER_MODULE))
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            for arg in (*node.exc.args, *(kw.value for kw in node.exc.keywords)):
                assert not isinstance(arg, ast.JoinedStr)
                if isinstance(arg, ast.Name):
                    assert arg.id not in {"chunks", "candidate", "response", "parsed"}


def test_create_app_and_composition_do_not_construct_openai_inference() -> None:
    forbidden_wiring = (
        "openai",
        "energy_trading.infrastructure.regulatory",
        "energy_trading.infrastructure.regulatory.openai_constraint_inference",
    )
    assert (
        collect_import_violations(
            API_ROOT,
            forbidden_wiring,
            exclude_relative_prefixes=(
                *REGULATORY_PROVIDER_COMPOSITION_RELATIVES,
                *DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES,
            ),
        )
        == []
    )
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        if is_document_vector_index_provider_composition_module(path):
            assert "AsyncOpenAI" in names
            assert "OpenAIRegulatoryConstraintInferenceAdapter" not in names
            continue
        if is_regulatory_provider_composition_module(path):
            assert "AsyncOpenAI" in names
            if is_regulatory_provider_runtime_module(path):
                assert "OpenAIRegulatoryConstraintInferenceAdapter" in names
            else:
                assert "OpenAIRegulatoryConstraintInferenceAdapter" not in names
            continue
        assert "OpenAIRegulatoryConstraintInferenceAdapter" not in names
        assert "AsyncOpenAI" not in names
    call_names = _create_app_call_names(API_APP)
    assert "OpenAIRegulatoryConstraintInferenceAdapter" not in call_names
    assert "AsyncOpenAI" not in call_names
    composition_source = COMPOSITION_MODULE.read_text(encoding="utf-8")
    assert "openai" not in composition_source.lower()
    assert "OpenAIRegulatoryConstraintInferenceAdapter" not in composition_source
    assert "AsyncOpenAI" not in composition_source
    assert "OpenAIDocumentQueryEmbeddingAdapter" not in composition_source


def test_graph_remains_unwired_to_openai_inference() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "OpenAIRegulatoryConstraintInferenceAdapter" not in names
    assert "AsyncOpenAI" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "openai" not in modules
    assert "energy_trading.infrastructure.regulatory" not in modules
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "openai" not in source.lower()
    assert "OpenAIRegulatoryConstraintInferenceAdapter" not in source
