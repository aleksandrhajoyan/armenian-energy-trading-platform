"""Regulatory Intelligence runtime composition root wires published application objects."""

from __future__ import annotations

import inspect
from typing import cast

import pytest

from energy_trading.api.composition import build_regulatory_intelligence_query_execution
from energy_trading.application.agents.regulatory_intelligence import (
    RegulatoryIntelligenceAgent,
    RegulatoryIntelligenceResult,
)
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration import (
    DocumentVectorSearchQueryPreparationService,
    RegulatoryIntelligenceQueryExecutionService,
)
from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk
from energy_trading.application.ports.document_query_embedding import (
    DocumentQueryEmbedding,
    DocumentQueryEmbeddingPort,
)
from energy_trading.application.ports.document_vector_search import (
    DocumentVectorSearchPort,
    DocumentVectorSearchQuery,
)
from energy_trading.application.ports.regulatory_constraint_inference import (
    RegulatoryConstraintInferencePort,
)
from energy_trading.domain.models.regulatory import RegulatoryConstraint
from tests.unit.domain._factories import constraint

_SENTINEL_VECTOR: tuple[float, ...] = (1.0, 0.0, -0.25)
_UNAVAILABLE_MESSAGE = "Document query embedding is unavailable."


class _FakeDocumentQueryEmbedder:
    """Test-only fake that structurally satisfies ``DocumentQueryEmbeddingPort``."""

    def __init__(
        self,
        *,
        vector: tuple[float, ...] = _SENTINEL_VECTOR,
        error: Exception | None = None,
    ) -> None:
        self._vector = vector
        self.error = error
        self.calls: list[str] = []
        self.received_query_text: str | None = None

    async def embed_query(self, query_text: str) -> DocumentQueryEmbedding:
        self.calls.append(query_text)
        self.received_query_text = query_text
        if self.error is not None:
            raise self.error
        return DocumentQueryEmbedding(vector=self._vector)


class _FakeDocumentVectorSearch:
    """Test-only search fake. Not a production adapter."""

    def __init__(
        self,
        chunks: tuple[ExtractedDocumentChunk, ...] = (),
        *,
        error: Exception | None = None,
    ) -> None:
        self.chunks = chunks
        self.error = error
        self.calls: list[DocumentVectorSearchQuery] = []

    async def search(
        self,
        query: DocumentVectorSearchQuery,
    ) -> tuple[ExtractedDocumentChunk, ...]:
        self.calls.append(query)
        if self.error is not None:
            raise self.error
        return self.chunks


class _FakeRegulatoryConstraintInference:
    """Test-only inference fake. Not a production adapter."""

    def __init__(
        self,
        constraints: tuple[RegulatoryConstraint, ...] = (),
        *,
        error: Exception | None = None,
    ) -> None:
        self.constraints = constraints
        self.error = error
        self.calls: list[tuple[ExtractedDocumentChunk, ...]] = []

    async def infer(
        self,
        *,
        chunks: tuple[ExtractedDocumentChunk, ...],
    ) -> tuple[RegulatoryConstraint, ...]:
        self.calls.append(chunks)
        if self.error is not None:
            raise self.error
        return self.constraints


def _chunk(**overrides: object) -> ExtractedDocumentChunk:
    values: dict[str, object] = {
        "document_id": "doc-1",
        "chunk_id": "chunk-1",
        "ordinal": 0,
        "text": "Normalized extracted regulatory text.",
        "page_number": 1,
    }
    values.update(overrides)
    return ExtractedDocumentChunk(**values)  # type: ignore[arg-type]


def _build(
    embedder: _FakeDocumentQueryEmbedder,
    search: _FakeDocumentVectorSearch,
    inference: _FakeRegulatoryConstraintInference,
) -> RegulatoryIntelligenceQueryExecutionService:
    return build_regulatory_intelligence_query_execution(
        document_query_embedding_port=cast(DocumentQueryEmbeddingPort, embedder),
        document_vector_search_port=cast(DocumentVectorSearchPort, search),
        regulatory_constraint_inference_port=cast(RegulatoryConstraintInferencePort, inference),
    )


def test_builder_signature_is_keyword_only_three_application_ports() -> None:
    signature = inspect.signature(build_regulatory_intelligence_query_execution)
    assert tuple(signature.parameters) == (
        "document_query_embedding_port",
        "document_vector_search_port",
        "regulatory_constraint_inference_port",
    )
    for name in signature.parameters:
        parameter = signature.parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert (
        signature.parameters["document_query_embedding_port"].annotation
        is DocumentQueryEmbeddingPort
    )
    assert (
        signature.parameters["document_vector_search_port"].annotation is DocumentVectorSearchPort
    )
    assert (
        signature.parameters["regulatory_constraint_inference_port"].annotation
        is RegulatoryConstraintInferencePort
    )
    assert signature.return_annotation is RegulatoryIntelligenceQueryExecutionService
    assert not inspect.iscoroutinefunction(build_regulatory_intelligence_query_execution)


def test_builder_accepts_structural_port_fakes_and_returns_execution_service() -> None:
    service = _build(
        _FakeDocumentQueryEmbedder(),
        _FakeDocumentVectorSearch(),
        _FakeRegulatoryConstraintInference(),
    )
    assert isinstance(service, RegulatoryIntelligenceQueryExecutionService)


def test_builder_wires_real_application_objects_to_the_supplied_ports() -> None:
    embedder = _FakeDocumentQueryEmbedder()
    search = _FakeDocumentVectorSearch()
    inference = _FakeRegulatoryConstraintInference()
    service = _build(embedder, search, inference)

    preparation = service._query_preparation_service
    agent = service._regulatory_intelligence_agent
    assert isinstance(preparation, DocumentVectorSearchQueryPreparationService)
    assert isinstance(agent, RegulatoryIntelligenceAgent)
    assert preparation._document_query_embedding_port is embedder
    assert agent._search is search
    assert agent._inference is inference


def test_builder_does_not_invoke_ports_or_application_runtime() -> None:
    embedder = _FakeDocumentQueryEmbedder()
    search = _FakeDocumentVectorSearch(chunks=(_chunk(),))
    inference = _FakeRegulatoryConstraintInference(constraints=(constraint(),))

    _build(embedder, search, inference)

    assert embedder.calls == []
    assert embedder.received_query_text is None
    assert search.calls == []
    assert inference.calls == []


async def test_built_service_runs_query_text_through_real_application_stack() -> None:
    query_text = "  keep surrounding spaces  "
    vector = (0.5, -1.0, 2.25)
    limit = 4
    chunk = _chunk()
    expected_constraint = constraint(constraint_id="composed-1")
    embedder = _FakeDocumentQueryEmbedder(vector=vector)
    search = _FakeDocumentVectorSearch(chunks=(chunk,))
    inference = _FakeRegulatoryConstraintInference(constraints=(expected_constraint,))
    service = _build(embedder, search, inference)

    result = await service.execute(query_text=query_text, limit=limit)

    assert embedder.calls == [query_text]
    assert embedder.received_query_text is query_text
    assert embedder.received_query_text != query_text.strip()
    assert len(search.calls) == 1
    assert search.calls[0].vector == vector
    assert search.calls[0].limit == limit
    assert inference.calls == [(chunk,)]
    assert inference.calls[0][0] is chunk
    assert result.constraints == (expected_constraint,)
    assert result.constraints[0] is expected_constraint
    assert isinstance(result, RegulatoryIntelligenceResult)


async def test_built_service_empty_retrieval_skips_inference() -> None:
    embedder = _FakeDocumentQueryEmbedder()
    search = _FakeDocumentVectorSearch(chunks=())
    inference = _FakeRegulatoryConstraintInference(
        constraints=(constraint(constraint_id="must-not-appear"),)
    )
    service = _build(embedder, search, inference)

    result = await service.execute(query_text="no evidence query", limit=3)

    assert embedder.calls == ["no evidence query"]
    assert len(search.calls) == 1
    assert inference.calls == []
    assert result.constraints == ()
    assert isinstance(result, RegulatoryIntelligenceResult)


async def test_built_service_propagates_embedding_failure_unchanged() -> None:
    error = DependencyUnavailableError(_UNAVAILABLE_MESSAGE)
    embedder = _FakeDocumentQueryEmbedder(error=error)
    search = _FakeDocumentVectorSearch(chunks=(_chunk(),))
    inference = _FakeRegulatoryConstraintInference(constraints=(constraint(),))
    service = _build(embedder, search, inference)

    with pytest.raises(DependencyUnavailableError) as caught:
        await service.execute(query_text="Confidential regulatory search query.", limit=5)

    assert caught.value is error
    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert embedder.calls == ["Confidential regulatory search query."]
    assert search.calls == []
    assert inference.calls == []
