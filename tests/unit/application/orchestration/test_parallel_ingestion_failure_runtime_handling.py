"""Phase 2 runtime failure handling composes preparation then existing handling."""

from __future__ import annotations

import inspect
from dataclasses import fields
from datetime import date
from typing import cast

import pytest

from energy_trading.application.agents import AgentName
from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.application.orchestration import (
    FailurePolicyContext,
    InitialParallelIngestionAttemptNumberSource,
    InitialParallelIngestionFailurePolicy,
    ParallelIngestionAgentFailure,
    ParallelIngestionFailureContextPreparationService,
    ParallelIngestionFailureContextResolutionService,
    ParallelIngestionFailureDecisionService,
    ParallelIngestionFailureHandlingService,
    ParallelIngestionFailureRuntimeHandlingService,
    StrictSingleParallelIngestionFailureSelector,
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
    fail_parallel_ingestion,
)
from energy_trading.domain.models.ingestion import AdapterDiagnostic, DiagnosticSeverity
from tests.unit.domain._factories import diagnostic

_WORKFLOW_STATE_FIELDS = (
    "workflow_id",
    "portfolio_id",
    "delivery_date",
    "correlation_id",
    "phase",
    "status",
    "diagnostics",
)

_UNATTRIBUTED_FAILURE_MESSAGE = "Parallel-ingestion failure group contains an unattributed failure."
_EXACTLY_ONE_FACT_MESSAGE = (
    "Parallel-ingestion failure selection requires exactly one failure fact."
)
_SENTINEL_TEXT = "secret provider payload not for clients"


class _RecordingPreparationService:
    """Test-only recording double. Not a production Protocol or abstraction."""

    def __init__(
        self,
        context: FailurePolicyContext | None = None,
        error: BaseException | None = None,
    ) -> None:
        self._context = context
        self._error = error
        self.calls = 0
        self.received_workflow_id: str | None = None
        self.received_phase: WorkflowPhase | None = None
        self.received_failure_group: BaseExceptionGroup | None = None

    async def prepare(
        self,
        *,
        workflow_id: str,
        phase: WorkflowPhase,
        failure_group: BaseExceptionGroup,
    ) -> FailurePolicyContext:
        self.calls += 1
        self.received_workflow_id = workflow_id
        self.received_phase = phase
        self.received_failure_group = failure_group
        if self._error is not None:
            raise self._error
        if self._context is None:
            msg = "recording preparation double requires a context or an error"
            raise AssertionError(msg)
        return self._context


class _RecordingHandlingService:
    """Test-only recording double. Not a production Protocol or abstraction."""

    def __init__(
        self,
        result: WorkflowState | None = None,
        error: BaseException | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls = 0
        self.received_state: WorkflowState | None = None
        self.received_context: FailurePolicyContext | None = None

    async def handle(
        self,
        *,
        state: WorkflowState,
        context: FailurePolicyContext,
    ) -> WorkflowState:
        self.calls += 1
        self.received_state = state
        self.received_context = context
        if self._error is not None:
            raise self._error
        if self._result is None:
            msg = "recording handling double requires a result or an error"
            raise AssertionError(msg)
        return self._result


class _OrderedPreparationService(_RecordingPreparationService):
    def __init__(self, context: FailurePolicyContext, events: list[str]) -> None:
        super().__init__(context=context)
        self._events = events

    async def prepare(
        self,
        *,
        workflow_id: str,
        phase: WorkflowPhase,
        failure_group: BaseExceptionGroup,
    ) -> FailurePolicyContext:
        self._events.append("prepare")
        return await super().prepare(
            workflow_id=workflow_id,
            phase=phase,
            failure_group=failure_group,
        )


class _OrderedHandlingService(_RecordingHandlingService):
    def __init__(self, result: WorkflowState, events: list[str]) -> None:
        super().__init__(result=result)
        self._events = events

    async def handle(
        self,
        *,
        state: WorkflowState,
        context: FailurePolicyContext,
    ) -> WorkflowState:
        self._events.append("handle")
        return await super().handle(state=state, context=context)


def _state(**overrides: object) -> WorkflowState:
    values: dict[str, object] = {
        "workflow_id": "workflow-1",
        "portfolio_id": "portfolio-1",
        "delivery_date": date(2026, 9, 7),
        "correlation_id": "corr-1",
        "phase": WorkflowPhase.INGESTION,
        "status": WorkflowStatus.RUNNING,
        "diagnostics": (),
    }
    values.update(overrides)
    return WorkflowState(**values)  # type: ignore[arg-type]


def _snapshot(state: WorkflowState) -> tuple[object, ...]:
    return (
        state.workflow_id,
        state.portfolio_id,
        state.delivery_date,
        state.correlation_id,
        state.phase,
        state.status,
        state.diagnostics,
    )


def _chained_failure(
    agent_name: AgentName,
    cause: BaseException,
) -> ParallelIngestionAgentFailure:
    try:
        raise ParallelIngestionAgentFailure(agent_name) from cause
    except ParallelIngestionAgentFailure as exc:
        return exc


def _real_runtime_service() -> ParallelIngestionFailureRuntimeHandlingService:
    preparation = ParallelIngestionFailureContextPreparationService(
        ParallelIngestionFailureContextResolutionService(
            StrictSingleParallelIngestionFailureSelector(),
            InitialParallelIngestionAttemptNumberSource(),
        )
    )
    handling = ParallelIngestionFailureHandlingService(
        ParallelIngestionFailureDecisionService(InitialParallelIngestionFailurePolicy())
    )
    return ParallelIngestionFailureRuntimeHandlingService(preparation, handling)


def test_constructor_accepts_exactly_the_published_preparation_and_handling_services() -> None:
    signature = inspect.signature(ParallelIngestionFailureRuntimeHandlingService.__init__)
    assert tuple(signature.parameters) == (
        "self",
        "context_preparation_service",
        "failure_handling_service",
    )
    assert (
        signature.parameters["context_preparation_service"].annotation
        is ParallelIngestionFailureContextPreparationService
    )
    assert (
        signature.parameters["failure_handling_service"].annotation
        is ParallelIngestionFailureHandlingService
    )


def test_handle_signature_is_keyword_only_state_and_failure_group() -> None:
    signature = inspect.signature(ParallelIngestionFailureRuntimeHandlingService.handle)
    assert tuple(signature.parameters) == ("self", "state", "failure_group")
    assert signature.parameters["state"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["failure_group"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["state"].annotation is WorkflowState
    assert signature.parameters["failure_group"].annotation is BaseExceptionGroup
    assert signature.return_annotation is WorkflowState
    assert inspect.iscoroutinefunction(ParallelIngestionFailureRuntimeHandlingService.handle)


def test_runtime_service_does_not_inherit_preparation_or_handling() -> None:
    runtime_mro = ParallelIngestionFailureRuntimeHandlingService.__mro__
    assert ParallelIngestionFailureContextPreparationService not in runtime_mro
    assert ParallelIngestionFailureHandlingService not in runtime_mro


async def test_single_attributed_failure_returns_terminal_ingestion_failed() -> None:
    first = diagnostic()
    second = AdapterDiagnostic(
        code="SCHEMA_AMBIGUOUS",
        message="header mapping was ambiguous",
        severity=DiagnosticSeverity.WARNING,
        field_name="timestamp",
    )
    state = _state(diagnostics=(first, second))
    leaf = _chained_failure(
        AgentName.MARKET_MONITORING,
        InvalidRequestError("market request is invalid"),
    )
    group = ExceptionGroup("group", [leaf])
    before = _snapshot(state)

    failed = await _real_runtime_service().handle(state=state, failure_group=group)
    expected = fail_parallel_ingestion(state)

    assert failed is not state
    assert _snapshot(state) == before
    assert failed == expected
    assert failed.phase is WorkflowPhase.INGESTION
    assert failed.status is WorkflowStatus.FAILED
    assert failed.workflow_id == "workflow-1"
    assert failed.portfolio_id == "portfolio-1"
    assert failed.delivery_date == date(2026, 9, 7)
    assert failed.correlation_id == "corr-1"
    assert failed.diagnostics == (first, second)
    assert failed.diagnostics is state.diagnostics
    assert failed.diagnostics[0] is first
    assert failed.diagnostics[1] is second
    assert tuple(item.name for item in fields(failed)) == _WORKFLOW_STATE_FIELDS


async def test_preparation_then_handling_occur_in_order() -> None:
    state = _state()
    context = FailurePolicyContext(
        phase=WorkflowPhase.INGESTION,
        error_code="invalid_request",
        attempt_number=1,
        agent_name=AgentName.HYDRO_RESOURCES,
    )
    expected = fail_parallel_ingestion(state)
    events: list[str] = []
    preparation = _OrderedPreparationService(context, events)
    handling = _OrderedHandlingService(expected, events)
    service = ParallelIngestionFailureRuntimeHandlingService(
        cast(ParallelIngestionFailureContextPreparationService, preparation),
        cast(ParallelIngestionFailureHandlingService, handling),
    )
    leaf = _chained_failure(
        AgentName.HYDRO_RESOURCES,
        InvalidRequestError("hydro request is invalid"),
    )
    group = ExceptionGroup("group", [leaf])

    failed = await service.handle(state=state, failure_group=group)

    assert events == ["prepare", "handle"]
    assert preparation.calls == 1
    assert handling.calls == 1
    assert preparation.received_workflow_id is state.workflow_id
    assert preparation.received_phase is state.phase
    assert preparation.received_failure_group is group
    assert handling.received_state is state
    assert handling.received_context is context
    assert failed is expected


async def test_preparation_failure_propagates_without_handling() -> None:
    state = _state()
    error = InvalidRequestError("preparation unavailable")
    preparation = _RecordingPreparationService(error=error)
    handling = _RecordingHandlingService()
    service = ParallelIngestionFailureRuntimeHandlingService(
        cast(ParallelIngestionFailureContextPreparationService, preparation),
        cast(ParallelIngestionFailureHandlingService, handling),
    )
    leaf = _chained_failure(
        AgentName.WEATHER_AND_RENEWABLE_FORECAST,
        InvalidRequestError("weather request is invalid"),
    )
    group = ExceptionGroup("group", [leaf])
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as caught:
        await service.handle(state=state, failure_group=group)

    assert caught.value is error
    assert preparation.calls == 1
    assert handling.calls == 0
    assert handling.received_state is None
    assert handling.received_context is None
    assert _snapshot(state) == before
    assert state.status is WorkflowStatus.RUNNING


async def test_multiple_attributed_failures_fail_closed_without_handling() -> None:
    state = _state()
    weather = _chained_failure(
        AgentName.WEATHER_AND_RENEWABLE_FORECAST,
        InvalidRequestError("weather request is invalid"),
    )
    hydro = _chained_failure(
        AgentName.HYDRO_RESOURCES,
        DependencyUnavailableError("hydro source unavailable"),
    )
    group = ExceptionGroup("group", [weather, hydro])
    handling = _RecordingHandlingService()
    service = ParallelIngestionFailureRuntimeHandlingService(
        ParallelIngestionFailureContextPreparationService(
            ParallelIngestionFailureContextResolutionService(
                StrictSingleParallelIngestionFailureSelector(),
                InitialParallelIngestionAttemptNumberSource(),
            )
        ),
        cast(ParallelIngestionFailureHandlingService, handling),
    )
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as caught:
        await service.handle(state=state, failure_group=group)

    assert caught.value.code == "invalid_request"
    assert caught.value.message == _EXACTLY_ONE_FACT_MESSAGE
    assert "first" not in caught.value.message.lower()
    assert "last" not in caught.value.message.lower()
    assert "winner" not in caught.value.message.lower()
    assert "priority" not in caught.value.message.lower()
    assert handling.calls == 0
    assert handling.received_state is None
    assert _snapshot(state) == before
    assert state.status is WorkflowStatus.RUNNING


async def test_unattributed_failure_propagates_without_handling() -> None:
    state = _state()
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
    handling = _RecordingHandlingService()
    service = ParallelIngestionFailureRuntimeHandlingService(
        ParallelIngestionFailureContextPreparationService(
            ParallelIngestionFailureContextResolutionService(
                StrictSingleParallelIngestionFailureSelector(),
                InitialParallelIngestionAttemptNumberSource(),
            )
        ),
        cast(ParallelIngestionFailureHandlingService, handling),
    )
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as caught:
        await service.handle(state=state, failure_group=group)

    assert caught.value.message == _UNATTRIBUTED_FAILURE_MESSAGE
    assert str(caught.value) == _UNATTRIBUTED_FAILURE_MESSAGE
    assert _SENTINEL_TEXT not in str(caught.value)
    assert "RuntimeError" not in str(caught.value)
    assert handling.calls == 0
    assert handling.received_context is None
    assert _snapshot(state) == before
    assert state.status is WorkflowStatus.RUNNING


async def test_handling_failure_propagates_unchanged_after_preparation() -> None:
    state = _state()
    context = FailurePolicyContext(
        phase=WorkflowPhase.INGESTION,
        error_code="invalid_request",
        attempt_number=1,
        agent_name=AgentName.NEWS_INTELLIGENCE,
    )
    error = InvalidRequestError("Parallel-ingestion retry action is not implemented.")
    preparation = _RecordingPreparationService(context=context)
    handling = _RecordingHandlingService(error=error)
    service = ParallelIngestionFailureRuntimeHandlingService(
        cast(ParallelIngestionFailureContextPreparationService, preparation),
        cast(ParallelIngestionFailureHandlingService, handling),
    )
    leaf = _chained_failure(
        AgentName.NEWS_INTELLIGENCE,
        InvalidRequestError("news request is invalid"),
    )
    group = ExceptionGroup("group", [leaf])
    before = _snapshot(state)

    with pytest.raises(InvalidRequestError) as caught:
        await service.handle(state=state, failure_group=group)

    assert caught.value is error
    assert preparation.calls == 1
    assert handling.calls == 1
    assert handling.received_context is context
    assert handling.received_state is state
    assert _snapshot(state) == before
    assert state.status is WorkflowStatus.RUNNING


async def test_terminal_fail_preserves_identity_date_and_diagnostics() -> None:
    first = diagnostic()
    state = _state(
        workflow_id="wf-preserve",
        portfolio_id="portfolio-preserve",
        delivery_date=date(2026, 9, 8),
        correlation_id="corr-preserve",
        diagnostics=(first,),
    )
    leaf = _chained_failure(
        AgentName.GENERATION_AVAILABILITY,
        DependencyUnavailableError("generation source unavailable"),
    )
    group = ExceptionGroup("group", [leaf])
    before = _snapshot(state)

    failed = await _real_runtime_service().handle(state=state, failure_group=group)

    assert failed is not state
    assert _snapshot(state) == before
    assert failed.workflow_id == "wf-preserve"
    assert failed.portfolio_id == "portfolio-preserve"
    assert failed.delivery_date == date(2026, 9, 8)
    assert failed.correlation_id == "corr-preserve"
    assert failed.phase is WorkflowPhase.INGESTION
    assert failed.status is WorkflowStatus.FAILED
    assert failed.diagnostics is state.diagnostics
    assert failed.diagnostics == (first,)
    assert failed.diagnostics[0] is first


async def test_runtime_handling_does_not_require_a_graph_object() -> None:
    state = _state()
    leaf = _chained_failure(
        AgentName.NEWS_INTELLIGENCE,
        InvalidRequestError("news request is invalid"),
    )
    group = ExceptionGroup("group", [leaf])

    failed = await _real_runtime_service().handle(state=state, failure_group=group)

    assert failed.phase is WorkflowPhase.INGESTION
    assert failed.status is WorkflowStatus.FAILED
    assert failed == fail_parallel_ingestion(state)
