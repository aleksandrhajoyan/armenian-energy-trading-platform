"""Adapter diagnostic and DLQ metadata contracts. No queue runtime."""

from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from energy_trading.domain.models.base import CanonicalModel
from energy_trading.domain.value_objects.quantities import EntityId, NonEmptyString
from energy_trading.domain.value_objects.time import UtcDateTime


class DiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class AdapterDiagnostic(CanonicalModel):
    """Canonical diagnostic envelope. No exception objects or stack traces."""

    code: NonEmptyString
    message: NonEmptyString
    severity: DiagnosticSeverity
    field_name: NonEmptyString | None = None


class DLQRecord(CanonicalModel):
    """Metadata for an ingestion normalization failure.

    Raw external payloads must not appear here. Store them behind
    ``payload_reference`` in infrastructure.
    """

    record_id: EntityId
    failed_at: UtcDateTime
    source_name: NonEmptyString
    adapter_name: NonEmptyString
    diagnostics: tuple[AdapterDiagnostic, ...] = Field(min_length=1)
    payload_reference: NonEmptyString
    correlation_id: EntityId | None = None

    @model_validator(mode="after")
    def require_diagnostics(self) -> Self:
        if len(self.diagnostics) < 1:
            msg = "DLQRecord requires at least one diagnostic"
            raise ValueError(msg)
        return self
