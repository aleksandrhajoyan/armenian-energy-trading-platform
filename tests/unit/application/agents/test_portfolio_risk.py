"""Portfolio & Risk Agent application contract.

These tests verify delegation to the injected assessment port only. They do
not prove any risk methodology and do not establish that the supplied inputs
are sufficient for a complete or acceptable risk assessment.
"""

from __future__ import annotations

import inspect
from datetime import date

import pytest
from tests.unit.domain._factories import amd_money, amd_price, availability, constraint, utc

from energy_trading.application.agents.base import AgentName, AgentPort
from energy_trading.application.agents.portfolio_risk import PortfolioRiskAgent
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.application.ports.portfolio_risk_assessment import (
    PortfolioRiskAssessmentPort,
    PortfolioRiskAssessmentRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint, PriceForecastPoint
from energy_trading.domain.models.observations import HydroRecord
from energy_trading.domain.models.trading import RiskAssessment


class _FakePortfolioRiskAssessment:
    """Test-only assessment fake. Not a risk engine and not a production adapter."""

    def __init__(
        self,
        results: dict[str, RiskAssessment] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.results = results or {}
        self.error = error
        self.calls: list[PortfolioRiskAssessmentRequest] = []

    async def assess(self, *, request: PortfolioRiskAssessmentRequest) -> RiskAssessment:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.results[request.workflow_id]


def _as_agent_port(
    agent: PortfolioRiskAgent,
) -> AgentPort[PortfolioRiskAssessmentRequest, RiskAssessment]:
    """Mypy-visible structural assignment to the shared agent port."""

    return agent


def _as_assessment_port(fake: _FakePortfolioRiskAssessment) -> PortfolioRiskAssessmentPort:
    """Mypy-visible structural assignment to the published assessment port."""

    return fake


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


def _request(**overrides: object) -> PortfolioRiskAssessmentRequest:
    values: dict[str, object] = {
        "workflow_id": "workflow-risk-1",
        "portfolio_id": "portfolio-1",
        "delivery_date": date(2026, 10, 2),
        "forecasting_success": _success(),
        "generation_availability": (availability(),),
        "hydro_resources": (_hydro(),),
        "regulatory_constraints": (constraint(),),
    }
    values.update(overrides)
    return PortfolioRiskAssessmentRequest(**values)  # type: ignore[arg-type]


def _agent(fake: _FakePortfolioRiskAssessment) -> PortfolioRiskAgent:
    return PortfolioRiskAgent(assessment_port=_as_assessment_port(fake))


def test_agent_does_not_inherit_agent_port() -> None:
    assert AgentPort not in PortfolioRiskAgent.__mro__
    assert PortfolioRiskAgent.__bases__ == (object,)


def test_fake_does_not_inherit_production_assessment_port() -> None:
    assert PortfolioRiskAssessmentPort not in _FakePortfolioRiskAssessment.__mro__
    assert _FakePortfolioRiskAssessment.__bases__ == (object,)


def test_agent_name_is_canonical_portfolio_and_risk_identity() -> None:
    port = _as_agent_port(_agent(_FakePortfolioRiskAssessment()))
    assert port.name is AgentName.PORTFOLIO_AND_RISK
    assert port.name.value == "Portfolio & Risk Agent"
    assert len(AgentName) == 13


def test_constructor_accepts_only_keyword_only_assessment_port() -> None:
    parameters = inspect.signature(PortfolioRiskAgent.__init__).parameters
    assert tuple(parameters) == ("self", "assessment_port")
    assessment_port = parameters["assessment_port"]
    assert assessment_port.kind is inspect.Parameter.KEYWORD_ONLY
    assert assessment_port.default is inspect.Parameter.empty
    fake = _FakePortfolioRiskAssessment()
    with pytest.raises(TypeError):
        PortfolioRiskAgent(fake)  # type: ignore[call-arg]


def test_run_signature_matches_published_agent_port() -> None:
    assert inspect.iscoroutinefunction(PortfolioRiskAgent.run)
    parameters = inspect.signature(PortfolioRiskAgent.run).parameters
    assert tuple(parameters) == ("self", "request")
    assert parameters["request"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert isinstance(inspect.getattr_static(PortfolioRiskAgent, "name"), property)


async def test_run_forwards_exact_request_and_returns_exact_assessment() -> None:
    request = _request()
    success = request.forecasting_success
    generation = request.generation_availability
    hydro = request.hydro_resources
    constraints = request.regulatory_constraints
    assessment = _assessment()
    fake = _FakePortfolioRiskAssessment({"workflow-risk-1": assessment})
    result = await _as_agent_port(_agent(fake)).run(request)
    assert len(fake.calls) == 1
    assert fake.calls[0] is request
    assert result is assessment
    assert request.forecasting_success is success
    assert request.generation_availability is generation
    assert request.hydro_resources is hydro
    assert request.regulatory_constraints is constraints
    assert request.forecasting_success.consumer_load_forecast is success.consumer_load_forecast
    assert request.forecasting_success.dam_price_forecast is success.dam_price_forecast


async def test_run_does_not_alter_assessment_fields() -> None:
    assessment = _assessment()
    snapshot = assessment.model_dump()
    expected_margin = assessment.expected_margin
    value_at_risk = assessment.value_at_risk
    fake = _FakePortfolioRiskAssessment({"workflow-risk-1": assessment})
    result = await _agent(fake).run(_request())
    assert result is assessment
    assert result.model_dump() == snapshot
    assert result.risk_score == 0.4
    assert result.expected_margin is expected_margin
    assert result.value_at_risk is value_at_risk
    assert result.price_volatility is None
    assert result.expected_balancing_penalty is None


async def test_run_delegates_explicitly_empty_input_tuples_unchanged() -> None:
    request = _request(generation_availability=(), hydro_resources=(), regulatory_constraints=())
    assessment = _assessment(notes="delegation only")
    fake = _FakePortfolioRiskAssessment({"workflow-risk-1": assessment})
    result = await _agent(fake).run(request)
    assert result is assessment
    assert len(fake.calls) == 1
    assert fake.calls[0] is request
    assert fake.calls[0].generation_availability == ()
    assert fake.calls[0].hydro_resources == ()
    assert fake.calls[0].regulatory_constraints == ()


async def test_run_propagates_dependency_unavailable_without_retry_or_fallback() -> None:
    error = DependencyUnavailableError("portfolio risk assessment unavailable")
    fake = _FakePortfolioRiskAssessment(error=error)
    with pytest.raises(DependencyUnavailableError) as caught:
        await _agent(fake).run(_request())
    assert caught.value is error
    assert len(fake.calls) == 1


async def test_run_does_not_catch_or_sanitize_unexpected_exceptions() -> None:
    error = RuntimeError("unexpected assessment failure")
    fake = _FakePortfolioRiskAssessment(error=error)
    with pytest.raises(RuntimeError) as caught:
        await _agent(fake).run(_request())
    assert caught.value is error
    assert str(caught.value) == "unexpected assessment failure"
    assert len(fake.calls) == 1


async def test_run_forwards_independent_requests_without_leaking_results() -> None:
    first_assessment = _assessment(assessment_id="assessment-1")
    second_assessment = _assessment(assessment_id="assessment-2", risk_score=0.9)
    fake = _FakePortfolioRiskAssessment(
        {"workflow-risk-1": first_assessment, "workflow-risk-2": second_assessment}
    )
    agent = _agent(fake)
    first_request = _request(workflow_id="workflow-risk-1")
    second_request = _request(workflow_id="workflow-risk-2")
    second_result = await agent.run(second_request)
    first_result = await agent.run(first_request)
    assert second_result is second_assessment
    assert first_result is first_assessment
    assert len(fake.calls) == 2
    assert fake.calls[0] is second_request
    assert fake.calls[1] is first_request
