"""Regulatory Intelligence Agent application boundary.

This module is the sixth concrete application agent. It consumes a typed
request carrying an already-constructed document-vector search query, calls
the injected retrieval port once, and — when retrieved chunks exist —
delegates inference of canonical ``RegulatoryConstraint`` values to an
injected agent-specific inference port. Raw PDFs, Qdrant payloads, prompt
objects, and vendor LLM responses never enter here.

Ownership:

* Application: owns the request/result DTOs and the concrete agent.
* Injected ``DocumentVectorSearchPort``: supplies already-normalized chunks.
* Injected ``RegulatoryConstraintInferencePort``: supplies already-canonical
  constraints from those chunks.
* Future infrastructure adapters: implement those ports. Query-text
  embedding, Qdrant, PDF/OCR, and LLM providers remain outside this module.
* LangGraph, API composition, persistence, retry, fallback, prompt catalogs,
  and hardcoded Armenian DAM rules remain deferred.

The agent satisfies ``AgentPort`` structurally. It does not inherit a base
class and is not registered in a factory.
"""

from dataclasses import dataclass

from energy_trading.application.agents.base import AgentName
from energy_trading.application.ports.document_vector_search import (
    DocumentVectorSearchPort,
    DocumentVectorSearchQuery,
)
from energy_trading.application.ports.regulatory_constraint_inference import (
    RegulatoryConstraintInferencePort,
)
from energy_trading.domain.models.regulatory import RegulatoryConstraint


@dataclass(frozen=True, slots=True)
class RegulatoryIntelligenceRequest:
    """Immutable agent request: an already-constructed vector-search query.

    This is an application DTO, not a domain entity and not a workflow
    snapshot. It carries no query text, file path, URL, PDF bytes, prompt,
    provider, model, collection, score, or credential fields. The caller
    supplies ``DocumentVectorSearchQuery``.
    """

    search_query: DocumentVectorSearchQuery

    def __post_init__(self) -> None:
        object.__setattr__(self, "search_query", _require_search_query(self.search_query))


@dataclass(frozen=True, slots=True)
class RegulatoryIntelligenceResult:
    """Immutable agent result wrapping canonical regulatory constraints.

    An empty tuple is valid. Ordering is the inference-port tuple order.
    This DTO carries no diagnostics, retrieved chunks, scores, prompts,
    token usage, model names, citations, or invented confidence.
    """

    constraints: tuple[RegulatoryConstraint, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "constraints", _require_regulatory_constraints(self.constraints))


class RegulatoryIntelligenceAgent:
    """Thin application agent over retrieval plus regulatory inference.

    ``run`` calls ``DocumentVectorSearchPort.search`` exactly once. An empty
    retrieval returns empty constraints without calling inference. Otherwise
    ``RegulatoryConstraintInferencePort.infer`` is awaited exactly once with
    the retrieved chunks. The agent does not construct constraints, parse
    regulatory text, embed query text, or inspect vector scores.
    """

    def __init__(
        self,
        *,
        search: DocumentVectorSearchPort,
        inference: RegulatoryConstraintInferencePort,
    ) -> None:
        self._search = search
        self._inference = inference

    @property
    def name(self) -> AgentName:
        return AgentName.REGULATORY_INTELLIGENCE

    async def run(self, request: RegulatoryIntelligenceRequest) -> RegulatoryIntelligenceResult:
        chunks = await self._search.search(request.search_query)
        if not chunks:
            return RegulatoryIntelligenceResult(constraints=())
        constraints = await self._inference.infer(chunks=chunks)
        return RegulatoryIntelligenceResult(constraints=constraints)


def _require_search_query(value: object) -> DocumentVectorSearchQuery:
    if not isinstance(value, DocumentVectorSearchQuery):
        msg = "search_query must be a DocumentVectorSearchQuery"
        raise TypeError(msg)
    return value


def _require_regulatory_constraints(value: object) -> tuple[RegulatoryConstraint, ...]:
    if not isinstance(value, tuple):
        msg = "constraints must be an immutable tuple"
        raise TypeError(msg)
    if not all(isinstance(item, RegulatoryConstraint) for item in value):
        msg = "constraints must contain RegulatoryConstraint values"
        raise TypeError(msg)
    return value
