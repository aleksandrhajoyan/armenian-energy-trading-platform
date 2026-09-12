"""LangGraph contract-phase Regulatory Intelligence wiring."""

from __future__ import annotations

from datetime import date

import pytest
from langgraph.graph import END, START

from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.application.orchestration import (
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
    build_workflow_graph,
)
from tests.unit.domain._factories import diagnostic

_INVALID_ENTRY_ROUTE_MESSAGE = (
    "Workflow entry routing requires contract running, ingestion running, "
    "or forecasting running status."
)
_PHASE2_APPLICATION_NODES = (
    "workflow_entry",
    "parallel_ingestion",
    "parallel_ingestion_success_transition",
)
_CONTRACT_APPLICATION_NODES = (
    "workflow_entry",
    "regulatory_intelligence",
)
_PHASE3_APPLICATION_NODES = (
    "workflow_entry",
    "forecasting",
)


class _RecordingRegulatoryIntelligenceNode:
    """Test-only stand-in for the injected Chunk 116 adapter."""

    def __init__(self, error: BaseException | None = None) -> None:
        self.error = error
        self.calls = 0
        self.received: list[WorkflowState] = []

    async def run(self, state: WorkflowState) -> WorkflowState:
        self.calls += 1
        self.received.append(state)
        if self.error is not None:
            raise self.error
        return state


class _RecordingParallelIngestionStep:
    """Test-only stand-in for the injected Phase 2 workflow step."""

    def __init__(self, error: BaseException | None = None) -> None:
        self.error = error
        self.calls = 0
        self.received: list[WorkflowState] = []

    async def run(self, state: WorkflowState) -> WorkflowState:
        self.calls += 1
        self.received.append(state)
        if self.error is not None:
            raise self.error
        return state


class _RecordingParallelIngestionFailureRuntimeHandler:
    """Test-only stand-in for the injected Phase 2 runtime failure handler."""

    def __init__(self) -> None:
        self.calls = 0

    async def handle(
        self,
        *,
        state: WorkflowState,
        failure_group: BaseExceptionGroup,
    ) -> WorkflowState:
        self.calls += 1
        return state


class _RecordingForecastingStep:
    """Test-only stand-in for the injected Phase 3 workflow step."""

    def __init__(self) -> None:
        self.calls = 0
        self.received: list[WorkflowState] = []

    async def run(self, state: WorkflowState) -> WorkflowState:
        self.calls += 1
        self.received.append(state)
        return state


def _state(**overrides: object) -> WorkflowState:
    values: dict[str, object] = {
        "workflow_id": "workflow-regulatory-1",
        "portfolio_id": "portfolio-1",
        "delivery_date": date(2026, 10, 1),
        "correlation_id": "corr-1",
        "phase": WorkflowPhase.CONTRACT,
        "status": WorkflowStatus.RUNNING,
        "diagnostics": (),
    }
    values.update(overrides)
    return WorkflowState(**values)  # type: ignore[arg-type]


def _reconstruct(payload: dict[str, object]) -> WorkflowState:
    return WorkflowState(
        workflow_id=payload["workflow_id"],  # type: ignore[arg-type]
        portfolio_id=payload["portfolio_id"],  # type: ignore[arg-type]
        delivery_date=payload["delivery_date"],  # type: ignore[arg-type]
        correlation_id=payload["correlation_id"],  # type: ignore[arg-type]
        phase=payload["phase"],  # type: ignore[arg-type]
        status=payload["status"],  # type: ignore[arg-type]
        diagnostics=payload["diagnostics"],  # type: ignore[arg-type]
    )


def _compile(
    *,
    regulatory: _RecordingRegulatoryIntelligenceNode | None = None,
    step: _RecordingParallelIngestionStep | None = None,
    handler: _RecordingParallelIngestionFailureRuntimeHandler | None = None,
    forecasting_step: _RecordingForecastingStep | None = None,
) -> tuple[
    object,
    _RecordingRegulatoryIntelligenceNode,
    _RecordingParallelIngestionStep,
    _RecordingParallelIngestionFailureRuntimeHandler,
    _RecordingForecastingStep,
]:
    injected_regulatory = (
        regulatory if regulatory is not None else _RecordingRegulatoryIntelligenceNode()
    )
    injected_step = step if step is not None else _RecordingParallelIngestionStep()
    injected_handler = (
        handler if handler is not None else _RecordingParallelIngestionFailureRuntimeHandler()
    )
    injected_forecasting = (
        forecasting_step if forecasting_step is not None else _RecordingForecastingStep()
    )
    compiled = build_workflow_graph(
        regulatory_intelligence_node=injected_regulatory,  # type: ignore[arg-type]
        parallel_ingestion_step=injected_step,  # type: ignore[arg-type]
        parallel_ingestion_failure_runtime_handler=injected_handler,  # type: ignore[arg-type]
        forecasting_step=injected_forecasting,  # type: ignore[arg-type]
    )
    return compiled, injected_regulatory, injected_step, injected_handler, injected_forecasting


def test_factory_requires_four_keyword_only_dependencies() -> None:
    regulatory = _RecordingRegulatoryIntelligenceNode()
    step = _RecordingParallelIngestionStep()
    handler = _RecordingParallelIngestionFailureRuntimeHandler()
    forecasting = _RecordingForecastingStep()
    with pytest.raises(TypeError):
        build_workflow_graph()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        build_workflow_graph(  # type: ignore[call-arg]
            parallel_ingestion_step=step,
            parallel_ingestion_failure_runtime_handler=handler,
            forecasting_step=forecasting,
        )
    with pytest.raises(TypeError):
        build_workflow_graph(  # type: ignore[call-arg]
            regulatory_intelligence_node=regulatory,
            parallel_ingestion_failure_runtime_handler=handler,
            forecasting_step=forecasting,
        )
    with pytest.raises(TypeError):
        build_workflow_graph(  # type: ignore[call-arg]
            regulatory_intelligence_node=regulatory,
            parallel_ingestion_step=step,
            forecasting_step=forecasting,
        )
    with pytest.raises(TypeError):
        build_workflow_graph(  # type: ignore[call-arg]
            regulatory_intelligence_node=regulatory,
            parallel_ingestion_step=step,
            parallel_ingestion_failure_runtime_handler=handler,
        )


def test_topology_includes_terminal_regulatory_slice() -> None:
    compiled, _regulatory, _step, _handler, _forecasting = _compile()
    representation = compiled.get_graph()
    application_nodes = {node_id for node_id in representation.nodes if node_id not in {START, END}}
    assert application_nodes == {
        "workflow_entry",
        "regulatory_intelligence",
        "parallel_ingestion",
        "parallel_ingestion_success_transition",
        "forecasting",
    }
    edges = {(edge.source, edge.target) for edge in representation.edges}
    assert edges == {
        (START, "workflow_entry"),
        ("workflow_entry", "regulatory_intelligence"),
        ("workflow_entry", "parallel_ingestion"),
        ("workflow_entry", "forecasting"),
        ("regulatory_intelligence", END),
        ("parallel_ingestion", "parallel_ingestion_success_transition"),
        ("parallel_ingestion", END),
        ("parallel_ingestion_success_transition", END),
        ("forecasting", END),
    }
    conditional = {
        (edge.source, edge.target)
        for edge in representation.edges
        if getattr(edge, "conditional", False)
    }
    assert conditional == {
        ("workflow_entry", "regulatory_intelligence"),
        ("workflow_entry", "parallel_ingestion"),
        ("workflow_entry", "forecasting"),
        ("parallel_ingestion", "parallel_ingestion_success_transition"),
        ("parallel_ingestion", END),
    }


async def test_contract_running_invokes_regulatory_and_terminates() -> None:
    first = diagnostic()
    original = _state(diagnostics=(first,))
    compiled, regulatory, step, handler, forecasting = _compile()
    node_order: list[str] = []
    async for chunk in compiled.astream(original, stream_mode="updates"):
        node_order.extend(chunk.keys())
    reconstructed = _reconstruct(await compiled.ainvoke(original))
    assert node_order == list(_CONTRACT_APPLICATION_NODES)
    assert regulatory.calls == 2
    assert len(regulatory.received) == 2
    received = regulatory.received[0]
    assert received.workflow_id == original.workflow_id
    assert received.portfolio_id == original.portfolio_id
    assert received.delivery_date == original.delivery_date
    assert received.correlation_id == original.correlation_id
    assert received.phase is WorkflowPhase.CONTRACT
    assert received.status is WorkflowStatus.RUNNING
    assert received.diagnostics == (first,)
    assert step.calls == 0
    assert handler.calls == 0
    assert forecasting.calls == 0
    assert reconstructed.phase is WorkflowPhase.CONTRACT
    assert reconstructed.status is WorkflowStatus.RUNNING
    assert reconstructed.workflow_id == original.workflow_id
    assert reconstructed.portfolio_id == original.portfolio_id
    assert reconstructed.delivery_date == original.delivery_date
    assert reconstructed.correlation_id == original.correlation_id
    assert reconstructed.diagnostics == (first,)
    assert original.phase is WorkflowPhase.CONTRACT
    assert original.status is WorkflowStatus.RUNNING
    assert "pricing" not in node_order
    assert "parallel_ingestion" not in node_order
    assert "parallel_ingestion_success_transition" not in node_order
    assert "forecasting" not in node_order


async def test_ingestion_running_preserves_phase2_and_skips_regulatory() -> None:
    original = _state(phase=WorkflowPhase.INGESTION, status=WorkflowStatus.RUNNING)
    compiled, regulatory, step, handler, forecasting = _compile()
    node_order: list[str] = []
    async for chunk in compiled.astream(original, stream_mode="updates"):
        node_order.extend(chunk.keys())
    reconstructed = _reconstruct(await compiled.ainvoke(original))
    assert node_order == list(_PHASE2_APPLICATION_NODES)
    assert regulatory.calls == 0
    assert step.calls == 2
    assert handler.calls == 0
    assert forecasting.calls == 0
    assert step.received[0].phase is WorkflowPhase.INGESTION
    assert step.received[0].status is WorkflowStatus.RUNNING
    assert reconstructed.phase is WorkflowPhase.FORECASTING
    assert reconstructed.status is WorkflowStatus.RUNNING
    assert reconstructed.workflow_id == original.workflow_id
    assert original.phase is WorkflowPhase.INGESTION
    assert original.status is WorkflowStatus.RUNNING
    assert "forecasting" not in node_order
    assert "regulatory_intelligence" not in node_order


@pytest.mark.parametrize(
    ("phase", "status"),
    [
        (WorkflowPhase.CONTRACT, WorkflowStatus.PENDING),
        (WorkflowPhase.CONTRACT, WorkflowStatus.FAILED),
        (WorkflowPhase.RISK_AND_BID, WorkflowStatus.RUNNING),
    ],
)
async def test_invalid_entry_routes_fail_closed_without_executing(
    phase: WorkflowPhase,
    status: WorkflowStatus,
) -> None:
    original = _state(phase=phase, status=status)
    compiled, regulatory, step, handler, forecasting = _compile()
    node_order: list[str] = []
    with pytest.raises(InvalidRequestError) as captured:
        async for chunk in compiled.astream(original, stream_mode="updates"):
            node_order.extend(chunk.keys())
    assert captured.value.code == "invalid_request"
    assert captured.value.message == _INVALID_ENTRY_ROUTE_MESSAGE
    assert regulatory.calls == 0
    assert step.calls == 0
    assert handler.calls == 0
    assert forecasting.calls == 0
    assert "regulatory_intelligence" not in node_order
    assert "parallel_ingestion" not in node_order
    assert "forecasting" not in node_order
    assert original.phase is phase
    assert original.status is status


async def test_forecasting_running_skips_regulatory_and_phase2() -> None:
    original = _state(phase=WorkflowPhase.FORECASTING, status=WorkflowStatus.RUNNING)
    compiled, regulatory, step, handler, forecasting = _compile()
    node_order: list[str] = []
    async for chunk in compiled.astream(original, stream_mode="updates"):
        node_order.extend(chunk.keys())
    reconstructed = _reconstruct(await compiled.ainvoke(original))
    assert node_order == list(_PHASE3_APPLICATION_NODES)
    assert regulatory.calls == 0
    assert step.calls == 0
    assert handler.calls == 0
    assert forecasting.calls == 2
    assert reconstructed.phase is WorkflowPhase.FORECASTING
    assert reconstructed.status is WorkflowStatus.RUNNING
    assert original.phase is WorkflowPhase.FORECASTING
    assert original.status is WorkflowStatus.RUNNING
    assert "regulatory_intelligence" not in node_order
    assert "parallel_ingestion" not in node_order


async def test_regulatory_failure_propagates_without_phase2_or_retry() -> None:
    error = DependencyUnavailableError("regulatory node unavailable")
    regulatory = _RecordingRegulatoryIntelligenceNode(error=error)
    compiled, injected, step, handler, forecasting = _compile(regulatory=regulatory)
    original = _state()
    with pytest.raises(DependencyUnavailableError) as captured:
        await compiled.ainvoke(original)
    assert captured.value is error
    assert injected is regulatory
    assert regulatory.calls == 1
    assert step.calls == 0
    assert handler.calls == 0
    assert forecasting.calls == 0
    assert original.phase is WorkflowPhase.CONTRACT
    assert original.status is WorkflowStatus.RUNNING
