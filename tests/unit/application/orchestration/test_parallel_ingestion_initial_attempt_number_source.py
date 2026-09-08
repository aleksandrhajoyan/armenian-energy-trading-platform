"""Initial Phase 2 attempt-number source always resolves the current attempt as one."""

from __future__ import annotations

import inspect
from typing import get_type_hints

import pytest

from energy_trading.application.agents import AgentName
from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration import (
    FailurePolicyContext,
    InitialParallelIngestionAttemptNumberSource,
    ParallelIngestionAttemptNumberPort,
    ParallelIngestionFailureContextResolutionService,
    ParallelIngestionFailureFact,
    StrictSingleParallelIngestionFailureSelector,
    WorkflowPhase,
)

_WORKFLOW_IDS = (
    "wf-alpha",
    "wf-beta",
    "wf/with/slashes",
    "WF-UPPER",
    "wf with spaces",
)


def _source() -> InitialParallelIngestionAttemptNumberSource:
    return InitialParallelIngestionAttemptNumberSource()


def test_source_does_not_inherit_attempt_number_port() -> None:
    assert ParallelIngestionAttemptNumberPort not in (
        InitialParallelIngestionAttemptNumberSource.__mro__
    )
    assert not any(
        base.__name__ in {"ParallelIngestionAttemptNumberPort", "Protocol"}
        for base in InitialParallelIngestionAttemptNumberSource.__bases__
    )


def test_source_structurally_satisfies_attempt_number_port() -> None:
    port: ParallelIngestionAttemptNumberPort = _source()
    assert isinstance(port, InitialParallelIngestionAttemptNumberSource)


def test_get_attempt_number_signature_matches_published_port() -> None:
    source_hints = get_type_hints(InitialParallelIngestionAttemptNumberSource.get_attempt_number)
    port_hints = get_type_hints(ParallelIngestionAttemptNumberPort.get_attempt_number)
    assert inspect.signature(
        InitialParallelIngestionAttemptNumberSource.get_attempt_number
    ).parameters.keys() == (
        inspect.signature(ParallelIngestionAttemptNumberPort.get_attempt_number).parameters.keys()
    )
    assert source_hints["workflow_id"] is port_hints["workflow_id"] is str
    assert source_hints["return"] is port_hints["return"] is int
    assert inspect.iscoroutinefunction(
        InitialParallelIngestionAttemptNumberSource.get_attempt_number
    )


def test_source_exposes_no_public_mutation_methods() -> None:
    public_operations = [
        name
        for name, value in vars(InitialParallelIngestionAttemptNumberSource).items()
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


@pytest.mark.parametrize("workflow_id", _WORKFLOW_IDS)
async def test_get_attempt_number_returns_literal_one(workflow_id: str) -> None:
    result = await _source().get_attempt_number(workflow_id)
    assert result == 1
    assert type(result) is int


async def test_repeated_calls_for_the_same_workflow_are_deterministic() -> None:
    source = _source()
    workflow_id = "wf-repeat"
    first = await source.get_attempt_number(workflow_id)
    second = await source.get_attempt_number(workflow_id)
    third = await source.get_attempt_number(workflow_id)
    assert first == second == third == 1


async def test_repeated_calls_for_different_workflows_return_one() -> None:
    source = _source()
    results = [await source.get_attempt_number(workflow_id) for workflow_id in _WORKFLOW_IDS]
    assert results == [1] * len(_WORKFLOW_IDS)


async def test_source_does_not_accumulate_per_workflow_state() -> None:
    source = _source()
    first_a = await source.get_attempt_number("wf-a")
    other = await source.get_attempt_number("wf-b")
    second_a = await source.get_attempt_number("wf-a")
    third_a = await source.get_attempt_number("wf-a")
    assert first_a == other == second_a == third_a == 1


async def test_result_is_independent_of_workflow_id_formatting() -> None:
    source = _source()
    compact = await source.get_attempt_number("wf-1")
    padded = await source.get_attempt_number("  wf-1  ")
    empty = await source.get_attempt_number("")
    assert compact == padded == empty == 1


async def test_real_composition_resolves_single_fact_context_with_attempt_one() -> None:
    fact = ParallelIngestionFailureFact(
        agent_name=AgentName.NEWS_INTELLIGENCE,
        error_code="conflict",
    )
    service = ParallelIngestionFailureContextResolutionService(
        StrictSingleParallelIngestionFailureSelector(),
        _source(),
    )
    workflow_id = "wf-initial-attempt"
    phase = WorkflowPhase.INGESTION

    context = await service.resolve(workflow_id=workflow_id, phase=phase, facts=(fact,))

    assert isinstance(context, FailurePolicyContext)
    assert context.phase is phase
    assert context.agent_name is fact.agent_name
    assert context.error_code == "conflict"
    assert context.attempt_number == 1


async def test_real_composition_still_fails_closed_on_multiple_facts() -> None:
    first = ParallelIngestionFailureFact(
        agent_name=AgentName.WEATHER_AND_RENEWABLE_FORECAST,
        error_code="invalid_request",
    )
    second = ParallelIngestionFailureFact(
        agent_name=AgentName.HYDRO_RESOURCES,
        error_code="dependency_unavailable",
    )
    service = ParallelIngestionFailureContextResolutionService(
        StrictSingleParallelIngestionFailureSelector(),
        _source(),
    )

    with pytest.raises(InvalidRequestError) as caught:
        await service.resolve(
            workflow_id="wf-initial-multi",
            phase=WorkflowPhase.INGESTION,
            facts=(first, second),
        )

    assert caught.value.code == "invalid_request"
    assert "Parallel-ingestion failure selection requires exactly one failure fact." == (
        caught.value.message
    )
