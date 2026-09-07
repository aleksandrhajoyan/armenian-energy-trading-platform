"""Phase 2 failure-policy decision service delegates without executing actions."""

from __future__ import annotations

import inspect

import pytest

from energy_trading.application.agents import AgentName
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.orchestration import (
    FailureAction,
    FailurePolicyContext,
    FailurePolicyPort,
    ParallelIngestionFailureDecisionService,
    WorkflowPhase,
)


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
        phase=WorkflowPhase.INGESTION,
        error_code="dependency_unavailable",
        attempt_number=1,
        agent_name=AgentName.MARKET_MONITORING,
    )


def test_recording_fake_does_not_inherit_failure_policy_port() -> None:
    assert FailurePolicyPort not in _RecordingFailurePolicyFake.__mro__
    assert not any(
        base.__name__ in {"FailurePolicyPort", "Protocol"}
        for base in _RecordingFailurePolicyFake.__bases__
    )


def test_service_does_not_inherit_failure_policy_port() -> None:
    assert FailurePolicyPort not in ParallelIngestionFailureDecisionService.__mro__
    assert not any(
        base.__name__ in {"FailurePolicyPort", "Protocol"}
        for base in ParallelIngestionFailureDecisionService.__bases__
    )


def test_service_constructor_accepts_structural_fake_without_inheritance() -> None:
    fake = _RecordingFailurePolicyFake(FailureAction.FAIL)
    service = ParallelIngestionFailureDecisionService(fake)
    assert isinstance(service, ParallelIngestionFailureDecisionService)


@pytest.mark.parametrize("action", list(FailureAction))
async def test_decide_returns_each_published_action_unchanged(action: FailureAction) -> None:
    context = _context()
    fake = _RecordingFailurePolicyFake(action)
    service = ParallelIngestionFailureDecisionService(fake)

    result = await service.decide(context)

    assert result is action
    assert fake.calls == 1
    assert fake.received is context


async def test_decide_signature_matches_published_policy_port() -> None:
    service_parameters = inspect.signature(
        ParallelIngestionFailureDecisionService.decide
    ).parameters
    port_parameters = inspect.signature(FailurePolicyPort.decide).parameters
    assert tuple(service_parameters) == ("self", "context")
    assert tuple(port_parameters) == ("self", "context")
    assert inspect.iscoroutinefunction(ParallelIngestionFailureDecisionService.decide)
    assert inspect.iscoroutinefunction(FailurePolicyPort.decide)


async def test_policy_exception_propagates_without_default_action() -> None:
    context = _context()
    error = DependencyUnavailableError("policy unavailable")
    fake = _RecordingFailurePolicyFake(error=error)
    service = ParallelIngestionFailureDecisionService(fake)

    with pytest.raises(DependencyUnavailableError) as caught:
        await service.decide(context)

    assert caught.value is error
    assert fake.calls == 1
    assert fake.received is context


def test_service_public_surface_is_constructor_and_decide() -> None:
    public = [
        name for name in dir(ParallelIngestionFailureDecisionService) if not name.startswith("_")
    ]
    assert public == ["decide"]
    init = inspect.signature(ParallelIngestionFailureDecisionService.__init__)
    assert tuple(init.parameters) == ("self", "policy")
    assert init.parameters["policy"].annotation == "FailurePolicyPort" or (
        init.parameters["policy"].annotation is FailurePolicyPort
    )
    decide = inspect.signature(ParallelIngestionFailureDecisionService.decide)
    assert decide.parameters["context"].annotation == "FailurePolicyContext" or (
        decide.parameters["context"].annotation is FailurePolicyContext
    )
    assert decide.return_annotation == "FailureAction" or (
        decide.return_annotation is FailureAction
    )
