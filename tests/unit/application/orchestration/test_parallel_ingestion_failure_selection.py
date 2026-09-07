"""Phase 2 failure-fact selection is a structural Protocol only."""

from __future__ import annotations

import inspect
from typing import get_type_hints

from energy_trading.application.agents import AgentName
from energy_trading.application.orchestration import (
    ParallelIngestionFailureFact,
    ParallelIngestionFailureSelectionPort,
)


class _StructuralParallelIngestionFailureSelectionFake:
    """Test-only fake that structurally satisfies the selection Protocol.

    Not a production selector. Does not inherit a production base class.
    The predetermined result is test-local wiring, not a multi-failure rule.
    """

    def __init__(self, result: ParallelIngestionFailureFact) -> None:
        self._result = result
        self.received: tuple[ParallelIngestionFailureFact, ...] | None = None

    def select(
        self, facts: tuple[ParallelIngestionFailureFact, ...]
    ) -> ParallelIngestionFailureFact:
        self.received = facts
        return self._result


def _as_selection_port(
    fake: _StructuralParallelIngestionFailureSelectionFake,
) -> ParallelIngestionFailureSelectionPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return fake


def _fact(agent_name: AgentName, error_code: str) -> ParallelIngestionFailureFact:
    return ParallelIngestionFailureFact(agent_name=agent_name, error_code=error_code)


def test_structural_fake_does_not_inherit_production_base() -> None:
    assert ParallelIngestionFailureSelectionPort not in (
        _StructuralParallelIngestionFailureSelectionFake.__mro__
    )
    assert not any(
        base.__name__ in {"ParallelIngestionFailureSelectionPort", "Protocol"}
        for base in _StructuralParallelIngestionFailureSelectionFake.__bases__
    )


def test_structural_fake_can_be_assigned_to_selection_port() -> None:
    chosen = _fact(AgentName.HYDRO_RESOURCES, "dependency_unavailable")
    port = _as_selection_port(_StructuralParallelIngestionFailureSelectionFake(chosen))
    assert isinstance(port, _StructuralParallelIngestionFailureSelectionFake)


def test_select_signature_is_fact_tuple_to_one_fact() -> None:
    parameters = inspect.signature(ParallelIngestionFailureSelectionPort.select).parameters
    assert tuple(parameters) == ("self", "facts")
    hints = get_type_hints(ParallelIngestionFailureSelectionPort.select)
    assert hints["facts"] == tuple[ParallelIngestionFailureFact, ...]
    assert hints["return"] is ParallelIngestionFailureFact
    assert not inspect.iscoroutinefunction(ParallelIngestionFailureSelectionPort.select)
    public_operations = [
        name
        for name, value in vars(ParallelIngestionFailureSelectionPort).items()
        if callable(value) and not name.startswith("_")
    ]
    assert public_operations == ["select"]


def test_select_receives_exact_tuple_and_returns_exact_fact() -> None:
    first = _fact(AgentName.WEATHER_AND_RENEWABLE_FORECAST, "invalid_request")
    second = _fact(AgentName.HYDRO_RESOURCES, "dependency_unavailable")
    facts = (first, second)
    fake = _StructuralParallelIngestionFailureSelectionFake(second)
    port = _as_selection_port(fake)
    selected = port.select(facts)
    assert fake.received is facts
    assert selected is second
    assert selected is not first


def test_duplicate_agent_identities_are_representable() -> None:
    first = _fact(AgentName.HYDRO_RESOURCES, "invalid_request")
    second = _fact(AgentName.HYDRO_RESOURCES, "dependency_unavailable")
    facts = (first, second)
    fake = _StructuralParallelIngestionFailureSelectionFake(first)
    port = _as_selection_port(fake)
    selected = port.select(facts)
    assert fake.received is facts
    assert selected is first
    assert facts[0].agent_name is facts[1].agent_name
    assert facts[0].error_code != facts[1].error_code


def test_mixed_error_codes_are_representable() -> None:
    weather = _fact(AgentName.WEATHER_AND_RENEWABLE_FORECAST, "invalid_request")
    news = _fact(AgentName.NEWS_INTELLIGENCE, "parallel_ingestion_unexpected_failure")
    market = _fact(AgentName.MARKET_MONITORING, "conflict")
    facts = (weather, news, market)
    fake = _StructuralParallelIngestionFailureSelectionFake(news)
    port = _as_selection_port(fake)
    selected = port.select(facts)
    assert fake.received is facts
    assert selected is news
    assert {fact.error_code for fact in facts} == {
        "invalid_request",
        "parallel_ingestion_unexpected_failure",
        "conflict",
    }


def test_select_does_not_require_exception_or_workflow_or_policy_types() -> None:
    parameters = inspect.signature(ParallelIngestionFailureSelectionPort.select).parameters
    assert "exception" not in parameters
    assert "exc" not in parameters
    assert "state" not in parameters
    assert "attempt_number" not in parameters
    assert "context" not in parameters
    assert "action" not in parameters
    fact = _fact(AgentName.GENERATION_AVAILABILITY, "resource_not_found")
    facts = (fact,)
    selected = _as_selection_port(_StructuralParallelIngestionFailureSelectionFake(fact)).select(
        facts
    )
    assert selected is fact
