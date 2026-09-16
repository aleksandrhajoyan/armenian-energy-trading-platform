"""Strict single-failure Phase 3 selector fails closed unless exactly one fact exists."""

from __future__ import annotations

import inspect
from typing import get_type_hints

import pytest

from energy_trading.application.agents import AgentName
from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration import (
    ForecastingFailureFact,
    ForecastingFailureSelectionPort,
    StrictSingleForecastingFailureSelector,
)

_EXACTLY_ONE_FACT_MESSAGE = "Forecasting failure selection requires exactly one failure fact."

_PHASE_3_AGENTS = (
    AgentName.CONSUMER_LOAD_FORECAST,
    AgentName.DAM_PRICE_FORECAST,
)


def _fact(agent_name: AgentName, error_code: str) -> ForecastingFailureFact:
    return ForecastingFailureFact(agent_name=agent_name, error_code=error_code)


def _selector() -> StrictSingleForecastingFailureSelector:
    return StrictSingleForecastingFailureSelector()


def test_selector_does_not_inherit_selection_port() -> None:
    assert ForecastingFailureSelectionPort not in (StrictSingleForecastingFailureSelector.__mro__)
    assert not any(
        base.__name__ in {"ForecastingFailureSelectionPort", "Protocol"}
        for base in StrictSingleForecastingFailureSelector.__bases__
    )


def test_selector_structurally_satisfies_selection_port() -> None:
    port: ForecastingFailureSelectionPort = _selector()
    assert isinstance(port, StrictSingleForecastingFailureSelector)


def test_select_signature_matches_published_port() -> None:
    selector_hints = get_type_hints(StrictSingleForecastingFailureSelector.select)
    port_hints = get_type_hints(ForecastingFailureSelectionPort.select)
    assert inspect.signature(StrictSingleForecastingFailureSelector.select).parameters.keys() == (
        inspect.signature(ForecastingFailureSelectionPort.select).parameters.keys()
    )
    assert selector_hints["facts"] == port_hints["facts"] == tuple[ForecastingFailureFact, ...]
    assert selector_hints["return"] is port_hints["return"] is ForecastingFailureFact
    assert not inspect.iscoroutinefunction(StrictSingleForecastingFailureSelector.select)


@pytest.mark.parametrize("agent_name", _PHASE_3_AGENTS)
def test_exactly_one_fact_returns_the_same_instance(agent_name: AgentName) -> None:
    fact = _fact(agent_name, "dependency_unavailable")
    facts = (fact,)
    selected = _selector().select(facts)
    assert selected is fact
    assert selected.agent_name is agent_name
    assert selected.error_code == "dependency_unavailable"


def test_exactly_one_fact_does_not_reconstruct_the_dto() -> None:
    fact = _fact(AgentName.CONSUMER_LOAD_FORECAST, "invalid_request")
    selected = _selector().select((fact,))
    assert selected is fact
    assert selected is not _fact(AgentName.CONSUMER_LOAD_FORECAST, "invalid_request")


def test_empty_tuple_raises_sanitized_invalid_request() -> None:
    with pytest.raises(InvalidRequestError) as caught:
        _selector().select(())
    assert caught.value.code == "invalid_request"
    assert caught.value.message == _EXACTLY_ONE_FACT_MESSAGE
    assert "tuple" not in caught.value.message.lower()
    assert "traceback" not in caught.value.message.lower()
    assert "repr" not in caught.value.message.lower()
    assert AgentName.CONSUMER_LOAD_FORECAST.value not in caught.value.message
    assert AgentName.DAM_PRICE_FORECAST.value not in caught.value.message


@pytest.mark.parametrize(
    "facts",
    [
        (
            _fact(AgentName.CONSUMER_LOAD_FORECAST, "invalid_request"),
            _fact(AgentName.DAM_PRICE_FORECAST, "dependency_unavailable"),
        ),
        (
            _fact(AgentName.CONSUMER_LOAD_FORECAST, "invalid_request"),
            _fact(AgentName.DAM_PRICE_FORECAST, "dependency_unavailable"),
            _fact(AgentName.CONSUMER_LOAD_FORECAST, "conflict"),
        ),
    ],
)
def test_multiple_facts_raise_sanitized_invalid_request(
    facts: tuple[ForecastingFailureFact, ...],
) -> None:
    with pytest.raises(InvalidRequestError) as caught:
        _selector().select(facts)
    assert caught.value.code == "invalid_request"
    assert caught.value.message == _EXACTLY_ONE_FACT_MESSAGE
    assert caught.value.message != facts[0].error_code
    assert facts[0].agent_name.value not in caught.value.message
    assert facts[-1].agent_name.value not in caught.value.message
    assert facts[0].error_code not in caught.value.message
    assert facts[-1].error_code not in caught.value.message


def test_duplicate_agent_identities_are_still_rejected() -> None:
    first = _fact(AgentName.CONSUMER_LOAD_FORECAST, "invalid_request")
    second = _fact(AgentName.CONSUMER_LOAD_FORECAST, "dependency_unavailable")
    facts = (first, second)
    with pytest.raises(InvalidRequestError) as caught:
        _selector().select(facts)
    assert caught.value.message == _EXACTLY_ONE_FACT_MESSAGE
    assert first is facts[0]
    assert second is facts[1]


def test_value_equal_duplicate_facts_are_still_rejected() -> None:
    first = _fact(AgentName.DAM_PRICE_FORECAST, "conflict")
    second = _fact(AgentName.DAM_PRICE_FORECAST, "conflict")
    assert first == second
    assert first is not second
    with pytest.raises(InvalidRequestError) as caught:
        _selector().select((first, second))
    assert caught.value.message == _EXACTLY_ONE_FACT_MESSAGE


def test_mixed_agents_and_error_codes_are_rejected_without_priority() -> None:
    consumer = _fact(AgentName.CONSUMER_LOAD_FORECAST, "invalid_request")
    dam = _fact(AgentName.DAM_PRICE_FORECAST, "forecasting_unexpected_failure")
    facts = (consumer, dam)
    with pytest.raises(InvalidRequestError) as caught:
        _selector().select(facts)
    assert caught.value.message == _EXACTLY_ONE_FACT_MESSAGE
    assert facts == (consumer, dam)


def test_input_tuple_and_facts_are_unchanged() -> None:
    fact = _fact(AgentName.DAM_PRICE_FORECAST, "resource_not_found")
    facts = (fact,)
    before = (fact.agent_name, fact.error_code)
    selected = _selector().select(facts)
    assert facts == (fact,)
    assert facts[0] is fact
    assert selected is fact
    assert (fact.agent_name, fact.error_code) == before


def test_single_fact_selection_is_deterministic() -> None:
    fact = _fact(AgentName.CONSUMER_LOAD_FORECAST, "dependency_unavailable")
    selector = _selector()
    first = selector.select((fact,))
    second = selector.select((fact,))
    assert first is fact
    assert second is fact
    assert first is second


def test_invalid_multi_fact_selection_is_deterministically_fail_closed() -> None:
    facts = (
        _fact(AgentName.CONSUMER_LOAD_FORECAST, "invalid_request"),
        _fact(AgentName.DAM_PRICE_FORECAST, "dependency_unavailable"),
    )
    selector = _selector()
    with pytest.raises(InvalidRequestError) as first:
        selector.select(facts)
    with pytest.raises(InvalidRequestError) as second:
        selector.select(facts)
    assert first.value.code == second.value.code == "invalid_request"
    assert first.value.message == second.value.message == _EXACTLY_ONE_FACT_MESSAGE


def test_zero_and_multiple_facts_use_the_same_sanitized_message() -> None:
    selector = _selector()
    with pytest.raises(InvalidRequestError) as first:
        selector.select(())
    with pytest.raises(InvalidRequestError) as second:
        selector.select(
            (
                _fact(AgentName.CONSUMER_LOAD_FORECAST, "invalid_request"),
                _fact(AgentName.DAM_PRICE_FORECAST, "dependency_unavailable"),
            )
        )
    assert first.value.message == second.value.message == _EXACTLY_ONE_FACT_MESSAGE
    assert first.value.code == second.value.code == "invalid_request"
