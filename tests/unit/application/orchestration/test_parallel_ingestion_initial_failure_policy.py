"""Initial Phase 2 failure policy always decides terminal FAIL."""

from __future__ import annotations

import inspect
from typing import get_type_hints

import pytest

from energy_trading.application.agents import AgentName
from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration import (
    FailureAction,
    FailurePolicyContext,
    FailurePolicyPort,
    InitialParallelIngestionAttemptNumberSource,
    InitialParallelIngestionFailurePolicy,
    ParallelIngestionAgentFailure,
    ParallelIngestionFailureContextPreparationService,
    ParallelIngestionFailureContextResolutionService,
    StrictSingleParallelIngestionFailureSelector,
    WorkflowPhase,
)

_ERROR_CODES = (
    "invalid_request",
    "dependency_unavailable",
    "conflict",
    "resource_not_found",
    "parallel_ingestion_unexpected_failure",
)

_ATTEMPT_NUMBERS = (1, 2, 3, 11)


def _policy() -> InitialParallelIngestionFailurePolicy:
    return InitialParallelIngestionFailurePolicy()


def _context(**overrides: object) -> FailurePolicyContext:
    values: dict[str, object] = {
        "phase": WorkflowPhase.INGESTION,
        "error_code": "invalid_request",
        "attempt_number": 1,
        "agent_name": None,
    }
    values.update(overrides)
    return FailurePolicyContext(**values)  # type: ignore[arg-type]


def _chained_failure(
    agent_name: AgentName,
    cause: BaseException,
) -> ParallelIngestionAgentFailure:
    try:
        raise ParallelIngestionAgentFailure(agent_name) from cause
    except ParallelIngestionAgentFailure as exc:
        return exc


def test_policy_does_not_inherit_failure_policy_port() -> None:
    assert FailurePolicyPort not in InitialParallelIngestionFailurePolicy.__mro__
    assert not any(
        base.__name__ in {"FailurePolicyPort", "Protocol"}
        for base in InitialParallelIngestionFailurePolicy.__bases__
    )


def test_policy_structurally_satisfies_failure_policy_port() -> None:
    port: FailurePolicyPort = _policy()
    assert isinstance(port, InitialParallelIngestionFailurePolicy)


def test_decide_signature_matches_published_port() -> None:
    policy_hints = get_type_hints(InitialParallelIngestionFailurePolicy.decide)
    port_hints = get_type_hints(FailurePolicyPort.decide)
    assert inspect.signature(InitialParallelIngestionFailurePolicy.decide).parameters.keys() == (
        inspect.signature(FailurePolicyPort.decide).parameters.keys()
    )
    assert policy_hints["context"] is port_hints["context"] is FailurePolicyContext
    assert policy_hints["return"] is port_hints["return"] is FailureAction
    assert inspect.iscoroutinefunction(InitialParallelIngestionFailurePolicy.decide)


def test_policy_exposes_no_public_configuration_methods() -> None:
    public_operations = [
        name
        for name, value in vars(InitialParallelIngestionFailurePolicy).items()
        if callable(value) and not name.startswith("_")
    ]
    assert public_operations == ["decide"]
    forbidden_write_names = {
        "configure",
        "set_action",
        "set_rules",
        "register",
        "add_rule",
        "enable_retry",
        "enable_fallback",
    }
    leaked = sorted(name for name in public_operations if name in forbidden_write_names)
    assert leaked == []


@pytest.mark.parametrize("phase", list(WorkflowPhase))
async def test_decide_returns_fail_for_each_phase(phase: WorkflowPhase) -> None:
    context = _context(phase=phase)
    result = await _policy().decide(context)
    assert result is FailureAction.FAIL
    assert result is not FailureAction.RETRY
    assert result is not FailureAction.FALLBACK


@pytest.mark.parametrize("error_code", _ERROR_CODES)
async def test_decide_returns_fail_for_distinct_error_codes(error_code: str) -> None:
    context = _context(error_code=error_code)
    result = await _policy().decide(context)
    assert result is FailureAction.FAIL


@pytest.mark.parametrize("attempt_number", _ATTEMPT_NUMBERS)
async def test_decide_returns_fail_for_positive_attempt_numbers(attempt_number: int) -> None:
    context = _context(attempt_number=attempt_number)
    result = await _policy().decide(context)
    assert result is FailureAction.FAIL


@pytest.mark.parametrize("agent_name", [None, *list(AgentName)])
async def test_decide_returns_fail_for_optional_agent_names(
    agent_name: AgentName | None,
) -> None:
    context = _context(agent_name=agent_name)
    result = await _policy().decide(context)
    assert result is FailureAction.FAIL


async def test_result_is_independent_of_context_fields() -> None:
    first = await _policy().decide(
        _context(
            phase=WorkflowPhase.CONTRACT,
            error_code="invalid_request",
            attempt_number=1,
            agent_name=AgentName.WEATHER_AND_RENEWABLE_FORECAST,
        )
    )
    second = await _policy().decide(
        _context(
            phase=WorkflowPhase.SETTLEMENT,
            error_code="parallel_ingestion_unexpected_failure",
            attempt_number=11,
            agent_name=None,
        )
    )
    assert first is second is FailureAction.FAIL


async def test_repeated_calls_with_the_same_context_are_deterministic() -> None:
    policy = _policy()
    context = _context(error_code="conflict", attempt_number=2)
    first = await policy.decide(context)
    second = await policy.decide(context)
    third = await policy.decide(context)
    assert first is second is third is FailureAction.FAIL


async def test_decide_does_not_mutate_supplied_context() -> None:
    context = _context(
        phase=WorkflowPhase.FORECASTING,
        error_code="dependency_unavailable",
        attempt_number=3,
        agent_name=AgentName.HYDRO_RESOURCES,
    )
    before = (
        context.phase,
        context.error_code,
        context.attempt_number,
        context.agent_name,
    )
    result = await _policy().decide(context)
    assert result is FailureAction.FAIL
    assert (
        context.phase,
        context.error_code,
        context.attempt_number,
        context.agent_name,
    ) == before
    assert context.phase is WorkflowPhase.FORECASTING
    assert context.agent_name is AgentName.HYDRO_RESOURCES


async def test_real_preparation_then_policy_decides_fail_without_action_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cause = InvalidRequestError("weather request is invalid")
    leaf = _chained_failure(AgentName.WEATHER_AND_RENEWABLE_FORECAST, cause)
    group = ExceptionGroup("group", [leaf])
    preparation = ParallelIngestionFailureContextPreparationService(
        ParallelIngestionFailureContextResolutionService(
            StrictSingleParallelIngestionFailureSelector(),
            InitialParallelIngestionAttemptNumberSource(),
        )
    )
    phase = WorkflowPhase.INGESTION
    policy_calls: list[str] = []

    def _track(name: str):
        def _inner(*args: object, **kwargs: object) -> object:
            policy_calls.append(name)
            raise AssertionError(f"{name} must not be invoked")

        return _inner

    monkeypatch.setattr(
        "energy_trading.application.orchestration.parallel_ingestion_failure_decision"
        ".ParallelIngestionFailureDecisionService.decide",
        _track("ParallelIngestionFailureDecisionService.decide"),
    )
    monkeypatch.setattr(
        "energy_trading.application.orchestration.parallel_ingestion_failure_handling"
        ".ParallelIngestionFailureHandlingService.handle",
        _track("ParallelIngestionFailureHandlingService.handle"),
    )
    monkeypatch.setattr(
        "energy_trading.application.orchestration.parallel_ingestion_failure_action"
        ".execute_parallel_ingestion_failure_action",
        _track("execute_parallel_ingestion_failure_action"),
    )
    monkeypatch.setattr(
        "energy_trading.application.orchestration.parallel_ingestion_failure_transition"
        ".fail_parallel_ingestion",
        _track("fail_parallel_ingestion"),
    )

    context = await preparation.prepare(
        workflow_id="wf-initial-policy",
        phase=phase,
        failure_group=group,
    )
    action = await _policy().decide(context)

    assert context.phase is phase
    assert context.error_code == cause.code
    assert context.agent_name is AgentName.WEATHER_AND_RENEWABLE_FORECAST
    assert context.attempt_number == 1
    assert action is FailureAction.FAIL
    assert policy_calls == []
