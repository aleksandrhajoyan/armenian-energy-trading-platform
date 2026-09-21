"""Phase 3 failure-policy decision service delegates without executing actions."""

from __future__ import annotations

import inspect
from typing import get_type_hints

import pytest

from energy_trading.application.agents.base import AgentName
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration.failure_policy import (
    FailureAction,
    FailurePolicyContext,
    FailurePolicyPort,
)
from energy_trading.application.orchestration.forecasting_failure_decision import (
    ForecastingFailureDecisionService,
)
from energy_trading.application.orchestration.state import WorkflowPhase


class _RecordingFailurePolicyFake:
    """Test-only fake that structurally satisfies ``FailurePolicyPort``.

    Not a production policy. Does not inherit a production base class.
    """

    def __init__(
        self,
        action: FailureAction | None = None,
        error: BaseException | None = None,
    ) -> None:
        self._action = action
        self._error = error
        self.calls = 0
        self.received: FailurePolicyContext | None = None

    async def decide(self, context: FailurePolicyContext) -> FailureAction:
        self.calls += 1
        self.received = context
        if self._error is not None:
            raise self._error
        if self._action is None:
            msg = "recording fake requires an action or an error"
            raise AssertionError(msg)
        return self._action


def _context() -> FailurePolicyContext:
    return FailurePolicyContext(
        phase=WorkflowPhase.FORECASTING,
        error_code="dependency_unavailable",
        attempt_number=1,
        agent_name=AgentName.CONSUMER_LOAD_FORECAST,
    )


def test_recording_fake_does_not_inherit_failure_policy_port() -> None:
    assert FailurePolicyPort not in _RecordingFailurePolicyFake.__mro__
    assert not any(
        base.__name__ in {"FailurePolicyPort", "Protocol"}
        for base in _RecordingFailurePolicyFake.__bases__
    )


def test_service_does_not_inherit_failure_policy_port() -> None:
    assert FailurePolicyPort not in ForecastingFailureDecisionService.__mro__
    assert not any(
        base.__name__ in {"FailurePolicyPort", "Protocol"}
        for base in ForecastingFailureDecisionService.__bases__
    )


def test_service_constructor_accepts_structural_fake_without_inheritance() -> None:
    fake = _RecordingFailurePolicyFake(FailureAction.FAIL)
    service = ForecastingFailureDecisionService(fake)
    assert isinstance(service, ForecastingFailureDecisionService)


async def test_decide_forwards_the_exact_context_and_awaits_policy_once() -> None:
    context = _context()
    fake = _RecordingFailurePolicyFake(FailureAction.FAIL)
    service = ForecastingFailureDecisionService(fake)

    result = await service.decide(context)

    assert result is FailureAction.FAIL
    assert fake.calls == 1
    assert fake.received is context


async def test_decide_returns_fail_unchanged() -> None:
    context = _context()
    fake = _RecordingFailurePolicyFake(FailureAction.FAIL)
    service = ForecastingFailureDecisionService(fake)

    result = await service.decide(context)

    assert result is FailureAction.FAIL
    assert fake.calls == 1
    assert fake.received is context


async def test_decide_returns_retry_unchanged() -> None:
    context = _context()
    fake = _RecordingFailurePolicyFake(FailureAction.RETRY)
    service = ForecastingFailureDecisionService(fake)

    result = await service.decide(context)

    assert result is FailureAction.RETRY
    assert fake.calls == 1
    assert fake.received is context


async def test_decide_returns_fallback_unchanged() -> None:
    context = _context()
    fake = _RecordingFailurePolicyFake(FailureAction.FALLBACK)
    service = ForecastingFailureDecisionService(fake)

    result = await service.decide(context)

    assert result is FailureAction.FALLBACK
    assert fake.calls == 1
    assert fake.received is context


def test_decide_signature_matches_published_policy_port() -> None:
    service_parameters = inspect.signature(ForecastingFailureDecisionService.decide).parameters
    port_parameters = inspect.signature(FailurePolicyPort.decide).parameters
    assert tuple(service_parameters) == ("self", "context")
    assert tuple(port_parameters) == ("self", "context")
    service_hints = get_type_hints(ForecastingFailureDecisionService.decide)
    port_hints = get_type_hints(FailurePolicyPort.decide)
    assert service_hints["context"] is port_hints["context"] is FailurePolicyContext
    assert service_hints["return"] is port_hints["return"] is FailureAction
    assert inspect.iscoroutinefunction(ForecastingFailureDecisionService.decide)
    assert inspect.iscoroutinefunction(FailurePolicyPort.decide)


async def test_policy_exception_propagates_without_default_action() -> None:
    context = _context()
    error = DependencyUnavailableError("policy unavailable")
    fake = _RecordingFailurePolicyFake(error=error)
    service = ForecastingFailureDecisionService(fake)

    with pytest.raises(DependencyUnavailableError) as caught:
        await service.decide(context)

    assert caught.value is error
    assert fake.calls == 1
    assert fake.received is context


def test_service_public_surface_is_constructor_and_decide() -> None:
    public = [name for name in dir(ForecastingFailureDecisionService) if not name.startswith("_")]
    assert public == ["decide"]
    init = inspect.signature(ForecastingFailureDecisionService.__init__)
    assert tuple(init.parameters) == ("self", "policy")
    assert init.parameters["policy"].annotation == "FailurePolicyPort" or (
        init.parameters["policy"].annotation is FailurePolicyPort
    )
    decide = inspect.signature(ForecastingFailureDecisionService.decide)
    assert decide.parameters["context"].annotation == "FailurePolicyContext" or (
        decide.parameters["context"].annotation is FailurePolicyContext
    )
    assert decide.return_annotation == "FailureAction" or (
        decide.return_annotation is FailureAction
    )
