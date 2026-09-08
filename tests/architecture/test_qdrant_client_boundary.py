"""Chunk 22 Qdrant client foundation must stay infrastructure-only."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    REGULATORY_INFRA_CLIENT_COMPOSITION_RELATIVES,
    REGULATORY_PROVIDER_COMPOSITION_RELATIVES,
    SRC_ROOT,
    collect_import_violations,
    imported_names,
    is_regulatory_managed_runtime_module,
    is_regulatory_provider_composition_module,
    is_regulatory_provider_runtime_module,
)

DOMAIN_ROOT = SRC_ROOT / "energy_trading" / "domain"
APPLICATION_ROOT = SRC_ROOT / "energy_trading" / "application"
API_ROOT = SRC_ROOT / "energy_trading" / "api"
API_APP = API_ROOT / "app.py"
ML_ROOT = SRC_ROOT / "energy_trading" / "ml"
CONFIG_ROOT = SRC_ROOT / "energy_trading" / "shared" / "config"
QDRANT_SETTINGS = CONFIG_ROOT / "qdrant.py"
QDRANT_ROOT = SRC_ROOT / "energy_trading" / "infrastructure" / "vector_store" / "qdrant"
QDRANT_CLIENT = QDRANT_ROOT / "client.py"

FORBIDDEN_INNER_QDRANT = (
    "qdrant_client",
    "energy_trading.infrastructure.vector_store.qdrant",
)

FORBIDDEN_SETTINGS_IMPORTS = (
    "qdrant_client",
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
    "openai",
)

FORBIDDEN_QDRANT_IMPLEMENTATION = (
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

FORBIDDEN_CONTRACT_NAMES = frozenset(
    {
        "DocumentEmbeddingPort",
        "DocumentChunkEmbedding",
        "DocumentVectorIndexPort",
        "DocumentVectorIndexEntry",
        "DocumentVectorSearchPort",
        "DocumentVectorSearchQuery",
        "ExtractedDocumentChunk",
    }
)

INFERENCE_FORBIDDEN_TEXT = (
    "cloud_inference=True",
    "models.Document",
    "FastEmbed",
    "get_embedding_size",
    "set_model",
    "set_sparse_model",
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
            exclude_relative_prefixes=REGULATORY_PROVIDER_COMPOSITION_RELATIVES,
        )
        == []
    )
    assert (
        collect_import_violations(
            API_ROOT,
            ("energy_trading.infrastructure.vector_store.qdrant",),
            exclude_relative_prefixes=REGULATORY_INFRA_CLIENT_COMPOSITION_RELATIVES,
        )
        == []
    )
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, FORBIDDEN_INNER_QDRANT) == []


def test_qdrant_settings_are_runtime_client_free() -> None:
    assert collect_import_violations(QDRANT_SETTINGS.parent, FORBIDDEN_SETTINGS_IMPORTS) == []
    names = imported_names(QDRANT_SETTINGS)
    assert "qdrant_client" not in names
    assert "AsyncQdrantClient" not in names
    assert "QdrantClient" not in names


def test_qdrant_infrastructure_forbidden_dependencies() -> None:
    assert collect_import_violations(QDRANT_ROOT, FORBIDDEN_QDRANT_IMPLEMENTATION) == []
    for path in sorted(QDRANT_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "numpy" not in names
        assert "np" not in names


def test_qdrant_client_foundation_does_not_import_application_document_contracts() -> None:
    names = imported_names(QDRANT_CLIENT)
    leaked = sorted(name for name in names if name in FORBIDDEN_CONTRACT_NAMES)
    assert leaked == []
    assert "energy_trading.application.errors" not in names
    assert "ConflictError" not in names
    assert "InvalidRequestError" not in names
    assert "DependencyUnavailableError" not in names
    assert "energy_trading.application.ports.document_vector_index" not in names
    assert "energy_trading.application.ports.document_vector_search" not in names
    assert "energy_trading.application.ports.document_extraction" not in names


def test_create_app_does_not_wire_qdrant() -> None:
    assert (
        collect_import_violations(
            API_ROOT,
            ("qdrant_client",),
            exclude_relative_prefixes=REGULATORY_PROVIDER_COMPOSITION_RELATIVES,
        )
        == []
    )
    assert (
        collect_import_violations(
            API_ROOT,
            (
                "energy_trading.infrastructure.vector_store",
                "energy_trading.infrastructure.vector_store.qdrant",
                "energy_trading.shared.config.qdrant",
            ),
            exclude_relative_prefixes=REGULATORY_INFRA_CLIENT_COMPOSITION_RELATIVES,
        )
        == []
    )
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        if is_regulatory_provider_composition_module(path):
            assert "AsyncQdrantClient" in names
            assert "QdrantDocumentVectorConfig" in names
            assert "QdrantSettings" not in names
            assert "create_qdrant_client" not in names
            assert "load_qdrant_settings" not in names
            assert "QdrantDocumentVectorIndex" not in names
            if is_regulatory_provider_runtime_module(path):
                assert "QdrantDocumentVectorSearch" in names
            else:
                assert "QdrantDocumentVectorSearch" not in names
            continue
        if is_regulatory_managed_runtime_module(path):
            assert "AsyncQdrantClient" not in names
            assert "QdrantDocumentVectorConfig" not in names
            assert "QdrantSettings" in names
            assert "create_qdrant_client" in names
            assert "load_qdrant_settings" not in names
            assert "QdrantDocumentVectorIndex" not in names
            assert "QdrantDocumentVectorSearch" not in names
            continue
        assert "AsyncQdrantClient" not in names
        assert "QdrantSettings" not in names
        assert "create_qdrant_client" not in names
        assert "load_qdrant_settings" not in names
        assert "QdrantDocumentVectorIndex" not in names
        assert "QdrantDocumentVectorSearch" not in names
        assert "QdrantDocumentVectorConfig" not in names
    call_names = _create_app_call_names(API_APP)
    assert "create_qdrant_client" not in call_names
    assert "AsyncQdrantClient" not in call_names
    assert "QdrantSettings" not in call_names
    assert "load_qdrant_settings" not in call_names
    assert "QdrantDocumentVectorIndex" not in call_names
    assert "QdrantDocumentVectorSearch" not in call_names
    assert "QdrantDocumentVectorConfig" not in call_names
    lowered = API_APP.read_text(encoding="utf-8").lower()
    assert "qdrant" not in lowered


def test_qdrant_client_foundation_disables_inference_and_local_mode() -> None:
    source = QDRANT_CLIENT.read_text(encoding="utf-8")
    for fragment in INFERENCE_FORBIDDEN_TEXT:
        assert fragment not in source
    assert "cloud_inference=False" in source
    assert "prefer_grpc=False" in source
    assert 'location=":memory:"' not in source
    tree = ast.parse(source, filename=str(QDRANT_CLIENT))
    create_fn = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "create_qdrant_client"
    )
    keywords: dict[str, str] = {}
    for node in ast.walk(create_fn):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        if name != "AsyncQdrantClient":
            continue
        for keyword in node.keywords:
            if keyword.arg is None:
                continue
            keywords[keyword.arg] = ast.unparse(keyword.value)
    assert keywords["prefer_grpc"] == "False"
    assert keywords["cloud_inference"] == "False"
    assert keywords["check_compatibility"] == "False"
    assert "location" not in keywords
    assert "path" not in keywords
    assert "url" not in keywords
