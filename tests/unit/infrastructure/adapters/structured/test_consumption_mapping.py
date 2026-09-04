"""Shared Consumption mapping policy unit tests."""

import pytest

from energy_trading.infrastructure.adapters.structured.consumption_mapping import (
    DEFAULT_CONSUMPTION_FIELD_SPECS,
    apply_consumption_unit_safety,
    default_consumption_field_specs,
    validated_consumption_field_specs,
)
from energy_trading.infrastructure.adapters.structured.normalization import PowerUnit
from energy_trading.infrastructure.adapters.structured.schema_mapping import (
    CanonicalFieldSpec,
    DeterministicFieldResolver,
    FieldResolutionMethod,
    FieldResolutionStatus,
)

_UNSAFE_HEADERS = (
    "Consumption_kW",
    "Consumption_kWh",
    "Consumption_W",
    "Consumption_MWh",
    "Consumption_MW_h",
    "Consumption_MW-hour",
)


def _resolver() -> DeterministicFieldResolver:
    return DeterministicFieldResolver(DEFAULT_CONSUMPTION_FIELD_SPECS)


def test_default_specs_require_mw_safe_alias_only() -> None:
    specs = validated_consumption_field_specs(DEFAULT_CONSUMPTION_FIELD_SPECS)
    by_name = {spec.canonical_name: spec for spec in specs}
    assert set(by_name) == {"consumer_id", "timestamp", "value_mw"}
    assert by_name["value_mw"].aliases == ("Consumption_MW",)
    assert by_name["consumer_id"].aliases == ()
    assert by_name["timestamp"].aliases == ()
    assert all(spec.required for spec in specs)


def test_validated_specs_reject_unrelated_canonical_fields() -> None:
    with pytest.raises(ValueError, match="exactly consumer_id, timestamp, and value_mw"):
        validated_consumption_field_specs(
            (
                CanonicalFieldSpec("consumer_id", aliases=(), required=True),
                CanonicalFieldSpec("timestamp", aliases=(), required=True),
                CanonicalFieldSpec("volume_mwh", aliases=(), required=True),
            )
        )


def test_fuzzy_standalone_mw_header_remains_resolved() -> None:
    schema = apply_consumption_unit_safety(
        _resolver().resolve_schema(("consumer_id", "timestamp", "Consumpton_MW"))
    )
    value_mw = schema.field_resolutions[2]
    assert value_mw.status is FieldResolutionStatus.RESOLVED
    assert value_mw.canonical_field == "value_mw"
    assert value_mw.method is FieldResolutionMethod.FUZZY
    assert schema.missing_required_fields == ()


def test_exact_consumption_mw_alias_is_unchanged() -> None:
    schema = apply_consumption_unit_safety(
        _resolver().resolve_schema(("consumer_id", "timestamp", "Consumption_MW"))
    )
    value_mw = schema.field_resolutions[2]
    assert value_mw.status is FieldResolutionStatus.RESOLVED
    assert value_mw.method is FieldResolutionMethod.EXACT
    assert value_mw.canonical_field == "value_mw"


def test_unsafe_unit_headers_are_downgraded_and_value_mw_is_missing() -> None:
    resolver = _resolver()
    for unsafe_header in _UNSAFE_HEADERS:
        schema = apply_consumption_unit_safety(
            resolver.resolve_schema(("consumer_id", "timestamp", unsafe_header))
        )
        value_header = schema.field_resolutions[2]
        assert value_header.status is FieldResolutionStatus.UNRESOLVED
        assert value_header.canonical_field is None
        assert "value_mw" in schema.missing_required_fields


def test_kw_profile_accepts_consumption_kw_and_fuzzy_kw() -> None:
    specs = default_consumption_field_specs(PowerUnit.KW)
    resolver = DeterministicFieldResolver(specs)
    exact = apply_consumption_unit_safety(
        resolver.resolve_schema(("consumer_id", "timestamp", "Consumption_kW")),
        source_power_unit=PowerUnit.KW,
    )
    assert exact.field_resolutions[2].status is FieldResolutionStatus.RESOLVED
    assert exact.field_resolutions[2].method is FieldResolutionMethod.EXACT
    fuzzy = apply_consumption_unit_safety(
        resolver.resolve_schema(("consumer_id", "timestamp", "Consumpton_kW")),
        source_power_unit=PowerUnit.KW,
    )
    assert fuzzy.field_resolutions[2].status is FieldResolutionStatus.RESOLVED
    assert fuzzy.field_resolutions[2].method is FieldResolutionMethod.FUZZY


def test_kw_profile_rejects_explicit_mw_and_energy_headers() -> None:
    specs = default_consumption_field_specs(PowerUnit.KW)
    resolver = DeterministicFieldResolver(specs)
    for header in ("value_mw", "Consumption_MW", "Consumption_MWh", "Consumption_kWh"):
        schema = apply_consumption_unit_safety(
            resolver.resolve_schema(("consumer_id", "timestamp", header)),
            source_power_unit=PowerUnit.KW,
        )
        assert schema.field_resolutions[2].status is FieldResolutionStatus.UNRESOLVED
        assert "value_mw" in schema.missing_required_fields
