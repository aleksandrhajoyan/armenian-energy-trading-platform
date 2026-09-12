"""Application-owned Regulatory Intelligence workflow-context Protocol."""

from __future__ import annotations

import inspect
from datetime import date
from typing import get_type_hints

from energy_trading.application.agents.regulatory_intelligence import (
    RegulatoryIntelligenceResult,
)
from energy_trading.application.orchestration import (
    RegulatoryIntelligenceWorkflowContextPort,
    RegulatoryIntelligenceWorkflowRequest,
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)
from tests.unit.domain._factories import constraint


class _StructuralRegulatoryIntelligenceWorkflowContextFake:
    """Test-only fake that structurally satisfies the context Protocol.

    Not a production context implementation. Does not inherit a production
    base class.
    """

    def __init__(
        self,
        request: RegulatoryIntelligenceWorkflowRequest,
        recorded: list[tuple[WorkflowState, RegulatoryIntelligenceResult]] | None = None,
    ) -> None:
        self._request = request
        self.received_resolve_state: WorkflowState | None = None
        self.received_record_state: WorkflowState | None = None
        self.received_result: RegulatoryIntelligenceResult | None = None
        self.recorded = recorded if recorded is not None else []

    async def resolve_request(
        self,
        *,
        state: WorkflowState,
    ) -> RegulatoryIntelligenceWorkflowRequest:
        self.received_resolve_state = state
        return self._request

    async def record_result(
        self,
        *,
        state: WorkflowState,
        result: RegulatoryIntelligenceResult,
    ) -> None:
        self.received_record_state = state
        self.received_result = result
        self.recorded.append((state, result))


def _request() -> RegulatoryIntelligenceWorkflowRequest:
    return RegulatoryIntelligenceWorkflowRequest(query_text="typed regulatory query", limit=4)


def _result() -> RegulatoryIntelligenceResult:
    return RegulatoryIntelligenceResult(constraints=(constraint(),))


def _state() -> WorkflowState:
    return WorkflowState(
        workflow_id="workflow-regulatory-1",
        portfolio_id="portfolio-1",
        delivery_date=date(2026, 10, 1),
        correlation_id="corr-1",
        phase=WorkflowPhase.CONTRACT,
        status=WorkflowStatus.RUNNING,
    )


def _as_context_port(
    fake: _StructuralRegulatoryIntelligenceWorkflowContextFake,
) -> RegulatoryIntelligenceWorkflowContextPort:
    """Application-shaped call site: the port type is the only accepted argument."""

    return fake


def test_context_port_is_typing_protocol() -> None:
    bases = RegulatoryIntelligenceWorkflowContextPort.__bases__
    assert any(base.__name__ == "Protocol" for base in bases)
    assert RegulatoryIntelligenceWorkflowContextPort.__type_params__ == ()


def test_context_fake_does_not_inherit_production_base() -> None:
    assert (
        RegulatoryIntelligenceWorkflowContextPort
        not in _StructuralRegulatoryIntelligenceWorkflowContextFake.__mro__
    )
    assert not any(
        base.__name__ in {"RegulatoryIntelligenceWorkflowContextPort", "Protocol"}
        for base in _StructuralRegulatoryIntelligenceWorkflowContextFake.__bases__
    )


def test_context_port_exposes_exactly_two_async_operations() -> None:
    defined_methods = {
        name
        for name, value in vars(RegulatoryIntelligenceWorkflowContextPort).items()
        if callable(value) and not name.startswith("_")
    }
    assert defined_methods == {"resolve_request", "record_result"}
    assert inspect.iscoroutinefunction(RegulatoryIntelligenceWorkflowContextPort.resolve_request)
    assert inspect.iscoroutinefunction(RegulatoryIntelligenceWorkflowContextPort.record_result)


def test_resolve_request_is_keyword_only_state_with_no_defaults() -> None:
    signature = inspect.signature(RegulatoryIntelligenceWorkflowContextPort.resolve_request)
    assert tuple(signature.parameters) == ("self", "state")
    state_parameter = signature.parameters["state"]
    assert state_parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert state_parameter.default is inspect.Parameter.empty
    assert state_parameter.annotation is WorkflowState
    assert signature.return_annotation is RegulatoryIntelligenceWorkflowRequest


def test_record_result_is_keyword_only_state_and_result_with_no_defaults() -> None:
    signature = inspect.signature(RegulatoryIntelligenceWorkflowContextPort.record_result)
    assert tuple(signature.parameters) == ("self", "state", "result")
    state_parameter = signature.parameters["state"]
    result_parameter = signature.parameters["result"]
    assert state_parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert result_parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert state_parameter.default is inspect.Parameter.empty
    assert result_parameter.default is inspect.Parameter.empty
    assert state_parameter.annotation is WorkflowState
    assert result_parameter.annotation is RegulatoryIntelligenceResult
    assert signature.return_annotation is None


def test_resolved_annotations_reuse_published_types() -> None:
    resolve_hints = get_type_hints(RegulatoryIntelligenceWorkflowContextPort.resolve_request)
    record_hints = get_type_hints(RegulatoryIntelligenceWorkflowContextPort.record_result)
    assert resolve_hints["state"] is WorkflowState
    assert resolve_hints["return"] is RegulatoryIntelligenceWorkflowRequest
    assert record_hints["state"] is WorkflowState
    assert record_hints["result"] is RegulatoryIntelligenceResult
    assert record_hints["return"] is type(None)


async def test_context_fake_satisfies_port_preserving_request_and_state_identity() -> None:
    request = _request()
    fake = _StructuralRegulatoryIntelligenceWorkflowContextFake(request)
    port = _as_context_port(fake)
    state = _state()
    resolved = await port.resolve_request(state=state)
    assert inspect.iscoroutinefunction(port.resolve_request)
    assert resolved is request
    assert fake.received_resolve_state is state
    assert isinstance(resolved, RegulatoryIntelligenceWorkflowRequest)
    assert resolved.query_text == "typed regulatory query"
    assert resolved.limit == 4


async def test_record_result_preserves_state_and_result_identity() -> None:
    request = _request()
    result = _result()
    fake = _StructuralRegulatoryIntelligenceWorkflowContextFake(request)
    port = _as_context_port(fake)
    state = _state()
    recorded = await port.record_result(state=state, result=result)
    assert recorded is None
    assert fake.received_record_state is state
    assert fake.received_result is result
    assert fake.recorded == [(state, result)]
    assert fake.recorded[0][0] is state
    assert fake.recorded[0][1] is result


async def test_context_does_not_mutate_workflow_state_or_use_generic_payloads() -> None:
    request = _request()
    result = _result()
    fake = _StructuralRegulatoryIntelligenceWorkflowContextFake(request)
    port = _as_context_port(fake)
    state = _state()
    original_workflow_id = state.workflow_id
    original_phase = state.phase
    original_status = state.status
    original_diagnostics = state.diagnostics
    resolved = await port.resolve_request(state=state)
    recorded = await port.record_result(state=state, result=result)
    assert resolved is request
    assert recorded is None
    assert state.workflow_id is original_workflow_id
    assert state.phase is original_phase
    assert state.status is original_status
    assert state.diagnostics is original_diagnostics
    assert "regulatory_request" not in state.__slots__
    assert "regulatory_result" not in state.__slots__
    assert "query_text" not in state.__slots__
    assert "payload" not in state.__slots__
    assert "data" not in state.__slots__
    assert "context" not in state.__slots__
    assert "artifacts" not in state.__slots__
    assert fake.received_resolve_state is state
    assert fake.received_record_state is state
    assert fake.received_result is result
