"""Minimal LangGraph skeleton over application-owned WorkflowState."""

from __future__ import annotations

from datetime import date
from importlib.metadata import version

from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph

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
        "phase": WorkflowPhase.CONTRACT,
        "status": WorkflowStatus.PENDING,
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


def test_installed_langgraph_satisfies_project_constraint() -> None:
    installed = version("langgraph")
    parsed = _parse_version(installed)
    assert parsed >= (1, 2, 11)
    assert parsed < (1, 3)
    assert installed.startswith("1.2.")


def test_build_workflow_graph_returns_compiled_langgraph() -> None:
    compiled = build_workflow_graph()
    assert isinstance(compiled, CompiledStateGraph)


def test_repeated_factory_calls_create_independent_graphs() -> None:
    first = build_workflow_graph()
    second = build_workflow_graph()
    assert first is not second
    assert type(first) is type(second)


def test_builder_uses_workflow_state_as_schema() -> None:
    compiled = build_workflow_graph()
    assert compiled.builder.state_schema is WorkflowState


def test_graph_contains_exactly_one_application_node() -> None:
    compiled = build_workflow_graph()
    representation = compiled.get_graph()
    application_nodes = {node_id for node_id in representation.nodes if node_id not in {START, END}}
    assert application_nodes == {"workflow_entry"}


def test_topology_is_start_to_workflow_entry_to_end() -> None:
    compiled = build_workflow_graph()
    representation = compiled.get_graph()
    assert set(representation.nodes) == {START, "workflow_entry", END}
    edges = {(edge.source, edge.target) for edge in representation.edges}
    assert edges == {(START, "workflow_entry"), ("workflow_entry", END)}


def test_graph_has_no_phase_specific_nodes() -> None:
    compiled = build_workflow_graph()
    node_ids = set(compiled.get_graph().nodes)
    leaked = sorted(node_ids & _FORBIDDEN_BUSINESS_NODES)
    assert leaked == []


def test_graph_has_no_conditional_branches() -> None:
    compiled = build_workflow_graph()
    representation = compiled.get_graph()
    assert len(representation.edges) == 2
    conditional = [
        edge
        for edge in representation.edges
        if getattr(edge, "conditional", False) or getattr(edge, "data", None) is not None
    ]
    assert conditional == []


async def test_ainvoke_preserves_all_workflow_state_fields() -> None:
    original = _state()
    original_values = (
        original.workflow_id,
        original.portfolio_id,
        original.delivery_date,
        original.correlation_id,
        original.phase,
        original.status,
        original.diagnostics,
    )
    compiled = build_workflow_graph()
    result = await compiled.ainvoke(original)
    reconstructed = _reconstruct(result)
    assert reconstructed == original
    assert original_values == (
        original.workflow_id,
        original.portfolio_id,
        original.delivery_date,
        original.correlation_id,
        original.phase,
        original.status,
        original.diagnostics,
    )
    assert original.phase is WorkflowPhase.CONTRACT
    assert original.status is WorkflowStatus.PENDING


async def test_ainvoke_does_not_mutate_original_frozen_state() -> None:
    original = _state()
    compiled = build_workflow_graph()
    await compiled.ainvoke(original)
    assert original.phase is WorkflowPhase.CONTRACT
    assert original.status is WorkflowStatus.PENDING
    assert original.diagnostics == ()
    assert original.workflow_id == "workflow-1"


async def test_ainvoke_preserves_canonical_diagnostics() -> None:
    first = diagnostic()
    second = AdapterDiagnostic(
        code="SCHEMA_AMBIGUOUS",
        message="header mapping was ambiguous",
        severity=DiagnosticSeverity.WARNING,
        field_name="timestamp",
    )
    original = _state(diagnostics=(first, second))
    compiled = build_workflow_graph()
    result = await compiled.ainvoke(original)
    reconstructed = _reconstruct(result)
    assert reconstructed.diagnostics == (first, second)
    assert original.diagnostics == (first, second)
    assert reconstructed.phase is original.phase
    assert reconstructed.status is original.status


async def test_noop_graph_does_not_change_phase_status_or_diagnostics() -> None:
    original = _state(
        phase=WorkflowPhase.FORECASTING,
        status=WorkflowStatus.RUNNING,
        diagnostics=(diagnostic(),),
    )
    compiled = build_workflow_graph()
    result = await compiled.ainvoke(original)
    reconstructed = _reconstruct(result)
    assert reconstructed.phase is WorkflowPhase.FORECASTING
    assert reconstructed.status is WorkflowStatus.RUNNING
    assert reconstructed.diagnostics == original.diagnostics
    assert reconstructed.workflow_id == original.workflow_id
    assert reconstructed.portfolio_id == original.portfolio_id
    assert reconstructed.delivery_date == original.delivery_date
    assert reconstructed.correlation_id == original.correlation_id
