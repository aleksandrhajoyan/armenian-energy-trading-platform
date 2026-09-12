"""Unit tests for Qdrant document-vector distance mapping.

These tests must not require a running Qdrant server, Docker, or a local ``.env``.
"""

from __future__ import annotations

import inspect

import pytest
from qdrant_client.http.models import Distance

from energy_trading.api.composition.qdrant_document_vector_distance import (
    map_qdrant_document_vector_distance,
)
from energy_trading.shared.config.qdrant import QdrantDocumentVectorDistance

_EXPECTED = (
    (QdrantDocumentVectorDistance.COSINE, Distance.COSINE),
    (QdrantDocumentVectorDistance.DOT, Distance.DOT),
    (QdrantDocumentVectorDistance.EUCLID, Distance.EUCLID),
    (QdrantDocumentVectorDistance.MANHATTAN, Distance.MANHATTAN),
)


@pytest.mark.parametrize(("configured", "expected"), _EXPECTED)
def test_canonical_values_map_to_qdrant_distance(
    configured: QdrantDocumentVectorDistance,
    expected: Distance,
) -> None:
    assert map_qdrant_document_vector_distance(distance=configured) is expected


def test_mapping_is_total_over_the_configured_enum() -> None:
    mapped = {
        member: map_qdrant_document_vector_distance(distance=member)
        for member in QdrantDocumentVectorDistance
    }
    assert set(mapped) == set(QdrantDocumentVectorDistance)
    assert mapped[QdrantDocumentVectorDistance.COSINE] is Distance.COSINE
    assert mapped[QdrantDocumentVectorDistance.DOT] is Distance.DOT
    assert mapped[QdrantDocumentVectorDistance.EUCLID] is Distance.EUCLID
    assert mapped[QdrantDocumentVectorDistance.MANHATTAN] is Distance.MANHATTAN


def test_mapper_is_keyword_only_with_no_default() -> None:
    signature = inspect.signature(map_qdrant_document_vector_distance)
    assert list(signature.parameters) == ["distance"]
    parameter = signature.parameters["distance"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        map_qdrant_document_vector_distance()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        map_qdrant_document_vector_distance(QdrantDocumentVectorDistance.COSINE)  # type: ignore[misc]


def test_mapper_does_not_load_settings_or_invoke_collection_primitives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_load(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("mapper must not load settings")

    def fail_collection(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("mapper must not invoke collection primitives")

    monkeypatch.setattr(
        "energy_trading.shared.config.qdrant.load_qdrant_document_vector_distance_settings",
        fail_load,
    )
    monkeypatch.setattr(
        "energy_trading.shared.config.qdrant.load_qdrant_settings",
        fail_load,
    )
    monkeypatch.setattr(
        "energy_trading.infrastructure.vector_store.qdrant.collection_creation.create_qdrant_document_collection",
        fail_collection,
    )
    monkeypatch.setattr(
        "energy_trading.infrastructure.vector_store.qdrant.collection_readiness.verify_qdrant_document_collection_ready",
        fail_collection,
    )
    monkeypatch.setattr(
        "energy_trading.infrastructure.vector_store.qdrant.collection_ensure.ensure_qdrant_document_collection_ready",
        fail_collection,
    )
    assert (
        map_qdrant_document_vector_distance(distance=QdrantDocumentVectorDistance.DOT)
        is Distance.DOT
    )


def test_unsupported_value_fails_closed_without_selecting_a_metric() -> None:
    with pytest.raises(ValueError, match="Unsupported document vector distance"):
        map_qdrant_document_vector_distance(distance="banana")  # type: ignore[arg-type]
