"""Deterministic schema field resolution inside the structured ACL.

Public types and the resolver are infrastructure-local. Raw external field
names never cross into application or domain layers through this package.
"""

from energy_trading.infrastructure.adapters.structured.schema_mapping.models import (
    CanonicalFieldCollision,
    CanonicalFieldSpec,
    FieldCandidate,
    FieldResolution,
    FieldResolutionMethod,
    FieldResolutionStatus,
    ResolverConfigurationError,
    SchemaResolution,
)
from energy_trading.infrastructure.adapters.structured.schema_mapping.normalization import (
    normalize_field_name,
)
from energy_trading.infrastructure.adapters.structured.schema_mapping.resolver import (
    DeterministicFieldResolver,
)

__all__ = [
    "CanonicalFieldCollision",
    "CanonicalFieldSpec",
    "DeterministicFieldResolver",
    "FieldCandidate",
    "FieldResolution",
    "FieldResolutionMethod",
    "FieldResolutionStatus",
    "ResolverConfigurationError",
    "SchemaResolution",
    "normalize_field_name",
]
