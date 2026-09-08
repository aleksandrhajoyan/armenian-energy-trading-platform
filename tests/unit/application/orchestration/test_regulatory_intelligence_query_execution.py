"""Regulatory Intelligence query execution composes preparation with the agent."""

from __future__ import annotations

import inspect
from typing import cast

import pytest

from energy_trading.application.agents.regulatory_intelligence import (
    RegulatoryIntelligenceAgent,
    RegulatoryIntelligenceRequest,
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
_AGENT_UNAVAILABLE_MESSAGE = "Regulatory Intelligence is unavailable."


class _RecordingQueryPreparationService:
    """Test-only recorder. Not a production Protocol or abstraction."""

    def __init__(
        self,
        *,
        query: DocumentVectorSearchQuery | None = None,
        error: BaseException | None = None,
    ) -> None:
        self._query = query
        self._error = error
        self.calls: list[tuple[str, int]] = []
        self.received_query_text: str | None = None
        self.received_limit: int | None = None

    async def prepare(self, *, query_text: str, limit: int) -> DocumentVectorSearchQuery:
        self.calls.append((query_text, limit))
        self.received_query_text = query_text
        self.received_limit = limit
        if self._error is not None:
            raise self._error
        if self._query is None:
            msg = "recording preparation double must return a query"
            raise AssertionError(msg)
        return self._query


class _RecordingRegulatoryIntelligenceAgent:
    """Test-only recorder. Not a production Protocol or abstraction."""

    def __init__(
        self,
        *,
        result: RegulatoryIntelligenceResult | None = None,
        error: BaseException | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls: list[RegulatoryIntelligenceRequest] = []

    async def run(self, request: RegulatoryIntelligenceRequest) -> RegulatoryIntelligenceResult:
        self.calls.append(request)
        if self._error is not None:
            raise self._error
        if self._result is None:
            msg = "recording agent double must return a result"
            raise AssertionError(msg)
        return self._result


class _FakeDocumentQueryEmbedder:
    """Test-only fake that structurally satisfies ``DocumentQueryEmbeddingPort``."""

    def __init__(self, *, vector: tuple[float, ...] = _SENTINEL_VECTOR) -> None:
        self._vector = vector
        self.received_query_text: str | None = None

    async def embed_query(self, query_text: str) -> DocumentQueryEmbedding:
        self.received_query_text = query_text
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


def _query(**overrides: object) -> DocumentVectorSearchQuery:
    values: dict[str, object] = {
        "vector": _SENTINEL_VECTOR,
        "limit": 5,
    }
    values.update(overrides)
    return DocumentVectorSearchQuery(**values)  # type: ignore[arg-type]


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


def _execution_service(
    preparation: _RecordingQueryPreparationService,
    agent: _RecordingRegulatoryIntelligenceAgent,
) -> RegulatoryIntelligenceQueryExecutionService:
    return RegulatoryIntelligenceQueryExecutionService(
        cast(DocumentVectorSearchQueryPreparationService, preparation),
        cast(RegulatoryIntelligenceAgent, agent),
    )


def test_constructor_accepts_exactly_the_two_published_dependencies() -> None:
    signature = inspect.signature(RegulatoryIntelligenceQueryExecutionService.__init__)
    assert tuple(signature.parameters) == (
        "self",
        "query_preparation_service",
        "regulatory_intelligence_agent",
    )
    assert (
        signature.parameters["query_preparation_service"].annotation
        is DocumentVectorSearchQueryPreparationService
    )
    assert (
        signature.parameters["regulatory_intelligence_agent"].annotation
        is RegulatoryIntelligenceAgent
    )
    service = _execution_service(
        _RecordingQueryPreparationService(query=_query()),
        _RecordingRegulatoryIntelligenceAgent(result=RegulatoryIntelligenceResult(constraints=())),
    )
    assert isinstance(service, RegulatoryIntelligenceQueryExecutionService)


def test_execute_signature_is_keyword_only_query_text_and_limit() -> None:
    signature = inspect.signature(RegulatoryIntelligenceQueryExecutionService.execute)
    assert tuple(signature.parameters) == ("self", "query_text", "limit")
    assert signature.parameters["query_text"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["limit"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["query_text"].annotation is str
    assert signature.parameters["limit"].annotation is int
    assert signature.return_annotation is RegulatoryIntelligenceResult
    assert inspect.iscoroutinefunction(RegulatoryIntelligenceQueryExecutionService.execute)


async def test_query_text_and_limit_reach_prepare_unchanged() -> None:
    query_text = "  surrounding spaces are preserved  "
    limit = 7
    prepared = _query(vector=(0.25, -0.5), limit=limit)
    preparation = _RecordingQueryPreparationService(query=prepared)
    agent = _RecordingRegulatoryIntelligenceAgent(
        result=RegulatoryIntelligenceResult(constraints=())
    )
    service = _execution_service(preparation, agent)

    await service.execute(query_text=query_text, limit=limit)

    assert preparation.calls == [(query_text, limit)]
    assert preparation.received_query_text is query_text
    assert preparation.received_query_text != query_text.strip()
    assert preparation.received_limit == limit
    assert len(preparation.calls) == 1


async def test_agent_receives_request_with_exact_prepared_query() -> None:
    prepared = _query(vector=(0.5, -1.25, 2.0), limit=4)
    preparation = _RecordingQueryPreparationService(query=prepared)
    result = RegulatoryIntelligenceResult(constraints=(constraint(),))
    agent = _RecordingRegulatoryIntelligenceAgent(result=result)
    service = _execution_service(preparation, agent)

    returned = await service.execute(query_text="sentinel query", limit=4)

    assert len(agent.calls) == 1
    request = agent.calls[0]
    assert isinstance(request, RegulatoryIntelligenceRequest)
    assert request.search_query is prepared
    assert request.search_query.vector == (0.5, -1.25, 2.0)
    assert request.search_query.limit == 4
    assert returned is result
    assert returned.constraints == result.constraints


async def test_preparation_failure_propagates_without_calling_the_agent() -> None:
    error = DependencyUnavailableError(_UNAVAILABLE_MESSAGE)
    preparation = _RecordingQueryPreparationService(error=error)
    agent = _RecordingRegulatoryIntelligenceAgent(
        result=RegulatoryIntelligenceResult(constraints=())
    )
    service = _execution_service(preparation, agent)

    with pytest.raises(DependencyUnavailableError) as caught:
        await service.execute(query_text="Confidential regulatory search query.", limit=5)

    assert caught.value is error
    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert preparation.calls == [("Confidential regulatory search query.", 5)]
    assert agent.calls == []


async def test_agent_failure_propagates_without_fabricating_empty_constraints() -> None:
    prepared = _query()
    error = DependencyUnavailableError(_AGENT_UNAVAILABLE_MESSAGE)
    preparation = _RecordingQueryPreparationService(query=prepared)
    agent = _RecordingRegulatoryIntelligenceAgent(error=error)
    service = _execution_service(preparation, agent)

    with pytest.raises(DependencyUnavailableError) as caught:
        await service.execute(query_text="valid query text", limit=3)

    assert caught.value is error
    assert caught.value.message == _AGENT_UNAVAILABLE_MESSAGE
    assert len(agent.calls) == 1
    assert agent.calls[0].search_query is prepared


async def test_empty_constraint_result_is_legitimate_success() -> None:
    prepared = _query()
    empty = RegulatoryIntelligenceResult(constraints=())
    preparation = _RecordingQueryPreparationService(query=prepared)
    agent = _RecordingRegulatoryIntelligenceAgent(result=empty)
    service = _execution_service(preparation, agent)

    returned = await service.execute(query_text="empty-success query", limit=2)

    assert returned is empty
    assert returned.constraints == ()
    assert isinstance(returned, RegulatoryIntelligenceResult)


async def test_equivalent_inputs_produce_value_equivalent_results() -> None:
    query_text = "same regulatory query"
    first_constraint = constraint(constraint_id="c-1")
    second_constraint = constraint(constraint_id="c-1")
    first_result = RegulatoryIntelligenceResult(constraints=(first_constraint,))
    second_result = RegulatoryIntelligenceResult(constraints=(second_constraint,))
    first = _execution_service(
        _RecordingQueryPreparationService(query=_query(limit=4)),
        _RecordingRegulatoryIntelligenceAgent(result=first_result),
    )
    second = _execution_service(
        _RecordingQueryPreparationService(query=_query(limit=4)),
        _RecordingRegulatoryIntelligenceAgent(result=second_result),
    )

    first_returned = await first.execute(query_text=query_text, limit=4)
    second_returned = await second.execute(query_text=query_text, limit=4)

    assert first_returned == second_returned
    assert first_returned is not second_returned
    assert first_returned.constraints == second_returned.constraints


async def test_real_composition_runs_query_text_through_preparation_and_agent() -> None:
    query_text = "  keep surrounding spaces  "
    vector = (0.5, -1.0, 2.25)
    limit = 4
    chunk = _chunk()
    expected_constraint = constraint(constraint_id="composed-1")
    embedder = _FakeDocumentQueryEmbedder(vector=vector)
    search = _FakeDocumentVectorSearch(chunks=(chunk,))
    inference = _FakeRegulatoryConstraintInference(constraints=(expected_constraint,))
    preparation = DocumentVectorSearchQueryPreparationService(
        cast(DocumentQueryEmbeddingPort, embedder)
    )
    agent = RegulatoryIntelligenceAgent(
        search=cast(DocumentVectorSearchPort, search),
        inference=cast(RegulatoryConstraintInferencePort, inference),
    )
    service = RegulatoryIntelligenceQueryExecutionService(preparation, agent)

    result = await service.execute(query_text=query_text, limit=limit)

    assert embedder.received_query_text is query_text
    assert embedder.received_query_text != query_text.strip()
    assert len(search.calls) == 1
    assert search.calls[0].vector == vector
    assert search.calls[0].limit == limit
    assert inference.calls == [(chunk,)]
    assert inference.calls[0][0] is chunk
    assert result.constraints == (expected_constraint,)
    assert result.constraints[0] is expected_constraint


async def test_real_composition_empty_retrieval_skips_inference() -> None:
    embedder = _FakeDocumentQueryEmbedder()
    search = _FakeDocumentVectorSearch(chunks=())
    inference = _FakeRegulatoryConstraintInference(
        constraints=(constraint(constraint_id="must-not-appear"),)
    )
    service = RegulatoryIntelligenceQueryExecutionService(
        DocumentVectorSearchQueryPreparationService(cast(DocumentQueryEmbeddingPort, embedder)),
        RegulatoryIntelligenceAgent(
            search=cast(DocumentVectorSearchPort, search),
            inference=cast(RegulatoryConstraintInferencePort, inference),
        ),
    )

    result = await service.execute(query_text="no evidence query", limit=3)

    assert len(search.calls) == 1
    assert inference.calls == []
    assert result.constraints == ()
    assert isinstance(result, RegulatoryIntelligenceResult)
