"""Phase 2 attempt-number source is a structural Protocol only."""

from __future__ import annotations

import inspect
from typing import get_type_hints

from energy_trading.application.orchestration import ParallelIngestionAttemptNumberPort


class _StructuralParallelIngestionAttemptNumberFake:
    """Test-only fake that structurally satisfies the attempt-number Protocol.

    Not a production tracker. Does not inherit a production base class.
    The predetermined result is test-local wiring, not increment semantics.
    """

    def __init__(self, result: int) -> None:
        self._result = result
        self.received: str | None = None

    async def get_attempt_number(self, workflow_id: str) -> int:
        self.received = workflow_id
        return self._result


def _as_attempt_number_port(
    fake: _StructuralParallelIngestionAttemptNumberFake,
) -> ParallelIngestionAttemptNumberPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return fake


def test_structural_fake_does_not_inherit_production_base() -> None:
    assert ParallelIngestionAttemptNumberPort not in (
        _StructuralParallelIngestionAttemptNumberFake.__mro__
    )
    assert not any(
        base.__name__ in {"ParallelIngestionAttemptNumberPort", "Protocol"}
        for base in _StructuralParallelIngestionAttemptNumberFake.__bases__
    )


def test_structural_fake_can_be_assigned_to_attempt_number_port() -> None:
    port = _as_attempt_number_port(_StructuralParallelIngestionAttemptNumberFake(1))
    assert isinstance(port, _StructuralParallelIngestionAttemptNumberFake)


def test_get_attempt_number_signature_is_async_workflow_id_to_int() -> None:
    parameters = inspect.signature(ParallelIngestionAttemptNumberPort.get_attempt_number).parameters
    assert tuple(parameters) == ("self", "workflow_id")
    hints = get_type_hints(ParallelIngestionAttemptNumberPort.get_attempt_number)
    assert hints["workflow_id"] is str
    assert hints["return"] is int
    assert inspect.iscoroutinefunction(ParallelIngestionAttemptNumberPort.get_attempt_number)
    public_operations = [
        name
        for name, value in vars(ParallelIngestionAttemptNumberPort).items()
        if callable(value) and not name.startswith("_")
    ]
    assert public_operations == ["get_attempt_number"]


async def test_get_attempt_number_receives_exact_workflow_id() -> None:
    workflow_id = "wf-unchanged-identity"
    fake = _StructuralParallelIngestionAttemptNumberFake(1)
    port = _as_attempt_number_port(fake)
    result = await port.get_attempt_number(workflow_id)
    assert fake.received is workflow_id
    assert result == 1


async def test_fake_may_return_later_positive_attempt_without_transformation() -> None:
    workflow_id = "wf-later-attempt"
    fake = _StructuralParallelIngestionAttemptNumberFake(3)
    port = _as_attempt_number_port(fake)
    result = await port.get_attempt_number(workflow_id)
    assert fake.received is workflow_id
    assert result == 3


def test_get_attempt_number_does_not_require_state_failure_or_policy_types() -> None:
    parameters = inspect.signature(ParallelIngestionAttemptNumberPort.get_attempt_number).parameters
    assert "state" not in parameters
    assert "facts" not in parameters
    assert "context" not in parameters
    assert "action" not in parameters
    assert "agent_name" not in parameters
    assert "exception" not in parameters
    assert "exc" not in parameters


def test_port_exposes_no_write_operations() -> None:
    public_operations = [
        name
        for name, value in vars(ParallelIngestionAttemptNumberPort).items()
        if callable(value) and not name.startswith("_")
    ]
    assert public_operations == ["get_attempt_number"]
    forbidden_write_names = {
        "increment",
        "increment_attempt",
        "next_attempt",
        "reset",
        "reset_attempt",
        "set_attempt",
        "record_attempt",
        "begin_attempt",
        "complete_attempt",
        "next",
        "set",
        "record",
        "begin",
        "complete",
    }
    leaked = sorted(name for name in public_operations if name in forbidden_write_names)
    assert leaked == []
