"""Phase 2 failure-context preparation composes extraction through resolution."""

from __future__ import annotations

import inspect
from typing import cast

import pytest

from energy_trading.application.agents import AgentName
from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.application.orchestration import (
    FailurePolicyContext,
    InitialParallelIngestionAttemptNumberSource,
    ParallelIngestionAgentFailure,
    ParallelIngestionFailureContextPreparationService,
    ParallelIngestionFailureContextResolutionService,
    ParallelIngestionFailureFact,
    StrictSingleParallelIngestionFailureSelector,
    WorkflowPhase,
    classify_parallel_ingestion_agent_failures,
    extract_parallel_ingestion_agent_failures,
)
from energy_trading.application.orchestration import (
    parallel_ingestion_failure_context_preparation as preparation_module,
)

_UNATTRIBUTED_FAILURE_MESSAGE = "Parallel-ingestion failure group contains an unattributed failure."
_EXACTLY_ONE_FACT_MESSAGE = (
    "Parallel-ingestion failure selection requires exactly one failure fact."
)
_UNEXPECTED_FAILURE_CODE = "parallel_ingestion_unexpected_failure"
_SENTINEL_TEXT = "secret provider payload not for clients"


class _RecordingResolutionService:
    """Test-only recording double. Not a production Protocol or abstraction."""

    def __init__(self, error: BaseException | None = None) -> None:
        self._error = error
        self.calls = 0
        self.received_workflow_id: str | None = None
        self.received_phase: WorkflowPhase | None = None
        self.received_facts: tuple[ParallelIngestionFailureFact, ...] | None = None

    async def resolve(
        self,
        *,
        workflow_id: str,
        phase: WorkflowPhase,
        facts: tuple[ParallelIngestionFailureFact, ...],
    ) -> FailurePolicyContext:
        self.calls += 1
        self.received_workflow_id = workflow_id
        self.received_phase = phase
        self.received_facts = facts
        if self._error is not None:
            raise self._error
        msg = "recording resolution double must not succeed in this test"
        raise AssertionError(msg)


class _DelegatingResolutionService:
    """Test-only recorder that forwards to the published resolution service."""

    def __init__(self, inner: ParallelIngestionFailureContextResolutionService) -> None:
        self._inner = inner
        self.calls = 0
        self.received_workflow_id: str | None = None
        self.received_phase: WorkflowPhase | None = None
        self.received_facts: tuple[ParallelIngestionFailureFact, ...] | None = None

    async def resolve(
        self,
        *,
        workflow_id: str,
        phase: WorkflowPhase,
        facts: tuple[ParallelIngestionFailureFact, ...],
    ) -> FailurePolicyContext:
        self.calls += 1
        self.received_workflow_id = workflow_id
        self.received_phase = phase
        self.received_facts = facts
        return await self._inner.resolve(
            workflow_id=workflow_id,
            phase=phase,
            facts=facts,
        )


def _chained_failure(
    agent_name: AgentName,
    cause: BaseException,
) -> ParallelIngestionAgentFailure:
    try:
        raise ParallelIngestionAgentFailure(agent_name) from cause
    except ParallelIngestionAgentFailure as exc:
        return exc


def _real_resolution_service() -> ParallelIngestionFailureContextResolutionService:
    return ParallelIngestionFailureContextResolutionService(
        StrictSingleParallelIngestionFailureSelector(),
        InitialParallelIngestionAttemptNumberSource(),
    )


def _real_preparation_service() -> ParallelIngestionFailureContextPreparationService:
    return ParallelIngestionFailureContextPreparationService(_real_resolution_service())


def test_constructor_accepts_exactly_the_published_resolution_service() -> None:
    signature = inspect.signature(ParallelIngestionFailureContextPreparationService.__init__)
    assert tuple(signature.parameters) == ("self", "context_resolution_service")
    assert (
        signature.parameters["context_resolution_service"].annotation
        is ParallelIngestionFailureContextResolutionService
    )


def test_prepare_signature_is_keyword_only_workflow_phase_and_failure_group() -> None:
    signature = inspect.signature(ParallelIngestionFailureContextPreparationService.prepare)
    assert tuple(signature.parameters) == ("self", "workflow_id", "phase", "failure_group")
    assert signature.parameters["workflow_id"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["phase"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["failure_group"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["workflow_id"].annotation is str
    assert signature.parameters["phase"].annotation is WorkflowPhase
    assert signature.parameters["failure_group"].annotation is BaseExceptionGroup
    assert signature.return_annotation is FailurePolicyContext
    assert inspect.iscoroutinefunction(ParallelIngestionFailureContextPreparationService.prepare)


async def test_single_attributed_application_error_prepares_context() -> None:
    cause = InvalidRequestError("weather request is invalid")
    leaf = _chained_failure(AgentName.WEATHER_AND_RENEWABLE_FORECAST, cause)
    group = ExceptionGroup("group", [leaf])
    workflow_id = "wf-single-application"
    phase = WorkflowPhase.INGESTION

    context = await _real_preparation_service().prepare(
        workflow_id=workflow_id,
        phase=phase,
        failure_group=group,
    )

    assert isinstance(context, FailurePolicyContext)
    assert context.phase is phase
    assert context.agent_name is AgentName.WEATHER_AND_RENEWABLE_FORECAST
    assert context.error_code == cause.code
    assert context.error_code == "invalid_request"
    assert context.attempt_number == 1


async def test_unexpected_non_application_cause_uses_sanitized_code() -> None:
    leaf = _chained_failure(AgentName.NEWS_INTELLIGENCE, RuntimeError(_SENTINEL_TEXT))
    group = ExceptionGroup("group", [leaf])

    context = await _real_preparation_service().prepare(
        workflow_id="wf-unexpected",
        phase=WorkflowPhase.INGESTION,
        failure_group=group,
    )

    assert context.agent_name is AgentName.NEWS_INTELLIGENCE
    assert context.error_code == _UNEXPECTED_FAILURE_CODE
    assert context.attempt_number == 1
    assert _SENTINEL_TEXT not in context.error_code
    assert _SENTINEL_TEXT not in repr(context)
    assert "RuntimeError" not in context.error_code


async def test_nested_exception_group_reuses_existing_extraction() -> None:
    leaf = _chained_failure(
        AgentName.HYDRO_RESOURCES,
        DependencyUnavailableError("hydro source unavailable"),
    )
    group = ExceptionGroup(
        "outer",
        [
            ExceptionGroup("inner", [leaf]),
        ],
    )
    extracted = extract_parallel_ingestion_agent_failures(group)
    expected_facts = classify_parallel_ingestion_agent_failures(extracted)

    context = await _real_preparation_service().prepare(
        workflow_id="wf-nested",
        phase=WorkflowPhase.INGESTION,
        failure_group=group,
    )

    assert extracted == (leaf,)
    assert extracted[0] is leaf
    assert len(expected_facts) == 1
    assert context.agent_name is AgentName.HYDRO_RESOURCES
    assert context.error_code == "dependency_unavailable"
    assert context.attempt_number == 1


async def test_multiple_attributed_failures_fail_closed_without_winner() -> None:
    weather = _chained_failure(
        AgentName.WEATHER_AND_RENEWABLE_FORECAST,
        InvalidRequestError("weather request is invalid"),
    )
    hydro = _chained_failure(
        AgentName.HYDRO_RESOURCES,
        DependencyUnavailableError("hydro source unavailable"),
    )
    group = ExceptionGroup("group", [weather, hydro])

    with pytest.raises(InvalidRequestError) as caught:
        await _real_preparation_service().prepare(
            workflow_id="wf-multi",
            phase=WorkflowPhase.INGESTION,
            failure_group=group,
        )

    assert caught.value.code == "invalid_request"
    assert caught.value.message == _EXACTLY_ONE_FACT_MESSAGE
    assert "first" not in caught.value.message.lower()
    assert "last" not in caught.value.message.lower()
    assert "winner" not in caught.value.message.lower()
    assert "priority" not in caught.value.message.lower()


async def test_unattributed_leaf_propagates_without_context_resolution() -> None:
    attributed = _chained_failure(
        AgentName.MARKET_MONITORING,
        InvalidRequestError("market request is invalid"),
    )
    group = ExceptionGroup(
        "group",
        [
            attributed,
            RuntimeError(_SENTINEL_TEXT),
        ],
    )
    recorder = _RecordingResolutionService()
    service = ParallelIngestionFailureContextPreparationService(
        cast(ParallelIngestionFailureContextResolutionService, recorder)
    )

    with pytest.raises(InvalidRequestError) as caught:
        await service.prepare(
            workflow_id="wf-unattributed",
            phase=WorkflowPhase.INGESTION,
            failure_group=group,
        )

    assert caught.value.message == _UNATTRIBUTED_FAILURE_MESSAGE
    assert str(caught.value) == _UNATTRIBUTED_FAILURE_MESSAGE
    assert _SENTINEL_TEXT not in str(caught.value)
    assert "RuntimeError" not in str(caught.value)
    assert recorder.calls == 0
    assert recorder.received_facts is None


async def test_input_workflow_id_and_phase_are_preserved() -> None:
    leaf = _chained_failure(
        AgentName.GENERATION_AVAILABILITY,
        InvalidRequestError("generation request is invalid"),
    )
    group = ExceptionGroup("group", [leaf])
    exceptions_before = group.exceptions
    workflow_id = "wf-preserve-identity"
    phase = WorkflowPhase.INGESTION
    recorder = _DelegatingResolutionService(_real_resolution_service())
    service = ParallelIngestionFailureContextPreparationService(
        cast(ParallelIngestionFailureContextResolutionService, recorder)
    )

    context = await service.prepare(
        workflow_id=workflow_id,
        phase=phase,
        failure_group=group,
    )

    assert recorder.calls == 1
    assert recorder.received_workflow_id is workflow_id
    assert recorder.received_phase is phase
    assert context.phase is phase
    assert group.exceptions is exceptions_before
    assert group.exceptions == (leaf,)
    assert group.exceptions[0] is leaf


async def test_prepare_does_not_invoke_policy_decision_or_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    leaf = _chained_failure(
        AgentName.NEWS_INTELLIGENCE,
        InvalidRequestError("news request is invalid"),
    )
    group = ExceptionGroup("group", [leaf])
    service = _real_preparation_service()
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
    monkeypatch.setattr(
        "energy_trading.application.orchestration.parallel_ingestion_failure_transition"
        ".fail_parallel_ingestion",
        _track("fail_parallel_ingestion"),
    )

    context = await service.prepare(
        workflow_id="wf-no-policy",
        phase=WorkflowPhase.INGESTION,
        failure_group=group,
    )

    assert isinstance(context, FailurePolicyContext)
    assert context.attempt_number == 1
    assert policy_calls == []


async def test_prepare_delegates_each_stage_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    leaf = _chained_failure(
        AgentName.MARKET_MONITORING,
        InvalidRequestError("market request is invalid"),
    )
    group = ExceptionGroup("group", [leaf])
    extract_calls: list[BaseExceptionGroup] = []
    classify_calls: list[tuple[ParallelIngestionAgentFailure, ...]] = []
    original_extract = preparation_module.extract_parallel_ingestion_agent_failures
    original_classify = preparation_module.classify_parallel_ingestion_agent_failures

    def _tracking_extract(
        failure: BaseExceptionGroup[BaseException],
    ) -> tuple[ParallelIngestionAgentFailure, ...]:
        extract_calls.append(failure)
        return original_extract(failure)

    def _tracking_classify(
        failures: tuple[ParallelIngestionAgentFailure, ...],
    ) -> tuple[ParallelIngestionFailureFact, ...]:
        classify_calls.append(failures)
        return original_classify(failures)

    monkeypatch.setattr(
        preparation_module,
        "extract_parallel_ingestion_agent_failures",
        _tracking_extract,
    )
    monkeypatch.setattr(
        preparation_module,
        "classify_parallel_ingestion_agent_failures",
        _tracking_classify,
    )
    recorder = _DelegatingResolutionService(_real_resolution_service())
    service = ParallelIngestionFailureContextPreparationService(
        cast(ParallelIngestionFailureContextResolutionService, recorder)
    )

    context = await service.prepare(
        workflow_id="wf-delegate-once",
        phase=WorkflowPhase.INGESTION,
        failure_group=group,
    )

    assert extract_calls == [group]
    assert len(classify_calls) == 1
    assert classify_calls[0] == (leaf,)
    assert classify_calls[0][0] is leaf
    assert recorder.calls == 1
    assert context.error_code == "invalid_request"


async def test_classification_failure_propagates_without_context_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    leaf = _chained_failure(
        AgentName.HYDRO_RESOURCES,
        InvalidRequestError("hydro request is invalid"),
    )
    group = ExceptionGroup("group", [leaf])
    error = InvalidRequestError("classification unavailable")
    recorder = _RecordingResolutionService()
    service = ParallelIngestionFailureContextPreparationService(
        cast(ParallelIngestionFailureContextResolutionService, recorder)
    )

    def _failing_classify(
        failures: tuple[ParallelIngestionAgentFailure, ...],
    ) -> tuple[ParallelIngestionFailureFact, ...]:
        del failures
        raise error

    monkeypatch.setattr(
        preparation_module,
        "classify_parallel_ingestion_agent_failures",
        _failing_classify,
    )

    with pytest.raises(InvalidRequestError) as caught:
        await service.prepare(
            workflow_id="wf-classify-failure",
            phase=WorkflowPhase.INGESTION,
            failure_group=group,
        )

    assert caught.value is error
    assert recorder.calls == 0
