"""Portfolio & Risk forecast-to-assessment execution service contract.

These tests verify exact-identity forecast retrieval, request construction,
single agent delegation, and unchanged propagation only. They do not prove
any risk methodology and do not establish that the supplied inputs are
sufficient for a complete or acceptable risk assessment. Assessments are
explicit test doubles, not results of a risk engine.
"""

from __future__ import annotations

import inspect
from datetime import date

import pytest

from energy_trading.application.agents.base import AgentName, AgentPort
from energy_trading.application.agents.portfolio_risk import PortfolioRiskAgent
from energy_trading.application.errors import (
    DependencyUnavailableError,
    ResourceNotFoundError,
)
from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.application.orchestration.forecasting_success_read import (
    ForecastingSuccessReadPort,
)
from energy_trading.application.orchestration.portfolio_risk_execution import (
    PortfolioRiskExecutionService,
)
from energy_trading.application.orchestration.state import (
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)
from energy_trading.application.ports.portfolio_risk_assessment import (
    PortfolioRiskAssessmentPort,
    PortfolioRiskAssessmentRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint, PriceForecastPoint
from energy_trading.domain.models.observations import GenerationAvailabilityRecord, HydroRecord
from energy_trading.domain.models.regulatory import RegulatoryConstraint
from energy_trading.domain.models.trading import RiskAssessment
from energy_trading.infrastructure.orchestration.forecasting_context import (
    InMemoryForecastingWorkflowContext,
)
from energy_trading.infrastructure.orchestration.forecasting_read_after_write_context import (
    InMemoryForecastingReadAfterWriteContext,
)
from tests.unit.domain._factories import amd_money, amd_price, availability, constraint, utc

_WORKFLOW_ID = "workflow-risk-exec-1"
_OTHER_WORKFLOW_ID = "workflow-risk-exec-2"
_MSG_SUCCESS_NOT_FOUND = "Forecasting success was not found."


class _FakeForecastReader:
    """Test-only reader fake. Not a storage adapter and not a production reader."""

    def __init__(
        self,
        successes: dict[str, ForecastingSuccess] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.successes = successes or {}
        self.error = error
        self.calls: list[str] = []

    async def get_success(self, *, workflow_id: str) -> ForecastingSuccess:
        self.calls.append(workflow_id)
        if self.error is not None:
            raise self.error
        try:
            return self.successes[workflow_id]
        except KeyError:
            raise ResourceNotFoundError(_MSG_SUCCESS_NOT_FOUND) from None


class _FakeRiskAgent:
    """Test-only structural agent fake. Not a risk engine."""

    def __init__(
        self,
        results: dict[str, RiskAssessment] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.results = results or {}
        self.error = error
        self.calls: list[PortfolioRiskAssessmentRequest] = []

    @property
    def name(self) -> AgentName:
        return AgentName.PORTFOLIO_AND_RISK

    async def run(self, request: PortfolioRiskAssessmentRequest) -> RiskAssessment:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.results[request.workflow_id]


class _FakeAssessmentPort:
    """Test-only assessment fake behind the real agent. Not a risk engine."""

    def __init__(self, results: dict[str, RiskAssessment]) -> None:
        self.results = results
        self.calls: list[PortfolioRiskAssessmentRequest] = []

    async def assess(self, *, request: PortfolioRiskAssessmentRequest) -> RiskAssessment:
        self.calls.append(request)
        return self.results[request.workflow_id]


def _as_reader(reader: _FakeForecastReader) -> ForecastingSuccessReadPort:
    """Mypy-visible structural assignment to the published read port."""

    return reader


def _as_agent_port(
    agent: _FakeRiskAgent | PortfolioRiskAgent,
) -> AgentPort[PortfolioRiskAssessmentRequest, RiskAssessment]:
    """Mypy-visible structural assignment to the shared agent port."""

    return agent


def _as_assessment_port(fake: _FakeAssessmentPort) -> PortfolioRiskAssessmentPort:
    """Mypy-visible structural assignment to the published assessment port."""

    return fake


def _service(
    reader: ForecastingSuccessReadPort,
    agent: _FakeRiskAgent | PortfolioRiskAgent,
) -> PortfolioRiskExecutionService:
    return PortfolioRiskExecutionService(forecast_reader=reader, risk_agent=_as_agent_port(agent))


def _success(*, value_mw: float = 3.25, price: str = "45.00") -> ForecastingSuccess:
    load_point = LoadForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "consumer_id": "consumer-1",
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "value_mw": value_mw,
        }
    )
    price_point = PriceForecastPoint.model_validate(
        {
            "forecast_run_id": "run-1",
            "market_id": "market-1",
            "generated_at": utc(),
            "target_timestamp": utc(hour=16),
            "price": amd_price(price),
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


def _assessment(**overrides: object) -> RiskAssessment:
    values: dict[str, object] = {
        "assessment_id": "assessment-1",
        "assessed_at": utc(hour=9),
        "delivery_timestamp": utc(day=2, hour=16),
        "risk_score": 0.4,
        "expected_margin": amd_money("1500.00"),
        "value_at_risk": amd_money("250.00"),
        "notes": "caller-prepared assessment",
    }
    values.update(overrides)
    return RiskAssessment.model_validate(values)


def _inputs() -> tuple[
    tuple[GenerationAvailabilityRecord, ...],
    tuple[HydroRecord, ...],
    tuple[RegulatoryConstraint, ...],
]:
    return (availability(),), (_hydro(),), (constraint(),)


def _state(workflow_id: str = _WORKFLOW_ID) -> WorkflowState:
    return WorkflowState(
        workflow_id=workflow_id,
        portfolio_id="portfolio-1",
        delivery_date=date(2026, 10, 2),
        correlation_id="corr-risk-exec-1",
        phase=WorkflowPhase.FORECASTING,
        status=WorkflowStatus.RUNNING,
    )


def test_service_does_not_inherit_a_base_class() -> None:
    assert PortfolioRiskExecutionService.__bases__ == (object,)


def test_fakes_do_not_inherit_published_protocols() -> None:
    assert AgentPort not in _FakeRiskAgent.__mro__
    assert _FakeRiskAgent.__bases__ == (object,)
    assert ForecastingSuccessReadPort not in _FakeForecastReader.__mro__
    assert _FakeForecastReader.__bases__ == (object,)


def test_constructor_requires_two_keyword_only_dependencies() -> None:
    parameters = inspect.signature(PortfolioRiskExecutionService.__init__).parameters
    assert tuple(parameters) == ("self", "forecast_reader", "risk_agent")
    for name in ("forecast_reader", "risk_agent"):
        assert parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
        assert parameters[name].default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        PortfolioRiskExecutionService(_FakeForecastReader(), _FakeRiskAgent())  # type: ignore[call-arg]


def test_execute_requires_exact_keyword_only_inputs() -> None:
    assert inspect.iscoroutinefunction(PortfolioRiskExecutionService.execute)
    parameters = inspect.signature(PortfolioRiskExecutionService.execute).parameters
    assert tuple(parameters) == (
        "self",
        "workflow_id",
        "portfolio_id",
        "delivery_date",
        "generation_availability",
        "hydro_resources",
        "regulatory_constraints",
    )
    for name, parameter in parameters.items():
        if name == "self":
            continue
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty


async def test_execute_reads_constructs_delegates_and_returns_exact_assessment() -> None:
    success = _success()
    consumer_load_forecast = success.consumer_load_forecast
    dam_price_forecast = success.dam_price_forecast
    generation, hydro, constraints = _inputs()
    assessment = _assessment()
    snapshot = assessment.model_dump()
    reader = _FakeForecastReader({_WORKFLOW_ID: success})
    agent = _FakeRiskAgent({_WORKFLOW_ID: assessment})
    delivery_date = date(2026, 10, 2)

    result = await _service(_as_reader(reader), agent).execute(
        workflow_id=_WORKFLOW_ID,
        portfolio_id="portfolio-1",
        delivery_date=delivery_date,
        generation_availability=generation,
        hydro_resources=hydro,
        regulatory_constraints=constraints,
    )

    assert reader.calls == [_WORKFLOW_ID]
    assert len(agent.calls) == 1
    request = agent.calls[0]
    assert type(request) is PortfolioRiskAssessmentRequest
    assert request.workflow_id == _WORKFLOW_ID
    assert request.portfolio_id == "portfolio-1"
    assert request.delivery_date is delivery_date
    assert request.forecasting_success is success
    assert request.forecasting_success.consumer_load_forecast is consumer_load_forecast
    assert request.forecasting_success.dam_price_forecast is dam_price_forecast
    assert request.generation_availability is generation
    assert request.hydro_resources is hydro
    assert request.regulatory_constraints is constraints
    assert result is assessment
    assert result.model_dump() == snapshot


async def test_execute_forwards_explicitly_empty_input_tuples_unchanged() -> None:
    success = _success()
    assessment = _assessment(notes="delegation only")
    reader = _FakeForecastReader({_WORKFLOW_ID: success})
    agent = _FakeRiskAgent({_WORKFLOW_ID: assessment})
    empty_generation: tuple[GenerationAvailabilityRecord, ...] = ()
    empty_hydro: tuple[HydroRecord, ...] = ()
    empty_constraints: tuple[RegulatoryConstraint, ...] = ()

    result = await _service(_as_reader(reader), agent).execute(
        workflow_id=_WORKFLOW_ID,
        portfolio_id="portfolio-1",
        delivery_date=date(2026, 10, 2),
        generation_availability=empty_generation,
        hydro_resources=empty_hydro,
        regulatory_constraints=empty_constraints,
    )

    assert result is assessment
    request = agent.calls[0]
    assert request.generation_availability is empty_generation
    assert request.hydro_resources is empty_hydro
    assert request.regulatory_constraints is empty_constraints
    assert request.forecasting_success is success


async def test_missing_forecast_propagates_and_never_calls_agent() -> None:
    error = ResourceNotFoundError(_MSG_SUCCESS_NOT_FOUND)
    reader = _FakeForecastReader(error=error)
    agent = _FakeRiskAgent({_WORKFLOW_ID: _assessment()})
    generation, hydro, constraints = _inputs()

    with pytest.raises(ResourceNotFoundError) as caught:
        await _service(_as_reader(reader), agent).execute(
            workflow_id=_WORKFLOW_ID,
            portfolio_id="portfolio-1",
            delivery_date=date(2026, 10, 2),
            generation_availability=generation,
            hydro_resources=hydro,
            regulatory_constraints=constraints,
        )

    assert caught.value is error
    assert reader.calls == [_WORKFLOW_ID]
    assert agent.calls == []


async def test_reader_dependency_failure_propagates_and_never_calls_agent() -> None:
    error = DependencyUnavailableError("forecasting success store unavailable")
    reader = _FakeForecastReader(error=error)
    agent = _FakeRiskAgent({_WORKFLOW_ID: _assessment()})
    generation, hydro, constraints = _inputs()

    with pytest.raises(DependencyUnavailableError) as caught:
        await _service(_as_reader(reader), agent).execute(
            workflow_id=_WORKFLOW_ID,
            portfolio_id="portfolio-1",
            delivery_date=date(2026, 10, 2),
            generation_availability=generation,
            hydro_resources=hydro,
            regulatory_constraints=constraints,
        )

    assert caught.value is error
    assert reader.calls == [_WORKFLOW_ID]
    assert agent.calls == []


async def test_blank_portfolio_id_fails_request_validation_before_agent() -> None:
    reader = _FakeForecastReader({_WORKFLOW_ID: _success()})
    agent = _FakeRiskAgent({_WORKFLOW_ID: _assessment()})
    generation, hydro, constraints = _inputs()

    with pytest.raises(ValueError, match="portfolio_id must be a non-empty string"):
        await _service(_as_reader(reader), agent).execute(
            workflow_id=_WORKFLOW_ID,
            portfolio_id="   ",
            delivery_date=date(2026, 10, 2),
            generation_availability=generation,
            hydro_resources=hydro,
            regulatory_constraints=constraints,
        )

    assert reader.calls == [_WORKFLOW_ID]
    assert agent.calls == []


async def test_non_tuple_input_fails_request_validation_before_agent() -> None:
    reader = _FakeForecastReader({_WORKFLOW_ID: _success()})
    agent = _FakeRiskAgent({_WORKFLOW_ID: _assessment()})
    _, hydro, constraints = _inputs()

    with pytest.raises(TypeError, match="generation_availability must be an immutable tuple"):
        await _service(_as_reader(reader), agent).execute(
            workflow_id=_WORKFLOW_ID,
            portfolio_id="portfolio-1",
            delivery_date=date(2026, 10, 2),
            generation_availability=[availability()],  # type: ignore[arg-type]
            hydro_resources=hydro,
            regulatory_constraints=constraints,
        )

    assert reader.calls == [_WORKFLOW_ID]
    assert agent.calls == []


async def test_risk_agent_application_error_propagates_without_retry() -> None:
    error = DependencyUnavailableError("portfolio risk assessment unavailable")
    reader = _FakeForecastReader({_WORKFLOW_ID: _success()})
    agent = _FakeRiskAgent(error=error)
    generation, hydro, constraints = _inputs()

    with pytest.raises(DependencyUnavailableError) as caught:
        await _service(_as_reader(reader), agent).execute(
            workflow_id=_WORKFLOW_ID,
            portfolio_id="portfolio-1",
            delivery_date=date(2026, 10, 2),
            generation_availability=generation,
            hydro_resources=hydro,
            regulatory_constraints=constraints,
        )

    assert caught.value is error
    assert reader.calls == [_WORKFLOW_ID]
    assert len(agent.calls) == 1


async def test_risk_agent_unexpected_error_propagates_unsanitized() -> None:
    error = RuntimeError("unexpected assessment failure")
    reader = _FakeForecastReader({_WORKFLOW_ID: _success()})
    agent = _FakeRiskAgent(error=error)
    generation, hydro, constraints = _inputs()

    with pytest.raises(RuntimeError) as caught:
        await _service(_as_reader(reader), agent).execute(
            workflow_id=_WORKFLOW_ID,
            portfolio_id="portfolio-1",
            delivery_date=date(2026, 10, 2),
            generation_availability=generation,
            hydro_resources=hydro,
            regulatory_constraints=constraints,
        )

    assert caught.value is error
    assert str(caught.value) == "unexpected assessment failure"
    assert len(agent.calls) == 1


async def test_independent_workflows_do_not_cross_contaminate() -> None:
    first_success = _success(value_mw=3.25, price="45.00")
    second_success = _success(value_mw=7.5, price="80.00")
    first_assessment = _assessment(assessment_id="assessment-1")
    second_assessment = _assessment(assessment_id="assessment-2", risk_score=0.9)
    reader = _FakeForecastReader({_WORKFLOW_ID: first_success, _OTHER_WORKFLOW_ID: second_success})
    agent = _FakeRiskAgent({_WORKFLOW_ID: first_assessment, _OTHER_WORKFLOW_ID: second_assessment})
    service = _service(_as_reader(reader), agent)
    generation, hydro, constraints = _inputs()

    second_result = await service.execute(
        workflow_id=_OTHER_WORKFLOW_ID,
        portfolio_id="portfolio-2",
        delivery_date=date(2026, 10, 3),
        generation_availability=generation,
        hydro_resources=hydro,
        regulatory_constraints=constraints,
    )
    first_result = await service.execute(
        workflow_id=_WORKFLOW_ID,
        portfolio_id="portfolio-1",
        delivery_date=date(2026, 10, 2),
        generation_availability=generation,
        hydro_resources=hydro,
        regulatory_constraints=constraints,
    )

    assert second_result is second_assessment
    assert first_result is first_assessment
    assert reader.calls == [_OTHER_WORKFLOW_ID, _WORKFLOW_ID]
    assert len(agent.calls) == 2
    assert agent.calls[0].workflow_id == _OTHER_WORKFLOW_ID
    assert agent.calls[0].portfolio_id == "portfolio-2"
    assert agent.calls[0].forecasting_success is second_success
    assert agent.calls[1].workflow_id == _WORKFLOW_ID
    assert agent.calls[1].portfolio_id == "portfolio-1"
    assert agent.calls[1].forecasting_success is first_success


async def test_unknown_workflow_after_success_fails_closed_without_last_result() -> None:
    reader = _FakeForecastReader({_WORKFLOW_ID: _success()})
    agent = _FakeRiskAgent({_WORKFLOW_ID: _assessment()})
    service = _service(_as_reader(reader), agent)
    generation, hydro, constraints = _inputs()

    await service.execute(
        workflow_id=_WORKFLOW_ID,
        portfolio_id="portfolio-1",
        delivery_date=date(2026, 10, 2),
        generation_availability=generation,
        hydro_resources=hydro,
        regulatory_constraints=constraints,
    )
    with pytest.raises(ResourceNotFoundError):
        await service.execute(
            workflow_id=_OTHER_WORKFLOW_ID,
            portfolio_id="portfolio-1",
            delivery_date=date(2026, 10, 2),
            generation_availability=generation,
            hydro_resources=hydro,
            regulatory_constraints=constraints,
        )

    assert reader.calls == [_WORKFLOW_ID, _OTHER_WORKFLOW_ID]
    assert len(agent.calls) == 1


async def test_real_portfolio_risk_agent_is_accepted_structurally() -> None:
    success = _success()
    assessment = _assessment()
    assessment_port = _FakeAssessmentPort({_WORKFLOW_ID: assessment})
    agent = PortfolioRiskAgent(assessment_port=_as_assessment_port(assessment_port))
    reader = _FakeForecastReader({_WORKFLOW_ID: success})
    generation, hydro, constraints = _inputs()

    result = await _service(_as_reader(reader), agent).execute(
        workflow_id=_WORKFLOW_ID,
        portfolio_id="portfolio-1",
        delivery_date=date(2026, 10, 2),
        generation_availability=generation,
        hydro_resources=hydro,
        regulatory_constraints=constraints,
    )

    assert result is assessment
    assert len(assessment_port.calls) == 1
    assert assessment_port.calls[0].forecasting_success is success


async def test_real_read_after_write_wrapper_supplies_recorded_success() -> None:
    wrapper = InMemoryForecastingReadAfterWriteContext(
        context=InMemoryForecastingWorkflowContext(plans={})
    )
    reader: ForecastingSuccessReadPort = wrapper
    assessment = _assessment()
    agent = _FakeRiskAgent({_WORKFLOW_ID: assessment})
    service = _service(reader, agent)
    generation, hydro, constraints = _inputs()

    with pytest.raises(ResourceNotFoundError, match=_MSG_SUCCESS_NOT_FOUND):
        await service.execute(
            workflow_id=_WORKFLOW_ID,
            portfolio_id="portfolio-1",
            delivery_date=date(2026, 10, 2),
            generation_availability=generation,
            hydro_resources=hydro,
            regulatory_constraints=constraints,
        )
    assert agent.calls == []

    success = _success()
    await wrapper.record_success(state=_state(), success=success)
    result = await service.execute(
        workflow_id=_WORKFLOW_ID,
        portfolio_id="portfolio-1",
        delivery_date=date(2026, 10, 2),
        generation_availability=generation,
        hydro_resources=hydro,
        regulatory_constraints=constraints,
    )

    assert result is assessment
    assert len(agent.calls) == 1
    assert agent.calls[0].forecasting_success is success
    assert agent.calls[0].workflow_id == _WORKFLOW_ID
