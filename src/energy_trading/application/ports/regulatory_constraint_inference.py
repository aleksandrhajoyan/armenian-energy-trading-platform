"""Application-owned regulatory-constraint inference boundary.

This port sits after document retrieval. A caller supplies already-normalized
``ExtractedDocumentChunk`` values. A future outer-layer implementation may
interpret those chunks and return canonical ``RegulatoryConstraint`` values.

Ownership:

* Application: owns ``RegulatoryConstraintInferencePort``.
* Future outer implementation: structurally implements the protocol.
  Prompt text, model names, provider SDKs, HTTP clients, and raw document
  bytes remain infrastructure concerns. There is no infrastructure base
  class and no generic ``LLMPort``.
* Retrieval remains ``DocumentVectorSearchPort``. This port does not search,
  embed, parse PDFs, or construct constraints from hardcoded market rules.

Returned tuples are already canonical. This port does not invent Armenian DAM
gate times, bid envelopes, price caps, currencies, or license limits. An empty
tuple is a valid successful result. Tuple order is the order returned by the
future implementation.

Expected unavailable backends use existing application errors such as
``DependencyUnavailableError``. There is no Regulatory-specific error
hierarchy.
"""

from typing import Protocol

from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk
from energy_trading.domain.models.regulatory import RegulatoryConstraint


class RegulatoryConstraintInferencePort(Protocol):
    """Application-owned inference of canonical regulatory constraints.

    Implementations satisfy this protocol structurally. The application
    depends on the protocol, never on a concrete LLM SDK, prompt catalog, or
    generic language-model port.

    ``infer`` accepts only already-normalized ``ExtractedDocumentChunk``
    values. It must not accept query text, prompts, model names, provider
    names, credentials, raw bytes, paths, URLs, Qdrant types, or workflow
    state.
    """

    async def infer(
        self,
        *,
        chunks: tuple[ExtractedDocumentChunk, ...],
    ) -> tuple[RegulatoryConstraint, ...]:
        """Return canonical regulatory constraints for retrieved chunks.

        An empty tuple is a valid successful result. Implementations must
        not raise merely because the chunks yielded no constraints.
        """
        ...
