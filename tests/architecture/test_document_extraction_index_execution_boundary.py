"""Chunk 101 document extraction-to-index execution stays application-owned."""

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
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
EXECUTION_MODULE = ORCHESTRATION_ROOT / "document_extraction_index_execution.py"
INDEX_EXECUTION_MODULE = ORCHESTRATION_ROOT / "document_vector_index_execution.py"
AGENT_MODULE = PRODUCTION_ROOT / "application" / "agents" / "regulatory_intelligence.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
COMPOSITION_ROOT = API_ROOT / "composition"
DOCUMENT_INDEX_ROUTER = API_ROOT / "routers" / "document_vector_index.py"
PRODUCTION_LIFESPAN = COMPOSITION_ROOT / "production_lifespan.py"
PDF_ADAPTER = (
    PRODUCTION_ROOT / "infrastructure" / "adapters" / "unstructured" / "pdf_text_extraction.py"
)

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.api",
    "energy_trading.ml",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.ports.document_embedding",
    "energy_trading.application.ports.document_query_embedding",
    "energy_trading.application.ports.document_vector_index",
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
    "pathlib",
    "pypdf",
    "pytesseract",
    "easyocr",
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
        "PurePath",
        "PosixPath",
        "WindowsPath",
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
        "DocumentVectorIndexPort",
        "DocumentVectorIndexEntry",
        "OpenAIDocumentEmbeddingAdapter",
        "QdrantDocumentVectorIndex",
        "PdfTextExtractionAdapter",
        "PdfReader",
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
        "DocumentVectorIndexPort",
        "DocumentVectorIndexEntry",
        "OpenAIDocumentEmbeddingAdapter",
        "QdrantDocumentVectorIndex",
        "PdfTextExtractionAdapter",
        "PdfReader",
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
        "pathlib",
        "pypdf",
        "to_thread",
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
        "DocumentPipeline",
        "VectorIndexingServiceBase",
        "GenericIndexExecutionService",
        "IndexingFactory",
        "IndexingRegistry",
        "EmbeddingPipeline",
        "GenericEmbeddingService",
        "DocumentExtractionPipeline",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.orchestration.document_vector_index_execution",
        "energy_trading.application.ports.document_extraction",
    }
)

ALLOWED_INIT_ANNOTATIONS = {
    "document_extraction_port": "DocumentExtractionPort",
    "index_execution_service": "DocumentVectorIndexExecutionService",
}

UNWIRED_MODULES = (
    GRAPH_MODULE,
    AGENT_MODULE,
    API_APP,
    DOCUMENT_INDEX_ROUTER,
    PRODUCTION_LIFESPAN,
    PDF_ADAPTER,
    INDEX_EXECUTION_MODULE,
    COMPOSITION_ROOT / "regulatory_intelligence.py",
    COMPOSITION_ROOT / "regulatory_intelligence_runtime.py",
    COMPOSITION_ROOT / "regulatory_intelligence_configured_runtime.py",
    COMPOSITION_ROOT / "regulatory_intelligence_managed_runtime.py",
    COMPOSITION_ROOT / "regulatory_intelligence_loaded_runtime.py",
    COMPOSITION_ROOT / "regulatory_intelligence_lifespan.py",
    COMPOSITION_ROOT / "document_vector_index_execution.py",
    COMPOSITION_ROOT / "document_vector_index_runtime.py",
    COMPOSITION_ROOT / "document_vector_index_configured_runtime.py",
    COMPOSITION_ROOT / "document_vector_index_managed_runtime.py",
    COMPOSITION_ROOT / "document_vector_index_loaded_runtime.py",
    COMPOSITION_ROOT / "document_vector_index_lifespan.py",
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
    msg = "async method 'execute' not found on DocumentExtractionIndexExecutionService"
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
    assert "DocumentExtractionPort" in names
    assert "DocumentExtractionResult" in names
    assert "DocumentVectorIndexExecutionService" in names
    assert "ExtractedDocumentChunk" not in names
    assert "DocumentVectorIndexEntry" not in names
    assert "DocumentEmbeddingPort" not in names
    assert "DocumentVectorIndexPort" not in names
    assert "PdfTextExtractionAdapter" not in names
    assert "Path" not in names
    assert "OpenAIDocumentEmbeddingAdapter" not in names
    assert "QdrantDocumentVectorIndex" not in names


def test_execution_module_exposes_exactly_one_production_class() -> None:
    assert _public_function_defs(EXECUTION_MODULE) == []
    assert _module_class_names(EXECUTION_MODULE) == ["DocumentExtractionIndexExecutionService"]
    class_def = _class_def(EXECUTION_MODULE, "DocumentExtractionIndexExecutionService")
    assert _base_names(class_def) == set()
    production_classes: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.ClassDef)
                and node.name == "DocumentExtractionIndexExecutionService"
            ):
                production_classes.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_classes == [
        "energy_trading/application/orchestration/document_extraction_index_execution.py"
    ]
    leaked_implementations = sorted(
        name
        for name in _module_class_names(EXECUTION_MODULE)
        if name in GENERIC_FRAMEWORK_CLASS_NAMES
    )
    assert leaked_implementations == []


def test_constructor_injects_exactly_extraction_port_and_index_execution() -> None:
    class_def = _class_def(EXECUTION_MODULE, "DocumentExtractionIndexExecutionService")
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert tuple(arg.arg for arg in init_fn.args.args) == (
        "self",
        "document_extraction_port",
        "index_execution_service",
    )
    assert init_fn.args.posonlyargs == []
    assert init_fn.args.kwonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    assert _init_arg_annotations(class_def) == ALLOWED_INIT_ANNOTATIONS
    constructed = [_call_name(node) for node in ast.walk(init_fn) if isinstance(node, ast.Call)]
    assert "DocumentExtractionPort" not in constructed
    assert "DocumentVectorIndexExecutionService" not in constructed
    assert "DocumentExtractionResult" not in constructed
    assert "ExtractedDocumentChunk" not in constructed
    assert "DocumentVectorIndexEntry" not in constructed
    assert "PdfTextExtractionAdapter" not in constructed
    assert "OpenAI" not in constructed
    assert "QdrantClient" not in constructed
    assert "Path" not in constructed


def test_execute_signature_is_async_self_only_returning_extraction_result() -> None:
    class_def = _class_def(EXECUTION_MODULE, "DocumentExtractionIndexExecutionService")
    execute_fn = _execute_method(class_def)
    assert tuple(arg.arg for arg in execute_fn.args.args) == ("self",)
    assert execute_fn.args.posonlyargs == []
    assert execute_fn.args.kwonlyargs == []
    assert execute_fn.args.vararg is None
    assert execute_fn.args.kwarg is None
    assert ast.unparse(execute_fn.returns) == "DocumentExtractionResult"
    public_methods = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]
    assert public_methods == ["execute"]


def test_execute_extracts_once_and_indexes_non_empty_chunks_without_reconstruction() -> None:
    class_def = _class_def(EXECUTION_MODULE, "DocumentExtractionIndexExecutionService")
    execute_fn = _execute_method(class_def)
    except_handlers = [node for node in ast.walk(execute_fn) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    control = [
        type(node).__name__
        for node in ast.walk(execute_fn)
        if isinstance(node, (ast.IfExp, ast.Match, ast.For, ast.While, ast.Try, ast.With))
    ]
    assert control == []
    if_nodes = [node for node in execute_fn.body if isinstance(node, ast.If)]
    assert len(if_nodes) == 1
    chunks_guard = if_nodes[0]
    assert ast.unparse(chunks_guard.test) == "result.chunks"
    assert chunks_guard.orelse == []

    extract_calls = 0
    execute_calls = 0
    constructed: list[str] = []
    for node in ast.walk(execute_fn):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name == "extract":
            extract_calls += 1
            assert node.args == []
            assert node.keywords == []
        if name == "execute":
            execute_calls += 1
            keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in node.keywords}
            assert keywords == {"chunks": "result.chunks"}
            assert node.args == []
        if name in {
            "ExtractedDocumentChunk",
            "DocumentExtractionResult",
            "DocumentVectorIndexEntry",
        }:
            constructed.append(name)
    assert extract_calls == 1
    assert execute_calls == 1
    assert constructed == []

    nested_execute = [
        node
        for node in ast.walk(chunks_guard)
        if isinstance(node, ast.Call) and _call_name(node) == "execute"
    ]
    assert len(nested_execute) == 1

    statements = [
        node
        for node in execute_fn.body
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))
    ]
    assert len(statements) == 3
    assign, guarded, returned = statements
    assert isinstance(assign, ast.Assign)
    assert [target.id for target in assign.targets if isinstance(target, ast.Name)] == ["result"]
    assert isinstance(assign.value, ast.Await)
    assert isinstance(assign.value.value, ast.Call)
    assert _call_name(assign.value.value) == "extract"
    assert guarded is chunks_guard
    assert len(chunks_guard.body) == 1
    indexed = chunks_guard.body[0]
    assert isinstance(indexed, ast.Expr)
    assert isinstance(indexed.value, ast.Await)
    assert isinstance(indexed.value.value, ast.Call)
    assert _call_name(indexed.value.value) == "execute"
    assert isinstance(returned, ast.Return)
    assert isinstance(returned.value, ast.Name)
    assert returned.value.id == "result"

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
    assert "pathlib" not in lowered
    assert "pypdf" not in lowered
    assert "PdfTextExtractionAdapter" not in source
    assert "ExtractedDocumentChunk(" not in source
    assert "DocumentExtractionResult(" not in source
    assert "DocumentVectorIndexEntry(" not in source
    assert "try:" not in source
    assert "except " not in source
    assert "retry" not in lowered


def test_create_app_router_runtime_and_graph_remain_unwired() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        assert "DocumentExtractionIndexExecutionService" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.document_extraction_index_execution"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "DocumentExtractionIndexExecutionService" not in source
        assert "document_extraction_index_execution" not in source
    builder_module = COMPOSITION_ROOT / "pdf_document_extraction_index.py"
    composition_init = COMPOSITION_ROOT / "__init__.py"
    for path in sorted(COMPOSITION_ROOT.rglob("*.py")):
        if path.resolve() == builder_module.resolve():
            continue
        names = imported_names(path)
        assert "DocumentExtractionIndexExecutionService" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.document_extraction_index_execution"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "DocumentExtractionIndexExecutionService" not in source
        if path.resolve() != composition_init.resolve():
            assert "document_extraction_index_execution" not in source


def test_api_composition_does_not_import_or_construct_the_execution_service() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration.document_extraction_index_execution",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "DocumentExtractionIndexExecutionService" not in names
    app_source = API_APP.read_text(encoding="utf-8")
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
    assert "DocumentExtractionIndexExecutionService" not in call_names
    lowered = app_source.lower()
    assert "documentextractionindexexecutionservice" not in lowered
    assert "document_extraction_index_execution" not in lowered
