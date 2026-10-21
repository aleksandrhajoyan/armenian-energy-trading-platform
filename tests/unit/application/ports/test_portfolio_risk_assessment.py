"""Application-owned Portfolio & Risk assessment request and Protocol.

These are contract-level tests against a test-only structural fake. They do
not prove any risk methodology: no concrete assessment implementation exists.
"""

from __future__ import annotations

import dataclasses
import inspect
from datetime import date, datetime
from decimal import Decimal
from typing import get_type_hints

import pytest

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.application.ports.portfolio_risk_assessment import (
    PortfolioRiskAssessmentPort,
    PortfolioRiskAssessmentRequest,
)
from energy_trading.domain.models import (
    GenerationAvailabilityRecord,
    HydroRecord,
    LoadForecastPoint,
    PriceForecastPoint,
    RegulatoryConstraint,
    RiskAssessment,
)
from tests.unit.domain._factories import amd_price, availability, constraint, utc

_FIELD_NAMES = (
    "workflow_id",
    "portfolio_id",
    "delivery_date",
    "forecasting_success",
    "generation_availability",
    "hydro_resources",
    "regulatory_constraints",
)


class _StructuralPortfolioRiskAssessmentFake:
    """Test-only fake that structurally satisfies the assessment Protocol.

    Not a risk engine. Does not inherit a production base class. Returns the
    caller-prepared assessment or raises the caller-prepared error.
    """

    def __init__(
        self,
        *,
        result: RiskAssessment | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.received_requests: list[PortfolioRiskAssessmentRequest] = []

    async def assess(self, *, request: PortfolioRiskAssessmentRequest) -> RiskAssessment:
        self.received_requests.append(request)
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


def _as_assessment_port(
    fake: _StructuralPortfolioRiskAssessmentFake,
) -> PortfolioRiskAssessmentPort:
    """Application-shaped call site: the port type is the only accepted argument."""

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


def _risk_assessment() -> RiskAssessment:
    return RiskAssessment.model_validate(
        {
            "assessment_id": "assessment-1",
            "assessed_at": utc(hour=9),
            "delivery_timestamp": utc(day=2, hour=16),
            "risk_score": Decimal("0.4"),
        }
    )


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


def test_request_accepts_exact_published_canonical_input_types() -> None:
    hints = get_type_hints(PortfolioRiskAssessmentRequest)
    assert tuple(hints) == _FIELD_NAMES
    assert hints["workflow_id"] is str
    assert hints["portfolio_id"] is str
    assert hints["delivery_date"] is date
    assert hints["forecasting_success"] is ForecastingSuccess
    assert hints["generation_availability"] == tuple[GenerationAvailabilityRecord, ...]
    assert hints["hydro_resources"] == tuple[HydroRecord, ...]
    assert hints["regulatory_constraints"] == tuple[RegulatoryConstraint, ...]
    request = _request()
    assert isinstance(request, PortfolioRiskAssessmentRequest)


def test_request_is_frozen() -> None:
    request = _request()
    with pytest.raises(dataclasses.FrozenInstanceError):
        request.workflow_id = "workflow-other"  # type: ignore[misc]


def test_request_uses_slots() -> None:
    request = _request()
    assert PortfolioRiskAssessmentRequest.__slots__ == _FIELD_NAMES
    assert not hasattr(request, "__dict__")


def test_request_fields_are_keyword_only_without_defaults() -> None:
    fields = dataclasses.fields(PortfolioRiskAssessmentRequest)
    assert tuple(field.name for field in fields) == _FIELD_NAMES
    for field in fields:
        assert field.kw_only is True
        assert field.default is dataclasses.MISSING
        assert field.default_factory is dataclasses.MISSING
    signature = inspect.signature(PortfolioRiskAssessmentRequest)
    for parameter in signature.parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        PortfolioRiskAssessmentRequest()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        PortfolioRiskAssessmentRequest(  # type: ignore[call-arg]
            "workflow-risk-1",
            "portfolio-1",
            date(2026, 10, 2),
            _success(),
            (),
            (),
            (),
        )


def test_request_preserves_forecasting_success_by_identity() -> None:
    success = _success()
    request = _request(forecasting_success=success)
    assert request.forecasting_success is success
    assert request.forecasting_success.consumer_load_forecast is success.consumer_load_forecast
    assert request.forecasting_success.dam_price_forecast is success.dam_price_forecast


def test_request_preserves_canonical_input_tuples_unchanged() -> None:
    later = availability(asset_id="asset-2", timestamp=utc(hour=12))
    earlier = availability(asset_id="asset-1", timestamp=utc(hour=8))
    generation = (later, earlier)
    hydro = (_hydro(),)
    constraints = (constraint(constraint_id="constraint-2"), constraint())
    request = _request(
        generation_availability=generation,
        hydro_resources=hydro,
        regulatory_constraints=constraints,
    )
    assert request.generation_availability is generation
    assert request.hydro_resources is hydro
    assert request.regulatory_constraints is constraints
    assert request.generation_availability[0] is later
    assert request.generation_availability[1] is earlier
    assert request.regulatory_constraints[0] is constraints[0]


def test_request_preserves_explicit_identity_and_delivery_date() -> None:
    delivery_date = date(2026, 10, 2)
    request = _request(
        workflow_id="workflow-risk-7",
        portfolio_id="portfolio-9",
        delivery_date=delivery_date,
    )
    assert request.workflow_id == "workflow-risk-7"
    assert request.portfolio_id == "portfolio-9"
    assert request.delivery_date is delivery_date


def test_request_represents_empty_canonical_input_tuples_without_generating_data() -> None:
    success = ForecastingSuccess(consumer_load_forecast=(), dam_price_forecast=())
    request = _request(
        forecasting_success=success,
        generation_availability=(),
        hydro_resources=(),
        regulatory_constraints=(),
    )
    assert request.forecasting_success is success
    assert request.forecasting_success.consumer_load_forecast == ()
    assert request.forecasting_success.dam_price_forecast == ()
    assert request.generation_availability == ()
    assert request.hydro_resources == ()
    assert request.regulatory_constraints == ()


@pytest.mark.parametrize(
    ("field_name", "value", "error_type"),
    [
        ("workflow_id", 7, TypeError),
        ("workflow_id", "   ", ValueError),
        ("portfolio_id", None, TypeError),
        ("portfolio_id", "", ValueError),
        ("delivery_date", datetime(2026, 10, 2, 0, 0), TypeError),
        ("delivery_date", "2026-10-02", TypeError),
        ("forecasting_success", object(), TypeError),
        ("generation_availability", [], TypeError),
        ("generation_availability", (object(),), TypeError),
        ("hydro_resources", [], TypeError),
        ("hydro_resources", (object(),), TypeError),
        ("regulatory_constraints", [], TypeError),
        ("regulatory_constraints", (object(),), TypeError),
    ],
)
def test_request_fails_closed_on_wrong_input_shapes(
    field_name: str,
    value: object,
    error_type: type[Exception],
) -> None:
    with pytest.raises(error_type):
        _request(**{field_name: value})


def test_assessment_port_is_nongeneric_typing_protocol() -> None:
    assert [base.__name__ for base in PortfolioRiskAssessmentPort.__bases__] == ["Protocol"]
    assert vars(PortfolioRiskAssessmentPort)["_is_protocol"] is True
    assert vars(PortfolioRiskAssessmentPort)["__parameters__"] == ()
    assert PortfolioRiskAssessmentPort.__type_params__ == ()


def test_assessment_port_exposes_keyword_only_async_assess() -> None:
    defined_methods = {
        name
        for name, value in vars(PortfolioRiskAssessmentPort).items()
        if callable(value) and not name.startswith("_")
    }
    assert defined_methods == {"assess"}
    assert inspect.iscoroutinefunction(PortfolioRiskAssessmentPort.assess)
    signature = inspect.signature(PortfolioRiskAssessmentPort.assess)
    assert tuple(signature.parameters) == ("self", "request")
    parameter = signature.parameters["request"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty
    hints = get_type_hints(PortfolioRiskAssessmentPort.assess)
    assert hints["request"] is PortfolioRiskAssessmentRequest
    assert hints["return"] is RiskAssessment


def test_structural_fake_does_not_inherit_the_port() -> None:
    assert PortfolioRiskAssessmentPort not in _StructuralPortfolioRiskAssessmentFake.__mro__
    assert _StructuralPortfolioRiskAssessmentFake.__bases__ == (object,)


async def test_fake_receives_exact_request_and_returns_exact_assessment() -> None:
    assessment = _risk_assessment()
    request = _request()
    fake = _StructuralPortfolioRiskAssessmentFake(result=assessment)
    port = _as_assessment_port(fake)
    assert inspect.iscoroutinefunction(port.assess)
    result = await port.assess(request=request)
    assert result is assessment
    assert len(fake.received_requests) == 1
    assert fake.received_requests[0] is request


async def test_fake_application_error_propagates_unchanged() -> None:
    error = DependencyUnavailableError("Risk assessment backend is unavailable.")
    request = _request()
    fake = _StructuralPortfolioRiskAssessmentFake(error=error)
    port = _as_assessment_port(fake)
    with pytest.raises(DependencyUnavailableError) as excinfo:
        await port.assess(request=request)
    assert excinfo.value is error
    assert fake.received_requests == [request]
