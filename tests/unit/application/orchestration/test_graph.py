"""LangGraph runtime over application-owned WorkflowState."""

from __future__ import annotations

from datetime import date
from importlib.metadata import version

import pytest
from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph

from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.application.orchestration import (
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
    build_workflow_graph,
)
from energy_trading.domain.models.ingestion import AdapterDiagnostic, DiagnosticSeverity
from tests.unit.domain._factories import diagnostic

_FORBIDDEN_BUSINESS_NODES = frozenset(
    {
        "contract",
        "regulatory",
        "pricing",
        "ingestion",
        "weather",
        "hydro",
        "generation",
        "news",
        "market",
        "forecasting",
        "load_forecast",
        "price_forecast",
        "risk",
        "trading",
        "bid",
        "settlement",
        "chief_orchestrator",
    }
)

_APPLICATION_NODES = (
    "workflow_entry",
    "parallel_ingestion",
    "parallel_ingestion_success_transition",
)


class _RecordingParallelIngestionStep:
    """Test-only stand-in for the injected Phase 2 workflow step."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls = 0
        self.received: list[WorkflowState] = []

    async def run(self, state: WorkflowState) -> WorkflowState:
        self.calls += 1
        self.received.append(state)
        if self.error is not None:
            raise self.error
        return state


def _parse_version(value: str) -> tuple[int, ...]:
    numeric: list[int] = []
    for part in value.split("."):
        digits = ""
        for char in part:
            if char.isdigit():
                digits += char
            else:
                break
        if digits:
            numeric.append(int(digits))
    return tuple(numeric)


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
    step: _RecordingParallelIngestionStep | None = None,
) -> tuple[
    CompiledStateGraph[WorkflowState, None, WorkflowState, WorkflowState],
    _RecordingParallelIngestionStep,
]:
    injected = step if step is not None else _RecordingParallelIngestionStep()
    compiled = build_workflow_graph(parallel_ingestion_step=injected)
    return compiled, injected


def test_installed_langgraph_satisfies_project_constraint() -> None:
    installed = version("langgraph")
    parsed = _parse_version(installed)
    assert parsed >= (1, 2, 11)
    assert parsed < (1, 3)
    assert installed.startswith("1.2.")


def test_build_workflow_graph_requires_parallel_ingestion_step() -> None:
    with pytest.raises(TypeError):
        build_workflow_graph()  # type: ignore[call-arg]


def test_build_workflow_graph_returns_compiled_langgraph() -> None:
    compiled, _step = _compile()
    assert isinstance(compiled, CompiledStateGraph)


def test_repeated_factory_calls_create_independent_graphs() -> None:
    first, _first_step = _compile()
    second, _second_step = _compile()
    assert first is not second
    assert type(first) is type(second)


def test_builder_uses_workflow_state_as_schema() -> None:
    compiled, _step = _compile()
    assert compiled.builder.state_schema is WorkflowState


def test_graph_contains_workflow_entry_parallel_ingestion_and_transition_nodes() -> None:
    compiled, _step = _compile()
    representation = compiled.get_graph()
    application_nodes = {node_id for node_id in representation.nodes if node_id not in {START, END}}
    assert application_nodes == set(_APPLICATION_NODES)


def test_topology_is_start_entry_ingestion_transition_end() -> None:
    compiled, _step = _compile()
    representation = compiled.get_graph()
    assert set(representation.nodes) == {START, *_APPLICATION_NODES, END}
    edges = {(edge.source, edge.target) for edge in representation.edges}
    assert edges == {
        (START, "workflow_entry"),
        ("workflow_entry", "parallel_ingestion"),
        ("parallel_ingestion", "parallel_ingestion_success_transition"),
        ("parallel_ingestion_success_transition", END),
    }


def test_graph_has_no_phase_specific_nodes() -> None:
    compiled, _step = _compile()
    node_ids = set(compiled.get_graph().nodes)
    leaked = sorted(node_ids & _FORBIDDEN_BUSINESS_NODES)
    assert leaked == []


def test_graph_has_no_conditional_branches() -> None:
    compiled, _step = _compile()
    representation = compiled.get_graph()
    assert len(representation.edges) == 4
    conditional = [
        edge
        for edge in representation.edges
        if getattr(edge, "conditional", False) or getattr(edge, "data", None) is not None
    ]
    assert conditional == []


async def test_ainvoke_successful_path_ends_forecasting_running() -> None:
    first = diagnostic()
    second = AdapterDiagnostic(
        code="SCHEMA_AMBIGUOUS",
        message="header mapping was ambiguous",
        severity=DiagnosticSeverity.WARNING,
        field_name="timestamp",
    )
    original = _state(diagnostics=(first, second))
    compiled, step = _compile()
    result = await compiled.ainvoke(original)
    reconstructed = _reconstruct(result)
    assert step.calls == 1
    assert len(step.received) == 1
    received = step.received[0]
    assert received.phase is WorkflowPhase.INGESTION
    assert received.status is WorkflowStatus.RUNNING
    assert received.workflow_id == original.workflow_id
    assert received.portfolio_id == original.portfolio_id
    assert received.delivery_date == original.delivery_date
    assert received.correlation_id == original.correlation_id
    assert received.diagnostics == (first, second)
    assert reconstructed.phase is WorkflowPhase.FORECASTING
    assert reconstructed.status is WorkflowStatus.RUNNING
    assert reconstructed.workflow_id == original.workflow_id
    assert reconstructed.portfolio_id == original.portfolio_id
    assert reconstructed.delivery_date == original.delivery_date
    assert reconstructed.correlation_id == original.correlation_id
    assert reconstructed.diagnostics == (first, second)
    assert original.phase is WorkflowPhase.INGESTION
    assert original.status is WorkflowStatus.RUNNING
    assert original.diagnostics == (first, second)


async def test_ainvoke_does_not_mutate_original_frozen_state() -> None:
    original = _state()
    compiled, _step = _compile()
    await compiled.ainvoke(original)
    assert original.phase is WorkflowPhase.INGESTION
    assert original.status is WorkflowStatus.RUNNING
    assert original.diagnostics == ()
    assert original.workflow_id == "workflow-1"


async def test_astream_runs_entry_then_ingestion_then_transition() -> None:
    original = _state()
    compiled, step = _compile()
    node_order: list[str] = []
    async for chunk in compiled.astream(original, stream_mode="updates"):
        node_order.extend(chunk.keys())
    assert node_order == list(_APPLICATION_NODES)
    assert step.calls == 1
    assert step.received[0].phase is WorkflowPhase.INGESTION
    assert step.received[0].status is WorkflowStatus.RUNNING


async def test_step_failure_propagates_from_ainvoke_without_retry() -> None:
    error = DependencyUnavailableError("phase 2 step unavailable")
    step = _RecordingParallelIngestionStep(error=error)
    compiled, _injected = _compile(step)
    original = _state()
    with pytest.raises(DependencyUnavailableError) as captured:
        await compiled.ainvoke(original)
    assert captured.value is error
    assert step.calls == 1
    assert original.phase is WorkflowPhase.INGESTION
    assert original.status is WorkflowStatus.RUNNING
    assert original.diagnostics == ()


async def test_step_failure_skips_transition_and_propagates_without_retry() -> None:
    error = DependencyUnavailableError("phase 2 step unavailable")
    step = _RecordingParallelIngestionStep(error=error)
    compiled, _injected = _compile(step)
    original = _state()
    node_order: list[str] = []
    with pytest.raises(DependencyUnavailableError) as captured:
        async for chunk in compiled.astream(original, stream_mode="updates"):
            node_order.extend(chunk.keys())
    assert captured.value is error
    assert step.calls == 1
    assert "parallel_ingestion_success_transition" not in node_order
    assert node_order == ["workflow_entry"]
    assert original.phase is WorkflowPhase.INGESTION
    assert original.status is WorkflowStatus.RUNNING
    assert original.diagnostics == ()


async def test_invalid_transition_precondition_propagates_unchanged() -> None:
    original = _state(phase=WorkflowPhase.CONTRACT, status=WorkflowStatus.PENDING)
    compiled, step = _compile()
    with pytest.raises(InvalidRequestError) as captured:
        await compiled.ainvoke(original)
    assert captured.value.code == "invalid_request"
    assert (
        captured.value.message
        == "Parallel-ingestion success transition requires ingestion phase and running status."
    )
    assert step.calls == 1
    assert step.received[0].phase is WorkflowPhase.CONTRACT
    assert step.received[0].status is WorkflowStatus.PENDING
    assert original.phase is WorkflowPhase.CONTRACT
    assert original.status is WorkflowStatus.PENDING
