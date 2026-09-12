"""Unit tests for explicit Qdrant document-vector distance settings.

These tests must not require a running Qdrant server, Docker, or a local ``.env``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from qdrant_client.http.models import Distance

from energy_trading.shared.config.qdrant import (
    QdrantDocumentVectorDistance,
    QdrantDocumentVectorDistanceSettings,
    QdrantSettings,
    load_qdrant_document_vector_distance_settings,
    load_qdrant_settings,
)
from tests.architecture.import_inspection import SRC_ROOT, imported_modules, imported_names

_DISTANCE_ENV_KEY = "QDRANT_DOCUMENT_VECTOR_DISTANCE"
_CANONICAL = (
    QdrantDocumentVectorDistance.COSINE,
    QdrantDocumentVectorDistance.DOT,
    QdrantDocumentVectorDistance.EUCLID,
    QdrantDocumentVectorDistance.MANHATTAN,
)
_INVALID = (
    "banana",
    "auto",
    "default",
    "cos",
    "euclidean",
    "",
    "COSINE",
    "Dot",
    "inner-product",
    "ip",
    "l2",
)


@pytest.fixture(autouse=True)
def clear_distance_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_DISTANCE_ENV_KEY, raising=False)
    monkeypatch.delenv("QDRANT_HOST", raising=False)


def test_canonical_values_are_accepted() -> None:
    for value in _CANONICAL:
        settings = QdrantDocumentVectorDistanceSettings(
            _env_file=None,
            document_vector_distance=value.value,
        )
        assert settings.document_vector_distance is value
        assert settings.document_vector_distance.value == value.value


def test_enum_members_are_accepted() -> None:
    for member in _CANONICAL:
        settings = QdrantDocumentVectorDistanceSettings(
            _env_file=None,
            document_vector_distance=member,
        )
        assert settings.document_vector_distance is member


def test_distance_is_required() -> None:
    with pytest.raises(ValidationError):
        QdrantDocumentVectorDistanceSettings(_env_file=None)


def test_no_implicit_default_on_field() -> None:
    field = QdrantDocumentVectorDistanceSettings.model_fields["document_vector_distance"]
    assert field.is_required()


@pytest.mark.parametrize("value", _INVALID)
def test_invalid_values_fail_validation(value: str) -> None:
    with pytest.raises(ValidationError):
        QdrantDocumentVectorDistanceSettings(
            _env_file=None,
            document_vector_distance=value,
        )


def test_whitespace_is_stripped_for_canonical_value() -> None:
    settings = QdrantDocumentVectorDistanceSettings(
        _env_file=None,
        document_vector_distance="  cosine  ",
    )
    assert settings.document_vector_distance is QdrantDocumentVectorDistance.COSINE


def test_whitespace_only_fails() -> None:
    with pytest.raises(ValidationError):
        QdrantDocumentVectorDistanceSettings(
            _env_file=None,
            document_vector_distance="   ",
        )


def test_load_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_DISTANCE_ENV_KEY, "dot")
    settings = load_qdrant_document_vector_distance_settings(env_file=None)
    assert settings.document_vector_distance is QdrantDocumentVectorDistance.DOT


def test_load_requires_environment_value() -> None:
    with pytest.raises(ValidationError):
        load_qdrant_document_vector_distance_settings(env_file=None)


def test_local_env_file_does_not_contaminate_explicit_settings(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("QDRANT_DOCUMENT_VECTOR_DISTANCE=manhattan\n", encoding="utf-8")
    settings = QdrantDocumentVectorDistanceSettings(
        document_vector_distance="euclid",
        _env_file=None,
    )
    assert settings.document_vector_distance is QdrantDocumentVectorDistance.EUCLID


def test_connection_settings_do_not_require_distance() -> None:
    settings = QdrantSettings(_env_file=None, host="localhost")
    assert settings.host == "localhost"
    assert "document_vector_distance" not in QdrantSettings.model_fields


def test_connection_settings_ignore_distance_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QDRANT_HOST", "vectors.internal")
    monkeypatch.setenv(_DISTANCE_ENV_KEY, "cosine")
    settings = load_qdrant_settings(env_file=None)
    assert settings.host == "vectors.internal"
    assert not hasattr(settings, "document_vector_distance")


def test_configured_value_is_not_a_qdrant_sdk_enum() -> None:
    settings = QdrantDocumentVectorDistanceSettings(
        _env_file=None,
        document_vector_distance="manhattan",
    )
    assert type(settings.document_vector_distance) is QdrantDocumentVectorDistance
    assert not isinstance(settings.document_vector_distance, Distance)


def test_settings_module_does_not_import_qdrant_sdk() -> None:
    module = SRC_ROOT / "energy_trading" / "shared" / "config" / "qdrant.py"
    names = imported_names(module)
    modules = imported_modules(module)
    assert "qdrant_client" not in names
    assert "Distance" not in names
    assert "AsyncQdrantClient" not in names
    assert "qdrant_client" not in modules
    assert "qdrant_client.http.models" not in modules
