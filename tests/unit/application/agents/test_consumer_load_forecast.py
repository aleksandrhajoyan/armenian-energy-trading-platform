"""Consumer Load Forecast Agent application contract."""

from __future__ import annotations

import pytest
from tests.unit.domain._factories import consumption, utc

from energy_trading.application.agents.base import AgentName, AgentPort
from energy_trading.application.agents.consumer_load_forecast import ConsumerLoadForecastAgent
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelPort,
    ConsumerLoadForecastModelRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint


class _FakeConsumerLoadForecastModel:
    """Test-only model fake. Not a production adapter."""

    def __init__(
        self,
        points: tuple[LoadForecastPoint, ...] = (),
        *,
        error: Exception | None = None,
    ) -> None:
        self.points = points
        self.error = error
        self.calls: list[ConsumerLoadForecastModelRequest] = []

    async def forecast(
        self,
        *,
        request: ConsumerLoadForecastModelRequest,
    ) -> tuple[LoadForecastPoint, ...]:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.points


def _as_agent_port(
    agent: ConsumerLoadForecastAgent,
) -> AgentPort[ConsumerLoadForecastModelRequest, tuple[LoadForecastPoint, ...]]:
    """Mypy-visible structural assignment to the shared agent port."""

    return agent


def _point(**overrides: object) -> LoadForecastPoint:
    values: dict[str, object] = {
        "forecast_run_id": "run-1",
        "consumer_id": "consumer-1",
        "generated_at": utc(),
        "target_timestamp": utc(hour=16),
        "value_mw": 3.25,
    }
    values.update(overrides)
    return LoadForecastPoint.model_validate(values)


def _request(**overrides: object) -> ConsumerLoadForecastModelRequest:
    values: dict[str, object] = {
        "consumer_id": "consumer-1",
        "history": (consumption(),),
        "target_timestamps": (utc(hour=16),),
    }
    values.update(overrides)
    return ConsumerLoadForecastModelRequest(**values)  # type: ignore[arg-type]


def test_agent_does_not_inherit_agent_port() -> None:
    assert AgentPort not in ConsumerLoadForecastAgent.__mro__
    assert not any(base.__name__ == "AgentPort" for base in ConsumerLoadForecastAgent.__bases__)


def test_fake_does_not_inherit_production_model_port() -> None:
    assert ConsumerLoadForecastModelPort not in _FakeConsumerLoadForecastModel.__mro__
    assert not any(
        base.__name__ == "ConsumerLoadForecastModelPort"
        for base in _FakeConsumerLoadForecastModel.__bases__
    )


def test_agent_name_is_canonical_consumer_load_forecast_identity() -> None:
    agent = ConsumerLoadForecastAgent(_FakeConsumerLoadForecastModel())
    port = _as_agent_port(agent)
    assert port.name is AgentName.CONSUMER_LOAD_FORECAST
    assert port.name.value == "Consumer Load Forecast Agent"
    assert len(AgentName) == 13


async def test_run_delegates_exact_request_and_returns_exact_points() -> None:
    first = _point()
    second = _point(target_timestamp=utc(hour=17), value_mw=4.5)
    model = _FakeConsumerLoadForecastModel((first, second))
    agent = ConsumerLoadForecastAgent(model)
    request = _request()
    result = await _as_agent_port(agent).run(request)
    assert len(model.calls) == 1
    assert model.calls[0] is request
    assert result is model.points
    assert result == (first, second)
    assert result[0] is first
    assert result[1] is second
    assert result[0].value_mw == 3.25
    assert result[1].value_mw == 4.5


async def test_run_empty_model_result_is_valid() -> None:
    model = _FakeConsumerLoadForecastModel()
    result = await ConsumerLoadForecastAgent(model).run(_request())
    assert result == ()
    assert isinstance(result, tuple)
    assert result is model.points
    assert len(model.calls) == 1


async def test_run_does_not_alter_mw_or_reorder_points() -> None:
    first = _point(value_mw=1.0, target_timestamp=utc(hour=18))
    second = _point(value_mw=9.75, target_timestamp=utc(hour=12))
    model = _FakeConsumerLoadForecastModel((first, second))
    result = await ConsumerLoadForecastAgent(model).run(_request())
    assert result == (first, second)
    assert result[0] is first
    assert result[1] is second
    assert result[0].value_mw == 1.0
    assert result[1].value_mw == 9.75


async def test_run_propagates_dependency_unavailable_without_retry() -> None:
    error = DependencyUnavailableError("consumer load forecast model unavailable")
    model = _FakeConsumerLoadForecastModel(error=error)
    agent = ConsumerLoadForecastAgent(model)
    with pytest.raises(
        DependencyUnavailableError, match="consumer load forecast model unavailable"
    ) as caught:
        await agent.run(_request())
    assert caught.value is error
    assert len(model.calls) == 1
