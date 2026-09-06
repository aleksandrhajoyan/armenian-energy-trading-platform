"""Application-owned orchestration failure-policy decision contract."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from enum import StrEnum

import pytest

from energy_trading.application.agents import AgentName
from energy_trading.application.orchestration import (
    FailureAction,
    FailurePolicyContext,
    FailurePolicyPort,
    WorkflowPhase,
)


class _StructuralFailurePolicyFake:
    """Test-only fake that structurally satisfies ``FailurePolicyPort``.

    Not a production policy. Does not inherit a production base class.
    """

    def __init__(self, action: FailureAction) -> None:
        self._action = action
        self.received: FailurePolicyContext | None = None

    async def decide(self, context: FailurePolicyContext) -> FailureAction:
        self.received = context
        return self._action


def _context(**overrides: object) -> FailurePolicyContext:
    values: dict[str, object] = {
        "phase": WorkflowPhase.INGESTION,
        "error_code": "dependency_unavailable",
        "attempt_number": 1,
        "agent_name": None,
    }
    values.update(overrides)
    return FailurePolicyContext(**values)  # type: ignore[arg-type]


def _as_failure_policy(policy: _StructuralFailurePolicyFake) -> FailurePolicyPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return policy


def test_failure_action_is_strenum() -> None:
    assert issubclass(FailureAction, StrEnum)
    assert issubclass(FailureAction, str)


def test_failure_action_has_exactly_three_members() -> None:
    assert len(FailureAction) == 3
    assert tuple(member.name for member in FailureAction) == (
        "RETRY",
        "FALLBACK",
        "FAIL",
    )
    assert tuple(member.value for member in FailureAction) == (
        "retry",
        "fallback",
        "fail",
    )


def test_failure_policy_context_succeeds_without_agent() -> None:
    context = _context(agent_name=None)
    assert context.phase is WorkflowPhase.INGESTION
    assert context.error_code == "dependency_unavailable"
    assert context.attempt_number == 1
    assert context.agent_name is None


@pytest.mark.parametrize("agent_name", list(AgentName))
def test_failure_policy_context_accepts_each_agent_name(agent_name: AgentName) -> None:
    context = _context(agent_name=agent_name)
    assert context.agent_name is agent_name


def test_failure_policy_context_is_frozen() -> None:
    context = _context()
    with pytest.raises(FrozenInstanceError):
        context.error_code = "mutated"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        context.attempt_number = 2  # type: ignore[misc]


def test_failure_policy_context_requires_workflow_phase() -> None:
    context = _context(phase=WorkflowPhase.CONTRACT)
    assert context.phase is WorkflowPhase.CONTRACT
    with pytest.raises(TypeError, match="phase must be a WorkflowPhase"):
        _context(phase="ingestion")
    with pytest.raises(TypeError, match="phase must be a WorkflowPhase"):
        _context(phase=FailureAction.FAIL)


def test_failure_policy_context_rejects_arbitrary_phase_string() -> None:
    with pytest.raises(TypeError, match="phase must be a WorkflowPhase"):
        _context(phase="forecasting")


def test_failure_policy_context_strips_error_code_whitespace() -> None:
    context = _context(error_code="  dependency_unavailable  ")
    assert context.error_code == "dependency_unavailable"


@pytest.mark.parametrize("error_code", ["", "   "])
def test_failure_policy_context_rejects_blank_error_code(error_code: str) -> None:
    with pytest.raises(ValueError, match="error_code"):
        _context(error_code=error_code)


@pytest.mark.parametrize("error_code", [None, 1, b"opaque", True])
def test_failure_policy_context_rejects_non_string_error_code(error_code: object) -> None:
    with pytest.raises(TypeError, match="error_code must be a string"):
        _context(error_code=error_code)


def test_failure_policy_context_accepts_attempt_one() -> None:
    context = _context(attempt_number=1)
    assert context.attempt_number == 1


def test_failure_policy_context_accepts_later_positive_attempt() -> None:
    context = _context(attempt_number=4)
    assert context.attempt_number == 4


def test_failure_policy_context_rejects_attempt_zero() -> None:
    with pytest.raises(ValueError, match="attempt_number must be greater than 0"):
        _context(attempt_number=0)


def test_failure_policy_context_rejects_negative_attempt() -> None:
    with pytest.raises(ValueError, match="attempt_number must be greater than 0"):
        _context(attempt_number=-1)


@pytest.mark.parametrize("attempt_number", [True, False])
def test_failure_policy_context_rejects_boolean_attempt(attempt_number: bool) -> None:
    with pytest.raises(TypeError, match="attempt_number must be an integer"):
        _context(attempt_number=attempt_number)


@pytest.mark.parametrize("attempt_number", [None, 1.5, "1", b"1"])
def test_failure_policy_context_rejects_non_int_attempt(attempt_number: object) -> None:
    with pytest.raises(TypeError, match="attempt_number must be an integer"):
        _context(attempt_number=attempt_number)


def test_failure_policy_context_accepts_none_agent_name() -> None:
    context = _context(agent_name=None)
    assert context.agent_name is None


def test_failure_policy_context_accepts_actual_agent_name() -> None:
    context = _context(agent_name=AgentName.MARKET_MONITORING)
    assert context.agent_name is AgentName.MARKET_MONITORING


def test_failure_policy_context_rejects_arbitrary_agent_name_string() -> None:
    with pytest.raises(TypeError, match="agent_name must be an AgentName or None"):
        _context(agent_name="Market Monitoring Agent")
    with pytest.raises(TypeError, match="agent_name must be an AgentName or None"):
        _context(agent_name="not-an-agent")


def test_structural_fake_does_not_inherit_production_base() -> None:
    assert FailurePolicyPort not in _StructuralFailurePolicyFake.__mro__
    assert not any(
        base.__name__ in {"FailurePolicyPort", "Protocol"}
        for base in _StructuralFailurePolicyFake.__bases__
    )


async def test_structural_fake_satisfies_failure_policy_port() -> None:
    fake = _StructuralFailurePolicyFake(FailureAction.FAIL)
    port = _as_failure_policy(fake)
    context = _context()
    decide_parameters = inspect.signature(FailurePolicyPort.decide).parameters
    assert tuple(decide_parameters) == ("self", "context")
    assert inspect.iscoroutinefunction(FailurePolicyPort.decide)
    assert inspect.iscoroutinefunction(port.decide)
    result = await port.decide(context)
    assert result is FailureAction.FAIL
    assert fake.received is context


@pytest.mark.parametrize(
    "action",
    [FailureAction.RETRY, FailureAction.FALLBACK, FailureAction.FAIL],
)
async def test_structural_fake_can_return_each_failure_action(action: FailureAction) -> None:
    port = _as_failure_policy(_StructuralFailurePolicyFake(action))
    result = await port.decide(_context())
    assert result is action
