"""Shared Consumption structured-source mapping policy.

CSV and Excel adapters both construct ``ConsumptionRecord`` values. This
module owns only the default canonical field profile and the MW-safe fuzzy
header predicate. It is not a generic adapter framework.
"""

from __future__ import annotations

from collections.abc import Sequence

from energy_trading.infrastructure.adapters.structured.schema_mapping import (
    CanonicalFieldCollision,
    CanonicalFieldSpec,
    FieldResolution,
    FieldResolutionMethod,
    FieldResolutionStatus,
    SchemaResolution,
)

_REQUIRED_CANONICAL_FIELDS = frozenset({"consumer_id", "timestamp", "value_mw"})
_REQUIRED_CANONICAL_ORDER = ("consumer_id", "timestamp", "value_mw")
_MW_TOKEN = "mw"

DEFAULT_CONSUMPTION_FIELD_SPECS = (
    CanonicalFieldSpec(canonical_name="consumer_id", aliases=(), required=True),
    CanonicalFieldSpec(canonical_name="timestamp", aliases=(), required=True),
    CanonicalFieldSpec(canonical_name="value_mw", aliases=("Consumption_MW",), required=True),
)


def validated_consumption_field_specs(
    field_specs: Sequence[CanonicalFieldSpec],
) -> tuple[CanonicalFieldSpec, ...]:
    """Require the three Consumption destinations, all marked required."""

    specs = tuple(field_specs)
    names = tuple(spec.canonical_name for spec in specs)
    if frozenset(names) != _REQUIRED_CANONICAL_FIELDS or len(names) != len(
        _REQUIRED_CANONICAL_FIELDS
    ):
        msg = "Consumption field specs must be exactly consumer_id, timestamp, and value_mw"
        raise ValueError(msg)
    if not all(spec.required for spec in specs):
        msg = "Consumption canonical fields must all be required"
        raise ValueError(msg)
    return specs


def apply_consumption_unit_safety(schema: SchemaResolution) -> SchemaResolution:
    """Reject fuzzy ``value_mw`` mappings that are not standalone MW.

    Chunk 5 may fuzzy-match energy-like headers to the MW alias. Consumption
    adapters accept a fuzzy ``value_mw`` mapping only when the normalized
    source's final token is exactly ``mw``. Exact ``Consumption_MW`` is
    unchanged. No unit conversion is performed.
    """

    resolutions = tuple(_downgrade_unsafe_fuzzy_mw(item) for item in schema.field_resolutions)
    resolved_sources: dict[str, list[str]] = {}
    for resolution in resolutions:
        if (
            resolution.status is FieldResolutionStatus.RESOLVED
            and resolution.canonical_field is not None
        ):
            resolved_sources.setdefault(resolution.canonical_field, []).append(
                resolution.source_field
            )
    missing = tuple(name for name in _REQUIRED_CANONICAL_ORDER if name not in resolved_sources)
    collisions = tuple(
        CanonicalFieldCollision(
            canonical_field=canonical_field,
            source_fields=tuple(source_fields),
        )
        for canonical_field, source_fields in sorted(resolved_sources.items())
        if len(source_fields) > 1
    )
    return SchemaResolution(
        field_resolutions=resolutions,
        missing_required_fields=missing,
        collisions=collisions,
    )


def canonical_column_index(schema: SchemaResolution) -> dict[str, int]:
    """Map resolved canonical field names to source column indexes."""

    mapping: dict[str, int] = {}
    for index, resolution in enumerate(schema.field_resolutions):
        if (
            resolution.status is FieldResolutionStatus.RESOLVED
            and resolution.canonical_field is not None
        ):
            mapping[resolution.canonical_field] = index
    return mapping


def _downgrade_unsafe_fuzzy_mw(resolution: FieldResolution) -> FieldResolution:
    if (
        resolution.status is not FieldResolutionStatus.RESOLVED
        or resolution.canonical_field != "value_mw"
        or resolution.method is not FieldResolutionMethod.FUZZY
    ):
        return resolution
    if _normalized_source_is_mw_safe(resolution.normalized_source_field):
        return resolution
    return FieldResolution(
        source_field=resolution.source_field,
        normalized_source_field=resolution.normalized_source_field,
        status=FieldResolutionStatus.UNRESOLVED,
        canonical_field=None,
        method=None,
        confidence=resolution.confidence,
        candidates=resolution.candidates,
    )


def _normalized_source_is_mw_safe(normalized_source: str) -> bool:
    tokens = normalized_source.split()
    return bool(tokens) and tokens[-1] == _MW_TOKEN
