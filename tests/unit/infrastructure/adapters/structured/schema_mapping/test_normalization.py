"""Deterministic field-name normalization."""

import unicodedata

import pytest

from energy_trading.infrastructure.adapters.structured.schema_mapping import (
    normalize_field_name,
)


def test_case_is_folded() -> None:
    assert normalize_field_name("Consumption_MW") == normalize_field_name("consumption_mw")
    assert normalize_field_name("CONSUMPTION_MW") == "consumption mw"


def test_underscores_hyphens_and_spaces_are_equivalent() -> None:
    assert normalize_field_name("Consumption_MW") == "consumption mw"
    assert normalize_field_name("consumption-mw") == "consumption mw"
    assert normalize_field_name("  CONSUMPTION   MW") == "consumption mw"
    assert (
        normalize_field_name("Consumption_MW")
        == normalize_field_name("consumption-mw")
        == normalize_field_name("  CONSUMPTION   MW")
    )


def test_repeated_whitespace_and_mixed_separators_collapse() -> None:
    assert normalize_field_name("Energy___Usage") == "energy usage"
    assert normalize_field_name("Energy---Usage") == "energy usage"
    assert normalize_field_name("Energy \t  Usage") == "energy usage"
    assert normalize_field_name("Energy.Usage") == "energy usage"


def test_nfkc_compatibility_characters_are_normalized() -> None:
    ligature = "ﬁ"  # U+FB01 LATIN SMALL LIGATURE FI
    assert unicodedata.normalize("NFKC", ligature) == "fi"
    assert normalize_field_name(f"{ligature}eld") == "field"

    fullwidth = "Ｃｏｎｓｕｍｐｔｉｏｎ＿ＭＷ"
    assert normalize_field_name(fullwidth) == normalize_field_name("Consumption_MW")

    nbsp = "Consumption\u00a0MW"
    assert normalize_field_name(nbsp) == "consumption mw"


def test_armenian_letters_are_preserved_and_casefolded() -> None:
    # Test-only Unicode sample; not claimed DAM terminology.
    assert normalize_field_name("Սպառում") == "սպառում"
    assert normalize_field_name("ՍՊԱՌՈՒՄ") == "սպառում"
    assert normalize_field_name("  Սպառում_ՄՎ  ") == "սպառում մվ"
    assert normalize_field_name("սպառում-մվ") == "սպառում մվ"
    assert "consumption" not in normalize_field_name("Սպառում")


def test_empty_and_whitespace_only_headers_normalize_to_empty() -> None:
    assert normalize_field_name("") == ""
    assert normalize_field_name("   ") == ""
    assert normalize_field_name("\t\n") == ""
    assert normalize_field_name("___") == ""
    assert normalize_field_name("---") == ""


def test_non_string_input_is_rejected() -> None:
    with pytest.raises(TypeError, match="string"):
        normalize_field_name(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="string"):
        normalize_field_name(1)  # type: ignore[arg-type]


def test_normalization_is_deterministic() -> None:
    raw = "  Consumption__MW  "
    first = normalize_field_name(raw)
    for _ in range(20):
        assert normalize_field_name(raw) == first
