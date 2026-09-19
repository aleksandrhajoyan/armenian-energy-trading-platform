"""Initial Phase 3 attempt-number source always resolves the current attempt as one."""

from __future__ import annotations

import inspect
from typing import get_type_hints

from energy_trading.application.orchestration.forecasting_attempt_number import (
    ForecastingAttemptNumberPort,
)
from energy_trading.application.orchestration.forecasting_initial_attempt_number_source import (
    InitialForecastingAttemptNumberSource,
)

_WORKFLOW_IDS = (
    "wf-1",
    "wf-alpha",
    "wf-beta",
    "wf/with/slashes",
    "WF-UPPER",
    "wf with spaces",
)

_OPAQUE_WORKFLOW_IDS = (
    "  wf-1  ",
    "wf/with/slashes",
    "wf%encoded",
    "wf\twith-tab",
    "wf-id!@#",
)


def _source() -> InitialForecastingAttemptNumberSource:
    return InitialForecastingAttemptNumberSource()


def test_source_does_not_inherit_attempt_number_port() -> None:
    assert ForecastingAttemptNumberPort not in (InitialForecastingAttemptNumberSource.__mro__)
    assert not any(
        base.__name__ in {"ForecastingAttemptNumberPort", "Protocol"}
        for base in InitialForecastingAttemptNumberSource.__bases__
    )


def test_source_structurally_satisfies_attempt_number_port() -> None:
    port: ForecastingAttemptNumberPort = _source()
    assert isinstance(port, InitialForecastingAttemptNumberSource)


def test_get_attempt_number_signature_matches_published_port() -> None:
    source_hints = get_type_hints(InitialForecastingAttemptNumberSource.get_attempt_number)
    port_hints = get_type_hints(ForecastingAttemptNumberPort.get_attempt_number)
    assert inspect.signature(
        InitialForecastingAttemptNumberSource.get_attempt_number
    ).parameters.keys() == (
        inspect.signature(ForecastingAttemptNumberPort.get_attempt_number).parameters.keys()
    )
    assert source_hints["workflow_id"] is port_hints["workflow_id"] is str
    assert source_hints["return"] is port_hints["return"] is int
    assert inspect.iscoroutinefunction(InitialForecastingAttemptNumberSource.get_attempt_number)


def test_source_exposes_no_public_mutation_methods() -> None:
    public_operations = [
        name
        for name, value in vars(InitialForecastingAttemptNumberSource).items()
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


def test_source_has_no_constructor_dependency() -> None:
    signature = inspect.signature(InitialForecastingAttemptNumberSource)
    assert tuple(signature.parameters) == ()


async def test_get_attempt_number_returns_literal_one() -> None:
    result = await _source().get_attempt_number("wf-1")
    assert result == 1
    assert type(result) is int


async def test_repeated_calls_for_the_same_workflow_are_deterministic() -> None:
    source = _source()
    workflow_id = "wf-repeat"
    first = await source.get_attempt_number(workflow_id)
    second = await source.get_attempt_number(workflow_id)
    third = await source.get_attempt_number(workflow_id)
    assert first == second == third == 1
    assert type(first) is int


async def test_repeated_calls_for_different_workflows_return_one() -> None:
    source = _source()
    results = [await source.get_attempt_number(workflow_id) for workflow_id in _WORKFLOW_IDS]
    assert results == [1] * len(_WORKFLOW_IDS)
    assert all(type(result) is int for result in results)


async def test_result_is_independent_of_opaque_workflow_id_formatting() -> None:
    source = _source()
    results = [await source.get_attempt_number(workflow_id) for workflow_id in _OPAQUE_WORKFLOW_IDS]
    assert results == [1] * len(_OPAQUE_WORKFLOW_IDS)


async def test_source_does_not_accumulate_per_workflow_state() -> None:
    source = _source()
    first_a = await source.get_attempt_number("wf-a")
    other = await source.get_attempt_number("wf-b")
    second_a = await source.get_attempt_number("wf-a")
    third_a = await source.get_attempt_number("wf-a")
    assert first_a == other == second_a == third_a == 1
    assert source.__dict__ == {}
