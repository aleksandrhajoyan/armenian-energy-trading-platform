"""Unit tests for typed document vector index runtime settings.

These tests must not require live providers, Docker, or a local ``.env``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
)
from energy_trading.shared.config.document_vector_index import (
    DocumentVectorIndexRuntimeSettings,
    load_document_vector_index_runtime_settings,
)
from energy_trading.shared.config.openai import OpenAISettings, load_openai_settings
from energy_trading.shared.config.qdrant import QdrantSettings, load_qdrant_settings
from energy_trading.shared.config.regulatory_intelligence import (
    RegulatoryIntelligenceRuntimeSettings,
    load_regulatory_intelligence_runtime_settings,
)
from energy_trading.shared.config.settings import load_settings
from tests.architecture.import_inspection import SRC_ROOT, imported_modules

SENTINEL_DOCUMENT_EMBEDDING_MODEL = "sentinel-document-embedding-model-chunk88"
SENTINEL_COLLECTION_NAME = "sentinel-document-index-collection-chunk88"
SENTINEL_VECTOR_SIZE = 8

_EXPECTED_FIELDS = frozenset(
    {
        "document_embedding_model",
        "qdrant_collection_name",
        "qdrant_vector_size",
    }
)

_DOCUMENT_INDEX_ENV_KEYS = (
    "ENERGY_DOCUMENT_INDEX_DOCUMENT_EMBEDDING_MODEL",
    "ENERGY_DOCUMENT_INDEX_QDRANT_COLLECTION_NAME",
    "ENERGY_DOCUMENT_INDEX_QDRANT_VECTOR_SIZE",
)


@pytest.fixture(autouse=True)
def clear_document_index_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _DOCUMENT_INDEX_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _settings(**overrides: object) -> DocumentVectorIndexRuntimeSettings:
    payload: dict[str, object] = {
        "document_embedding_model": SENTINEL_DOCUMENT_EMBEDDING_MODEL,
        "qdrant_collection_name": SENTINEL_COLLECTION_NAME,
        "qdrant_vector_size": SENTINEL_VECTOR_SIZE,
    }
    payload.update(overrides)
    return DocumentVectorIndexRuntimeSettings(_env_file=None, **payload)


def test_valid_explicit_construction() -> None:
    settings = _settings()
    assert settings.document_embedding_model == SENTINEL_DOCUMENT_EMBEDDING_MODEL
    assert settings.qdrant_collection_name == SENTINEL_COLLECTION_NAME
    assert settings.qdrant_vector_size == SENTINEL_VECTOR_SIZE


def test_exactly_three_production_fields() -> None:
    assert set(DocumentVectorIndexRuntimeSettings.model_fields) == _EXPECTED_FIELDS


def test_missing_document_embedding_model_fails() -> None:
    with pytest.raises(ValidationError):
        DocumentVectorIndexRuntimeSettings(
            _env_file=None,
            qdrant_collection_name=SENTINEL_COLLECTION_NAME,
            qdrant_vector_size=SENTINEL_VECTOR_SIZE,
        )


def test_missing_qdrant_collection_name_fails() -> None:
    with pytest.raises(ValidationError):
        DocumentVectorIndexRuntimeSettings(
            _env_file=None,
            document_embedding_model=SENTINEL_DOCUMENT_EMBEDDING_MODEL,
            qdrant_vector_size=SENTINEL_VECTOR_SIZE,
        )


def test_missing_qdrant_vector_size_fails() -> None:
    with pytest.raises(ValidationError):
        DocumentVectorIndexRuntimeSettings(
            _env_file=None,
            document_embedding_model=SENTINEL_DOCUMENT_EMBEDDING_MODEL,
            qdrant_collection_name=SENTINEL_COLLECTION_NAME,
        )


def test_blank_document_embedding_model_fails() -> None:
    with pytest.raises(ValidationError):
        _settings(document_embedding_model="")


def test_whitespace_only_document_embedding_model_fails() -> None:
    with pytest.raises(ValidationError):
        _settings(document_embedding_model="   ")
    with pytest.raises(ValidationError):
        _settings(document_embedding_model="\t\n")


def test_blank_qdrant_collection_name_fails() -> None:
    with pytest.raises(ValidationError):
        _settings(qdrant_collection_name="")


def test_whitespace_only_qdrant_collection_name_fails() -> None:
    with pytest.raises(ValidationError):
        _settings(qdrant_collection_name="   ")
    with pytest.raises(ValidationError):
        _settings(qdrant_collection_name="\t\n")


def test_vector_size_zero_fails() -> None:
    with pytest.raises(ValidationError):
        _settings(qdrant_vector_size=0)


def test_negative_vector_size_fails() -> None:
    with pytest.raises(ValidationError):
        _settings(qdrant_vector_size=-1)


def test_valid_positive_vector_size_passes() -> None:
    settings = _settings(qdrant_vector_size=1)
    assert settings.qdrant_vector_size == 1
    settings = _settings(qdrant_vector_size=32)
    assert settings.qdrant_vector_size == 32


def test_model_and_collection_strings_are_stripped() -> None:
    settings = _settings(
        document_embedding_model=f"  {SENTINEL_DOCUMENT_EMBEDDING_MODEL}  ",
        qdrant_collection_name=f"  {SENTINEL_COLLECTION_NAME}  ",
    )
    assert settings.document_embedding_model == SENTINEL_DOCUMENT_EMBEDDING_MODEL
    assert settings.qdrant_collection_name == SENTINEL_COLLECTION_NAME


def test_loader_reads_exact_energy_document_index_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "ENERGY_DOCUMENT_INDEX_DOCUMENT_EMBEDDING_MODEL",
        SENTINEL_DOCUMENT_EMBEDDING_MODEL,
    )
    monkeypatch.setenv("ENERGY_DOCUMENT_INDEX_QDRANT_COLLECTION_NAME", SENTINEL_COLLECTION_NAME)
    monkeypatch.setenv("ENERGY_DOCUMENT_INDEX_QDRANT_VECTOR_SIZE", str(SENTINEL_VECTOR_SIZE))
    settings = load_document_vector_index_runtime_settings(env_file=None)
    assert settings.document_embedding_model == SENTINEL_DOCUMENT_EMBEDDING_MODEL
    assert settings.qdrant_collection_name == SENTINEL_COLLECTION_NAME
    assert settings.qdrant_vector_size == SENTINEL_VECTOR_SIZE


def test_loader_does_not_require_openai_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENERGY_OPENAI_API_KEY", raising=False)
    monkeypatch.setenv(
        "ENERGY_DOCUMENT_INDEX_DOCUMENT_EMBEDDING_MODEL",
        SENTINEL_DOCUMENT_EMBEDDING_MODEL,
    )
    monkeypatch.setenv("ENERGY_DOCUMENT_INDEX_QDRANT_COLLECTION_NAME", SENTINEL_COLLECTION_NAME)
    monkeypatch.setenv("ENERGY_DOCUMENT_INDEX_QDRANT_VECTOR_SIZE", str(SENTINEL_VECTOR_SIZE))
    settings = load_document_vector_index_runtime_settings(env_file=None)
    assert settings.document_embedding_model == SENTINEL_DOCUMENT_EMBEDDING_MODEL
    with pytest.raises(ValidationError):
        load_openai_settings(env_file=None)


def test_loader_does_not_require_qdrant_connection_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("QDRANT_HOST", raising=False)
    monkeypatch.delenv("QDRANT_API_KEY", raising=False)
    monkeypatch.setenv(
        "ENERGY_DOCUMENT_INDEX_DOCUMENT_EMBEDDING_MODEL",
        SENTINEL_DOCUMENT_EMBEDDING_MODEL,
    )
    monkeypatch.setenv("ENERGY_DOCUMENT_INDEX_QDRANT_COLLECTION_NAME", SENTINEL_COLLECTION_NAME)
    monkeypatch.setenv("ENERGY_DOCUMENT_INDEX_QDRANT_VECTOR_SIZE", str(SENTINEL_VECTOR_SIZE))
    settings = load_document_vector_index_runtime_settings(env_file=None)
    assert settings.qdrant_collection_name == SENTINEL_COLLECTION_NAME
    with pytest.raises(ValidationError):
        load_qdrant_settings(env_file=None)


def test_loader_does_not_require_regulatory_intelligence_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ENERGY_REGULATORY_QUERY_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("ENERGY_REGULATORY_CONSTRAINT_INFERENCE_MODEL", raising=False)
    monkeypatch.delenv("ENERGY_REGULATORY_QDRANT_COLLECTION_NAME", raising=False)
    monkeypatch.delenv("ENERGY_REGULATORY_QDRANT_VECTOR_SIZE", raising=False)
    monkeypatch.setenv(
        "ENERGY_DOCUMENT_INDEX_DOCUMENT_EMBEDDING_MODEL",
        SENTINEL_DOCUMENT_EMBEDDING_MODEL,
    )
    monkeypatch.setenv("ENERGY_DOCUMENT_INDEX_QDRANT_COLLECTION_NAME", SENTINEL_COLLECTION_NAME)
    monkeypatch.setenv("ENERGY_DOCUMENT_INDEX_QDRANT_VECTOR_SIZE", str(SENTINEL_VECTOR_SIZE))
    settings = load_document_vector_index_runtime_settings(env_file=None)
    assert settings.document_embedding_model == SENTINEL_DOCUMENT_EMBEDDING_MODEL
    with pytest.raises(ValidationError):
        load_regulatory_intelligence_runtime_settings(env_file=None)


def test_env_file_none_isolates_local_env(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "ENERGY_DOCUMENT_INDEX_DOCUMENT_EMBEDDING_MODEL=from-local-env-file-model",
                "ENERGY_DOCUMENT_INDEX_QDRANT_COLLECTION_NAME=from-local-env-file-collection",
                "ENERGY_DOCUMENT_INDEX_QDRANT_VECTOR_SIZE=99",
            ]
        ),
        encoding="utf-8",
    )
    settings = DocumentVectorIndexRuntimeSettings(
        document_embedding_model=SENTINEL_DOCUMENT_EMBEDDING_MODEL,
        qdrant_collection_name=SENTINEL_COLLECTION_NAME,
        qdrant_vector_size=SENTINEL_VECTOR_SIZE,
        _env_file=None,
    )
    assert settings.document_embedding_model == SENTINEL_DOCUMENT_EMBEDDING_MODEL
    assert settings.qdrant_collection_name == SENTINEL_COLLECTION_NAME
    assert settings.qdrant_vector_size == SENTINEL_VECTOR_SIZE
    assert "from-local-env-file-model" not in repr(settings)
    assert "from-local-env-file-collection" not in repr(settings)


def test_loader_missing_required_environment_values_fails() -> None:
    with pytest.raises(ValidationError):
        load_document_vector_index_runtime_settings(env_file=None)


def test_loader_invalid_vector_size_environment_value_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "ENERGY_DOCUMENT_INDEX_DOCUMENT_EMBEDDING_MODEL",
        SENTINEL_DOCUMENT_EMBEDDING_MODEL,
    )
    monkeypatch.setenv("ENERGY_DOCUMENT_INDEX_QDRANT_COLLECTION_NAME", SENTINEL_COLLECTION_NAME)
    monkeypatch.setenv("ENERGY_DOCUMENT_INDEX_QDRANT_VECTOR_SIZE", "not-an-integer")
    with pytest.raises(ValidationError):
        load_document_vector_index_runtime_settings(env_file=None)


def test_loader_zero_vector_size_environment_value_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "ENERGY_DOCUMENT_INDEX_DOCUMENT_EMBEDDING_MODEL",
        SENTINEL_DOCUMENT_EMBEDDING_MODEL,
    )
    monkeypatch.setenv("ENERGY_DOCUMENT_INDEX_QDRANT_COLLECTION_NAME", SENTINEL_COLLECTION_NAME)
    monkeypatch.setenv("ENERGY_DOCUMENT_INDEX_QDRANT_VECTOR_SIZE", "0")
    with pytest.raises(ValidationError):
        load_document_vector_index_runtime_settings(env_file=None)


def test_settings_are_separate_from_app_settings() -> None:
    app_settings = load_settings(env_file=None)
    assert type(app_settings).__name__ == "AppSettings"
    assert not hasattr(app_settings, "document_embedding_model")
    assert not hasattr(app_settings, "qdrant_collection_name")
    assert not hasattr(app_settings, "qdrant_vector_size")
    settings = _settings()
    assert type(settings).__name__ == "DocumentVectorIndexRuntimeSettings"
    assert type(settings) is not type(app_settings)


def test_settings_are_separate_from_openai_settings() -> None:
    assert "document_embedding_model" not in OpenAISettings.model_fields
    assert "api_key" not in DocumentVectorIndexRuntimeSettings.model_fields
    with pytest.raises(ValidationError):
        load_openai_settings(env_file=None)


def test_settings_are_separate_from_qdrant_connection_settings() -> None:
    assert "host" not in DocumentVectorIndexRuntimeSettings.model_fields
    assert "port" not in DocumentVectorIndexRuntimeSettings.model_fields
    assert "api_key" not in DocumentVectorIndexRuntimeSettings.model_fields
    assert "https" not in DocumentVectorIndexRuntimeSettings.model_fields
    assert "timeout_seconds" not in DocumentVectorIndexRuntimeSettings.model_fields
    assert "qdrant_collection_name" not in QdrantSettings.model_fields
    assert "qdrant_vector_size" not in QdrantSettings.model_fields
    with pytest.raises(ValidationError):
        load_qdrant_settings(env_file=None)


def test_settings_are_separate_from_regulatory_runtime_settings() -> None:
    assert "query_embedding_model" not in DocumentVectorIndexRuntimeSettings.model_fields
    assert "constraint_inference_model" not in DocumentVectorIndexRuntimeSettings.model_fields
    assert "document_embedding_model" not in RegulatoryIntelligenceRuntimeSettings.model_fields
    with pytest.raises(ValidationError):
        load_regulatory_intelligence_runtime_settings(env_file=None)


def test_no_secret_or_api_key_field_exists() -> None:
    fields = DocumentVectorIndexRuntimeSettings.model_fields
    assert "api_key" not in fields
    assert "password" not in fields
    assert "secret" not in fields
    settings = _settings()
    assert not hasattr(settings, "api_key")
    assert "SecretStr" not in type(settings.document_embedding_model).__name__


def test_no_provider_client_field_exists() -> None:
    fields = DocumentVectorIndexRuntimeSettings.model_fields
    assert "openai_client" not in fields
    assert "qdrant_client" not in fields
    assert "client" not in fields
    settings = _settings()
    assert not hasattr(settings, "openai_client")
    assert not hasattr(settings, "qdrant_client")


def test_no_query_inference_retry_prompt_or_lifecycle_fields_exist() -> None:
    fields = DocumentVectorIndexRuntimeSettings.model_fields
    forbidden = {
        "query_embedding_model",
        "constraint_inference_model",
        "prompt",
        "prompts",
        "retry",
        "retries",
        "max_retries",
        "timeout",
        "lifespan",
        "lifecycle",
        "base_url",
        "organization",
        "adapter",
        "catalog",
    }
    leaked = sorted(name for name in forbidden if name in fields)
    assert leaked == []


def test_valid_settings_feed_qdrant_document_vector_config_without_transformation() -> None:
    settings = _settings()
    config = QdrantDocumentVectorConfig(
        collection_name=settings.qdrant_collection_name,
        vector_size=settings.qdrant_vector_size,
    )
    assert config.collection_name == settings.qdrant_collection_name
    assert config.vector_size == settings.qdrant_vector_size


def test_settings_module_does_not_import_sdks_or_infrastructure() -> None:
    settings_path = SRC_ROOT / "energy_trading" / "shared" / "config" / "document_vector_index.py"
    modules = imported_modules(settings_path)
    assert "openai" not in modules
    assert "qdrant_client" not in modules
    assert "energy_trading.infrastructure" not in modules
    assert "energy_trading.application" not in modules
    assert "energy_trading.api" not in modules
    settings = _settings()
    assert settings.qdrant_vector_size == SENTINEL_VECTOR_SIZE
