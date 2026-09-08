"""Regulatory Intelligence Agent application contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

import pytest
from tests.unit.domain._factories import constraint

from energy_trading.application.agents.base import AgentName, AgentPort
from energy_trading.application.agents.regulatory_intelligence import (
    RegulatoryIntelligenceAgent,
    RegulatoryIntelligenceRequest,
    RegulatoryIntelligenceResult,
)
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk
from energy_trading.application.ports.document_vector_search import (
    DocumentVectorSearchPort,
    DocumentVectorSearchQuery,
)
from energy_trading.application.ports.regulatory_constraint_inference import (
    RegulatoryConstraintInferencePort,
)
from energy_trading.domain.models.regulatory import RegulatoryConstraint


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


def _as_agent_port(
    agent: RegulatoryIntelligenceAgent,
) -> AgentPort[RegulatoryIntelligenceRequest, RegulatoryIntelligenceResult]:
    """Mypy-visible structural assignment to the shared agent port."""

    return agent


def _as_search_port(search: _FakeDocumentVectorSearch) -> DocumentVectorSearchPort:
    return search


def _as_inference_port(
    inference: _FakeRegulatoryConstraintInference,
) -> RegulatoryConstraintInferencePort:
    return inference


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


def _query(**overrides: object) -> DocumentVectorSearchQuery:
    values: dict[str, object] = {
        "vector": (1.0, 0.0, -0.25),
        "limit": 5,
    }
    values.update(overrides)
    return DocumentVectorSearchQuery(**values)  # type: ignore[arg-type]


def _request(
    search_query: DocumentVectorSearchQuery | None = None,
) -> RegulatoryIntelligenceRequest:
    query = _query() if search_query is None else search_query
    return RegulatoryIntelligenceRequest(search_query=query)


def _agent(
    *,
    search: _FakeDocumentVectorSearch | None = None,
    inference: _FakeRegulatoryConstraintInference | None = None,
) -> tuple[
    RegulatoryIntelligenceAgent,
    _FakeDocumentVectorSearch,
    _FakeRegulatoryConstraintInference,
]:
    search_fake = _FakeDocumentVectorSearch() if search is None else search
    inference_fake = _FakeRegulatoryConstraintInference() if inference is None else inference
    agent = RegulatoryIntelligenceAgent(
        search=_as_search_port(search_fake),
        inference=_as_inference_port(inference_fake),
    )
    return agent, search_fake, inference_fake


def test_request_preserves_search_query_identity() -> None:
    query = _query()
    request = RegulatoryIntelligenceRequest(search_query=query)
    assert request.search_query is query
    assert request.search_query.vector == (1.0, 0.0, -0.25)
    assert request.search_query.limit == 5


def test_request_rejects_non_search_query() -> None:
    with pytest.raises(TypeError, match="search_query must be a DocumentVectorSearchQuery"):
        RegulatoryIntelligenceRequest(search_query="not-a-query")  # type: ignore[arg-type]


def test_request_is_frozen_and_slotted() -> None:
    request = _request()
    assert hasattr(RegulatoryIntelligenceRequest, "__slots__")
    with pytest.raises(FrozenInstanceError):
        request.search_query = _query(limit=1)  # type: ignore[misc]
    field_names = tuple(item.name for item in fields(RegulatoryIntelligenceRequest))
    assert field_names == ("search_query",)


def test_request_rejects_unrequested_fields() -> None:
    with pytest.raises(TypeError):
        RegulatoryIntelligenceRequest(
            search_query=_query(),
            prompt="extract rules",  # type: ignore[call-arg]
        )


def test_result_empty_tuple_is_valid() -> None:
    result = RegulatoryIntelligenceResult(constraints=())
    assert result.constraints == ()
    assert isinstance(result.constraints, tuple)


def test_result_accepts_one_canonical_constraint() -> None:
    record = constraint()
    result = RegulatoryIntelligenceResult(constraints=(record,))
    assert result.constraints == (record,)
    assert result.constraints[0] is record


def test_result_preserves_multiple_constraint_order() -> None:
    first = constraint(constraint_id="constraint-1")
    second = constraint(
        constraint_id="constraint-2",
        constraint_type="license_window",
        description="Generic effective window",
    )
    result = RegulatoryIntelligenceResult(constraints=(first, second))
    assert result.constraints == (first, second)


def test_result_canonical_fields_remain_unchanged() -> None:
    record = constraint(
        constraint_id="constraint-keep",
        description="Generic numeric bound",
        minimum_value=2.5,
        maximum_value=7.5,
        unit="MW",
        source_document_id="doc-1",
    )
    result = RegulatoryIntelligenceResult(constraints=(record,))
    passed = result.constraints[0]
    assert passed is record
    assert passed.constraint_id == "constraint-keep"
    assert passed.description == "Generic numeric bound"
    assert passed.minimum_value == 2.5
    assert passed.maximum_value == 7.5
    assert passed.unit == "MW"
    assert passed.source_document_id == "doc-1"


def test_result_rejects_mutable_constraints_collection() -> None:
    with pytest.raises(TypeError, match="constraints must be an immutable tuple"):
        RegulatoryIntelligenceResult(constraints=[constraint()])  # type: ignore[arg-type]


def test_result_rejects_non_regulatory_constraint_values() -> None:
    with pytest.raises(TypeError, match="constraints must contain RegulatoryConstraint values"):
        RegulatoryIntelligenceResult(constraints=("not-constraint",))  # type: ignore[arg-type]


def test_result_is_frozen() -> None:
    result = RegulatoryIntelligenceResult(constraints=())
    assert hasattr(RegulatoryIntelligenceResult, "__slots__")
    with pytest.raises(FrozenInstanceError):
        result.constraints = ()  # type: ignore[misc]


def test_agent_does_not_inherit_agent_port() -> None:
    assert AgentPort not in RegulatoryIntelligenceAgent.__mro__
    assert not any(base.__name__ == "AgentPort" for base in RegulatoryIntelligenceAgent.__bases__)


def test_agent_name_is_canonical_regulatory_identity() -> None:
    agent, _, _ = _agent()
    port = _as_agent_port(agent)
    assert port.name is AgentName.REGULATORY_INTELLIGENCE
    assert port.name.value == "Regulatory Intelligence Agent"


async def test_run_invokes_search_once_with_exact_query() -> None:
    query = _query(vector=(0.5, -1.0), limit=3)
    record = constraint()
    search = _FakeDocumentVectorSearch((_chunk(),))
    inference = _FakeRegulatoryConstraintInference((record,))
    agent, _, _ = _agent(search=search, inference=inference)
    result = await _as_agent_port(agent).run(RegulatoryIntelligenceRequest(search_query=query))
    assert len(search.calls) == 1
    assert search.calls[0] is query
    assert result.constraints == (record,)
    assert result.constraints[0] is record


async def test_run_forwards_retrieved_chunks_and_preserves_constraints() -> None:
    first_chunk = _chunk()
    second_chunk = _chunk(chunk_id="chunk-2", ordinal=1, text="Second normalized chunk.")
    chunks = (first_chunk, second_chunk)
    first = constraint(constraint_id="constraint-1")
    second = constraint(
        constraint_id="constraint-2",
        constraint_type="license_window",
        description="Generic effective window",
    )
    search = _FakeDocumentVectorSearch(chunks)
    inference = _FakeRegulatoryConstraintInference((first, second))
    result = await RegulatoryIntelligenceAgent(
        search=_as_search_port(search),
        inference=_as_inference_port(inference),
    ).run(_request())
    assert len(search.calls) == 1
    assert len(inference.calls) == 1
    assert inference.calls[0] is chunks
    assert inference.calls[0] == (first_chunk, second_chunk)
    assert result.constraints == (first, second)
    assert result.constraints[0] is first
    assert result.constraints[1] is second


async def test_run_empty_retrieval_skips_inference() -> None:
    search = _FakeDocumentVectorSearch()
    inference = _FakeRegulatoryConstraintInference((constraint(),))
    result = await RegulatoryIntelligenceAgent(
        search=_as_search_port(search),
        inference=_as_inference_port(inference),
    ).run(_request())
    assert result == RegulatoryIntelligenceResult(constraints=())
    assert result.constraints == ()
    assert len(search.calls) == 1
    assert inference.calls == []


async def test_run_propagates_search_dependency_unavailable_without_inference() -> None:
    error = DependencyUnavailableError("document vector search unavailable")
    search = _FakeDocumentVectorSearch(error=error)
    inference = _FakeRegulatoryConstraintInference((constraint(),))
    agent = RegulatoryIntelligenceAgent(
        search=_as_search_port(search),
        inference=_as_inference_port(inference),
    )
    with pytest.raises(
        DependencyUnavailableError, match="document vector search unavailable"
    ) as caught:
        await agent.run(_request())
    assert caught.value is error
    assert len(search.calls) == 1
    assert inference.calls == []


async def test_run_propagates_inference_dependency_unavailable_without_empty_success() -> None:
    error = DependencyUnavailableError("regulatory inference unavailable")
    search = _FakeDocumentVectorSearch((_chunk(),))
    inference = _FakeRegulatoryConstraintInference(error=error)
    agent = RegulatoryIntelligenceAgent(
        search=_as_search_port(search),
        inference=_as_inference_port(inference),
    )
    with pytest.raises(
        DependencyUnavailableError, match="regulatory inference unavailable"
    ) as caught:
        await agent.run(_request())
    assert caught.value is error
    assert len(search.calls) == 1
    assert len(inference.calls) == 1
    assert inference.calls[0] is search.chunks


async def test_run_does_not_mutate_request_chunks_or_constraints() -> None:
    query = _query()
    request = RegulatoryIntelligenceRequest(search_query=query)
    chunks = (_chunk(),)
    record = constraint()
    search = _FakeDocumentVectorSearch(chunks)
    inference = _FakeRegulatoryConstraintInference((record,))
    result = await RegulatoryIntelligenceAgent(
        search=_as_search_port(search),
        inference=_as_inference_port(inference),
    ).run(request)
    assert request.search_query is query
    assert search.chunks is chunks
    assert search.chunks[0].text == "Normalized extracted regulatory text."
    assert inference.constraints[0] is record
    assert result.constraints[0] is record
    assert record.constraint_id == "constraint-1"
