"""Canonical timestamp, strictness, numeric, and monetary behavior."""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from math import inf, nan

import pytest
from pydantic import ValidationError

from energy_trading.domain.models import ConsumptionRecord, WeatherRecord
from energy_trading.domain.value_objects import EnergyPrice, MoneyAmount
from tests.unit.domain._factories import consumption, utc


def test_timezone_aware_timestamp_is_normalized_to_utc() -> None:
    yerevan = timezone(timedelta(hours=4))
    record = consumption(timestamp=datetime(2026, 10, 1, 14, 0, 0, tzinfo=yerevan))

    assert record.timestamp == datetime(2026, 10, 1, 10, 0, 0, tzinfo=UTC)
    assert record.timestamp.tzinfo is UTC


def test_offset_iso_string_is_normalized_to_utc() -> None:
    record = consumption(timestamp="2026-10-01T14:00:00+04:00")

    assert record.timestamp == datetime(2026, 10, 1, 10, 0, 0, tzinfo=UTC)


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(ValidationError):
        consumption(timestamp=datetime(2026, 10, 1, 14, 0, 0))


def test_naive_iso_string_is_rejected() -> None:
    with pytest.raises(ValidationError):
        consumption(timestamp="2026-10-01T14:00:00")


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ConsumptionRecord.model_validate(
            {
                "consumer_id": "consumer-1",
                "timestamp": utc(),
                "value_mw": 1.0,
                "Consumption_kW": 1000,
            }
        )


def test_frozen_model_rejects_mutation() -> None:
    record = consumption()
    with pytest.raises(ValidationError):
        record.value_mw = 9.0  # type: ignore[misc]


def test_negative_mw_is_rejected() -> None:
    with pytest.raises(ValidationError):
        consumption(value_mw=-0.1)


def test_nan_and_infinity_mw_are_rejected() -> None:
    with pytest.raises(ValidationError):
        consumption(value_mw=nan)
    with pytest.raises(ValidationError):
        consumption(value_mw=inf)


def test_negative_optional_weather_measurement_is_rejected() -> None:
    with pytest.raises(ValidationError):
        WeatherRecord(
            location_id="loc-1",
            timestamp=utc(),
            temperature_c=12.0,
            precipitation_mm=-1.0,
        )


def test_valid_currency_code_is_accepted() -> None:
    price = EnergyPrice(amount_per_mwh=Decimal("10.00"), currency="EUR")
    assert price.currency == "EUR"


def test_malformed_currency_code_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EnergyPrice(amount_per_mwh=Decimal("10.00"), currency="amd")
    with pytest.raises(ValidationError):
        EnergyPrice(amount_per_mwh=Decimal("10.00"), currency="AM")
    with pytest.raises(ValidationError):
        EnergyPrice(amount_per_mwh=Decimal("10.00"), currency="EURO")


def test_monetary_values_preserve_decimal_and_reject_float() -> None:
    amount = MoneyAmount(amount=Decimal("10.50"), currency="AMD")
    assert amount.amount == Decimal("10.50")
    assert isinstance(amount.amount, Decimal)

    with pytest.raises(ValidationError):
        MoneyAmount(amount=10.5, currency="AMD")  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        EnergyPrice(amount_per_mwh=Decimal("NaN"), currency="AMD")
