"""Phase 3 failure-context preparation composes extraction through resolution."""

from __future__ import annotations

import inspect
from typing import cast

import pytest

from energy_trading.application.agents.base import AgentName
from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.application.orchestration import (
    forecasting_failure_context_preparation as preparation_module,
)
from energy_trading.application.orchestration.failure_policy import FailurePolicyContext
from energy_trading.application.orchestration.forecasting_agent_failure import (
    ForecastingAgentFailure,
)
from energy_trading.application.orchestration.forecasting_failure_classification import (
    classify_forecasting_agent_failures,
)
from energy_trading.application.orchestration.forecasting_failure_context_preparation import (
    ForecastingFailureContextPreparationService,
)
from energy_trading.application.orchestration.forecasting_failure_context_resolution import (
    ForecastingFailureContextResolutionService,
)
from energy_trading.application.orchestration.forecasting_failure_fact import (
    ForecastingFailureFact,
)
from energy_trading.application.orchestration.forecasting_strict_single_failure_selector import (
    StrictSingleForecastingFailureSelector,
)
from energy_trading.application.orchestration.state import WorkflowPhase

_UNEXPECTED_FAILURE_CODE = "forecasting_unexpected_failure"
_SENTINEL_TEXT = "secret provider payload not for clients"


class _ExtractBoom(Exception):
    """Test-only sentinel; not a production extraction error."""


class _ClassifyBoom(Exception):
    """Test-only sentinel; not a production classification error."""


class _ResolveBoom(Exception):
    """Test-only sentinel; not a production resolution error."""


class _RecordingAttemptNumberFake:
    """Test-only fake that structurally satisfies the attempt-number Protocol.

    Not a production tracker. Does not inherit a production base class.
    The predetermined result is test-local wiring, not increment semantics.
    """

    def __init__(self, result: int) -> None:
        self._result = result
        self.calls = 0
        self.received: str | None = None

    async def get_attempt_number(self, workflow_id: str) -> int:
        self.calls += 1
        self.received = workflow_id
        return self._result


class _RecordingResolutionService:
    """Test-only recording double. Not a production Protocol or abstraction."""

    def __init__(self, error: BaseException | None = None) -> None:
        self._error = error
        self.calls = 0
        self.received_workflow_id: str | None = None
        self.received_phase: WorkflowPhase | None = None
        self.received_facts: tuple[ForecastingFailureFact, ...] | None = None

    async def resolve(
        self,
        *,
        workflow_id: str,
        phase: WorkflowPhase,
        facts: tuple[ForecastingFailureFact, ...],
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

    def __init__(
        self,
        inner: ForecastingFailureContextResolutionService,
        call_order: list[str] | None = None,
    ) -> None:
        self._inner = inner
        self.calls = 0
        self.call_order = call_order if call_order is not None else []
        self.received_workflow_id: str | None = None
        self.received_phase: WorkflowPhase | None = None
        self.received_facts: tuple[ForecastingFailureFact, ...] | None = None

    async def resolve(
        self,
        *,
        workflow_id: str,
        phase: WorkflowPhase,
        facts: tuple[ForecastingFailureFact, ...],
    ) -> FailurePolicyContext:
        self.calls += 1
        self.call_order.append("resolve")
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
) -> ForecastingAgentFailure:
    try:
        raise ForecastingAgentFailure(agent_name) from cause
    except ForecastingAgentFailure as exc:
        return exc


def _real_resolution_service(
    attempt_number: int = 1,
) -> tuple[ForecastingFailureContextResolutionService, _RecordingAttemptNumberFake]:
    attempt = _RecordingAttemptNumberFake(attempt_number)
    service = ForecastingFailureContextResolutionService(
        StrictSingleForecastingFailureSelector(),
        attempt,
    )
    return service, attempt


def _real_preparation_service(
    attempt_number: int = 1,
) -> tuple[ForecastingFailureContextPreparationService, _RecordingAttemptNumberFake]:
    resolution, attempt = _real_resolution_service(attempt_number)
    return ForecastingFailureContextPreparationService(resolution), attempt


def test_constructor_accepts_exactly_the_published_resolution_service() -> None:
    signature = inspect.signature(ForecastingFailureContextPreparationService.__init__)
    assert tuple(signature.parameters) == ("self", "context_resolution_service")
    assert (
        signature.parameters["context_resolution_service"].annotation
        is ForecastingFailureContextResolutionService
    )
    assert signature.parameters["context_resolution_service"].default is inspect.Parameter.empty


def test_prepare_signature_is_keyword_only_workflow_phase_and_error() -> None:
    signature = inspect.signature(ForecastingFailureContextPreparationService.prepare)
    assert tuple(signature.parameters) == ("self", "workflow_id", "phase", "error")
    assert signature.parameters["workflow_id"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["phase"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["error"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["workflow_id"].annotation is str
    assert signature.parameters["phase"].annotation is WorkflowPhase
    assert signature.parameters["error"].annotation is BaseException
    assert signature.return_annotation is FailurePolicyContext
    assert inspect.iscoroutinefunction(ForecastingFailureContextPreparationService.prepare)


async def test_single_attributed_application_error_prepares_context() -> None:
    cause = InvalidRequestError("consumer load request is invalid")
    leaf = _chained_failure(AgentName.CONSUMER_LOAD_FORECAST, cause)
    group = ExceptionGroup("group", [leaf])
    workflow_id = "wf-single-application"
    phase = WorkflowPhase.FORECASTING
    service, attempt = _real_preparation_service(attempt_number=4)

    context = await service.prepare(
        workflow_id=workflow_id,
        phase=phase,
        error=group,
    )

    assert isinstance(context, FailurePolicyContext)
    assert context.phase is phase
    assert context.agent_name is AgentName.CONSUMER_LOAD_FORECAST
    assert context.error_code == cause.code
    assert context.error_code == "invalid_request"
    assert context.attempt_number == 4
    assert attempt.calls == 1
    assert attempt.received is workflow_id


async def test_unexpected_non_application_cause_uses_sanitized_code() -> None:
    leaf = _chained_failure(AgentName.DAM_PRICE_FORECAST, RuntimeError(_SENTINEL_TEXT))
    group = ExceptionGroup("group", [leaf])
    service, _attempt = _real_preparation_service()

    context = await service.prepare(
        workflow_id="wf-unexpected",
        phase=WorkflowPhase.FORECASTING,
        error=group,
    )

    assert context.agent_name is AgentName.DAM_PRICE_FORECAST
    assert context.error_code == _UNEXPECTED_FAILURE_CODE
    assert context.attempt_number == 1
    assert _SENTINEL_TEXT not in context.error_code
    assert _SENTINEL_TEXT not in repr(context)
    assert "RuntimeError" not in context.error_code


async def test_nested_exception_group_preserves_depth_first_order() -> None:
    consumer = _chained_failure(
        AgentName.CONSUMER_LOAD_FORECAST,
        InvalidRequestError("consumer load request is invalid"),
    )
    dam = _chained_failure(
        AgentName.DAM_PRICE_FORECAST,
        DependencyUnavailableError("dam source unavailable"),
    )
    second_consumer = _chained_failure(
        AgentName.CONSUMER_LOAD_FORECAST,
        InvalidRequestError("second consumer load request is invalid"),
    )
    group = ExceptionGroup(
        "outer",
        [
            consumer,
            ExceptionGroup("inner", [dam]),
            second_consumer,
        ],
    )
    expected_facts = classify_forecasting_agent_failures((consumer, dam, second_consumer))
    recorder = _RecordingResolutionService()
    service = ForecastingFailureContextPreparationService(
        cast(ForecastingFailureContextResolutionService, recorder)
    )

    with pytest.raises(AssertionError):
        await service.prepare(
            workflow_id="wf-nested",
            phase=WorkflowPhase.FORECASTING,
            error=group,
        )

    assert recorder.calls == 1
    assert recorder.received_facts == expected_facts
    assert recorder.received_facts is not None
    assert len(recorder.received_facts) == 3
    assert recorder.received_facts[0].agent_name is AgentName.CONSUMER_LOAD_FORECAST
    assert recorder.received_facts[0].error_code == "invalid_request"
    assert recorder.received_facts[1].agent_name is AgentName.DAM_PRICE_FORECAST
    assert recorder.received_facts[1].error_code == "dependency_unavailable"
    assert recorder.received_facts[2].agent_name is AgentName.CONSUMER_LOAD_FORECAST
    assert recorder.received_facts[2].error_code == "invalid_request"


async def test_duplicate_attributed_failure_object_is_not_deduplicated() -> None:
    leaf = _chained_failure(
        AgentName.CONSUMER_LOAD_FORECAST,
        InvalidRequestError("consumer load request is invalid"),
    )
    group = ExceptionGroup("group", [leaf, leaf])
    expected_facts = classify_forecasting_agent_failures((leaf, leaf))
    recorder = _RecordingResolutionService()
    service = ForecastingFailureContextPreparationService(
        cast(ForecastingFailureContextResolutionService, recorder)
    )

    with pytest.raises(AssertionError):
        await service.prepare(
            workflow_id="wf-duplicate",
            phase=WorkflowPhase.FORECASTING,
            error=group,
        )

    assert recorder.calls == 1
    assert recorder.received_facts == expected_facts
    assert recorder.received_facts is not None
    assert len(recorder.received_facts) == 2
    assert recorder.received_facts[0] == recorder.received_facts[1]
    assert recorder.received_facts[0].agent_name is AgentName.CONSUMER_LOAD_FORECAST
    assert recorder.received_facts[0].error_code == "invalid_request"


async def test_opaque_workflow_id_is_forwarded_unchanged() -> None:
    leaf = _chained_failure(
        AgentName.DAM_PRICE_FORECAST,
        InvalidRequestError("dam request is invalid"),
    )
    group = ExceptionGroup("group", [leaf])
    workflow_id = "  wf::FORECAST/161%20ID\tpath  "
    recorder = _DelegatingResolutionService(_real_resolution_service()[0])
    service = ForecastingFailureContextPreparationService(
        cast(ForecastingFailureContextResolutionService, recorder)
    )

    context = await service.prepare(
        workflow_id=workflow_id,
        phase=WorkflowPhase.FORECASTING,
        error=group,
    )

    assert recorder.calls == 1
    assert recorder.received_workflow_id is workflow_id
    assert recorder.received_workflow_id == "  wf::FORECAST/161%20ID\tpath  "
    assert context.agent_name is AgentName.DAM_PRICE_FORECAST


async def test_non_forecasting_phase_is_forwarded_unchanged() -> None:
    leaf = _chained_failure(
        AgentName.CONSUMER_LOAD_FORECAST,
        InvalidRequestError("consumer load request is invalid"),
    )
    group = ExceptionGroup("group", [leaf])
    phase = WorkflowPhase.CONTRACT
    recorder = _DelegatingResolutionService(_real_resolution_service()[0])
    service = ForecastingFailureContextPreparationService(
        cast(ForecastingFailureContextResolutionService, recorder)
    )

    context = await service.prepare(
        workflow_id="wf-contract-phase",
        phase=phase,
        error=group,
    )

    assert recorder.calls == 1
    assert recorder.received_phase is phase
    assert recorder.received_phase is WorkflowPhase.CONTRACT
    assert context.phase is WorkflowPhase.CONTRACT
    assert context.phase is phase


async def test_extraction_failure_short_circuits_classification_and_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    leaf = _chained_failure(
        AgentName.CONSUMER_LOAD_FORECAST,
        InvalidRequestError("consumer load request is invalid"),
    )
    group = ExceptionGroup("group", [leaf])
    error = _ExtractBoom("extraction unavailable")
    classify_calls: list[object] = []
    recorder = _RecordingResolutionService()
    service = ForecastingFailureContextPreparationService(
        cast(ForecastingFailureContextResolutionService, recorder)
    )

    def _failing_extract(failure: BaseException) -> tuple[ForecastingAgentFailure, ...]:
        del failure
        raise error

    def _tracking_classify(
        failures: tuple[ForecastingAgentFailure, ...],
    ) -> tuple[ForecastingFailureFact, ...]:
        classify_calls.append(failures)
        raise AssertionError("classifier must not run after extraction failure")

    monkeypatch.setattr(
        preparation_module,
        "extract_forecasting_agent_failures",
        _failing_extract,
    )
    monkeypatch.setattr(
        preparation_module,
        "classify_forecasting_agent_failures",
        _tracking_classify,
    )

    with pytest.raises(_ExtractBoom) as caught:
        await service.prepare(
            workflow_id="wf-extract-failure",
            phase=WorkflowPhase.FORECASTING,
            error=group,
        )

    assert caught.value is error
    assert classify_calls == []
    assert recorder.calls == 0
    assert recorder.received_facts is None


async def test_classification_failure_short_circuits_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    leaf = _chained_failure(
        AgentName.DAM_PRICE_FORECAST,
        InvalidRequestError("dam request is invalid"),
    )
    group = ExceptionGroup("group", [leaf])
    error = _ClassifyBoom("classification unavailable")
    recorder = _RecordingResolutionService()
    service = ForecastingFailureContextPreparationService(
        cast(ForecastingFailureContextResolutionService, recorder)
    )

    def _failing_classify(
        failures: tuple[ForecastingAgentFailure, ...],
    ) -> tuple[ForecastingFailureFact, ...]:
        del failures
        raise error

    monkeypatch.setattr(
        preparation_module,
        "classify_forecasting_agent_failures",
        _failing_classify,
    )

    with pytest.raises(_ClassifyBoom) as caught:
        await service.prepare(
            workflow_id="wf-classify-failure",
            phase=WorkflowPhase.FORECASTING,
            error=group,
        )

    assert caught.value is error
    assert recorder.calls == 0
    assert recorder.received_facts is None


async def test_resolution_failure_propagates_unchanged() -> None:
    leaf = _chained_failure(
        AgentName.CONSUMER_LOAD_FORECAST,
        InvalidRequestError("consumer load request is invalid"),
    )
    group = ExceptionGroup("group", [leaf])
    error = _ResolveBoom("resolution unavailable")
    recorder = _RecordingResolutionService(error=error)
    service = ForecastingFailureContextPreparationService(
        cast(ForecastingFailureContextResolutionService, recorder)
    )

    with pytest.raises(_ResolveBoom) as caught:
        await service.prepare(
            workflow_id="wf-resolve-failure",
            phase=WorkflowPhase.FORECASTING,
            error=group,
        )

    assert caught.value is error
    assert recorder.calls == 1
    assert recorder.received_workflow_id == "wf-resolve-failure"
    assert recorder.received_facts is not None
    assert len(recorder.received_facts) == 1


async def test_prepare_delegates_each_stage_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    leaf = _chained_failure(
        AgentName.DAM_PRICE_FORECAST,
        InvalidRequestError("dam request is invalid"),
    )
    group = ExceptionGroup("group", [leaf])
    call_order: list[str] = []
    extract_calls: list[BaseException] = []
    classify_calls: list[tuple[ForecastingAgentFailure, ...]] = []
    original_extract = preparation_module.extract_forecasting_agent_failures
    original_classify = preparation_module.classify_forecasting_agent_failures

    def _tracking_extract(
        failure: BaseException,
    ) -> tuple[ForecastingAgentFailure, ...]:
        extract_calls.append(failure)
        call_order.append("extract")
        return original_extract(failure)

    def _tracking_classify(
        failures: tuple[ForecastingAgentFailure, ...],
    ) -> tuple[ForecastingFailureFact, ...]:
        classify_calls.append(failures)
        call_order.append("classify")
        return original_classify(failures)

    monkeypatch.setattr(
        preparation_module,
        "extract_forecasting_agent_failures",
        _tracking_extract,
    )
    monkeypatch.setattr(
        preparation_module,
        "classify_forecasting_agent_failures",
        _tracking_classify,
    )
    recorder = _DelegatingResolutionService(
        _real_resolution_service()[0],
        call_order=call_order,
    )
    service = ForecastingFailureContextPreparationService(
        cast(ForecastingFailureContextResolutionService, recorder)
    )

    context = await service.prepare(
        workflow_id="wf-delegate-once",
        phase=WorkflowPhase.FORECASTING,
        error=group,
    )

    assert extract_calls == [group]
    assert extract_calls[0] is group
    assert len(classify_calls) == 1
    assert classify_calls[0] == (leaf,)
    assert classify_calls[0][0] is leaf
    assert recorder.calls == 1
    assert call_order == ["extract", "classify", "resolve"]
    assert context.error_code == "invalid_request"
