"""Initial Phase 3 failure policy always decides terminal FAIL."""

from __future__ import annotations

import inspect
from typing import get_type_hints

from energy_trading.application.agents.base import AgentName
from energy_trading.application.orchestration.failure_policy import (
    FailureAction,
    FailurePolicyContext,
    FailurePolicyPort,
)
from energy_trading.application.orchestration.forecasting_initial_failure_policy import (
    InitialForecastingFailurePolicy,
)
from energy_trading.application.orchestration.state import WorkflowPhase


def _policy() -> InitialForecastingFailurePolicy:
    return InitialForecastingFailurePolicy()


def _context(**overrides: object) -> FailurePolicyContext:
    values: dict[str, object] = {
        "phase": WorkflowPhase.FORECASTING,
        "error_code": "invalid_request",
        "attempt_number": 1,
        "agent_name": None,
    }
    values.update(overrides)
    return FailurePolicyContext(**values)  # type: ignore[arg-type]


def test_policy_does_not_inherit_failure_policy_port() -> None:
    assert FailurePolicyPort not in InitialForecastingFailurePolicy.__mro__
    assert not any(
        base.__name__ in {"FailurePolicyPort", "Protocol"}
        for base in InitialForecastingFailurePolicy.__bases__
    )


def test_policy_structurally_satisfies_failure_policy_port() -> None:
    port: FailurePolicyPort = _policy()
    assert isinstance(port, InitialForecastingFailurePolicy)


def test_decide_signature_matches_published_port() -> None:
    policy_hints = get_type_hints(InitialForecastingFailurePolicy.decide)
    port_hints = get_type_hints(FailurePolicyPort.decide)
    assert inspect.signature(InitialForecastingFailurePolicy.decide).parameters.keys() == (
        inspect.signature(FailurePolicyPort.decide).parameters.keys()
    )
    assert policy_hints["context"] is port_hints["context"] is FailurePolicyContext
    assert policy_hints["return"] is port_hints["return"] is FailureAction
    assert inspect.iscoroutinefunction(InitialForecastingFailurePolicy.decide)


def test_policy_exposes_no_additional_public_methods() -> None:
    public_operations = [
        name
        for name, value in vars(InitialForecastingFailurePolicy).items()
        if callable(value) and not name.startswith("_")
    ]
    assert public_operations == ["decide"]


def test_policy_has_no_constructor_dependency() -> None:
    signature = inspect.signature(InitialForecastingFailurePolicy)
    assert tuple(signature.parameters) == ()


async def test_decide_returns_fail_for_a_valid_phase_3_context() -> None:
    result = await _policy().decide(_context())
    assert result is FailureAction.FAIL


async def test_decide_returns_fail_for_consumer_load_forecast() -> None:
    result = await _policy().decide(_context(agent_name=AgentName.CONSUMER_LOAD_FORECAST))
    assert result is FailureAction.FAIL


async def test_decide_returns_fail_for_dam_price_forecast() -> None:
    result = await _policy().decide(_context(agent_name=AgentName.DAM_PRICE_FORECAST))
    assert result is FailureAction.FAIL


async def test_decide_returns_fail_for_distinct_sanitized_error_codes() -> None:
    first = await _policy().decide(_context(error_code="invalid_request"))
    second = await _policy().decide(_context(error_code="forecasting_unexpected_failure"))
    assert first is second is FailureAction.FAIL


async def test_decide_returns_fail_for_valid_attempt_numbers() -> None:
    first = await _policy().decide(_context(attempt_number=1))
    second = await _policy().decide(_context(attempt_number=2))
    assert first is second is FailureAction.FAIL


async def test_decide_returns_fail_when_agent_name_is_absent() -> None:
    result = await _policy().decide(_context(agent_name=None))
    assert result is FailureAction.FAIL


async def test_decide_returns_fail_for_a_non_forecasting_phase() -> None:
    result = await _policy().decide(_context(phase=WorkflowPhase.INGESTION))
    assert result is FailureAction.FAIL


async def test_repeated_unrelated_calls_remain_stateless() -> None:
    policy = _policy()
    first = await policy.decide(
        _context(
            phase=WorkflowPhase.FORECASTING,
            error_code="invalid_request",
            attempt_number=1,
            agent_name=AgentName.CONSUMER_LOAD_FORECAST,
        )
    )
    second = await policy.decide(
        _context(
            phase=WorkflowPhase.CONTRACT,
            error_code="dependency_unavailable",
            attempt_number=2,
            agent_name=AgentName.DAM_PRICE_FORECAST,
        )
    )
    third = await policy.decide(
        _context(
            phase=WorkflowPhase.FORECASTING,
            error_code="invalid_request",
            attempt_number=1,
            agent_name=AgentName.CONSUMER_LOAD_FORECAST,
        )
    )
    assert first is second is third is FailureAction.FAIL
    assert policy.__dict__ == {}
