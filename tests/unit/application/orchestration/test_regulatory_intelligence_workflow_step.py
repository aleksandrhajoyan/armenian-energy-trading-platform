"""Regulatory Intelligence workflow step delegates typed query execution."""

from __future__ import annotations

import inspect
from dataclasses import MISSING, FrozenInstanceError, fields
from typing import cast

import pytest

from energy_trading.application.agents.base import AgentName, AgentPort
from energy_trading.application.agents.regulatory_intelligence import (
    RegulatoryIntelligenceResult,
)
from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.application.orchestration import (
    RegulatoryIntelligenceQueryExecutionService,
    RegulatoryIntelligenceWorkflowRequest,
    RegulatoryIntelligenceWorkflowStep,
)
from tests.unit.domain._factories import constraint

_UNAVAILABLE_MESSAGE = "Regulatory Intelligence is unavailable."
_INVALID_MESSAGE = "Regulatory Intelligence query is invalid."


class _RecordingQueryExecutionService:
    """Test-only recorder. Not a production Protocol or abstraction."""

    def __init__(
        self,
        *,
        result: RegulatoryIntelligenceResult | None = None,
        error: BaseException | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls: list[tuple[str, int]] = []
        self.received_query_text: str | None = None
        self.received_limit: int | None = None

    async def execute(
        self,
        *,
        query_text: str,
        limit: int,
    ) -> RegulatoryIntelligenceResult:
        self.calls.append((query_text, limit))
        self.received_query_text = query_text
        self.received_limit = limit
        if self._error is not None:
            raise self._error
        if self._result is None:
            msg = "recording query-execution double must return a result"
            raise AssertionError(msg)
        return self._result


def _as_query_execution_service(
    recorder: _RecordingQueryExecutionService,
) -> RegulatoryIntelligenceQueryExecutionService:
    return cast(RegulatoryIntelligenceQueryExecutionService, recorder)


def _as_agent_port(
    step: RegulatoryIntelligenceWorkflowStep,
) -> AgentPort[RegulatoryIntelligenceWorkflowRequest, RegulatoryIntelligenceResult]:
    """Mypy-visible structural assignment to the shared agent port."""

    return step


def _step(
    recorder: _RecordingQueryExecutionService,
) -> RegulatoryIntelligenceWorkflowStep:
    return RegulatoryIntelligenceWorkflowStep(_as_query_execution_service(recorder))


def test_request_is_frozen_and_slotted() -> None:
    request = RegulatoryIntelligenceWorkflowRequest(query_text="typed query", limit=4)
    assert hasattr(RegulatoryIntelligenceWorkflowRequest, "__slots__")
    with pytest.raises(FrozenInstanceError):
        request.query_text = "mutated"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        request.limit = 1  # type: ignore[misc]
    field_names = tuple(item.name for item in fields(RegulatoryIntelligenceWorkflowRequest))
    assert field_names == ("query_text", "limit")


def test_request_has_exactly_query_text_and_limit_with_no_defaults() -> None:
    signature = inspect.signature(RegulatoryIntelligenceWorkflowRequest)
    assert tuple(signature.parameters) == ("query_text", "limit")
    assert signature.parameters["query_text"].annotation is str
    assert signature.parameters["limit"].annotation is int
    for item in fields(RegulatoryIntelligenceWorkflowRequest):
        assert item.default is MISSING
        assert item.default_factory is MISSING
    with pytest.raises(TypeError):
        RegulatoryIntelligenceWorkflowRequest()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        RegulatoryIntelligenceWorkflowRequest(query_text="typed query")  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        RegulatoryIntelligenceWorkflowRequest(limit=4)  # type: ignore[call-arg]


def test_request_rejects_unrequested_fields() -> None:
    with pytest.raises(TypeError):
        RegulatoryIntelligenceWorkflowRequest(
            query_text="typed query",
            limit=4,
            model="must-not-exist",  # type: ignore[call-arg]
        )


def test_constructor_accepts_exactly_the_published_query_execution_service() -> None:
    signature = inspect.signature(RegulatoryIntelligenceWorkflowStep.__init__)
    assert tuple(signature.parameters) == ("self", "query_execution_service")
    assert (
        signature.parameters["query_execution_service"].annotation
        is RegulatoryIntelligenceQueryExecutionService
    )
    recorder = _RecordingQueryExecutionService(result=RegulatoryIntelligenceResult(constraints=()))
    step = _step(recorder)
    assert isinstance(step, RegulatoryIntelligenceWorkflowStep)
    assert recorder.calls == []


def test_step_does_not_inherit_agent_port() -> None:
    assert AgentPort not in RegulatoryIntelligenceWorkflowStep.__mro__
    assert not any(
        base.__name__ == "AgentPort" for base in RegulatoryIntelligenceWorkflowStep.__bases__
    )


def test_step_name_is_canonical_regulatory_identity() -> None:
    empty = RegulatoryIntelligenceResult(constraints=())
    step = _step(_RecordingQueryExecutionService(result=empty))
    port = _as_agent_port(step)
    assert port.name is AgentName.REGULATORY_INTELLIGENCE
    assert port.name.value == "Regulatory Intelligence Agent"


def test_run_signature_matches_agent_port() -> None:
    signature = inspect.signature(RegulatoryIntelligenceWorkflowStep.run)
    assert tuple(signature.parameters) == ("self", "request")
    assert signature.parameters["request"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert signature.parameters["request"].annotation is RegulatoryIntelligenceWorkflowRequest
    assert signature.return_annotation is RegulatoryIntelligenceResult
    assert inspect.iscoroutinefunction(RegulatoryIntelligenceWorkflowStep.run)


async def test_run_delegates_exactly_once_with_unchanged_query_text_and_limit() -> None:
    query_text = "  surrounding spaces are preserved  "
    limit = 7
    result = RegulatoryIntelligenceResult(constraints=(constraint(),))
    recorder = _RecordingQueryExecutionService(result=result)
    step = _step(recorder)
    request = RegulatoryIntelligenceWorkflowRequest(query_text=query_text, limit=limit)

    returned = await _as_agent_port(step).run(request)

    assert recorder.calls == [(query_text, limit)]
    assert recorder.received_query_text is query_text
    assert recorder.received_query_text != query_text.strip()
    assert recorder.received_limit == limit
    assert returned is result
    assert returned.constraints == result.constraints


async def test_empty_constraint_result_identity_is_returned_unchanged() -> None:
    empty = RegulatoryIntelligenceResult(constraints=())
    recorder = _RecordingQueryExecutionService(result=empty)
    step = _step(recorder)

    returned = await step.run(
        RegulatoryIntelligenceWorkflowRequest(query_text="empty-success query", limit=2)
    )

    assert returned is empty
    assert returned.constraints == ()
    assert isinstance(returned, RegulatoryIntelligenceResult)


async def test_dependency_unavailable_error_identity_propagates_without_retry() -> None:
    error = DependencyUnavailableError(_UNAVAILABLE_MESSAGE)
    recorder = _RecordingQueryExecutionService(error=error)
    step = _step(recorder)
    request = RegulatoryIntelligenceWorkflowRequest(
        query_text="Confidential regulatory search query.",
        limit=5,
    )

    with pytest.raises(DependencyUnavailableError) as caught:
        await step.run(request)

    assert caught.value is error
    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert recorder.calls == [("Confidential regulatory search query.", 5)]


async def test_invalid_request_error_identity_propagates_without_retry() -> None:
    error = InvalidRequestError(_INVALID_MESSAGE)
    recorder = _RecordingQueryExecutionService(error=error)
    step = _step(recorder)

    with pytest.raises(InvalidRequestError) as caught:
        await step.run(RegulatoryIntelligenceWorkflowRequest(query_text="invalid query", limit=3))

    assert caught.value is error
    assert caught.value.message == _INVALID_MESSAGE
    assert recorder.calls == [("invalid query", 3)]


async def test_repeated_run_delegates_once_per_call_without_retaining_results() -> None:
    first_result = RegulatoryIntelligenceResult(constraints=(constraint(constraint_id="c-1"),))
    second_result = RegulatoryIntelligenceResult(constraints=(constraint(constraint_id="c-2"),))
    recorder = _RecordingQueryExecutionService(result=first_result)
    step = _step(recorder)

    first_returned = await step.run(
        RegulatoryIntelligenceWorkflowRequest(query_text="first query", limit=4)
    )
    recorder._result = second_result
    second_returned = await step.run(
        RegulatoryIntelligenceWorkflowRequest(query_text="second query", limit=1)
    )

    assert recorder.calls == [("first query", 4), ("second query", 1)]
    assert first_returned is first_result
    assert second_returned is second_result
    assert first_returned is not second_returned
