"""OpenAI infrastructure adapter for regulatory-constraint inference.

This class structurally implements ``RegulatoryConstraintInferencePort``. It
does not own the ``AsyncOpenAI`` lifecycle, load API keys, select a default
model, or wire ``create_app()``.

OpenAI SDK types and private provider schemas terminate here. Callers receive
only canonical ``RegulatoryConstraint`` values.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Final, Self

from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk
from energy_trading.domain.models.regulatory import RegulatoryConstraint

_MSG_UNAVAILABLE: Final[str] = "Regulatory constraint inference is unavailable."
_INFERENCE_INSTRUCTIONS: Final[str] = (
    "Infer structured regulatory constraints only from the supplied normalized "
    "document chunks. Infer a constraint only when those chunks explicitly "
    "support it. Omit a constraint when evidence is missing or ambiguous. "
    "Never invent numeric thresholds, price caps, bid limits, gate times, "
    "license limits, currencies, or effective dates. Never perform unsupported "
    "arithmetic or unit conversion. Never use outside knowledge as evidence. "
    "Every inferred constraint must cite at least one supplied chunk_id in "
    "evidence_chunk_ids. Use only chunk_id values that appear in the supplied "
    "chunks."
)


class _ProviderConstraintCandidate(BaseModel):
    """Private OpenAI structured-output candidate. Not a domain contract."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    constraint_id: str
    constraint_type: str
    description: str
    effective_from: date
    evidence_chunk_ids: tuple[str, ...] = Field(min_length=1)
    effective_to: date | None = None
    minimum_value: float | None = Field(default=None, allow_inf_nan=False)
    maximum_value: float | None = Field(default=None, allow_inf_nan=False)
    unit: str | None = None
    currency: str | None = None
    source_document_id: str | None = None

    @model_validator(mode="after")
    def validate_evidence_chunk_ids(self) -> Self:
        if any(not item for item in self.evidence_chunk_ids):
            msg = "evidence_chunk_ids must contain non-empty strings"
            raise ValueError(msg)
        return self


class _ProviderInferenceEnvelope(BaseModel):
    """Private OpenAI structured-output envelope. Not an application DTO."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    constraints: tuple[_ProviderConstraintCandidate, ...]


class OpenAIRegulatoryConstraintInferenceAdapter:
    """OpenAI structured-output adapter for already-normalized document chunks."""

    def __init__(self, *, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    async def infer(
        self,
        *,
        chunks: tuple[ExtractedDocumentChunk, ...],
    ) -> tuple[RegulatoryConstraint, ...]:
        """Return canonical regulatory constraints for retrieved chunks."""

        if not chunks:
            return ()
        try:
            response = await self._client.responses.parse(
                model=self._model,
                input=_provider_input(chunks),
                instructions=_INFERENCE_INSTRUCTIONS,
                text_format=_ProviderInferenceEnvelope,
            )
        except OpenAIError as exc:
            raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc
        return _to_constraints(response, chunks=chunks)


def _provider_input(chunks: tuple[ExtractedDocumentChunk, ...]) -> str:
    parts: list[str] = []
    for chunk in chunks:
        parts.append(
            f"chunk_id: {chunk.chunk_id}\n"
            f"document_id: {chunk.document_id}\n"
            f"ordinal: {chunk.ordinal}\n"
            f"text:\n{chunk.text}"
        )
    return "\n\n".join(parts)


def _to_constraints(
    response: object,
    *,
    chunks: tuple[ExtractedDocumentChunk, ...],
) -> tuple[RegulatoryConstraint, ...]:
    if _has_refusal(response):
        raise DependencyUnavailableError(_MSG_UNAVAILABLE)
    envelope = _require_envelope(response)
    known_chunk_ids = frozenset(chunk.chunk_id for chunk in chunks)
    converted: list[RegulatoryConstraint] = []
    for candidate in envelope.constraints:
        if not _evidence_is_known(candidate.evidence_chunk_ids, known_chunk_ids):
            raise DependencyUnavailableError(_MSG_UNAVAILABLE)
        converted.append(_to_canonical(candidate))
    return tuple(converted)


def _require_envelope(response: object) -> _ProviderInferenceEnvelope:
    parsed = getattr(response, "output_parsed", None)
    if parsed is None:
        raise DependencyUnavailableError(_MSG_UNAVAILABLE)
    if isinstance(parsed, _ProviderInferenceEnvelope):
        return parsed
    try:
        return _ProviderInferenceEnvelope.model_validate(parsed)
    except (TypeError, ValueError, ValidationError) as exc:
        raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc


def _evidence_is_known(
    evidence_chunk_ids: tuple[str, ...],
    known_chunk_ids: frozenset[str],
) -> bool:
    return all(chunk_id in known_chunk_ids for chunk_id in evidence_chunk_ids)


def _to_canonical(candidate: _ProviderConstraintCandidate) -> RegulatoryConstraint:
    try:
        return RegulatoryConstraint(
            constraint_id=candidate.constraint_id,
            constraint_type=candidate.constraint_type,
            description=candidate.description,
            effective_from=candidate.effective_from,
            effective_to=candidate.effective_to,
            minimum_value=candidate.minimum_value,
            maximum_value=candidate.maximum_value,
            unit=candidate.unit,
            currency=candidate.currency,
            source_document_id=candidate.source_document_id,
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc


def _has_refusal(response: object) -> bool:
    output = getattr(response, "output", None)
    if not isinstance(output, Sequence) or isinstance(output, (str, bytes, bytearray)):
        return False
    for item in output:
        content = getattr(item, "content", None)
        if not isinstance(content, Sequence) or isinstance(content, (str, bytes, bytearray)):
            continue
        for part in content:
            if getattr(part, "type", None) == "refusal":
                return True
    return False
