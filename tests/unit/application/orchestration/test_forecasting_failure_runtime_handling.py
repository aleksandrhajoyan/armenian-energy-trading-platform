"""Phase 3 runtime failure handling composes preparation then existing handling."""

from __future__ import annotations

import inspect
from dataclasses import fields
from datetime import date
from typing import cast, get_type_hints

import pytest

from energy_trading.application.agents.base import AgentName
from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.application.orchestration.failure_policy import FailurePolicyContext
from energy_trading.application.orchestration.forecasting_agent_failure import (
    ForecastingAgentFailure,
)
from energy_trading.application.orchestration.forecasting_failure_context_preparation import (
    ForecastingFailureContextPreparationService,
)
from energy_trading.application.orchestration.forecasting_failure_context_resolution import (
    ForecastingFailureContextResolutionService,
)
from energy_trading.application.orchestration.forecasting_failure_decision import (
    ForecastingFailureDecisionService,
)
from energy_trading.application.orchestration.forecasting_failure_handling import (
    ForecastingFailureHandlingService,
)
from energy_trading.application.orchestration.forecasting_failure_runtime_handling import (
    ForecastingFailureRuntimeHandlingService,
)
from energy_trading.application.orchestration.forecasting_failure_transition import (
    fail_after_forecasting,
)
from energy_trading.application.orchestration.forecasting_initial_attempt_number_source import (
    InitialForecastingAttemptNumberSource,
)
from energy_trading.application.orchestration.forecasting_initial_failure_policy import (
    InitialForecastingFailurePolicy,
)
from energy_trading.application.orchestration.forecasting_strict_single_failure_selector import (
    StrictSingleForecastingFailureSelector,
)
from energy_trading.application.orchestration.state import (
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
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

_EXACTLY_ONE_FACT_MESSAGE = "Forecasting failure selection requires exactly one failure fact."


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
        self.received_error: BaseException | None = None

    async def prepare(
        self,
        *,
        workflow_id: str,
        phase: WorkflowPhase,
        error: BaseException,
    ) -> FailurePolicyContext:
        self.calls += 1
        self.received_workflow_id = workflow_id
        self.received_phase = phase
        self.received_error = error
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
        error: BaseException,
    ) -> FailurePolicyContext:
        self._events.append("prepare")
        return await super().prepare(
            workflow_id=workflow_id,
            phase=phase,
            error=error,
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
        "phase": WorkflowPhase.FORECASTING,
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
) -> ForecastingAgentFailure:
    try:
        raise ForecastingAgentFailure(agent_name) from cause
    except ForecastingAgentFailure as exc:
        return exc


def _real_runtime_service() -> ForecastingFailureRuntimeHandlingService:
    preparation = ForecastingFailureContextPreparationService(
        ForecastingFailureContextResolutionService(
            StrictSingleForecastingFailureSelector(),
            InitialForecastingAttemptNumberSource(),
        )
    )
    handling = ForecastingFailureHandlingService(
        ForecastingFailureDecisionService(InitialForecastingFailurePolicy())
    )
    return ForecastingFailureRuntimeHandlingService(preparation, handling)


def test_constructor_accepts_exactly_the_published_preparation_and_handling_services() -> None:
    signature = inspect.signature(ForecastingFailureRuntimeHandlingService.__init__)
    assert tuple(signature.parameters) == (
        "self",
        "context_preparation_service",
        "failure_handling_service",
    )
    assert (
        signature.parameters["context_preparation_service"].annotation
        is ForecastingFailureContextPreparationService
    )
    assert (
        signature.parameters["failure_handling_service"].annotation
        is ForecastingFailureHandlingService
    )


def test_handle_signature_is_keyword_only_state_and_failure_group() -> None:
    signature = inspect.signature(ForecastingFailureRuntimeHandlingService.handle)
    assert tuple(signature.parameters) == ("self", "state", "failure_group")
    assert signature.parameters["state"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["failure_group"].kind is inspect.Parameter.KEYWORD_ONLY
    hints = get_type_hints(ForecastingFailureRuntimeHandlingService.handle)
    assert hints["state"] is WorkflowState
    assert hints["failure_group"] is BaseExceptionGroup
    assert hints["return"] is WorkflowState
    assert inspect.iscoroutinefunction(ForecastingFailureRuntimeHandlingService.handle)
    public = [
        name for name in dir(ForecastingFailureRuntimeHandlingService) if not name.startswith("_")
    ]
    assert public == ["handle"]


def test_runtime_service_does_not_inherit_preparation_or_handling() -> None:
    runtime_mro = ForecastingFailureRuntimeHandlingService.__mro__
    assert ForecastingFailureContextPreparationService not in runtime_mro
    assert ForecastingFailureHandlingService not in runtime_mro


async def test_single_attributed_failure_returns_terminal_forecasting_failed() -> None:
    first = diagnostic()
    second = AdapterDiagnostic(
        code="SCHEMA_AMBIGUOUS",
        message="header mapping was ambiguous",
        severity=DiagnosticSeverity.WARNING,
        field_name="timestamp",
    )
    state = _state(diagnostics=(first, second))
    leaf = _chained_failure(
        AgentName.CONSUMER_LOAD_FORECAST,
        InvalidRequestError("consumer load request is invalid"),
    )
    group = ExceptionGroup("group", [leaf])
    before = _snapshot(state)

    failed = await _real_runtime_service().handle(state=state, failure_group=group)
    expected = fail_after_forecasting(state)

    assert failed is not state
    assert _snapshot(state) == before
    assert failed == expected
    assert failed.phase is WorkflowPhase.FORECASTING
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
        phase=WorkflowPhase.FORECASTING,
        error_code="invalid_request",
        attempt_number=1,
        agent_name=AgentName.DAM_PRICE_FORECAST,
    )
    expected = fail_after_forecasting(state)
    events: list[str] = []
    preparation = _OrderedPreparationService(context, events)
    handling = _OrderedHandlingService(expected, events)
    service = ForecastingFailureRuntimeHandlingService(
        cast(ForecastingFailureContextPreparationService, preparation),
        cast(ForecastingFailureHandlingService, handling),
    )
    leaf = _chained_failure(
        AgentName.DAM_PRICE_FORECAST,
        InvalidRequestError("dam price request is invalid"),
    )
    group = ExceptionGroup("group", [leaf])

    failed = await service.handle(state=state, failure_group=group)

    assert events == ["prepare", "handle"]
    assert preparation.calls == 1
    assert handling.calls == 1
    assert preparation.received_workflow_id is state.workflow_id
    assert preparation.received_phase is state.phase
    assert preparation.received_error is group
    assert handling.received_state is state
    assert handling.received_context is context
    assert failed is expected


async def test_preparation_failure_propagates_without_handling() -> None:
    state = _state()
    error = InvalidRequestError("preparation unavailable")
    preparation = _RecordingPreparationService(error=error)
    handling = _RecordingHandlingService()
    service = ForecastingFailureRuntimeHandlingService(
        cast(ForecastingFailureContextPreparationService, preparation),
        cast(ForecastingFailureHandlingService, handling),
    )
    leaf = _chained_failure(
        AgentName.CONSUMER_LOAD_FORECAST,
        InvalidRequestError("consumer load request is invalid"),
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


async def test_handling_failure_propagates_unchanged_after_preparation() -> None:
    state = _state()
    context = FailurePolicyContext(
        phase=WorkflowPhase.FORECASTING,
        error_code="invalid_request",
        attempt_number=1,
        agent_name=AgentName.CONSUMER_LOAD_FORECAST,
    )
    error = InvalidRequestError("Forecasting retry action is not implemented.")
    preparation = _RecordingPreparationService(context=context)
    handling = _RecordingHandlingService(error=error)
    service = ForecastingFailureRuntimeHandlingService(
        cast(ForecastingFailureContextPreparationService, preparation),
        cast(ForecastingFailureHandlingService, handling),
    )
    leaf = _chained_failure(
        AgentName.CONSUMER_LOAD_FORECAST,
        InvalidRequestError("consumer load request is invalid"),
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


async def test_multiple_attributed_failures_fail_closed_without_handling() -> None:
    state = _state()
    consumer = _chained_failure(
        AgentName.CONSUMER_LOAD_FORECAST,
        InvalidRequestError("consumer load request is invalid"),
    )
    dam = _chained_failure(
        AgentName.DAM_PRICE_FORECAST,
        DependencyUnavailableError("dam price source unavailable"),
    )
    group = ExceptionGroup("group", [consumer, dam])
    handling = _RecordingHandlingService()
    service = ForecastingFailureRuntimeHandlingService(
        ForecastingFailureContextPreparationService(
            ForecastingFailureContextResolutionService(
                StrictSingleForecastingFailureSelector(),
                InitialForecastingAttemptNumberSource(),
            )
        ),
        cast(ForecastingFailureHandlingService, handling),
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


async def test_runtime_handling_does_not_require_a_graph_object() -> None:
    state = _state()
    leaf = _chained_failure(
        AgentName.DAM_PRICE_FORECAST,
        InvalidRequestError("dam price request is invalid"),
    )
    group = ExceptionGroup("group", [leaf])

    failed = await _real_runtime_service().handle(state=state, failure_group=group)

    assert failed.phase is WorkflowPhase.FORECASTING
    assert failed.status is WorkflowStatus.FAILED
    assert failed == fail_after_forecasting(state)
