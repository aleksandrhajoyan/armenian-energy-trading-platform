"""Power-unit normalization primitive tests."""

from datetime import UTC, datetime

import pytest

from energy_trading.infrastructure.adapters.structured.normalization import (
    NormalizationConfigurationError,
    PowerUnit,
    SourceValueNormalizationError,
    normalize_power_to_mw,
)


def test_power_unit_enum_is_power_only() -> None:
    assert {member.value for member in PowerUnit} == {"MW", "KW"}
    assert not hasattr(PowerUnit, "MWH")
    assert not hasattr(PowerUnit, "KWH")


def test_mw_is_unchanged() -> None:
    assert normalize_power_to_mw(1, PowerUnit.MW) == 1.0
    assert normalize_power_to_mw(12.5, PowerUnit.MW) == 12.5


def test_kw_converts_deterministically() -> None:
    assert normalize_power_to_mw(1000, PowerUnit.KW) == 1.0
    assert normalize_power_to_mw(12500, PowerUnit.KW) == 12.5
    assert normalize_power_to_mw("12500", PowerUnit.KW) == 12.5
    first = normalize_power_to_mw(12500, PowerUnit.KW)
    second = normalize_power_to_mw(12500, PowerUnit.KW)
    assert first == second == 12.5


def test_boolean_power_is_rejected() -> None:
    for value in (True, False):
        with pytest.raises(SourceValueNormalizationError):
            normalize_power_to_mw(value, PowerUnit.MW)
        with pytest.raises(SourceValueNormalizationError):
            normalize_power_to_mw(value, PowerUnit.KW)


def test_invalid_power_unit_is_configuration_error() -> None:
    with pytest.raises(NormalizationConfigurationError):
        normalize_power_to_mw(1, "MW")  # type: ignore[arg-type]


def test_nonnumeric_power_is_source_error() -> None:
    with pytest.raises(SourceValueNormalizationError):
        normalize_power_to_mw("not-a-number", PowerUnit.MW)
    with pytest.raises(SourceValueNormalizationError):
        normalize_power_to_mw(datetime(2026, 1, 1, tzinfo=UTC), PowerUnit.MW)
