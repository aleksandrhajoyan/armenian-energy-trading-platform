"""Unit tests for typed Regulatory Intelligence runtime settings.

These tests must not require live providers, Docker, or a local ``.env``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
)
from energy_trading.shared.config.openai import OpenAISettings, load_openai_settings
from energy_trading.shared.config.qdrant import QdrantSettings, load_qdrant_settings
from energy_trading.shared.config.regulatory_intelligence import (
    RegulatoryIntelligenceRuntimeSettings,
    load_regulatory_intelligence_runtime_settings,
)
from energy_trading.shared.config.settings import load_settings
from tests.architecture.import_inspection import SRC_ROOT, imported_modules

SENTINEL_QUERY_EMBEDDING_MODEL = "sentinel-query-embedding-model-chunk72"
SENTINEL_CONSTRAINT_INFERENCE_MODEL = "sentinel-constraint-inference-model-chunk72"
SENTINEL_COLLECTION_NAME = "sentinel-regulatory-collection-chunk72"
SENTINEL_VECTOR_SIZE = 8

_EXPECTED_FIELDS = frozenset(
    {
        "query_embedding_model",
        "constraint_inference_model",
        "qdrant_collection_name",
        "qdrant_vector_size",
    }
)

_REGULATORY_ENV_KEYS = (
    "ENERGY_REGULATORY_QUERY_EMBEDDING_MODEL",
    "ENERGY_REGULATORY_CONSTRAINT_INFERENCE_MODEL",
    "ENERGY_REGULATORY_QDRANT_COLLECTION_NAME",
    "ENERGY_REGULATORY_QDRANT_VECTOR_SIZE",
)


@pytest.fixture(autouse=True)
def clear_regulatory_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _REGULATORY_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _settings(**overrides: object) -> RegulatoryIntelligenceRuntimeSettings:
    payload: dict[str, object] = {
        "query_embedding_model": SENTINEL_QUERY_EMBEDDING_MODEL,
        "constraint_inference_model": SENTINEL_CONSTRAINT_INFERENCE_MODEL,
        "qdrant_collection_name": SENTINEL_COLLECTION_NAME,
        "qdrant_vector_size": SENTINEL_VECTOR_SIZE,
    }
    payload.update(overrides)
    return RegulatoryIntelligenceRuntimeSettings(_env_file=None, **payload)


def test_valid_explicit_construction() -> None:
    settings = _settings()
    assert settings.query_embedding_model == SENTINEL_QUERY_EMBEDDING_MODEL
    assert settings.constraint_inference_model == SENTINEL_CONSTRAINT_INFERENCE_MODEL
    assert settings.qdrant_collection_name == SENTINEL_COLLECTION_NAME
    assert settings.qdrant_vector_size == SENTINEL_VECTOR_SIZE


def test_exactly_four_production_fields() -> None:
    assert set(RegulatoryIntelligenceRuntimeSettings.model_fields) == _EXPECTED_FIELDS


def test_missing_query_embedding_model_fails() -> None:
    with pytest.raises(ValidationError):
        RegulatoryIntelligenceRuntimeSettings(
            _env_file=None,
            constraint_inference_model=SENTINEL_CONSTRAINT_INFERENCE_MODEL,
            qdrant_collection_name=SENTINEL_COLLECTION_NAME,
            qdrant_vector_size=SENTINEL_VECTOR_SIZE,
        )


def test_missing_constraint_inference_model_fails() -> None:
    with pytest.raises(ValidationError):
        RegulatoryIntelligenceRuntimeSettings(
            _env_file=None,
            query_embedding_model=SENTINEL_QUERY_EMBEDDING_MODEL,
            qdrant_collection_name=SENTINEL_COLLECTION_NAME,
            qdrant_vector_size=SENTINEL_VECTOR_SIZE,
        )


def test_missing_qdrant_collection_name_fails() -> None:
    with pytest.raises(ValidationError):
        RegulatoryIntelligenceRuntimeSettings(
            _env_file=None,
            query_embedding_model=SENTINEL_QUERY_EMBEDDING_MODEL,
            constraint_inference_model=SENTINEL_CONSTRAINT_INFERENCE_MODEL,
            qdrant_vector_size=SENTINEL_VECTOR_SIZE,
        )


def test_missing_qdrant_vector_size_fails() -> None:
    with pytest.raises(ValidationError):
        RegulatoryIntelligenceRuntimeSettings(
            _env_file=None,
            query_embedding_model=SENTINEL_QUERY_EMBEDDING_MODEL,
            constraint_inference_model=SENTINEL_CONSTRAINT_INFERENCE_MODEL,
            qdrant_collection_name=SENTINEL_COLLECTION_NAME,
        )


def test_blank_query_embedding_model_fails() -> None:
    with pytest.raises(ValidationError):
        _settings(query_embedding_model="")


def test_whitespace_only_query_embedding_model_fails() -> None:
    with pytest.raises(ValidationError):
        _settings(query_embedding_model="   ")
    with pytest.raises(ValidationError):
        _settings(query_embedding_model="\t\n")


def test_blank_constraint_inference_model_fails() -> None:
    with pytest.raises(ValidationError):
        _settings(constraint_inference_model="")


def test_whitespace_only_constraint_inference_model_fails() -> None:
    with pytest.raises(ValidationError):
        _settings(constraint_inference_model="   ")
    with pytest.raises(ValidationError):
        _settings(constraint_inference_model="\t\n")


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
        query_embedding_model=f"  {SENTINEL_QUERY_EMBEDDING_MODEL}  ",
        constraint_inference_model=f"  {SENTINEL_CONSTRAINT_INFERENCE_MODEL}  ",
        qdrant_collection_name=f"  {SENTINEL_COLLECTION_NAME}  ",
    )
    assert settings.query_embedding_model == SENTINEL_QUERY_EMBEDDING_MODEL
    assert settings.constraint_inference_model == SENTINEL_CONSTRAINT_INFERENCE_MODEL
    assert settings.qdrant_collection_name == SENTINEL_COLLECTION_NAME


def test_identical_model_strings_are_allowed() -> None:
    settings = _settings(
        query_embedding_model=SENTINEL_QUERY_EMBEDDING_MODEL,
        constraint_inference_model=SENTINEL_QUERY_EMBEDDING_MODEL,
    )
    assert settings.query_embedding_model == SENTINEL_QUERY_EMBEDDING_MODEL
    assert settings.constraint_inference_model == SENTINEL_QUERY_EMBEDDING_MODEL


def test_loader_reads_exact_energy_regulatory_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENERGY_REGULATORY_QUERY_EMBEDDING_MODEL", SENTINEL_QUERY_EMBEDDING_MODEL)
    monkeypatch.setenv(
        "ENERGY_REGULATORY_CONSTRAINT_INFERENCE_MODEL",
        SENTINEL_CONSTRAINT_INFERENCE_MODEL,
    )
    monkeypatch.setenv("ENERGY_REGULATORY_QDRANT_COLLECTION_NAME", SENTINEL_COLLECTION_NAME)
    monkeypatch.setenv("ENERGY_REGULATORY_QDRANT_VECTOR_SIZE", str(SENTINEL_VECTOR_SIZE))
    settings = load_regulatory_intelligence_runtime_settings(env_file=None)
    assert settings.query_embedding_model == SENTINEL_QUERY_EMBEDDING_MODEL
    assert settings.constraint_inference_model == SENTINEL_CONSTRAINT_INFERENCE_MODEL
    assert settings.qdrant_collection_name == SENTINEL_COLLECTION_NAME
    assert settings.qdrant_vector_size == SENTINEL_VECTOR_SIZE


def test_env_file_none_isolates_local_env(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "ENERGY_REGULATORY_QUERY_EMBEDDING_MODEL=from-local-env-file-model",
                "ENERGY_REGULATORY_CONSTRAINT_INFERENCE_MODEL=from-local-env-file-inference",
                "ENERGY_REGULATORY_QDRANT_COLLECTION_NAME=from-local-env-file-collection",
                "ENERGY_REGULATORY_QDRANT_VECTOR_SIZE=99",
            ]
        ),
        encoding="utf-8",
    )
    settings = RegulatoryIntelligenceRuntimeSettings(
        query_embedding_model=SENTINEL_QUERY_EMBEDDING_MODEL,
        constraint_inference_model=SENTINEL_CONSTRAINT_INFERENCE_MODEL,
        qdrant_collection_name=SENTINEL_COLLECTION_NAME,
        qdrant_vector_size=SENTINEL_VECTOR_SIZE,
        _env_file=None,
    )
    assert settings.query_embedding_model == SENTINEL_QUERY_EMBEDDING_MODEL
    assert settings.constraint_inference_model == SENTINEL_CONSTRAINT_INFERENCE_MODEL
    assert settings.qdrant_collection_name == SENTINEL_COLLECTION_NAME
    assert settings.qdrant_vector_size == SENTINEL_VECTOR_SIZE
    assert "from-local-env-file-model" not in repr(settings)
    assert "from-local-env-file-collection" not in repr(settings)


def test_settings_are_separate_from_app_settings() -> None:
    app_settings = load_settings(env_file=None)
    assert type(app_settings).__name__ == "AppSettings"
    assert not hasattr(app_settings, "query_embedding_model")
    assert not hasattr(app_settings, "constraint_inference_model")
    assert not hasattr(app_settings, "qdrant_collection_name")
    assert not hasattr(app_settings, "qdrant_vector_size")
    settings = _settings()
    assert type(settings).__name__ == "RegulatoryIntelligenceRuntimeSettings"
    assert type(settings) is not type(app_settings)


def test_settings_are_separate_from_openai_settings() -> None:
    assert "query_embedding_model" not in OpenAISettings.model_fields
    assert "constraint_inference_model" not in OpenAISettings.model_fields
    assert "api_key" not in RegulatoryIntelligenceRuntimeSettings.model_fields
    with pytest.raises(ValidationError):
        load_openai_settings(env_file=None)


def test_settings_are_separate_from_qdrant_connection_settings() -> None:
    assert "host" not in RegulatoryIntelligenceRuntimeSettings.model_fields
    assert "port" not in RegulatoryIntelligenceRuntimeSettings.model_fields
    assert "api_key" not in RegulatoryIntelligenceRuntimeSettings.model_fields
    assert "https" not in RegulatoryIntelligenceRuntimeSettings.model_fields
    assert "timeout_seconds" not in RegulatoryIntelligenceRuntimeSettings.model_fields
    assert "qdrant_collection_name" not in QdrantSettings.model_fields
    assert "qdrant_vector_size" not in QdrantSettings.model_fields
    with pytest.raises(ValidationError):
        load_qdrant_settings(env_file=None)


def test_no_secret_or_api_key_field_exists() -> None:
    fields = RegulatoryIntelligenceRuntimeSettings.model_fields
    assert "api_key" not in fields
    assert "password" not in fields
    assert "secret" not in fields
    settings = _settings()
    assert not hasattr(settings, "api_key")
    assert "SecretStr" not in type(settings.query_embedding_model).__name__


def test_no_provider_client_field_exists() -> None:
    fields = RegulatoryIntelligenceRuntimeSettings.model_fields
    assert "openai_client" not in fields
    assert "qdrant_client" not in fields
    assert "client" not in fields
    settings = _settings()
    assert not hasattr(settings, "openai_client")
    assert not hasattr(settings, "qdrant_client")


def test_no_retry_prompt_or_lifecycle_fields_exist() -> None:
    fields = RegulatoryIntelligenceRuntimeSettings.model_fields
    forbidden = {
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
    settings_path = SRC_ROOT / "energy_trading" / "shared" / "config" / "regulatory_intelligence.py"
    modules = imported_modules(settings_path)
    assert "openai" not in modules
    assert "qdrant_client" not in modules
    assert "energy_trading.infrastructure" not in modules
    assert "energy_trading.application" not in modules
    assert "energy_trading.api" not in modules
    settings = _settings()
    assert settings.qdrant_vector_size == SENTINEL_VECTOR_SIZE
