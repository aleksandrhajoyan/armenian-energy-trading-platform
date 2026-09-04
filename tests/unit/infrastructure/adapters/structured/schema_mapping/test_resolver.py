"""Deterministic field and schema resolution."""

from dataclasses import FrozenInstanceError, fields
from math import inf, nan

import pytest

from energy_trading.infrastructure.adapters.structured.schema_mapping import (
    CanonicalFieldSpec,
    DeterministicFieldResolver,
    FieldResolutionMethod,
    FieldResolutionStatus,
    ResolverConfigurationError,
    normalize_field_name,
)

# Local test schema shaped like ConsumptionRecord. Not a production alias catalog.
# "սպառում" is a test-only Unicode alias, not claimed DAM terminology.
_CONSUMPTION_SPECS = (
    CanonicalFieldSpec(
        canonical_name="consumer_id",
        aliases=("Consumer", "ConsumerID"),
        required=True,
    ),
    CanonicalFieldSpec(
        canonical_name="timestamp",
        aliases=("Time", "Datetime"),
        required=True,
    ),
    CanonicalFieldSpec(
        canonical_name="value_mw",
        aliases=(
            "Consumption_MW",
            "Consumption_kW",
            "Load",
            "Energy Usage",
            "սպառում",
        ),
        required=True,
    ),
)


def _resolver() -> DeterministicFieldResolver:
    return DeterministicFieldResolver(_CONSUMPTION_SPECS)


def test_canonical_name_is_an_exact_match_without_repeating_it_as_an_alias() -> None:
    resolution = _resolver().resolve_field("timestamp")
    assert resolution.status is FieldResolutionStatus.RESOLVED
    assert resolution.method is FieldResolutionMethod.EXACT
    assert resolution.canonical_field == "timestamp"
    assert resolution.confidence == 1.0

    value = _resolver().resolve_field("value_mw")
    assert value.status is FieldResolutionStatus.RESOLVED
    assert value.method is FieldResolutionMethod.EXACT
    assert value.canonical_field == "value_mw"


def test_configured_aliases_resolve_exactly() -> None:
    resolver = _resolver()
    load = resolver.resolve_field("Load")
    usage = resolver.resolve_field("Energy Usage")
    mw = resolver.resolve_field("Consumption_MW")

    assert load.canonical_field == "value_mw"
    assert usage.canonical_field == "value_mw"
    assert mw.canonical_field == "value_mw"
    assert load.method is FieldResolutionMethod.EXACT
    assert usage.method is FieldResolutionMethod.EXACT
    assert mw.method is FieldResolutionMethod.EXACT
    assert load.confidence == usage.confidence == mw.confidence == 1.0


def test_normalized_alias_is_an_exact_match() -> None:
    resolution = _resolver().resolve_field("  consumption-mw  ")
    assert resolution.status is FieldResolutionStatus.RESOLVED
    assert resolution.method is FieldResolutionMethod.EXACT
    assert resolution.canonical_field == "value_mw"
    assert resolution.normalized_source_field == "consumption mw"
    assert resolution.source_field == "  consumption-mw  "


def test_configured_armenian_alias_matches_exactly() -> None:
    resolver = _resolver()
    lower = resolver.resolve_field("սպառում")
    folded = resolver.resolve_field("ՍՊԱՌՈՒՄ")
    separated = resolver.resolve_field("  Սպառում  ")

    assert lower.status is FieldResolutionStatus.RESOLVED
    assert folded.status is FieldResolutionStatus.RESOLVED
    assert separated.status is FieldResolutionStatus.RESOLVED
    assert lower.method is folded.method is separated.method is FieldResolutionMethod.EXACT
    assert (
        lower.canonical_field == folded.canonical_field == separated.canonical_field == "value_mw"
    )
    assert normalize_field_name("ՍՊԱՌՈՒՄ") == "սպառում"


def test_clear_typo_resolves_by_fuzzy_match() -> None:
    resolution = _resolver().resolve_field("Consumpton_MW")
    assert resolution.status is FieldResolutionStatus.RESOLVED
    assert resolution.method is FieldResolutionMethod.FUZZY
    assert resolution.canonical_field == "value_mw"
    assert resolution.confidence >= 0.85
    assert resolution.confidence < 1.0


def test_unrelated_header_remains_unresolved() -> None:
    resolution = _resolver().resolve_field("wind_speed_knots")
    assert resolution.status is FieldResolutionStatus.UNRESOLVED
    assert resolution.canonical_field is None
    assert resolution.method is None
    assert resolution.confidence < 0.85


def test_empty_header_is_unresolved_without_raising() -> None:
    resolver = _resolver()
    for raw in ("", "   ", "\t", "___"):
        resolution = resolver.resolve_field(raw)
        assert resolution.status is FieldResolutionStatus.UNRESOLVED
        assert resolution.canonical_field is None
        assert resolution.method is None
        assert resolution.normalized_source_field == ""
        assert resolution.source_field == raw


def test_ambiguity_does_not_choose_a_canonical_field() -> None:
    resolver = DeterministicFieldResolver(
        (
            CanonicalFieldSpec(canonical_name="load_mw", aliases=(), required=False),
            CanonicalFieldSpec(canonical_name="load_kw", aliases=(), required=False),
        )
    )
    resolution = resolver.resolve_field("load_xw")

    assert resolution.status is FieldResolutionStatus.AMBIGUOUS
    assert resolution.canonical_field is None
    assert resolution.method is None
    assert len(resolution.candidates) >= 2
    canonicals = tuple(candidate.canonical_field for candidate in resolution.candidates)
    assert canonicals == tuple(sorted(canonicals))
    assert set(canonicals) == {"load_kw", "load_mw"}
    first = resolver.resolve_field("load_xw")
    second = resolver.resolve_field("load_xw")
    assert first.candidates == second.candidates


def test_duplicate_canonical_definitions_are_rejected() -> None:
    with pytest.raises(ResolverConfigurationError, match="duplicate canonical field"):
        DeterministicFieldResolver(
            (
                CanonicalFieldSpec("value_mw", aliases=("Load",), required=True),
                CanonicalFieldSpec("Value-MW", aliases=("Consumption",), required=True),
            )
        )


def test_canonical_name_versus_alias_collision_is_rejected() -> None:
    load_as_canonical = CanonicalFieldSpec(canonical_name="load", aliases=(), required=False)
    load_as_alias = CanonicalFieldSpec(
        canonical_name="value_mw",
        aliases=("Load",),
        required=False,
    )
    for specs in ((load_as_canonical, load_as_alias), (load_as_alias, load_as_canonical)):
        with pytest.raises(ResolverConfigurationError, match="assigned to both"):
            DeterministicFieldResolver(specs)


def test_empty_canonical_name_is_rejected() -> None:
    with pytest.raises(ResolverConfigurationError, match="canonical field name is empty"):
        DeterministicFieldResolver((CanonicalFieldSpec("   ", aliases=("Load",), required=True),))


def test_empty_alias_is_rejected() -> None:
    with pytest.raises(ResolverConfigurationError, match="empty after normalization"):
        DeterministicFieldResolver(
            (CanonicalFieldSpec("value_mw", aliases=("Load", "___"), required=True),)
        )


def test_normalized_alias_reused_across_canonical_fields_is_rejected() -> None:
    with pytest.raises(ResolverConfigurationError, match="assigned to both"):
        DeterministicFieldResolver(
            (
                CanonicalFieldSpec("value_mw", aliases=("Energy Usage",), required=True),
                CanonicalFieldSpec("volume_mwh", aliases=("energy-usage",), required=True),
            )
        )


def test_constructor_rejects_invalid_thresholds() -> None:
    specs = (CanonicalFieldSpec("timestamp", aliases=(), required=True),)
    for kwargs in (
        {"fuzzy_threshold": -0.1},
        {"fuzzy_threshold": 1.1},
        {"fuzzy_threshold": inf},
        {"fuzzy_threshold": nan},
        {"ambiguity_margin": -0.01},
        {"ambiguity_margin": 2.0},
        {"ambiguity_margin": inf},
    ):
        with pytest.raises(ResolverConfigurationError, match="finite number"):
            DeterministicFieldResolver(specs, **kwargs)


def test_schema_preserves_source_header_order() -> None:
    headers = ("Load", "timestamp", "Consumer")
    result = _resolver().resolve_schema(headers)
    assert tuple(item.source_field for item in result.field_resolutions) == headers
    assert tuple(item.canonical_field for item in result.field_resolutions) == (
        "value_mw",
        "timestamp",
        "consumer_id",
    )
    assert result.missing_required_fields == ()
    assert result.collisions == ()


def test_missing_required_fields_are_reported() -> None:
    result = _resolver().resolve_schema(("Load",))
    assert result.field_resolutions[0].canonical_field == "value_mw"
    assert result.missing_required_fields == ("consumer_id", "timestamp")
    assert result.collisions == ()


def test_duplicate_destination_collision_is_reported_without_overwrite() -> None:
    headers = ("Load", "Consumption_MW", "timestamp", "Consumer")
    result = _resolver().resolve_schema(headers)

    assert tuple(item.source_field for item in result.field_resolutions) == headers
    assert result.field_resolutions[0].canonical_field == "value_mw"
    assert result.field_resolutions[1].canonical_field == "value_mw"
    assert len(result.collisions) == 1
    collision = result.collisions[0]
    assert collision.canonical_field == "value_mw"
    assert collision.source_fields == ("Load", "Consumption_MW")
    assert result.missing_required_fields == ()


def test_mw_and_kw_aliases_resolve_to_the_same_field_without_unit_conversion() -> None:
    resolver = _resolver()
    mw = resolver.resolve_field("Consumption_MW")
    kw = resolver.resolve_field("Consumption_kW")

    assert mw.canonical_field == kw.canonical_field == "value_mw"
    assert mw.status is kw.status is FieldResolutionStatus.RESOLVED
    field_names = {item.name for item in fields(mw)}
    assert "value" not in field_names
    assert "unit" not in field_names
    assert "converted_value" not in field_names
    assert mw.canonical_field == "value_mw"
    assert kw.canonical_field == "value_mw"


def test_resolution_results_are_immutable() -> None:
    resolution = _resolver().resolve_field("Load")
    with pytest.raises(FrozenInstanceError):
        resolution.canonical_field = "timestamp"  # type: ignore[misc]


def test_same_resolver_and_input_are_deterministic() -> None:
    resolver = _resolver()
    headers = ("Consumpton_MW", "wind_speed", "  Load  ", "սպառում", "")
    first_fields = tuple(resolver.resolve_field(item) for item in headers)
    first_schema = resolver.resolve_schema(headers)
    for _ in range(10):
        assert tuple(resolver.resolve_field(item) for item in headers) == first_fields
        assert resolver.resolve_schema(headers) == first_schema


def test_resolver_configuration_error_is_a_value_error() -> None:
    with pytest.raises(ValueError):
        DeterministicFieldResolver((CanonicalFieldSpec("", aliases=(), required=False),))
