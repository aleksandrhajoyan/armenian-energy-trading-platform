"""DAM Price Forecast Agent application contract."""

from __future__ import annotations

from decimal import Decimal

import pytest
from tests.unit.domain._factories import amd_price, utc

from energy_trading.application.agents.base import AgentName, AgentPort
from energy_trading.application.agents.dam_price_forecast import DAMPriceForecastAgent
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports.dam_price_forecast_model import (
    DAMPriceForecastModelPort,
    DAMPriceForecastModelRequest,
)
from energy_trading.domain.models.forecasting import PriceForecastPoint
from energy_trading.domain.models.observations import MarketPriceRecord
from energy_trading.domain.value_objects.money import EnergyPrice


class _FakeDAMPriceForecastModel:
    """Test-only model fake. Not a production adapter."""

    def __init__(
        self,
        points: tuple[PriceForecastPoint, ...] = (),
        *,
        error: Exception | None = None,
    ) -> None:
        self.points = points
        self.error = error
        self.calls: list[DAMPriceForecastModelRequest] = []

    async def forecast(
        self,
        *,
        request: DAMPriceForecastModelRequest,
    ) -> tuple[PriceForecastPoint, ...]:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.points


def _as_agent_port(
    agent: DAMPriceForecastAgent,
) -> AgentPort[DAMPriceForecastModelRequest, tuple[PriceForecastPoint, ...]]:
    """Mypy-visible structural assignment to the shared agent port."""

    return agent


def _market(**overrides: object) -> MarketPriceRecord:
    values: dict[str, object] = {
        "market_id": "market-1",
        "timestamp": utc(),
        "price": amd_price(),
    }
    values.update(overrides)
    return MarketPriceRecord.model_validate(values)


def _point(**overrides: object) -> PriceForecastPoint:
    values: dict[str, object] = {
        "forecast_run_id": "run-1",
        "market_id": "market-1",
        "generated_at": utc(),
        "target_timestamp": utc(hour=16),
        "price": amd_price("45.00"),
    }
    values.update(overrides)
    return PriceForecastPoint.model_validate(values)


def _request(**overrides: object) -> DAMPriceForecastModelRequest:
    values: dict[str, object] = {
        "market_id": "market-1",
        "currency": "AMD",
        "history": (_market(),),
        "target_timestamps": (utc(hour=16),),
    }
    values.update(overrides)
    return DAMPriceForecastModelRequest(**values)  # type: ignore[arg-type]


def test_agent_does_not_inherit_agent_port() -> None:
    assert AgentPort not in DAMPriceForecastAgent.__mro__
    assert not any(base.__name__ == "AgentPort" for base in DAMPriceForecastAgent.__bases__)


def test_fake_does_not_inherit_production_model_port() -> None:
    assert DAMPriceForecastModelPort not in _FakeDAMPriceForecastModel.__mro__
    assert not any(
        base.__name__ == "DAMPriceForecastModelPort"
        for base in _FakeDAMPriceForecastModel.__bases__
    )


def test_agent_name_is_canonical_dam_price_forecast_identity() -> None:
    agent = DAMPriceForecastAgent(_FakeDAMPriceForecastModel())
    port = _as_agent_port(agent)
    assert port.name is AgentName.DAM_PRICE_FORECAST
    assert port.name.value == "DAM Price Forecast Agent"
    assert len(AgentName) == 13


async def test_run_delegates_exact_request_and_returns_exact_points() -> None:
    first_price = amd_price("45.00")
    second_price = EnergyPrice(amount_per_mwh=Decimal("10.50"), currency="EUR")
    first = _point(price=first_price)
    second = _point(target_timestamp=utc(hour=17), price=second_price)
    model = _FakeDAMPriceForecastModel((first, second))
    agent = DAMPriceForecastAgent(model)
    request = _request()
    result = await _as_agent_port(agent).run(request)
    assert len(model.calls) == 1
    assert model.calls[0] is request
    assert result is model.points
    assert result == (first, second)
    assert result[0] is first
    assert result[1] is second


async def test_run_empty_model_result_is_valid() -> None:
    model = _FakeDAMPriceForecastModel()
    result = await DAMPriceForecastAgent(model).run(_request())
    assert result == ()
    assert isinstance(result, tuple)
    assert result is model.points
    assert len(model.calls) == 1


async def test_run_does_not_alter_price_currency_or_reorder_points() -> None:
    first_price = amd_price("45.00")
    second_price = EnergyPrice(amount_per_mwh=Decimal("90.00"), currency="AMD")
    first = _point(price=first_price, target_timestamp=utc(hour=18))
    second = _point(price=second_price, target_timestamp=utc(hour=12))
    model = _FakeDAMPriceForecastModel((first, second))
    result = await DAMPriceForecastAgent(model).run(_request())
    assert result == (first, second)
    assert result[0] is first
    assert result[1] is second
    assert result[0].price is first_price
    assert result[1].price is second_price
    assert result[0].price.amount_per_mwh == Decimal("45.00")
    assert result[1].price.amount_per_mwh == Decimal("90.00")
    assert result[0].price.currency == "AMD"
    assert result[1].price.currency == "AMD"


async def test_run_propagates_dependency_unavailable_without_retry() -> None:
    error = DependencyUnavailableError("dam price forecast model unavailable")
    model = _FakeDAMPriceForecastModel(error=error)
    agent = DAMPriceForecastAgent(model)
    with pytest.raises(
        DependencyUnavailableError, match="dam price forecast model unavailable"
    ) as caught:
        await agent.run(_request())
    assert caught.value is error
    assert len(model.calls) == 1
