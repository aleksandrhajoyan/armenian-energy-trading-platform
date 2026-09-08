"""Strict single-failure Phase 2 selector fails closed unless exactly one fact exists."""

from __future__ import annotations

import inspect
from typing import get_type_hints

import pytest

from energy_trading.application.agents import AgentName
from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration import (
    FailurePolicyContext,
    ParallelIngestionAttemptNumberPort,
    ParallelIngestionFailureContextResolutionService,
    ParallelIngestionFailureFact,
    ParallelIngestionFailureSelectionPort,
    StrictSingleParallelIngestionFailureSelector,
    WorkflowPhase,
)

_EXACTLY_ONE_FACT_MESSAGE = (
    "Parallel-ingestion failure selection requires exactly one failure fact."
)

_PHASE_2_AGENTS = (
    AgentName.WEATHER_AND_RENEWABLE_FORECAST,
    AgentName.HYDRO_RESOURCES,
    AgentName.GENERATION_AVAILABILITY,
    AgentName.NEWS_INTELLIGENCE,
    AgentName.MARKET_MONITORING,
)


class _RecordingAttemptNumberFake:
    """Test-only fake that structurally satisfies the attempt-number Protocol.

    Not a production tracker. Does not inherit a production base class.
    """

    def __init__(self, result: int = 2) -> None:
        self._result = result
        self.calls = 0
        self.received: str | None = None

    async def get_attempt_number(self, workflow_id: str) -> int:
        self.calls += 1
        self.received = workflow_id
        return self._result


def _fact(agent_name: AgentName, error_code: str) -> ParallelIngestionFailureFact:
    return ParallelIngestionFailureFact(agent_name=agent_name, error_code=error_code)


def _selector() -> StrictSingleParallelIngestionFailureSelector:
    return StrictSingleParallelIngestionFailureSelector()


def test_selector_does_not_inherit_selection_port() -> None:
    assert ParallelIngestionFailureSelectionPort not in (
        StrictSingleParallelIngestionFailureSelector.__mro__
    )
    assert not any(
        base.__name__ in {"ParallelIngestionFailureSelectionPort", "Protocol"}
        for base in StrictSingleParallelIngestionFailureSelector.__bases__
    )


def test_selector_structurally_satisfies_selection_port() -> None:
    port: ParallelIngestionFailureSelectionPort = _selector()
    assert isinstance(port, StrictSingleParallelIngestionFailureSelector)


def test_select_signature_matches_published_port() -> None:
    selector_hints = get_type_hints(StrictSingleParallelIngestionFailureSelector.select)
    port_hints = get_type_hints(ParallelIngestionFailureSelectionPort.select)
    assert inspect.signature(
        StrictSingleParallelIngestionFailureSelector.select
    ).parameters.keys() == (
        inspect.signature(ParallelIngestionFailureSelectionPort.select).parameters.keys()
    )
    assert (
        selector_hints["facts"] == port_hints["facts"] == tuple[ParallelIngestionFailureFact, ...]
    )
    assert selector_hints["return"] is port_hints["return"] is ParallelIngestionFailureFact
    assert not inspect.iscoroutinefunction(StrictSingleParallelIngestionFailureSelector.select)


@pytest.mark.parametrize("agent_name", _PHASE_2_AGENTS)
def test_exactly_one_fact_returns_the_same_instance(agent_name: AgentName) -> None:
    fact = _fact(agent_name, "dependency_unavailable")
    facts = (fact,)
    selected = _selector().select(facts)
    assert selected is fact
    assert selected.agent_name is agent_name
    assert selected.error_code == "dependency_unavailable"


def test_exactly_one_fact_does_not_reconstruct_the_dto() -> None:
    fact = _fact(AgentName.HYDRO_RESOURCES, "invalid_request")
    selected = _selector().select((fact,))
    assert selected is fact
    assert selected is not _fact(AgentName.HYDRO_RESOURCES, "invalid_request")


def test_empty_tuple_raises_sanitized_invalid_request() -> None:
    with pytest.raises(InvalidRequestError) as caught:
        _selector().select(())
    assert caught.value.code == "invalid_request"
    assert caught.value.message == _EXACTLY_ONE_FACT_MESSAGE
    assert "tuple" not in caught.value.message.lower()
    assert "traceback" not in caught.value.message.lower()


@pytest.mark.parametrize(
    "facts",
    [
        (
            _fact(AgentName.WEATHER_AND_RENEWABLE_FORECAST, "invalid_request"),
            _fact(AgentName.HYDRO_RESOURCES, "dependency_unavailable"),
        ),
        (
            _fact(AgentName.WEATHER_AND_RENEWABLE_FORECAST, "invalid_request"),
            _fact(AgentName.HYDRO_RESOURCES, "dependency_unavailable"),
            _fact(AgentName.MARKET_MONITORING, "conflict"),
        ),
    ],
)
def test_multiple_facts_raise_sanitized_invalid_request(
    facts: tuple[ParallelIngestionFailureFact, ...],
) -> None:
    with pytest.raises(InvalidRequestError) as caught:
        _selector().select(facts)
    assert caught.value.code == "invalid_request"
    assert caught.value.message == _EXACTLY_ONE_FACT_MESSAGE
    assert caught.value.message != facts[0].error_code
    assert facts[0].agent_name.value not in caught.value.message
    assert facts[-1].agent_name.value not in caught.value.message


def test_duplicate_agent_identities_are_still_rejected() -> None:
    first = _fact(AgentName.NEWS_INTELLIGENCE, "invalid_request")
    second = _fact(AgentName.NEWS_INTELLIGENCE, "dependency_unavailable")
    facts = (first, second)
    with pytest.raises(InvalidRequestError) as caught:
        _selector().select(facts)
    assert caught.value.message == _EXACTLY_ONE_FACT_MESSAGE
    assert first is facts[0]
    assert second is facts[1]


def test_value_equal_duplicate_facts_are_still_rejected() -> None:
    first = _fact(AgentName.GENERATION_AVAILABILITY, "conflict")
    second = _fact(AgentName.GENERATION_AVAILABILITY, "conflict")
    assert first == second
    assert first is not second
    with pytest.raises(InvalidRequestError) as caught:
        _selector().select((first, second))
    assert caught.value.message == _EXACTLY_ONE_FACT_MESSAGE


def test_mixed_agents_and_error_codes_are_rejected_without_priority() -> None:
    weather = _fact(AgentName.WEATHER_AND_RENEWABLE_FORECAST, "invalid_request")
    news = _fact(AgentName.NEWS_INTELLIGENCE, "parallel_ingestion_unexpected_failure")
    market = _fact(AgentName.MARKET_MONITORING, "conflict")
    facts = (weather, news, market)
    with pytest.raises(InvalidRequestError) as caught:
        _selector().select(facts)
    assert caught.value.message == _EXACTLY_ONE_FACT_MESSAGE
    assert facts == (weather, news, market)


def test_input_tuple_and_facts_are_unchanged() -> None:
    fact = _fact(AgentName.MARKET_MONITORING, "resource_not_found")
    facts = (fact,)
    before = (fact.agent_name, fact.error_code)
    selected = _selector().select(facts)
    assert facts == (fact,)
    assert facts[0] is fact
    assert selected is fact
    assert (fact.agent_name, fact.error_code) == before


def test_single_fact_selection_is_deterministic() -> None:
    fact = _fact(AgentName.HYDRO_RESOURCES, "dependency_unavailable")
    selector = _selector()
    first = selector.select((fact,))
    second = selector.select((fact,))
    assert first is fact
    assert second is fact
    assert first is second


def test_invalid_multi_fact_selection_is_deterministically_fail_closed() -> None:
    facts = (
        _fact(AgentName.WEATHER_AND_RENEWABLE_FORECAST, "invalid_request"),
        _fact(AgentName.HYDRO_RESOURCES, "dependency_unavailable"),
    )
    selector = _selector()
    with pytest.raises(InvalidRequestError) as first:
        selector.select(facts)
    with pytest.raises(InvalidRequestError) as second:
        selector.select(facts)
    assert first.value.code == second.value.code == "invalid_request"
    assert first.value.message == second.value.message == _EXACTLY_ONE_FACT_MESSAGE


async def test_strict_selector_resolves_single_fact_context() -> None:
    fact = _fact(AgentName.NEWS_INTELLIGENCE, "conflict")
    attempt = _RecordingAttemptNumberFake(result=2)
    service = ParallelIngestionFailureContextResolutionService(_selector(), attempt)
    workflow_id = "wf-strict-single"
    phase = WorkflowPhase.INGESTION

    context = await service.resolve(workflow_id=workflow_id, phase=phase, facts=(fact,))

    assert isinstance(context, FailurePolicyContext)
    assert context.phase is phase
    assert context.agent_name is fact.agent_name
    assert context.error_code == "conflict"
    assert context.attempt_number == 2
    assert attempt.calls == 1
    assert attempt.received is workflow_id


async def test_strict_selector_multi_failure_short_circuits_attempt_lookup() -> None:
    first = _fact(AgentName.WEATHER_AND_RENEWABLE_FORECAST, "invalid_request")
    second = _fact(AgentName.HYDRO_RESOURCES, "dependency_unavailable")
    attempt = _RecordingAttemptNumberFake(result=2)
    service = ParallelIngestionFailureContextResolutionService(_selector(), attempt)

    with pytest.raises(InvalidRequestError) as caught:
        await service.resolve(
            workflow_id="wf-strict-multi",
            phase=WorkflowPhase.INGESTION,
            facts=(first, second),
        )

    assert caught.value.code == "invalid_request"
    assert caught.value.message == _EXACTLY_ONE_FACT_MESSAGE
    assert attempt.calls == 0
    assert attempt.received is None
    assert ParallelIngestionAttemptNumberPort not in _RecordingAttemptNumberFake.__mro__
