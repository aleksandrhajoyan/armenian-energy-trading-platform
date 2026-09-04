"""Infrastructure-local types for deterministic schema field resolution.

These objects describe header/field interpretation only. They are not domain
contracts, not application port payloads, and they never carry row values or
unit conversions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FieldResolutionStatus(StrEnum):
    """Outcome of resolving one source header to a canonical field."""

    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class FieldResolutionMethod(StrEnum):
    """How a successful resolution was obtained.

    Unresolved and ambiguous results leave the method unset; they must not
    pretend that a resolution method succeeded.
    """

    EXACT = "exact"
    FUZZY = "fuzzy"


class ResolverConfigurationError(ValueError):
    """Invalid resolver mapping configuration.

    Raised when constructing ``DeterministicFieldResolver``. This is an
    adapter/configuration bug, not source-data ambiguity.
    """


@dataclass(frozen=True, slots=True)
class CanonicalFieldSpec:
    """One canonical destination field an adapter may later populate.

    Defines schema interpretation only. ``aliases`` are exact-match strings
    after normalization; they do not encode unit conversion.
    """

    canonical_name: str
    aliases: tuple[str, ...]
    required: bool

    def __post_init__(self) -> None:
        canonical_name = _require_str("canonical_name", self.canonical_name)
        aliases = _require_str_tuple("aliases", self.aliases)
        required = _require_bool("required", self.required)
        object.__setattr__(self, "canonical_name", canonical_name)
        object.__setattr__(self, "aliases", aliases)
        object.__setattr__(self, "required", required)


@dataclass(frozen=True, slots=True)
class FieldCandidate:
    """One scored canonical destination considered for a source header."""

    canonical_field: str
    confidence: float
    matched_representation: str


@dataclass(frozen=True, slots=True)
class FieldResolution:
    """Immutable resolution result for one raw source header."""

    source_field: str
    normalized_source_field: str
    status: FieldResolutionStatus
    canonical_field: str | None
    method: FieldResolutionMethod | None
    confidence: float
    candidates: tuple[FieldCandidate, ...]


@dataclass(frozen=True, slots=True)
class CanonicalFieldCollision:
    """Multiple source headers independently resolved to one canonical field."""

    canonical_field: str
    source_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SchemaResolution:
    """Batch schema interpretation for an ordered sequence of source headers.

    This is infrastructure-internal schema information. It is not a
    ``StructuredIngestionResult`` and does not contain canonical records.
    """

    field_resolutions: tuple[FieldResolution, ...]
    missing_required_fields: tuple[str, ...]
    collisions: tuple[CanonicalFieldCollision, ...]


def _require_str(field_name: str, value: object) -> str:
    if not isinstance(value, str):
        msg = f"{field_name} must be a string"
        raise TypeError(msg)
    return value


def _require_str_tuple(field_name: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        msg = f"{field_name} must be an immutable tuple"
        raise TypeError(msg)
    if not all(isinstance(item, str) for item in value):
        msg = f"{field_name} must contain strings"
        raise TypeError(msg)
    return value


def _require_bool(field_name: str, value: object) -> bool:
    if not isinstance(value, bool):
        msg = f"{field_name} must be a bool"
        raise TypeError(msg)
    return value
