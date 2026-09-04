"""Pydantic v2 JSON serialization of representative canonical contracts."""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

from energy_trading.domain.models import BidSide, LoadForecastPoint, MarketBid
from energy_trading.domain.value_objects import EnergyPrice
from tests.unit.domain._factories import utc


def test_nested_price_enum_decimal_and_utc_serialize_stably() -> None:
    yerevan = timezone(timedelta(hours=4))
    bid = MarketBid(
        bid_id="bid-1",
        created_at=datetime(2026, 10, 1, 14, 0, 0, tzinfo=yerevan),
        delivery_timestamp=utc(hour=16),
        side=BidSide.SELL,
        quantity_mw=5.0,
        limit_price=EnergyPrice(amount_per_mwh=Decimal("12.50"), currency="AMD"),
    )

    payload = bid.model_dump(mode="json")

    assert payload["created_at"] == "2026-10-01T10:00:00+00:00"
    assert payload["side"] == "sell"
    assert payload["limit_price"] == {"amount_per_mwh": "12.50", "currency": "AMD"}
    round_trip = MarketBid.model_validate(payload)
    assert round_trip.limit_price.amount_per_mwh == Decimal("12.50")
    assert round_trip.created_at == datetime(2026, 10, 1, 10, 0, 0, tzinfo=UTC)


def test_load_forecast_serializes_mw_and_utc() -> None:
    point = LoadForecastPoint(
        forecast_run_id="run-1",
        consumer_id="consumer-1",
        generated_at=utc(),
        target_timestamp=utc(hour=16),
        value_mw=3.25,
    )
    payload = point.model_dump(mode="json")
    assert payload["generated_at"] == "2026-10-01T10:00:00+00:00"
    assert payload["value_mw"] == 3.25
