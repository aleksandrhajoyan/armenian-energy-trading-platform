"""Shared Consumption structured-source mapping policy.

CSV and Excel adapters both construct ``ConsumptionRecord`` values. This
module owns the default canonical field profile, configured power-unit aliases,
and header/unit consistency plus fuzzy unit-token safety. It is not a generic
adapter framework.
"""

from __future__ import annotations

from collections.abc import Sequence

from energy_trading.infrastructure.adapters.structured.normalization import PowerUnit
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
_ENERGY_LAST_TOKENS = frozenset({"mwh", "kwh", "wh", "w", "hour"})
_POWER_TOKENS = {
    PowerUnit.MW: "mw",
    PowerUnit.KW: "kw",
}
_KNOWN_POWER_TOKENS = frozenset(_POWER_TOKENS.values())


def default_consumption_field_specs(
    source_power_unit: PowerUnit = PowerUnit.MW,
) -> tuple[CanonicalFieldSpec, ...]:
    """Build the default Consumption header profile for an explicit power unit."""

    alias = "Consumption_MW" if source_power_unit is PowerUnit.MW else "Consumption_kW"
    return (
        CanonicalFieldSpec(canonical_name="consumer_id", aliases=(), required=True),
        CanonicalFieldSpec(canonical_name="timestamp", aliases=(), required=True),
        CanonicalFieldSpec(canonical_name="value_mw", aliases=(alias,), required=True),
    )


DEFAULT_CONSUMPTION_FIELD_SPECS = default_consumption_field_specs(PowerUnit.MW)


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


def apply_consumption_unit_safety(
    schema: SchemaResolution,
    *,
    source_power_unit: PowerUnit = PowerUnit.MW,
) -> SchemaResolution:
    """Apply fuzzy unit-token safety and header/config unit consistency.

    Fuzzy ``value_mw`` mappings require the normalized source's final token to
    be the configured power unit. Exact mappings that explicitly claim a
    conflicting power unit or any energy unit fail closed. No conversion.
    """

    expected_token = _POWER_TOKENS[source_power_unit]
    resolutions = tuple(
        _apply_header_unit_policy(item, expected_token=expected_token)
        for item in schema.field_resolutions
    )
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


def _apply_header_unit_policy(
    resolution: FieldResolution,
    *,
    expected_token: str,
) -> FieldResolution:
    if (
        resolution.status is not FieldResolutionStatus.RESOLVED
        or resolution.canonical_field != "value_mw"
    ):
        return resolution
    tokens = resolution.normalized_source_field.split()
    last = tokens[-1] if tokens else ""
    if resolution.method is FieldResolutionMethod.FUZZY:
        if last != expected_token or _is_energy_like(tokens):
            return _unresolved(resolution)
        return resolution
    if _header_claims_conflicting_unit(tokens, expected_token=expected_token):
        return _unresolved(resolution)
    return resolution


def _header_claims_conflicting_unit(tokens: list[str], *, expected_token: str) -> bool:
    if not tokens:
        return False
    if _is_energy_like(tokens):
        return True
    last = tokens[-1]
    return last in _KNOWN_POWER_TOKENS and last != expected_token


def _is_energy_like(tokens: list[str]) -> bool:
    if not tokens:
        return False
    if tokens[-1] in _ENERGY_LAST_TOKENS:
        return True
    return len(tokens) >= 2 and tokens[-2:] == ["mw", "h"]


def _unresolved(resolution: FieldResolution) -> FieldResolution:
    return FieldResolution(
        source_field=resolution.source_field,
        normalized_source_field=resolution.normalized_source_field,
        status=FieldResolutionStatus.UNRESOLVED,
        canonical_field=None,
        method=None,
        confidence=resolution.confidence,
        candidates=resolution.candidates,
    )
