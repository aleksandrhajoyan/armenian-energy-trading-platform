"""Chunk 97 Document Vector Index HTTP request schemas stay API-owned transport contracts."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES,
    SRC_ROOT,
    annotation_type_names,
    collect_http_api_import_violations,
    collect_import_violations,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
HEALTH_ROUTER = API_ROOT / "routers" / "health.py"
REGULATORY_ROUTER = API_ROOT / "routers" / "regulatory_intelligence.py"
SCHEMA_MODULE = API_ROOT / "schemas" / "document_vector_index.py"
SCHEMA_PACKAGE_INIT = API_ROOT / "schemas" / "__init__.py"
ACCESSOR_MODULE = API_ROOT / "dependencies" / "document_vector_index.py"
LIFESPAN_MODULE = API_ROOT / "composition" / "document_vector_index_lifespan.py"
PRODUCTION_LIFESPAN_MODULE = API_ROOT / "composition" / "production_lifespan.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
DOMAIN_ROOT = PRODUCTION_ROOT / "domain"
ML_ROOT = PRODUCTION_ROOT / "ml"

FORBIDDEN_PREFIXES = (
    "openai",
    "qdrant_client",
    "fastapi",
    "starlette",
    "energy_trading.ml",
    "energy_trading.application",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration.document_vector_index_execution",
    "energy_trading.application.ports.document_extraction",
    "energy_trading.api.app",
    "energy_trading.api.routers",
    "energy_trading.api.dependencies",
    "energy_trading.api.dependencies.document_vector_index",
    "energy_trading.api.composition",
    "energy_trading.api.composition.document_vector_index_lifespan",
    "energy_trading.shared.config",
    "energy_trading.infrastructure",
    "langgraph",
    "langchain",
    "langchain_core",
    "redis",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "httpx",
    "os",
    "sys",
    "dotenv",
    "pathlib",
)

FORBIDDEN_TYPE_NAMES = frozenset(
    {
        "Any",
        "dict",
        "Dict",
        "Mapping",
        "HTTPException",
        "APIRouter",
        "Depends",
        "Request",
        "UploadFile",
        "File",
        "Path",
        "bytes",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "OpenAISettings",
        "QdrantSettings",
        "DocumentVectorIndexRuntimeSettings",
        "DocumentVectorIndexExecutionService",
        "ExtractedDocumentChunk",
        "SchemaFactory",
        "GenericMapper",
        "ServiceRegistry",
        "DocumentVectorIndexResponse",
    }
)

GENERIC_FRAMEWORK_NAMES = frozenset(
    {
        "SchemaFactory",
        "GenericMapper",
        "ServiceRegistry",
        "HTTPException",
        "Depends",
        "APIRouter",
        "Request",
        "UploadFile",
        "ExtractedDocumentChunk",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "pydantic",
    }
)

RUNTIME_CALL_NAMES = frozenset(
    {
        "execute",
        "run",
        "embed",
        "prepare",
        "index",
        "search",
        "infer",
        "Depends",
        "HTTPException",
        "include_router",
        "add_api_route",
        "get_document_vector_index_execution_service",
        "build_document_vector_index_lifespan",
        "loaded_document_vector_index_runtime",
        "ExtractedDocumentChunk",
    }
)

PUBLIC_CLASS_NAMES = (
    "DocumentVectorIndexChunkRequest",
    "DocumentVectorIndexRequest",
)

FORBIDDEN_SURFACE_TOKENS = (
    "UploadFile",
    "multipart",
    "base64",
    "HttpUrl",
    "MIME",
    "openai",
    "qdrant",
    "api_key",
    "DocumentVectorIndexResponse",
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "Path",
        "bytes",
        "URL",
        "File",
        "UploadFile",
        "APIRouter",
        "Depends",
        "Request",
        "Any",
        "dict",
        "Dict",
        "Mapping",
    }
)


def _module_class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def _module_function_defs(path: Path) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _class_by_name(path: Path, name: str) -> ast.ClassDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    msg = f"{name} not found"
    raise AssertionError(msg)


def _ann_assign_fields(node: ast.ClassDef) -> dict[str, str]:
    fields: dict[str, str] = {}
    for statement in node.body:
        if not isinstance(statement, ast.AnnAssign):
            continue
        if not isinstance(statement.target, ast.Name):
            continue
        if statement.target.id == "model_config":
            continue
        assert statement.annotation is not None
        fields[statement.target.id] = ast.unparse(statement.annotation)
    return fields


def test_schema_module_lives_in_api_schemas_package() -> None:
    assert SCHEMA_MODULE.parent == API_ROOT / "schemas"
    assert SCHEMA_MODULE.exists()
    assert SCHEMA_PACKAGE_INIT.exists()
    init_names = imported_names(SCHEMA_PACKAGE_INIT)
    assert "DocumentVectorIndexChunkRequest" in init_names
    assert "DocumentVectorIndexRequest" in init_names
    assert "Depends" not in init_names
    assert "APIRouter" not in init_names
    assert _module_function_defs(SCHEMA_PACKAGE_INIT) == []


def test_schema_imports_only_approved_surfaces() -> None:
    leaked = sorted(
        module
        for module in imported_modules(SCHEMA_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(SCHEMA_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(SCHEMA_MODULE)
    assert "BaseModel" in names
    assert "ConfigDict" in names
    assert "Request" not in names
    assert "Depends" not in names
    assert "APIRouter" not in names
    assert "get_document_vector_index_execution_service" not in names
    assert "build_document_vector_index_lifespan" not in names
    assert "ExtractedDocumentChunk" not in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_schema_exposes_only_the_two_request_models() -> None:
    assert _module_class_names(SCHEMA_MODULE) == list(PUBLIC_CLASS_NAMES)
    assert _module_function_defs(SCHEMA_MODULE) == []
    tree = ast.parse(SCHEMA_MODULE.read_text(encoding="utf-8"), filename=str(SCHEMA_MODULE))
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        base_names = [ast.unparse(base) for base in node.bases]
        assert "BaseModel" in base_names
        assert "DocumentVectorIndexResponse" not in node.name


def test_models_are_frozen_and_forbid_extra_fields() -> None:
    source = SCHEMA_MODULE.read_text(encoding="utf-8")
    assert 'ConfigDict(frozen=True, extra="forbid")' in source
    for name in PUBLIC_CLASS_NAMES:
        node = _class_by_name(SCHEMA_MODULE, name)
        configs = [
            statement
            for statement in node.body
            if isinstance(statement, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "model_config"
                for target in statement.targets
            )
        ]
        assert len(configs) == 1
        value = configs[0].value
        assert isinstance(value, ast.Call)
        assert ast.unparse(value.func) == "ConfigDict"
        keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in value.keywords}
        assert keywords == {"frozen": "True", "extra": "'forbid'"}


def test_chunk_and_request_fields_match_the_published_shape() -> None:
    chunk_fields = _ann_assign_fields(
        _class_by_name(SCHEMA_MODULE, "DocumentVectorIndexChunkRequest")
    )
    assert chunk_fields == {
        "document_id": "str",
        "chunk_id": "str",
        "text": "str",
        "ordinal": "int",
        "page_number": "int | None",
    }
    request_fields = _ann_assign_fields(_class_by_name(SCHEMA_MODULE, "DocumentVectorIndexRequest"))
    assert request_fields == {"chunks": "tuple[DocumentVectorIndexChunkRequest, ...]"}


def test_schema_has_no_routes_depends_or_execution() -> None:
    source = SCHEMA_MODULE.read_text(encoding="utf-8")
    assert "Depends(" not in source
    assert "@" not in source
    assert "APIRouter" not in source
    assert "HTTPException" not in source
    assert ".execute(" not in source
    assert ".run(" not in source
    runtime_calls: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name in RUNTIME_CALL_NAMES:
            runtime_calls.append(name)
    assert runtime_calls == []
    identifiers = {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    leaked_frameworks = sorted(name for name in identifiers if name in GENERIC_FRAMEWORK_NAMES)
    assert leaked_frameworks == []
    names = annotation_type_names(SCHEMA_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    leaked_identifiers = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked_identifiers == []
    for token in FORBIDDEN_SURFACE_TOKENS:
        assert token not in source
    field_names = {
        *_ann_assign_fields(_class_by_name(SCHEMA_MODULE, "DocumentVectorIndexChunkRequest")),
        *_ann_assign_fields(_class_by_name(SCHEMA_MODULE, "DocumentVectorIndexRequest")),
    }
    assert field_names == {
        "document_id",
        "chunk_id",
        "text",
        "ordinal",
        "page_number",
        "chunks",
    }


def test_provider_sdk_allowlist_remains_the_existing_document_index_modules() -> None:
    assert DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES == (
        "energy_trading/api/composition/document_vector_index_runtime.py",
        "energy_trading/api/composition/document_vector_index_configured_runtime.py",
    )
    relative = SCHEMA_MODULE.relative_to(SRC_ROOT).as_posix()
    assert relative not in DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES
    assert "openai" not in imported_modules(SCHEMA_MODULE)
    assert "qdrant_client" not in imported_modules(SCHEMA_MODULE)


def test_application_domain_and_graph_do_not_import_the_schema() -> None:
    forbidden = (
        "energy_trading.api",
        "energy_trading.api.schemas",
        "energy_trading.api.schemas.document_vector_index",
        "openai",
        "qdrant_client",
    )
    assert collect_import_violations(APPLICATION_ROOT, forbidden) == []
    assert collect_import_violations(DOMAIN_ROOT, forbidden) == []
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, forbidden) == []
    names = imported_names(GRAPH_MODULE)
    assert "DocumentVectorIndexRequest" not in names
    assert "DocumentVectorIndexChunkRequest" not in names
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "energy_trading.api.schemas" not in source


def test_app_health_accessor_and_routers_remain_unwired_to_the_schema() -> None:
    for path in (
        API_APP,
        HEALTH_ROUTER,
        REGULATORY_ROUTER,
        ACCESSOR_MODULE,
        LIFESPAN_MODULE,
        PRODUCTION_LIFESPAN_MODULE,
    ):
        names = imported_names(path)
        assert "DocumentVectorIndexRequest" not in names
        assert "DocumentVectorIndexChunkRequest" not in names
        source = path.read_text(encoding="utf-8")
        assert "DocumentVectorIndexRequest" not in source
        assert "energy_trading.api.schemas.document_vector_index" not in source
    for path in sorted((API_ROOT / "routers").rglob("*.py")):
        if path.resolve() == (API_ROOT / "routers" / "document_vector_index.py").resolve():
            continue
        source = path.read_text(encoding="utf-8")
        assert "DocumentVectorIndexRequest" not in source
        assert "DocumentVectorIndexChunkRequest" not in source
        if path.resolve() == REGULATORY_ROUTER.resolve():
            continue
        assert "energy_trading.api.schemas.document_vector_index" not in source
    assert (
        collect_http_api_import_violations(
            API_ROOT,
            (
                "openai",
                "qdrant_client",
                "energy_trading.api.composition.document_vector_index_loaded_runtime",
            ),
        )
        == []
    )
