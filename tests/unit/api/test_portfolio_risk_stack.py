"""Portfolio & Risk execution composition wires published application objects.

Reader and assessment fakes are test-only structural port implementations.
Assessments are caller-prepared fixtures, not results of a risk engine.
"""

from __future__ import annotations

import inspect
from datetime import date

import pytest

from energy_trading.api.composition import portfolio_risk_stack
from energy_trading.api.composition.portfolio_risk_stack import (
    build_portfolio_risk_execution_service,
)
from energy_trading.application.agents.base import AgentPort
from energy_trading.application.agents.portfolio_risk import PortfolioRiskAgent
from energy_trading.application.errors import DependencyUnavailableError, ResourceNotFoundError
from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.application.orchestration.forecasting_success_read import (
    ForecastingSuccessReadPort,
)
from energy_trading.application.orchestration.portfolio_risk_execution import (
    PortfolioRiskExecutionService,
)
from energy_trading.application.ports.portfolio_risk_assessment import (
    PortfolioRiskAssessmentPort,
    PortfolioRiskAssessmentRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint, PriceForecastPoint
from energy_trading.domain.models.observations import GenerationAvailabilityRecord, HydroRecord
from energy_trading.domain.models.regulatory import RegulatoryConstraint
from energy_trading.domain.models.trading import RiskAssessment
from energy_trading.domain.value_objects.quantities import EntityId
from tests.unit.domain._factories import amd_money, amd_price, availability, constraint, utc

_WORKFLOW_ID = "workflow-risk-stack-1"
_PORTFOLIO_ID = "portfolio-risk-stack"
_DELIVERY_DATE = date(2026, 10, 2)


class _FakeForecastReader:
    """Test-only reader fake. Not a storage adapter and not a production reader."""

    def __init__(
        self,
        successes: dict[str, ForecastingSuccess] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._successes = successes or {}
        self._error = error
        self.calls: list[str] = []

    async def get_success(self, *, workflow_id: str) -> ForecastingSuccess:
        self.calls.append(workflow_id)
        if self._error is not None:
            raise self._error
        return self._successes[workflow_id]


class _FakeAssessmentPort:
    """Test-only assessment fake. Not a risk engine."""

    def __init__(
        self,
        result: RiskAssessment | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls: list[PortfolioRiskAssessmentRequest] = []

    async def assess(self, *, request: PortfolioRiskAssessmentRequest) -> RiskAssessment:
        self.calls.append(request)
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


def _as_reader(reader: _FakeForecastReader) -> ForecastingSuccessReadPort:
    return reader


def _as_assessment_port(port: _FakeAssessmentPort) -> PortfolioRiskAssessmentPort:
    return port


def _build(
    reader: _FakeForecastReader,
    port: _FakeAssessmentPort,
) -> PortfolioRiskExecutionService:
    return build_portfolio_risk_execution_service(
        forecast_reader=_as_reader(reader),
        assessment_port=_as_assessment_port(port),
    )


class _RecordingPortfolioRiskAgent(PortfolioRiskAgent):
    instances: list[_RecordingPortfolioRiskAgent] = []
    run_calls: int = 0

    def __init__(self, *, assessment_port: PortfolioRiskAssessmentPort) -> None:
        super().__init__(assessment_port=assessment_port)
        self.received_assessment_port = assessment_port
        type(self).instances.append(self)

    async def run(self, request: PortfolioRiskAssessmentRequest) -> RiskAssessment:
        type(self).run_calls += 1
        return await super().run(request)


class _RecordingPortfolioRiskExecutionService(PortfolioRiskExecutionService):
    instances: list[_RecordingPortfolioRiskExecutionService] = []
    execute_calls: int = 0

    def __init__(
        self,
        *,
        forecast_reader: ForecastingSuccessReadPort,
        risk_agent: AgentPort[PortfolioRiskAssessmentRequest, RiskAssessment],
    ) -> None:
        super().__init__(forecast_reader=forecast_reader, risk_agent=risk_agent)
        self.received_forecast_reader = forecast_reader
        self.received_risk_agent = risk_agent
        type(self).instances.append(self)

    async def execute(
        self,
        *,
        workflow_id: str,
        portfolio_id: EntityId,
        delivery_date: date,
        generation_availability: tuple[GenerationAvailabilityRecord, ...],
        hydro_resources: tuple[HydroRecord, ...],
        regulatory_constraints: tuple[RegulatoryConstraint, ...],
    ) -> RiskAssessment:
        type(self).execute_calls += 1
        return await super().execute(
            workflow_id=workflow_id,
            portfolio_id=portfolio_id,
            delivery_date=delivery_date,
            generation_availability=generation_availability,
            hydro_resources=hydro_resources,
            regulatory_constraints=regulatory_constraints,
        )


@pytest.fixture
def recording_constructors(monkeypatch: pytest.MonkeyPatch) -> None:
    _RecordingPortfolioRiskAgent.instances = []
    _RecordingPortfolioRiskAgent.run_calls = 0
    _RecordingPortfolioRiskExecutionService.instances = []
    _RecordingPortfolioRiskExecutionService.execute_calls = 0
    monkeypatch.setattr(portfolio_risk_stack, "PortfolioRiskAgent", _RecordingPortfolioRiskAgent)
    monkeypatch.setattr(
        portfolio_risk_stack,
        "PortfolioRiskExecutionService",
        _RecordingPortfolioRiskExecutionService,
    )


def _success() -> ForecastingSuccess:
    load_point = LoadForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "consumer_id": "consumer-1",
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "value_mw": 3.25,
        }
    )
    price_point = PriceForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "market_id": "market-1",
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "price": amd_price("45.00"),
        }
    )
    return ForecastingSuccess(
        consumer_load_forecast=(load_point,),
        dam_price_forecast=(price_point,),
    )


def _hydro() -> HydroRecord:
    return HydroRecord.model_validate(
        {
            "resource_id": "hydro-1",
            "timestamp": utc(),
            "reservoir_level_m": 12.5,
            "available_generation_mw": 4.0,
        }
    )


def _assessment() -> RiskAssessment:
    return RiskAssessment.model_validate(
        {
            "assessment_id": "assessment-stack-1",
            "assessed_at": utc(hour=9),
            "delivery_timestamp": utc(day=2, hour=16),
            "risk_score": 0.4,
            "expected_margin": amd_money("1500.00"),
            "value_at_risk": amd_money("250.00"),
            "notes": "caller-prepared test assessment",
        }
    )


async def _execute(
    service: PortfolioRiskExecutionService,
    workflow_id: str = _WORKFLOW_ID,
) -> RiskAssessment:
    return await service.execute(
        workflow_id=workflow_id,
        portfolio_id=_PORTFOLIO_ID,
        delivery_date=_DELIVERY_DATE,
        generation_availability=(availability(),),
        hydro_resources=(_hydro(),),
        regulatory_constraints=(constraint(),),
    )


def test_builder_signature_is_keyword_only_two_application_ports() -> None:
    signature = inspect.signature(build_portfolio_risk_execution_service)
    assert tuple(signature.parameters) == ("forecast_reader", "assessment_port")
    for parameter in signature.parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    assert signature.parameters["forecast_reader"].annotation is ForecastingSuccessReadPort
    assert signature.parameters["assessment_port"].annotation is PortfolioRiskAssessmentPort
    assert signature.return_annotation is PortfolioRiskExecutionService
    assert not inspect.iscoroutinefunction(build_portfolio_risk_execution_service)


def test_builder_rejects_positional_arguments() -> None:
    reader = _FakeForecastReader()
    port = _FakeAssessmentPort()
    with pytest.raises(TypeError):
        build_portfolio_risk_execution_service(reader, port)  # type: ignore[call-arg]


def test_builder_returns_the_existing_execution_service_type() -> None:
    service = _build(_FakeForecastReader(), _FakeAssessmentPort())
    assert type(service) is PortfolioRiskExecutionService
    assert ForecastingSuccessReadPort not in _FakeForecastReader.__mro__
    assert PortfolioRiskAssessmentPort not in _FakeAssessmentPort.__mro__


def test_builder_forwards_identities_through_each_constructor(
    recording_constructors: None,
) -> None:
    reader = _FakeForecastReader()
    port = _FakeAssessmentPort()

    service = _build(reader, port)

    assert len(_RecordingPortfolioRiskAgent.instances) == 1
    assert len(_RecordingPortfolioRiskExecutionService.instances) == 1
    agent = _RecordingPortfolioRiskAgent.instances[0]
    built = _RecordingPortfolioRiskExecutionService.instances[0]
    assert agent.received_assessment_port is port
    assert built.received_forecast_reader is reader
    assert built.received_risk_agent is agent
    assert service is built


def test_builder_does_not_execute_anything(recording_constructors: None) -> None:
    reader = _FakeForecastReader()
    port = _FakeAssessmentPort()

    _build(reader, port)

    assert reader.calls == []
    assert port.calls == []
    assert _RecordingPortfolioRiskAgent.run_calls == 0
    assert _RecordingPortfolioRiskExecutionService.execute_calls == 0


async def test_assembled_service_reads_once_and_delegates_once_through_real_agent() -> None:
    success = _success()
    expected = _assessment()
    reader = _FakeForecastReader({_WORKFLOW_ID: success})
    port = _FakeAssessmentPort(expected)
    service = _build(reader, port)
    generation = (availability(),)
    hydro = (_hydro(),)
    regulatory = (constraint(),)

    result = await service.execute(
        workflow_id=_WORKFLOW_ID,
        portfolio_id=_PORTFOLIO_ID,
        delivery_date=_DELIVERY_DATE,
        generation_availability=generation,
        hydro_resources=hydro,
        regulatory_constraints=regulatory,
    )

    assert result is expected
    assert reader.calls == [_WORKFLOW_ID]
    assert len(port.calls) == 1
    request = port.calls[0]
    assert request.workflow_id == _WORKFLOW_ID
    assert request.portfolio_id == _PORTFOLIO_ID
    assert request.delivery_date == _DELIVERY_DATE
    assert request.forecasting_success is success
    assert request.generation_availability is generation
    assert request.hydro_resources is hydro
    assert request.regulatory_constraints is regulatory
    assert result.risk_score == 0.4
    assert result.value_at_risk == amd_money("250.00")


@pytest.mark.parametrize(
    "error",
    [
        ResourceNotFoundError("Forecasting success was not found."),
        DependencyUnavailableError("Forecasting success reader is unavailable."),
    ],
)
async def test_reader_failure_propagates_without_assessment(error: Exception) -> None:
    reader = _FakeForecastReader(error=error)
    port = _FakeAssessmentPort(_assessment())
    service = _build(reader, port)

    with pytest.raises(type(error)) as captured:
        await _execute(service)

    assert captured.value is error
    assert reader.calls == [_WORKFLOW_ID]
    assert port.calls == []


async def test_assessment_failure_propagates_unchanged_without_fallback() -> None:
    error = DependencyUnavailableError("Portfolio risk assessment is unavailable.")
    reader = _FakeForecastReader({_WORKFLOW_ID: _success()})
    port = _FakeAssessmentPort(error=error)
    service = _build(reader, port)

    with pytest.raises(DependencyUnavailableError) as captured:
        await _execute(service)

    assert captured.value is error
    assert reader.calls == [_WORKFLOW_ID]
    assert len(port.calls) == 1


async def test_independent_builds_use_only_their_own_dependencies() -> None:
    first_success = _success()
    second_success = _success()
    first_expected = _assessment()
    second_expected = _assessment()
    first_reader = _FakeForecastReader({_WORKFLOW_ID: first_success})
    second_reader = _FakeForecastReader({_WORKFLOW_ID: second_success})
    first_port = _FakeAssessmentPort(first_expected)
    second_port = _FakeAssessmentPort(second_expected)

    first = _build(first_reader, first_port)
    second = _build(second_reader, second_port)

    assert first is not second
    assert await _execute(first) is first_expected
    assert first_reader.calls == [_WORKFLOW_ID]
    assert [request.forecasting_success for request in first_port.calls] == [first_success]
    assert first_port.calls[0].forecasting_success is first_success
    assert second_reader.calls == []
    assert second_port.calls == []

    assert await _execute(second) is second_expected
    assert second_reader.calls == [_WORKFLOW_ID]
    assert second_port.calls[0].forecasting_success is second_success
    assert len(first_reader.calls) == 1
    assert len(first_port.calls) == 1


def test_repeated_builds_construct_new_object_graphs(recording_constructors: None) -> None:
    reader = _FakeForecastReader()
    port = _FakeAssessmentPort()

    first = _build(reader, port)
    second = _build(reader, port)

    assert first is not second
    first_agent, second_agent = _RecordingPortfolioRiskAgent.instances
    assert first_agent is not second_agent
    assert first_agent.received_assessment_port is port
    assert second_agent.received_assessment_port is port
