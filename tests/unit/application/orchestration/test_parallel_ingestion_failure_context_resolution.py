"""Phase 2 failure-policy context resolution composes selection and attempt lookup."""

from __future__ import annotations

import inspect

import pytest

from energy_trading.application.agents import AgentName
from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.application.orchestration import (
    FailurePolicyContext,
    ParallelIngestionAttemptNumberPort,
    ParallelIngestionFailureContextResolutionService,
    ParallelIngestionFailureFact,
    ParallelIngestionFailureSelectionPort,
    WorkflowPhase,
    build_parallel_ingestion_failure_policy_context,
)


class _RecordingSelectionFake:
    """Test-only fake that structurally satisfies the selection Protocol.

    Not a production selector. Does not inherit a production base class.
    The predetermined result is test-local wiring, not a multi-failure rule.
    """

    def __init__(
        self,
        result: ParallelIngestionFailureFact | None = None,
        error: BaseException | None = None,
        call_order: list[str] | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self._call_order = call_order if call_order is not None else []
        self.calls = 0
        self.received: tuple[ParallelIngestionFailureFact, ...] | None = None

    def select(
        self, facts: tuple[ParallelIngestionFailureFact, ...]
    ) -> ParallelIngestionFailureFact:
        self.calls += 1
        self._call_order.append("select")
        self.received = facts
        if self._error is not None:
            raise self._error
        if self._result is None:
            msg = "recording selection fake requires a result or an error"
            raise AssertionError(msg)
        return self._result


class _RecordingAttemptNumberFake:
    """Test-only fake that structurally satisfies the attempt-number Protocol.

    Not a production tracker. Does not inherit a production base class.
    The predetermined result is test-local wiring, not increment semantics.
    """

    def __init__(
        self,
        result: int | None = None,
        error: BaseException | None = None,
        call_order: list[str] | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self._call_order = call_order if call_order is not None else []
        self.calls = 0
        self.received: str | None = None

    async def get_attempt_number(self, workflow_id: str) -> int:
        self.calls += 1
        self._call_order.append("get_attempt_number")
        self.received = workflow_id
        if self._error is not None:
            raise self._error
        if self._result is None:
            msg = "recording attempt fake requires a result or an error"
            raise AssertionError(msg)
        return self._result


def _fact(agent_name: AgentName, error_code: str) -> ParallelIngestionFailureFact:
    return ParallelIngestionFailureFact(agent_name=agent_name, error_code=error_code)


def _as_selection_port(
    fake: _RecordingSelectionFake,
) -> ParallelIngestionFailureSelectionPort:
    return fake


def _as_attempt_number_port(
    fake: _RecordingAttemptNumberFake,
) -> ParallelIngestionAttemptNumberPort:
    return fake


def _service(
    selection: _RecordingSelectionFake,
    attempt: _RecordingAttemptNumberFake,
) -> ParallelIngestionFailureContextResolutionService:
    return ParallelIngestionFailureContextResolutionService(
        _as_selection_port(selection),
        _as_attempt_number_port(attempt),
    )


def test_structural_fakes_do_not_inherit_production_ports() -> None:
    assert ParallelIngestionFailureSelectionPort not in _RecordingSelectionFake.__mro__
    assert ParallelIngestionAttemptNumberPort not in _RecordingAttemptNumberFake.__mro__
    assert not any(
        base.__name__
        in {
            "ParallelIngestionFailureSelectionPort",
            "ParallelIngestionAttemptNumberPort",
            "Protocol",
        }
        for base in (*_RecordingSelectionFake.__bases__, *_RecordingAttemptNumberFake.__bases__)
    )


def test_service_does_not_inherit_selection_or_attempt_ports() -> None:
    service_mro = ParallelIngestionFailureContextResolutionService.__mro__
    assert ParallelIngestionFailureSelectionPort not in service_mro
    assert ParallelIngestionAttemptNumberPort not in service_mro


def test_constructor_accepts_exactly_the_two_published_ports() -> None:
    signature = inspect.signature(ParallelIngestionFailureContextResolutionService.__init__)
    assert tuple(signature.parameters) == ("self", "selection_port", "attempt_number_port")
    assert (
        signature.parameters["selection_port"].annotation is ParallelIngestionFailureSelectionPort
    )
    assert (
        signature.parameters["attempt_number_port"].annotation is ParallelIngestionAttemptNumberPort
    )


def test_resolve_signature_is_keyword_only_workflow_phase_and_facts() -> None:
    signature = inspect.signature(ParallelIngestionFailureContextResolutionService.resolve)
    assert tuple(signature.parameters) == ("self", "workflow_id", "phase", "facts")
    assert signature.parameters["workflow_id"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["phase"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["facts"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["workflow_id"].annotation is str
    assert signature.parameters["phase"].annotation is WorkflowPhase
    assert signature.parameters["facts"].annotation == tuple[ParallelIngestionFailureFact, ...]
    assert signature.return_annotation is FailurePolicyContext
    assert inspect.iscoroutinefunction(ParallelIngestionFailureContextResolutionService.resolve)


async def test_resolve_builds_context_from_selected_fact_and_attempt_number() -> None:
    workflow_id = "wf-context-resolution"
    phase = WorkflowPhase.INGESTION
    first = _fact(AgentName.WEATHER_AND_RENEWABLE_FORECAST, "invalid_request")
    second = _fact(AgentName.HYDRO_RESOURCES, "dependency_unavailable")
    third = _fact(AgentName.MARKET_MONITORING, "conflict")
    facts = (first, second, third)
    facts_before = facts
    second_before = (second.agent_name, second.error_code)
    call_order: list[str] = []
    selection = _RecordingSelectionFake(result=second, call_order=call_order)
    attempt = _RecordingAttemptNumberFake(result=3, call_order=call_order)
    service = _service(selection, attempt)

    context = await service.resolve(workflow_id=workflow_id, phase=phase, facts=facts)
    expected = build_parallel_ingestion_failure_policy_context(
        phase=phase,
        error_code=second.error_code,
        attempt_number=3,
        agent_name=second.agent_name,
    )

    assert isinstance(context, FailurePolicyContext)
    assert context == expected
    assert context.phase is phase
    assert context.error_code == "dependency_unavailable"
    assert context.agent_name is second.agent_name
    assert context.attempt_number == 3
    assert selection.calls == 1
    assert selection.received is facts
    assert selection.received is facts_before
    assert attempt.calls == 1
    assert attempt.received is workflow_id
    assert call_order == ["select", "get_attempt_number"]
    assert facts == (first, second, third)
    assert (second.agent_name, second.error_code) == second_before


async def test_resolve_delegates_to_published_builder_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = _fact(AgentName.NEWS_INTELLIGENCE, "resource_not_found")
    facts = (selected,)
    workflow_id = "wf-builder-delegation"
    phase = WorkflowPhase.INGESTION
    selection = _RecordingSelectionFake(result=selected)
    attempt = _RecordingAttemptNumberFake(result=1)
    service = _service(selection, attempt)
    builder_calls: list[dict[str, object]] = []
    original = build_parallel_ingestion_failure_policy_context

    def _tracking_builder(
        *,
        phase: WorkflowPhase,
        error_code: str,
        attempt_number: int,
        agent_name: AgentName | None = None,
    ) -> FailurePolicyContext:
        builder_calls.append(
            {
                "phase": phase,
                "error_code": error_code,
                "attempt_number": attempt_number,
                "agent_name": agent_name,
            }
        )
        return original(
            phase=phase,
            error_code=error_code,
            attempt_number=attempt_number,
            agent_name=agent_name,
        )

    monkeypatch.setattr(
        "energy_trading.application.orchestration.parallel_ingestion_failure_context_resolution"
        ".build_parallel_ingestion_failure_policy_context",
        _tracking_builder,
    )

    context = await service.resolve(workflow_id=workflow_id, phase=phase, facts=facts)

    assert len(builder_calls) == 1
    assert builder_calls[0] == {
        "phase": phase,
        "error_code": selected.error_code,
        "attempt_number": 1,
        "agent_name": selected.agent_name,
    }
    assert context.agent_name is selected.agent_name
    assert selection.calls == 1
    assert attempt.calls == 1


async def test_selection_failure_propagates_without_attempt_lookup() -> None:
    facts = (_fact(AgentName.GENERATION_AVAILABILITY, "invalid_request"),)
    error = InvalidRequestError("selector unavailable")
    selection = _RecordingSelectionFake(error=error)
    attempt = _RecordingAttemptNumberFake(result=1)
    service = _service(selection, attempt)

    with pytest.raises(InvalidRequestError) as caught:
        await service.resolve(
            workflow_id="wf-selection-failure",
            phase=WorkflowPhase.INGESTION,
            facts=facts,
        )

    assert caught.value is error
    assert selection.calls == 1
    assert selection.received is facts
    assert attempt.calls == 0
    assert attempt.received is None


async def test_attempt_number_failure_propagates_without_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = _fact(AgentName.HYDRO_RESOURCES, "dependency_unavailable")
    facts = (selected,)
    error = DependencyUnavailableError("attempt source unavailable")
    selection = _RecordingSelectionFake(result=selected)
    attempt = _RecordingAttemptNumberFake(error=error)
    service = _service(selection, attempt)
    builder_calls: list[object] = []

    def _tracking_builder(**kwargs: object) -> FailurePolicyContext:
        builder_calls.append(kwargs)
        raise AssertionError("builder must not run after attempt lookup failure")

    monkeypatch.setattr(
        "energy_trading.application.orchestration.parallel_ingestion_failure_context_resolution"
        ".build_parallel_ingestion_failure_policy_context",
        _tracking_builder,
    )

    with pytest.raises(DependencyUnavailableError) as caught:
        await service.resolve(
            workflow_id="wf-attempt-failure",
            phase=WorkflowPhase.INGESTION,
            facts=facts,
        )

    assert caught.value is error
    assert selection.calls == 1
    assert selection.received is facts
    assert attempt.calls == 1
    assert attempt.received == "wf-attempt-failure"
    assert builder_calls == []


async def test_builder_validation_propagates_unchanged() -> None:
    selected = _fact(AgentName.MARKET_MONITORING, "dependency_unavailable")
    facts = (selected,)
    selection = _RecordingSelectionFake(result=selected)
    attempt = _RecordingAttemptNumberFake(result=0)
    service = _service(selection, attempt)

    with pytest.raises(ValueError, match="attempt_number must be greater than 0") as via_resolve:
        await service.resolve(
            workflow_id="wf-invalid-attempt",
            phase=WorkflowPhase.INGESTION,
            facts=facts,
        )
    with pytest.raises(ValueError, match="attempt_number must be greater than 0") as via_builder:
        build_parallel_ingestion_failure_policy_context(
            phase=WorkflowPhase.INGESTION,
            error_code=selected.error_code,
            attempt_number=0,
            agent_name=selected.agent_name,
        )

    assert str(via_resolve.value) == str(via_builder.value)
    assert selection.calls == 1
    assert attempt.calls == 1


async def test_resolve_does_not_invoke_policy_decision_or_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = _fact(AgentName.NEWS_INTELLIGENCE, "conflict")
    facts = (selected,)
    selection = _RecordingSelectionFake(result=selected)
    attempt = _RecordingAttemptNumberFake(result=2)
    service = _service(selection, attempt)
    policy_calls: list[str] = []

    def _track(name: str):
        def _inner(*args: object, **kwargs: object) -> object:
            policy_calls.append(name)
            raise AssertionError(f"{name} must not be invoked")

        return _inner

    monkeypatch.setattr(
        "energy_trading.application.orchestration.failure_policy.FailurePolicyPort.decide",
        _track("FailurePolicyPort.decide"),
        raising=False,
    )
    monkeypatch.setattr(
        "energy_trading.application.orchestration.parallel_ingestion_failure_decision"
        ".ParallelIngestionFailureDecisionService.decide",
        _track("ParallelIngestionFailureDecisionService.decide"),
    )
    monkeypatch.setattr(
        "energy_trading.application.orchestration.parallel_ingestion_failure_action"
        ".execute_parallel_ingestion_failure_action",
        _track("execute_parallel_ingestion_failure_action"),
    )
    monkeypatch.setattr(
        "energy_trading.application.orchestration.parallel_ingestion_failure_handling"
        ".ParallelIngestionFailureHandlingService.handle",
        _track("ParallelIngestionFailureHandlingService.handle"),
    )

    context = await service.resolve(
        workflow_id="wf-no-policy",
        phase=WorkflowPhase.INGESTION,
        facts=facts,
    )

    assert context.attempt_number == 2
    assert context.error_code == "conflict"
    assert policy_calls == []
    assert selection.calls == 1
    assert attempt.calls == 1
