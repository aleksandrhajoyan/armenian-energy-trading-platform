"""Forecasting execution composition wires published application objects."""

from __future__ import annotations

import inspect

import pytest

from energy_trading.api.composition import forecasting_execution
from energy_trading.api.composition.forecasting_execution import (
    build_parallel_forecasting_execution_service,
)
from energy_trading.application.agents.consumer_load_forecast import ConsumerLoadForecastAgent
from energy_trading.application.agents.dam_price_forecast import DAMPriceForecastAgent
from energy_trading.application.orchestration.forecasting_executor import (
    ParallelForecastingExecutionService,
)
from energy_trading.application.orchestration.forecasting_plan import ForecastingPlan
from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelPort,
    ConsumerLoadForecastModelRequest,
)
from energy_trading.application.ports.dam_price_forecast_model import (
    DAMPriceForecastModelPort,
    DAMPriceForecastModelRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint, PriceForecastPoint


class _FakeConsumerLoadModel:
    """Test-only fake that structurally satisfies ``ConsumerLoadForecastModelPort``."""

    def __init__(self) -> None:
        self.calls: list[ConsumerLoadForecastModelRequest] = []

    async def forecast(
        self,
        *,
        request: ConsumerLoadForecastModelRequest,
    ) -> tuple[LoadForecastPoint, ...]:
        self.calls.append(request)
        return ()


class _FakeDAMPriceModel:
    """Test-only fake that structurally satisfies ``DAMPriceForecastModelPort``."""

    def __init__(self) -> None:
        self.calls: list[DAMPriceForecastModelRequest] = []

    async def forecast(
        self,
        *,
        request: DAMPriceForecastModelRequest,
    ) -> tuple[PriceForecastPoint, ...]:
        self.calls.append(request)
        return ()


def _as_consumer_port(model: _FakeConsumerLoadModel) -> ConsumerLoadForecastModelPort:
    return model


def _as_dam_port(model: _FakeDAMPriceModel) -> DAMPriceForecastModelPort:
    return model


def _build(
    consumer_model: _FakeConsumerLoadModel,
    dam_model: _FakeDAMPriceModel,
) -> ParallelForecastingExecutionService:
    return build_parallel_forecasting_execution_service(
        consumer_load_model=_as_consumer_port(consumer_model),
        dam_price_model=_as_dam_port(dam_model),
    )


class _RecordingConsumerLoadForecastAgent(ConsumerLoadForecastAgent):
    instances: list[_RecordingConsumerLoadForecastAgent] = []
    run_calls: int = 0

    def __init__(self, model: ConsumerLoadForecastModelPort) -> None:
        super().__init__(model)
        self.received_model = model
        type(self).instances.append(self)

    async def run(self, request: ConsumerLoadForecastModelRequest) -> tuple[LoadForecastPoint, ...]:
        type(self).run_calls += 1
        return await super().run(request)


class _RecordingDAMPriceForecastAgent(DAMPriceForecastAgent):
    instances: list[_RecordingDAMPriceForecastAgent] = []
    run_calls: int = 0

    def __init__(self, model: DAMPriceForecastModelPort) -> None:
        super().__init__(model)
        self.received_model = model
        type(self).instances.append(self)

    async def run(self, request: DAMPriceForecastModelRequest) -> tuple[PriceForecastPoint, ...]:
        type(self).run_calls += 1
        return await super().run(request)


class _RecordingParallelForecastingExecutionService(ParallelForecastingExecutionService):
    instances: list[_RecordingParallelForecastingExecutionService] = []
    execute_calls: int = 0

    def __init__(
        self,
        consumer_load_forecast: ConsumerLoadForecastAgent,
        dam_price_forecast: DAMPriceForecastAgent,
    ) -> None:
        super().__init__(consumer_load_forecast, dam_price_forecast)
        self.received_consumer_load_forecast = consumer_load_forecast
        self.received_dam_price_forecast = dam_price_forecast
        type(self).instances.append(self)

    async def execute(self, *, plan: ForecastingPlan) -> ForecastingSuccess:
        type(self).execute_calls += 1
        return await super().execute(plan=plan)


@pytest.fixture
def recording_constructors(monkeypatch: pytest.MonkeyPatch) -> None:
    _RecordingConsumerLoadForecastAgent.instances = []
    _RecordingConsumerLoadForecastAgent.run_calls = 0
    _RecordingDAMPriceForecastAgent.instances = []
    _RecordingDAMPriceForecastAgent.run_calls = 0
    _RecordingParallelForecastingExecutionService.instances = []
    _RecordingParallelForecastingExecutionService.execute_calls = 0
    monkeypatch.setattr(
        forecasting_execution,
        "ConsumerLoadForecastAgent",
        _RecordingConsumerLoadForecastAgent,
    )
    monkeypatch.setattr(
        forecasting_execution,
        "DAMPriceForecastAgent",
        _RecordingDAMPriceForecastAgent,
    )
    monkeypatch.setattr(
        forecasting_execution,
        "ParallelForecastingExecutionService",
        _RecordingParallelForecastingExecutionService,
    )


def test_builder_signature_is_keyword_only_two_application_model_ports() -> None:
    signature = inspect.signature(build_parallel_forecasting_execution_service)
    assert tuple(signature.parameters) == ("consumer_load_model", "dam_price_model")
    for parameter in signature.parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    assert signature.parameters["consumer_load_model"].annotation is ConsumerLoadForecastModelPort
    assert signature.parameters["dam_price_model"].annotation is DAMPriceForecastModelPort
    assert signature.return_annotation is ParallelForecastingExecutionService
    assert not inspect.iscoroutinefunction(build_parallel_forecasting_execution_service)


def test_builder_accepts_structural_fakes_and_returns_existing_executor() -> None:
    service = _build(_FakeConsumerLoadModel(), _FakeDAMPriceModel())
    assert type(service) is ParallelForecastingExecutionService
    assert ConsumerLoadForecastModelPort not in _FakeConsumerLoadModel.__mro__
    assert DAMPriceForecastModelPort not in _FakeDAMPriceModel.__mro__


def test_builder_wires_real_agents_to_the_exact_supplied_models() -> None:
    consumer_model = _FakeConsumerLoadModel()
    dam_model = _FakeDAMPriceModel()
    service = _build(consumer_model, dam_model)

    consumer_agent = service._consumer_load_forecast
    dam_agent = service._dam_price_forecast
    assert type(consumer_agent) is ConsumerLoadForecastAgent
    assert type(dam_agent) is DAMPriceForecastAgent
    assert consumer_agent._model is consumer_model
    assert dam_agent._model is dam_model


def test_builder_forwards_identities_through_each_constructor(
    recording_constructors: None,
) -> None:
    consumer_model = _FakeConsumerLoadModel()
    dam_model = _FakeDAMPriceModel()
    service = _build(consumer_model, dam_model)

    assert len(_RecordingConsumerLoadForecastAgent.instances) == 1
    assert len(_RecordingDAMPriceForecastAgent.instances) == 1
    assert len(_RecordingParallelForecastingExecutionService.instances) == 1
    consumer_agent = _RecordingConsumerLoadForecastAgent.instances[0]
    dam_agent = _RecordingDAMPriceForecastAgent.instances[0]
    executor = _RecordingParallelForecastingExecutionService.instances[0]
    assert consumer_agent.received_model is consumer_model
    assert dam_agent.received_model is dam_model
    assert executor.received_consumer_load_forecast is consumer_agent
    assert executor.received_dam_price_forecast is dam_agent
    assert service is executor


def test_builder_does_not_invoke_models_agents_or_executor(
    recording_constructors: None,
) -> None:
    consumer_model = _FakeConsumerLoadModel()
    dam_model = _FakeDAMPriceModel()
    _build(consumer_model, dam_model)

    assert consumer_model.calls == []
    assert dam_model.calls == []
    assert _RecordingConsumerLoadForecastAgent.run_calls == 0
    assert _RecordingDAMPriceForecastAgent.run_calls == 0
    assert _RecordingParallelForecastingExecutionService.execute_calls == 0


def test_independent_builds_construct_independent_object_graphs() -> None:
    first_consumer = _FakeConsumerLoadModel()
    first_dam = _FakeDAMPriceModel()
    second_consumer = _FakeConsumerLoadModel()
    second_dam = _FakeDAMPriceModel()

    first = _build(first_consumer, first_dam)
    second = _build(second_consumer, second_dam)

    assert first is not second
    assert first._consumer_load_forecast is not second._consumer_load_forecast
    assert first._dam_price_forecast is not second._dam_price_forecast
    assert first._consumer_load_forecast._model is first_consumer
    assert first._dam_price_forecast._model is first_dam
    assert second._consumer_load_forecast._model is second_consumer
    assert second._dam_price_forecast._model is second_dam


def test_repeated_builds_with_same_models_still_construct_new_graphs() -> None:
    consumer_model = _FakeConsumerLoadModel()
    dam_model = _FakeDAMPriceModel()

    first = _build(consumer_model, dam_model)
    second = _build(consumer_model, dam_model)

    assert first is not second
    assert first._consumer_load_forecast is not second._consumer_load_forecast
    assert first._dam_price_forecast is not second._dam_price_forecast
    assert second._consumer_load_forecast._model is consumer_model
    assert second._dam_price_forecast._model is dam_model
