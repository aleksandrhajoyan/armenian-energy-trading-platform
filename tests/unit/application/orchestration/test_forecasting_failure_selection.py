"""Phase 3 failure-fact selection is a structural Protocol only."""

from __future__ import annotations

import inspect
from typing import get_type_hints

from energy_trading.application.agents import AgentName
from energy_trading.application.orchestration import (
    ForecastingFailureFact,
    ForecastingFailureSelectionPort,
)


class _StructuralForecastingFailureSelectionFake:
    """Test-only fake that structurally satisfies the selection Protocol.

    Not a production selector. Does not inherit a production base class.
    The predetermined result is test-local wiring, not a multi-failure rule.
    """

    def __init__(self, result: ForecastingFailureFact) -> None:
        self._result = result
        self.received: tuple[ForecastingFailureFact, ...] | None = None

    def select(self, facts: tuple[ForecastingFailureFact, ...]) -> ForecastingFailureFact:
        self.received = facts
        return self._result


def _as_selection_port(
    fake: _StructuralForecastingFailureSelectionFake,
) -> ForecastingFailureSelectionPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return fake


def _fact(agent_name: AgentName, error_code: str) -> ForecastingFailureFact:
    return ForecastingFailureFact(agent_name=agent_name, error_code=error_code)


def test_structural_fake_does_not_inherit_production_base() -> None:
    assert ForecastingFailureSelectionPort not in (
        _StructuralForecastingFailureSelectionFake.__mro__
    )
    assert not any(
        base.__name__ in {"ForecastingFailureSelectionPort", "Protocol"}
        for base in _StructuralForecastingFailureSelectionFake.__bases__
    )


def test_structural_fake_can_be_assigned_to_selection_port() -> None:
    chosen = _fact(AgentName.CONSUMER_LOAD_FORECAST, "dependency_unavailable")
    port = _as_selection_port(_StructuralForecastingFailureSelectionFake(chosen))
    assert isinstance(port, _StructuralForecastingFailureSelectionFake)


def test_select_signature_is_fact_tuple_to_one_fact() -> None:
    parameters = inspect.signature(ForecastingFailureSelectionPort.select).parameters
    assert tuple(parameters) == ("self", "facts")
    hints = get_type_hints(ForecastingFailureSelectionPort.select)
    assert hints["facts"] == tuple[ForecastingFailureFact, ...]
    assert hints["return"] is ForecastingFailureFact
    assert not inspect.iscoroutinefunction(ForecastingFailureSelectionPort.select)
    public_operations = [
        name
        for name, value in vars(ForecastingFailureSelectionPort).items()
        if callable(value) and not name.startswith("_")
    ]
    assert public_operations == ["select"]


def test_select_receives_exact_tuple_and_returns_exact_fact() -> None:
    first = _fact(AgentName.CONSUMER_LOAD_FORECAST, "invalid_request")
    second = _fact(AgentName.DAM_PRICE_FORECAST, "dependency_unavailable")
    facts = (first, second)
    fake = _StructuralForecastingFailureSelectionFake(second)
    port = _as_selection_port(fake)
    selected = port.select(facts)
    assert fake.received is facts
    assert selected is second
    assert selected is not first


def test_duplicate_agent_identities_are_representable() -> None:
    first = _fact(AgentName.CONSUMER_LOAD_FORECAST, "invalid_request")
    second = _fact(AgentName.CONSUMER_LOAD_FORECAST, "dependency_unavailable")
    facts = (first, second)
    fake = _StructuralForecastingFailureSelectionFake(first)
    port = _as_selection_port(fake)
    selected = port.select(facts)
    assert fake.received is facts
    assert selected is first
    assert facts[0].agent_name is facts[1].agent_name
    assert facts[0].error_code != facts[1].error_code


def test_mixed_error_codes_are_representable() -> None:
    consumer = _fact(AgentName.CONSUMER_LOAD_FORECAST, "invalid_request")
    dam = _fact(AgentName.DAM_PRICE_FORECAST, "forecasting_unexpected_failure")
    facts = (consumer, dam)
    fake = _StructuralForecastingFailureSelectionFake(dam)
    port = _as_selection_port(fake)
    selected = port.select(facts)
    assert fake.received is facts
    assert selected is dam
    assert {fact.error_code for fact in facts} == {
        "invalid_request",
        "forecasting_unexpected_failure",
    }


def test_select_does_not_require_exception_or_workflow_or_policy_types() -> None:
    parameters = inspect.signature(ForecastingFailureSelectionPort.select).parameters
    assert "exception" not in parameters
    assert "exc" not in parameters
    assert "state" not in parameters
    assert "attempt_number" not in parameters
    assert "context" not in parameters
    assert "action" not in parameters
    fact = _fact(AgentName.DAM_PRICE_FORECAST, "resource_not_found")
    facts = (fact,)
    selected = _as_selection_port(_StructuralForecastingFailureSelectionFake(fact)).select(facts)
    assert selected is fact
