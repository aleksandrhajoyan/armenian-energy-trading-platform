"""Chunk 23 Qdrant document vector adapters must stay infrastructure-only."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    DOCUMENT_VECTOR_INDEX_PROVIDER_RUNTIME_RELATIVE,
    REGULATORY_INFRA_CLIENT_COMPOSITION_RELATIVES,
    REGULATORY_PROVIDER_COMPOSITION_RELATIVES,
    SRC_ROOT,
    collect_import_violations,
    imported_modules,
    imported_names,
    is_document_vector_index_provider_runtime_module,
    is_regulatory_provider_composition_module,
    is_regulatory_provider_runtime_module,
)

DOMAIN_ROOT = SRC_ROOT / "energy_trading" / "domain"
APPLICATION_ROOT = SRC_ROOT / "energy_trading" / "application"
API_ROOT = SRC_ROOT / "energy_trading" / "api"
API_APP = API_ROOT / "app.py"
ML_ROOT = SRC_ROOT / "energy_trading" / "ml"
QDRANT_ROOT = SRC_ROOT / "energy_trading" / "infrastructure" / "vector_store" / "qdrant"
QDRANT_CLIENT = QDRANT_ROOT / "client.py"
DOCUMENT_VECTOR = QDRANT_ROOT / "document_vector.py"

FORBIDDEN_INNER_QDRANT = (
    "qdrant_client",
    "energy_trading.infrastructure.vector_store.qdrant",
)

FORBIDDEN_ADAPTER_IMPLEMENTATION = (
    "fastapi",
    "starlette",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "redis",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.application.ports.document_embedding",
    "langchain",
    "langchain_core",
    "langgraph",
    "openai",
    "pandas",
    "polars",
    "openpyxl",
    "numpy",
    "fastembed",
    "sentence_transformers",
    "pypdf",
    "PyPDF2",
    "pdfplumber",
    "fitz",
    "pymupdf",
    "pytesseract",
)

ALLOWED_ADAPTER_APPLICATION = {
    "energy_trading.application.errors",
    "energy_trading.application.ports.document_extraction",
    "energy_trading.application.ports.document_vector_index",
    "energy_trading.application.ports.document_vector_search",
}

INFERENCE_FORBIDDEN_TEXT = (
    "cloud_inference=True",
    "models.Document",
    "models.Image",
    "InferenceObject",
    "FastEmbed",
)

COLLECTION_FORBIDDEN_TEXT = (
    "create_collection",
    "recreate_collection",
    "delete_collection",
    "VectorParams",
    "Distance.COSINE",
    "Distance.DOT",
)


def _create_app_call_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
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
    return call_names


def test_inner_layers_do_not_import_qdrant() -> None:
    assert collect_import_violations(DOMAIN_ROOT, FORBIDDEN_INNER_QDRANT) == []
    assert collect_import_violations(APPLICATION_ROOT, FORBIDDEN_INNER_QDRANT) == []
    assert (
        collect_import_violations(
            API_ROOT,
            ("qdrant_client",),
            exclude_relative_prefixes=(
                *REGULATORY_PROVIDER_COMPOSITION_RELATIVES,
                DOCUMENT_VECTOR_INDEX_PROVIDER_RUNTIME_RELATIVE,
            ),
        )
        == []
    )
    assert (
        collect_import_violations(
            API_ROOT,
            ("energy_trading.infrastructure.vector_store.qdrant",),
            exclude_relative_prefixes=(
                *REGULATORY_INFRA_CLIENT_COMPOSITION_RELATIVES,
                DOCUMENT_VECTOR_INDEX_PROVIDER_RUNTIME_RELATIVE,
            ),
        )
        == []
    )
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, FORBIDDEN_INNER_QDRANT) == []


def test_document_adapter_forbidden_dependencies() -> None:
    assert collect_import_violations(DOCUMENT_VECTOR.parent, FORBIDDEN_ADAPTER_IMPLEMENTATION) == []
    names = imported_names(DOCUMENT_VECTOR)
    assert "numpy" not in names
    assert "np" not in names
    modules = imported_modules(DOCUMENT_VECTOR)
    leaked = sorted(
        module
        for module in modules
        if module.startswith("energy_trading.application")
        and module not in ALLOWED_ADAPTER_APPLICATION
    )
    assert leaked == []
    for allowed in ALLOWED_ADAPTER_APPLICATION:
        assert allowed in modules
    assert "energy_trading.infrastructure.vector_store.qdrant.client" not in modules
    assert "qdrant_client" in modules


def test_document_adapter_imports_qdrant_client_foundation_types() -> None:
    names = imported_names(DOCUMENT_VECTOR)
    assert "AsyncQdrantClient" in names
    assert "QdrantDocumentVectorIndex" in {
        node.name
        for node in ast.walk(ast.parse(DOCUMENT_VECTOR.read_text(encoding="utf-8")))
        if isinstance(node, ast.ClassDef)
    }
    assert "QdrantDocumentVectorSearch" in {
        node.name
        for node in ast.walk(ast.parse(DOCUMENT_VECTOR.read_text(encoding="utf-8")))
        if isinstance(node, ast.ClassDef)
    }


def test_qdrant_client_foundation_stays_application_port_free() -> None:
    names = imported_names(QDRANT_CLIENT)
    modules = imported_modules(QDRANT_CLIENT)
    assert "energy_trading.application.errors" not in modules
    assert "energy_trading.application.ports.document_extraction" not in modules
    assert "energy_trading.application.ports.document_embedding" not in modules
    assert "energy_trading.application.ports.document_vector_index" not in modules
    assert "energy_trading.application.ports.document_vector_search" not in modules
    for forbidden in (
        "DocumentEmbeddingPort",
        "DocumentChunkEmbedding",
        "DocumentVectorIndexPort",
        "DocumentVectorIndexEntry",
        "DocumentVectorSearchPort",
        "DocumentVectorSearchQuery",
        "ExtractedDocumentChunk",
        "ConflictError",
        "InvalidRequestError",
        "DependencyUnavailableError",
    ):
        assert forbidden not in names


def test_document_adapter_has_no_inference_or_collection_management() -> None:
    source = DOCUMENT_VECTOR.read_text(encoding="utf-8")
    for fragment in INFERENCE_FORBIDDEN_TEXT:
        assert fragment not in source
    for fragment in COLLECTION_FORBIDDEN_TEXT:
        assert fragment not in source
    assert "upload_points" not in source
    assert "upload_collection" not in source
    assert "VectorStore" not in source
    assert "cloud_inference=True" not in source
    assert "await self._client.close" not in source
    assert "INSERT_ONLY" in source
    assert "query_points" in source


def test_production_qdrant_package_has_no_inference() -> None:
    for path in sorted(QDRANT_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        for fragment in INFERENCE_FORBIDDEN_TEXT:
            assert fragment not in source


def test_create_app_does_not_wire_document_vector_adapters() -> None:
    assert (
        collect_import_violations(
            API_ROOT,
            (
                "qdrant_client",
                "energy_trading.infrastructure.vector_store.qdrant.document_vector",
            ),
            exclude_relative_prefixes=(
                *REGULATORY_PROVIDER_COMPOSITION_RELATIVES,
                DOCUMENT_VECTOR_INDEX_PROVIDER_RUNTIME_RELATIVE,
            ),
        )
        == []
    )
    assert (
        collect_import_violations(
            API_ROOT,
            (
                "energy_trading.infrastructure.vector_store",
                "energy_trading.infrastructure.vector_store.qdrant",
            ),
            exclude_relative_prefixes=(
                *REGULATORY_INFRA_CLIENT_COMPOSITION_RELATIVES,
                DOCUMENT_VECTOR_INDEX_PROVIDER_RUNTIME_RELATIVE,
            ),
        )
        == []
    )
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        if is_document_vector_index_provider_runtime_module(path):
            assert "QdrantDocumentVectorConfig" in names
            assert "AsyncQdrantClient" in names
            assert "QdrantDocumentVectorIndex" in names
            assert "QdrantDocumentVectorSearch" not in names
            continue
        if is_regulatory_provider_composition_module(path):
            assert "QdrantDocumentVectorConfig" in names
            assert "AsyncQdrantClient" in names
            assert "QdrantDocumentVectorIndex" not in names
            if is_regulatory_provider_runtime_module(path):
                assert "QdrantDocumentVectorSearch" in names
            else:
                assert "QdrantDocumentVectorSearch" not in names
            continue
        assert "QdrantDocumentVectorIndex" not in names
        assert "QdrantDocumentVectorSearch" not in names
        assert "QdrantDocumentVectorConfig" not in names
        assert "AsyncQdrantClient" not in names
    call_names = _create_app_call_names(API_APP)
    assert "QdrantDocumentVectorIndex" not in call_names
    assert "QdrantDocumentVectorSearch" not in call_names
    assert "QdrantDocumentVectorConfig" not in call_names
    assert "AsyncQdrantClient" not in call_names
    assert "create_qdrant_client" not in call_names
    lowered = API_APP.read_text(encoding="utf-8").lower()
    assert "qdrant" not in lowered
    assert "documentvector" not in lowered
