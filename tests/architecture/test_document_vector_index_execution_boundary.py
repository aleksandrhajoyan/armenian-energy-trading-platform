"""Chunk 85 document vector index execution stays application-owned."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    collect_http_api_import_violations,
    http_transport_api_paths,
    imported_modules,
    imported_names,
    is_document_vector_index_loaded_runtime_module,
    is_document_vector_index_managed_runtime_module,
    is_document_vector_index_provider_composition_module,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
EXECUTION_MODULE = ORCHESTRATION_ROOT / "document_vector_index_execution.py"
PREPARATION_MODULE = ORCHESTRATION_ROOT / "document_vector_index_entry_preparation.py"
AGENT_MODULE = PRODUCTION_ROOT / "application" / "agents" / "regulatory_intelligence.py"
EXTRACTION_PORT = PRODUCTION_ROOT / "application" / "ports" / "document_extraction.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
OPENAI_DOCUMENT_EMBEDDING = (
    PRODUCTION_ROOT / "infrastructure" / "embeddings" / "openai_document_embedding.py"
)
QDRANT_INDEX = PRODUCTION_ROOT / "infrastructure" / "vector_store" / "qdrant" / "document_vector.py"
COMPOSITION_ROOT = API_ROOT / "composition"
DOCUMENT_VECTOR_INDEX_EXECUTION_COMPOSITION = (
    COMPOSITION_ROOT / "document_vector_index_execution.py"
)

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.api",
    "energy_trading.ml",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.ports.document_embedding",
    "energy_trading.application.ports.document_query_embedding",
    "energy_trading.application.ports.document_vector_search",
    "energy_trading.application.ports.regulatory_constraint_inference",
    "fastapi",
    "starlette",
    "langgraph",
    "langchain",
    "langchain_core",
    "openai",
    "anthropic",
    "google.generativeai",
    "google.genai",
    "sentence_transformers",
    "transformers",
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
    "scipy",
    "sklearn",
    "lightgbm",
    "xgboost",
    "prophet",
    "torch",
    "tensorflow",
    "n8n",
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
        "MutableMapping",
        "TypedDict",
        "ndarray",
        "NDArray",
        "DataFrame",
        "Path",
        "bytes",
        "bytearray",
        "Protocol",
        "ABC",
        "EmbeddingPort",
        "LLMPort",
        "AIProviderPort",
        "DocumentEmbeddingPort",
        "DocumentChunkEmbedding",
        "DocumentQueryEmbeddingPort",
        "DocumentVectorSearchPort",
        "OpenAIDocumentEmbeddingAdapter",
        "QdrantDocumentVectorIndex",
        "RegulatoryIntelligenceAgent",
        "QdrantClient",
        "Qdrant",
        "OpenAI",
        "Anthropic",
        "SentenceTransformer",
        "HttpUrl",
        "AnyUrl",
        "URL",
        "Request",
        "Response",
        "WorkflowState",
        "FailurePolicyPort",
        "CachePort",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "Any",
        "dict",
        "Mapping",
        "ndarray",
        "embed",
        "search",
        "upsert",
        "infer",
        "run",
        "create_app",
        "build_workflow_graph",
        "DocumentEmbeddingPort",
        "OpenAIDocumentEmbeddingAdapter",
        "QdrantDocumentVectorIndex",
        "RegulatoryIntelligenceAgent",
        "EmbeddingPort",
        "LLMPort",
        "AIProviderPort",
        "provider",
        "model_name",
        "prompt",
        "collection_name",
        "score",
        "filter",
        "retry",
        "cache",
        "numpy",
        "asarray",
        "normalize",
        "clamp",
        "rewrite",
        "expand",
        "tokenize",
        "registry",
        "factory",
    }
)

GENERIC_FRAMEWORK_CLASS_NAMES = frozenset(
    {
        "EmbeddingPort",
        "LLMPort",
        "AIProviderPort",
        "GenericEmbeddingPort",
        "RagPipeline",
        "IndexingPipeline",
        "DocumentIndexingPipeline",
        "VectorIndexingServiceBase",
        "GenericIndexExecutionService",
        "DocumentPipeline",
        "IndexingFactory",
        "IndexingRegistry",
        "EmbeddingPipeline",
        "GenericEmbeddingService",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.orchestration.document_vector_index_entry_preparation",
        "energy_trading.application.ports.document_extraction",
        "energy_trading.application.ports.document_vector_index",
    }
)

ALLOWED_INIT_ANNOTATIONS = {
    "preparation_service": "DocumentVectorIndexEntryPreparationService",
    "document_vector_index_port": "DocumentVectorIndexPort",
}

UNWIRED_MODULES = (
    GRAPH_MODULE,
    AGENT_MODULE,
    EXTRACTION_PORT,
    OPENAI_DOCUMENT_EMBEDDING,
    QDRANT_INDEX,
    PREPARATION_MODULE,
    ORCHESTRATION_ROOT / "state.py",
    ORCHESTRATION_ROOT / "parallel_ingestion_workflow.py",
    ORCHESTRATION_ROOT / "parallel_ingestion_executor.py",
    ORCHESTRATION_ROOT / "parallel_ingestion_failure_runtime_handling.py",
    ORCHESTRATION_ROOT / "document_vector_search_query_preparation.py",
    ORCHESTRATION_ROOT / "regulatory_intelligence_query_execution.py",
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


def _public_function_defs(path: Path) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]


def _init_arg_annotations(class_def: ast.ClassDef) -> dict[str, str]:
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    annotations: dict[str, str] = {}
    for arg in (*init_fn.args.args, *init_fn.args.kwonlyargs):
        if arg.arg == "self" or arg.annotation is None:
            continue
        annotations[arg.arg] = ast.unparse(arg.annotation)
    return annotations


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
            names.update(param.name for param in node.type_params)
    return names


def _execute_method(class_def: ast.ClassDef) -> ast.AsyncFunctionDef:
    for node in class_def.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "execute":
            return node
    msg = "async method 'execute' not found on DocumentVectorIndexExecutionService"
    raise AssertionError(msg)


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def test_execution_module_belongs_to_application_orchestration() -> None:
    assert EXECUTION_MODULE.parent == ORCHESTRATION_ROOT
    assert EXECUTION_MODULE.exists()


def test_execution_service_does_not_import_outer_layers_or_providers() -> None:
    leaked = sorted(
        module
        for module in imported_modules(EXECUTION_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(EXECUTION_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(EXECUTION_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(EXECUTION_MODULE)
    assert "DocumentVectorIndexEntryPreparationService" in names
    assert "DocumentVectorIndexPort" in names
    assert "ExtractedDocumentChunk" in names
    assert "DocumentEmbeddingPort" not in names
    assert "DocumentVectorIndexEntry" not in names
    assert "OpenAIDocumentEmbeddingAdapter" not in names
    assert "QdrantDocumentVectorIndex" not in names


def test_execution_module_exposes_exactly_one_production_class() -> None:
    assert _public_function_defs(EXECUTION_MODULE) == []
    assert _module_class_names(EXECUTION_MODULE) == ["DocumentVectorIndexExecutionService"]
    class_def = _class_def(EXECUTION_MODULE, "DocumentVectorIndexExecutionService")
    assert _base_names(class_def) == set()
    production_classes: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.ClassDef)
                and node.name == "DocumentVectorIndexExecutionService"
            ):
                production_classes.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_classes == [
        "energy_trading/application/orchestration/document_vector_index_execution.py"
    ]
    leaked_implementations = sorted(
        name
        for name in _module_class_names(EXECUTION_MODULE)
        if name in GENERIC_FRAMEWORK_CLASS_NAMES
    )
    assert leaked_implementations == []


def test_constructor_injects_exactly_preparation_service_and_index_port() -> None:
    class_def = _class_def(EXECUTION_MODULE, "DocumentVectorIndexExecutionService")
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert tuple(arg.arg for arg in init_fn.args.args) == (
        "self",
        "preparation_service",
        "document_vector_index_port",
    )
    assert init_fn.args.posonlyargs == []
    assert init_fn.args.kwonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    assert _init_arg_annotations(class_def) == ALLOWED_INIT_ANNOTATIONS
    constructed = [_call_name(node) for node in ast.walk(init_fn) if isinstance(node, ast.Call)]
    assert "DocumentVectorIndexEntryPreparationService" not in constructed
    assert "DocumentVectorIndexPort" not in constructed
    assert "DocumentEmbeddingPort" not in constructed
    assert "OpenAIDocumentEmbeddingAdapter" not in constructed
    assert "QdrantDocumentVectorIndex" not in constructed
    assert "OpenAI" not in constructed
    assert "QdrantClient" not in constructed


def test_execute_signature_is_async_keyword_only_chunks_returning_none() -> None:
    class_def = _class_def(EXECUTION_MODULE, "DocumentVectorIndexExecutionService")
    execute_fn = _execute_method(class_def)
    assert tuple(arg.arg for arg in execute_fn.args.args) == ("self",)
    assert execute_fn.args.posonlyargs == []
    assert tuple(arg.arg for arg in execute_fn.args.kwonlyargs) == ("chunks",)
    assert execute_fn.args.vararg is None
    assert execute_fn.args.kwarg is None
    assert ast.unparse(execute_fn.args.kwonlyargs[0].annotation) == (
        "tuple[ExtractedDocumentChunk, ...]"
    )
    assert ast.unparse(execute_fn.returns) == "None"
    public_methods = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]
    assert public_methods == ["execute"]


def test_execute_prepares_once_then_indexes_once_without_embed_or_entry_construction() -> None:
    class_def = _class_def(EXECUTION_MODULE, "DocumentVectorIndexExecutionService")
    execute_fn = _execute_method(class_def)
    control = [
        type(node).__name__
        for node in ast.walk(execute_fn)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try, ast.With))
    ]
    assert control == []
    except_handlers = [node for node in ast.walk(execute_fn) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    prepare_calls = 0
    index_calls = 0
    embed_calls = 0
    entry_calls = 0
    for node in ast.walk(execute_fn):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name == "prepare":
            prepare_calls += 1
            keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in node.keywords}
            assert keywords == {"chunks": "chunks"}
        if name == "index":
            index_calls += 1
            assert len(node.args) == 1
            assert isinstance(node.args[0], ast.Name)
            assert node.args[0].id == "entries"
        if name == "embed":
            embed_calls += 1
        if name == "DocumentVectorIndexEntry":
            entry_calls += 1
    assert prepare_calls == 1
    assert index_calls == 1
    assert embed_calls == 0
    assert entry_calls == 0
    statements = [
        node
        for node in execute_fn.body
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))
    ]
    assert len(statements) == 2
    first, second = statements
    assert isinstance(first, ast.Assign)
    assert isinstance(first.value, ast.Await)
    assert isinstance(first.value.value, ast.Call)
    assert _call_name(first.value.value) == "prepare"
    assert isinstance(second, ast.Expr)
    assert isinstance(second.value, ast.Await)
    assert isinstance(second.value.value, ast.Call)
    assert _call_name(second.value.value) == "index"
    identifiers = _identifier_names(EXECUTION_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(EXECUTION_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    application_implementations: list[str] = []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if isinstance(node, ast.ClassDef) and node.name in GENERIC_FRAMEWORK_CLASS_NAMES:
                application_implementations.append(node.name)
    assert application_implementations == []
    source = EXECUTION_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "qdrant" not in lowered
    assert "openai" not in lowered
    assert "numpy" not in lowered
    assert "fastapi" not in lowered
    assert ".embed(" not in source
    assert "DocumentVectorIndexEntry(" not in source
    assert "try:" not in source
    assert "except " not in source
    assert "DocumentEmbeddingPort" not in source
    assert "retry" not in lowered


def test_graph_runtime_and_providers_remain_unwired_to_the_execution_service() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        assert "DocumentVectorIndexExecutionService" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.document_vector_index_execution"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "DocumentVectorIndexExecutionService" not in source
        assert "document_vector_index_execution" not in source
    for path in sorted(COMPOSITION_ROOT.rglob("*.py")):
        if path.resolve() == DOCUMENT_VECTOR_INDEX_EXECUTION_COMPOSITION.resolve():
            continue
        if is_document_vector_index_provider_composition_module(path):
            continue
        if is_document_vector_index_managed_runtime_module(path):
            continue
        if is_document_vector_index_loaded_runtime_module(path):
            continue
        names = imported_names(path)
        assert "DocumentVectorIndexExecutionService" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.document_vector_index_execution"
            not in modules
        )


def test_api_composition_does_not_import_or_construct_the_execution_service() -> None:
    forbidden_wiring = ("energy_trading.application.orchestration.document_vector_index_execution",)
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    accessor = (API_ROOT / "dependencies" / "document_vector_index.py").resolve()
    document_index_router = (API_ROOT / "routers" / "document_vector_index.py").resolve()
    for path in http_transport_api_paths(API_ROOT):
        if path.resolve() in {accessor, document_index_router}:
            continue
        names = imported_names(path)
        assert "DocumentVectorIndexExecutionService" not in names
    app_source = API_APP.read_text(encoding="utf-8")
    tree = ast.parse(app_source, filename=str(API_APP))
    create_app = next(
        node
        for node in ast.walk(tree)
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
    assert "DocumentVectorIndexExecutionService" not in call_names
    lowered = app_source.lower()
    assert "documentvectorindexexecutionservice" not in lowered
    assert "document_vector_index_execution" not in lowered
