"""LangGraph runtime over application-owned WorkflowState."""

from __future__ import annotations

from datetime import date
from importlib.metadata import version

import pytest
from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph

from energy_trading.application.agents import AgentName
from energy_trading.application.errors import DependencyUnavailableError, InvalidRequestError
from energy_trading.application.orchestration import (
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

_UNATTRIBUTED_FAILURE_MESSAGE = "Parallel-ingestion failure group contains an unattributed failure."
_EXACTLY_ONE_FACT_MESSAGE = (
    "Parallel-ingestion failure selection requires exactly one failure fact."
)
_INVALID_POST_PHASE2_ROUTE_MESSAGE = (
    "Parallel-ingestion routing requires ingestion phase and running or failed status."
)
_SENTINEL_TEXT = "secret provider payload not for clients"


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

    def __init__(
        self,
        result: WorkflowState | None = None,
        error: BaseException | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls = 0
        self.received_state: list[WorkflowState] = []
        self.received_failure_group: list[BaseExceptionGroup] = []

    async def handle(
        self,
        *,
        state: WorkflowState,
        failure_group: BaseExceptionGroup,
    ) -> WorkflowState:
        self.calls += 1
        self.received_state.append(state)
        self.received_failure_group.append(failure_group)
        if self._error is not None:
            raise self._error
        if self._result is None:
            msg = "recording failure-runtime handler requires a result or an error"
            raise AssertionError(msg)
        return self._result


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


def _chained_failure(
    agent_name: AgentName,
    cause: BaseException,
) -> ParallelIngestionAgentFailure:
    try:
        raise ParallelIngestionAgentFailure(agent_name) from cause
    except ParallelIngestionAgentFailure as exc:
        return exc


def _real_runtime_handler() -> ParallelIngestionFailureRuntimeHandlingService:
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


def _compile(
    step: _RecordingParallelIngestionStep | None = None,
    handler: (
        _RecordingParallelIngestionFailureRuntimeHandler
        | ParallelIngestionFailureRuntimeHandlingService
        | None
    ) = None,
) -> tuple[
    CompiledStateGraph[WorkflowState, None, WorkflowState, WorkflowState],
    _RecordingParallelIngestionStep,
    _RecordingParallelIngestionFailureRuntimeHandler
    | ParallelIngestionFailureRuntimeHandlingService,
]:
    injected_step = step if step is not None else _RecordingParallelIngestionStep()
    injected_handler: (
        _RecordingParallelIngestionFailureRuntimeHandler
        | ParallelIngestionFailureRuntimeHandlingService
    ) = handler if handler is not None else _RecordingParallelIngestionFailureRuntimeHandler()
    compiled = build_workflow_graph(
        parallel_ingestion_step=injected_step,
        parallel_ingestion_failure_runtime_handler=injected_handler,
    )
    return compiled, injected_step, injected_handler


def test_installed_langgraph_satisfies_project_constraint() -> None:
    installed = version("langgraph")
    parsed = _parse_version(installed)
    assert parsed >= (1, 2, 11)
    assert parsed < (1, 3)
    assert installed.startswith("1.2.")


def test_build_workflow_graph_requires_both_keyword_only_dependencies() -> None:
    step = _RecordingParallelIngestionStep()
    handler = _RecordingParallelIngestionFailureRuntimeHandler()
    with pytest.raises(TypeError):
        build_workflow_graph()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        build_workflow_graph(parallel_ingestion_step=step)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        build_workflow_graph(parallel_ingestion_failure_runtime_handler=handler)  # type: ignore[call-arg]


def test_build_workflow_graph_returns_compiled_langgraph() -> None:
    compiled, _step, _handler = _compile()
    assert isinstance(compiled, CompiledStateGraph)


def test_repeated_factory_calls_create_independent_graphs() -> None:
    first, _first_step, _first_handler = _compile()
    second, _second_step, _second_handler = _compile()
    assert first is not second
    assert type(first) is type(second)


def test_builder_uses_workflow_state_as_schema() -> None:
    compiled, _step, _handler = _compile()
    assert compiled.builder.state_schema is WorkflowState


def test_graph_contains_workflow_entry_parallel_ingestion_and_transition_nodes() -> None:
    compiled, _step, _handler = _compile()
    representation = compiled.get_graph()
    application_nodes = {node_id for node_id in representation.nodes if node_id not in {START, END}}
    assert application_nodes == set(_APPLICATION_NODES)


def test_topology_routes_success_to_transition_and_failure_to_end() -> None:
    compiled, _step, _handler = _compile()
    representation = compiled.get_graph()
    assert set(representation.nodes) == {START, *_APPLICATION_NODES, END}
    edges = {(edge.source, edge.target) for edge in representation.edges}
    assert edges == {
        (START, "workflow_entry"),
        ("workflow_entry", "parallel_ingestion"),
        ("parallel_ingestion", "parallel_ingestion_success_transition"),
        ("parallel_ingestion", END),
        ("parallel_ingestion_success_transition", END),
    }
    conditional = {
        (edge.source, edge.target)
        for edge in representation.edges
        if getattr(edge, "conditional", False)
    }
    assert conditional == {
        ("parallel_ingestion", "parallel_ingestion_success_transition"),
        ("parallel_ingestion", END),
    }


def test_graph_has_no_phase_specific_nodes() -> None:
    compiled, _step, _handler = _compile()
    node_ids = set(compiled.get_graph().nodes)
    leaked = sorted(node_ids & _FORBIDDEN_BUSINESS_NODES)
    assert leaked == []


def test_graph_has_exactly_one_phase2_conditional_routing_seam() -> None:
    compiled, _step, _handler = _compile()
    representation = compiled.get_graph()
    conditional = [
        edge
        for edge in representation.edges
        if getattr(edge, "conditional", False) or getattr(edge, "data", None) is not None
    ]
    sources = {edge.source for edge in conditional}
    assert sources == {"parallel_ingestion"}
    destinations = {edge.target for edge in conditional}
    assert destinations == {"parallel_ingestion_success_transition", END}


async def test_ainvoke_successful_path_ends_forecasting_running() -> None:
    first = diagnostic()
    second = AdapterDiagnostic(
        code="SCHEMA_AMBIGUOUS",
        message="header mapping was ambiguous",
        severity=DiagnosticSeverity.WARNING,
        field_name="timestamp",
    )
    original = _state(diagnostics=(first, second))
    compiled, step, handler = _compile()
    result = await compiled.ainvoke(original)
    reconstructed = _reconstruct(result)
    assert step.calls == 1
    assert len(step.received) == 1
    assert isinstance(handler, _RecordingParallelIngestionFailureRuntimeHandler)
    assert handler.calls == 0
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
    compiled, _step, _handler = _compile()
    await compiled.ainvoke(original)
    assert original.phase is WorkflowPhase.INGESTION
    assert original.status is WorkflowStatus.RUNNING
    assert original.diagnostics == ()
    assert original.workflow_id == "workflow-1"


async def test_astream_runs_entry_then_ingestion_then_transition() -> None:
    original = _state()
    compiled, step, handler = _compile()
    node_order: list[str] = []
    async for chunk in compiled.astream(original, stream_mode="updates"):
        node_order.extend(chunk.keys())
    assert node_order == list(_APPLICATION_NODES)
    assert step.calls == 1
    assert isinstance(handler, _RecordingParallelIngestionFailureRuntimeHandler)
    assert handler.calls == 0
    assert step.received[0].phase is WorkflowPhase.INGESTION
    assert step.received[0].status is WorkflowStatus.RUNNING


async def test_step_failure_propagates_from_ainvoke_without_retry() -> None:
    error = DependencyUnavailableError("phase 2 step unavailable")
    step = _RecordingParallelIngestionStep(error=error)
    compiled, _injected, handler = _compile(step)
    original = _state()
    with pytest.raises(DependencyUnavailableError) as captured:
        await compiled.ainvoke(original)
    assert captured.value is error
    assert step.calls == 1
    assert isinstance(handler, _RecordingParallelIngestionFailureRuntimeHandler)
    assert handler.calls == 0
    assert original.phase is WorkflowPhase.INGESTION
    assert original.status is WorkflowStatus.RUNNING
    assert original.diagnostics == ()


async def test_step_failure_skips_transition_and_propagates_without_retry() -> None:
    error = DependencyUnavailableError("phase 2 step unavailable")
    step = _RecordingParallelIngestionStep(error=error)
    compiled, _injected, handler = _compile(step)
    original = _state()
    node_order: list[str] = []
    with pytest.raises(DependencyUnavailableError) as captured:
        async for chunk in compiled.astream(original, stream_mode="updates"):
            node_order.extend(chunk.keys())
    assert captured.value is error
    assert step.calls == 1
    assert isinstance(handler, _RecordingParallelIngestionFailureRuntimeHandler)
    assert handler.calls == 0
    assert "parallel_ingestion_success_transition" not in node_order
    assert node_order == ["workflow_entry"]
    assert original.phase is WorkflowPhase.INGESTION
    assert original.status is WorkflowStatus.RUNNING
    assert original.diagnostics == ()


async def test_non_group_invalid_request_propagates_without_runtime_handler() -> None:
    error = InvalidRequestError("phase 2 request is invalid")
    step = _RecordingParallelIngestionStep(error=error)
    compiled, _injected, handler = _compile(step)
    original = _state()
    with pytest.raises(InvalidRequestError) as captured:
        await compiled.ainvoke(original)
    assert captured.value is error
    assert step.calls == 1
    assert isinstance(handler, _RecordingParallelIngestionFailureRuntimeHandler)
    assert handler.calls == 0
    assert original.status is WorkflowStatus.RUNNING


async def test_exception_group_is_delegated_to_runtime_handler_and_skips_success() -> None:
    first = diagnostic()
    original = _state(
        workflow_id="wf-group",
        portfolio_id="portfolio-group",
        delivery_date=date(2026, 9, 8),
        correlation_id="corr-group",
        diagnostics=(first,),
    )
    group = ExceptionGroup("phase 2 failed", [RuntimeError("leaf")])
    step = _RecordingParallelIngestionStep(error=group)
    failed = _state(
        workflow_id="wf-group",
        portfolio_id="portfolio-group",
        delivery_date=date(2026, 9, 8),
        correlation_id="corr-group",
        phase=WorkflowPhase.INGESTION,
        status=WorkflowStatus.FAILED,
        diagnostics=(first,),
    )
    handler = _RecordingParallelIngestionFailureRuntimeHandler(result=failed)
    compiled, _injected, injected_handler = _compile(step, handler)
    node_order: list[str] = []
    result = None
    async for chunk in compiled.astream(original, stream_mode="updates"):
        node_order.extend(chunk.keys())
        result = chunk
    reconstructed = _reconstruct(await compiled.ainvoke(original))
    assert step.calls == 2
    assert injected_handler is handler
    assert handler.calls == 2
    assert handler.received_failure_group[0] is group
    assert handler.received_failure_group[1] is group
    assert handler.received_state[0] is step.received[0]
    assert handler.received_state[0].workflow_id == original.workflow_id
    assert handler.received_state[0].portfolio_id == original.portfolio_id
    assert handler.received_state[0].delivery_date == original.delivery_date
    assert handler.received_state[0].correlation_id == original.correlation_id
    assert handler.received_state[0].diagnostics == (first,)
    assert handler.received_state[0].phase is WorkflowPhase.INGESTION
    assert handler.received_state[0].status is WorkflowStatus.RUNNING
    assert "parallel_ingestion_success_transition" not in node_order
    assert node_order == ["workflow_entry", "parallel_ingestion"]
    assert reconstructed.phase is WorkflowPhase.INGESTION
    assert reconstructed.status is WorkflowStatus.FAILED
    assert reconstructed.workflow_id == "wf-group"
    assert reconstructed.portfolio_id == "portfolio-group"
    assert reconstructed.delivery_date == date(2026, 9, 8)
    assert reconstructed.correlation_id == "corr-group"
    assert reconstructed.diagnostics == (first,)
    assert reconstructed.diagnostics[0] is first
    assert original.phase is WorkflowPhase.INGESTION
    assert original.status is WorkflowStatus.RUNNING
    assert result is not None


async def test_real_single_attributed_failure_ends_ingestion_failed() -> None:
    first = diagnostic()
    second = AdapterDiagnostic(
        code="SCHEMA_AMBIGUOUS",
        message="header mapping was ambiguous",
        severity=DiagnosticSeverity.WARNING,
        field_name="timestamp",
    )
    original = _state(diagnostics=(first, second))
    leaf = _chained_failure(
        AgentName.MARKET_MONITORING,
        InvalidRequestError("market request is invalid"),
    )
    group = ExceptionGroup("phase 2 failed", [leaf])
    step = _RecordingParallelIngestionStep(error=group)
    compiled, _injected, _handler = _compile(step, _real_runtime_handler())
    node_order: list[str] = []
    async for chunk in compiled.astream(original, stream_mode="updates"):
        node_order.extend(chunk.keys())
    reconstructed = _reconstruct(await compiled.ainvoke(original))
    assert step.calls == 2
    assert "parallel_ingestion_success_transition" not in node_order
    assert node_order == ["workflow_entry", "parallel_ingestion"]
    assert reconstructed.phase is WorkflowPhase.INGESTION
    assert reconstructed.status is WorkflowStatus.FAILED
    assert reconstructed.workflow_id == original.workflow_id
    assert reconstructed.portfolio_id == original.portfolio_id
    assert reconstructed.delivery_date == original.delivery_date
    assert reconstructed.correlation_id == original.correlation_id
    assert reconstructed.diagnostics == (first, second)
    assert reconstructed.diagnostics[0] is first
    assert reconstructed.diagnostics[1] is second
    assert original.status is WorkflowStatus.RUNNING


async def test_multiple_attributed_failures_fail_closed_without_success_transition() -> None:
    original = _state()
    weather = _chained_failure(
        AgentName.WEATHER_AND_RENEWABLE_FORECAST,
        InvalidRequestError("weather request is invalid"),
    )
    hydro = _chained_failure(
        AgentName.HYDRO_RESOURCES,
        DependencyUnavailableError("hydro source unavailable"),
    )
    group = ExceptionGroup("phase 2 failed", [weather, hydro])
    step = _RecordingParallelIngestionStep(error=group)
    compiled, _injected, _handler = _compile(step, _real_runtime_handler())
    node_order: list[str] = []
    with pytest.raises(InvalidRequestError) as captured:
        async for chunk in compiled.astream(original, stream_mode="updates"):
            node_order.extend(chunk.keys())
    assert captured.value.code == "invalid_request"
    assert captured.value.message == _EXACTLY_ONE_FACT_MESSAGE
    assert "first" not in captured.value.message.lower()
    assert "last" not in captured.value.message.lower()
    assert "winner" not in captured.value.message.lower()
    assert "priority" not in captured.value.message.lower()
    assert "parallel_ingestion_success_transition" not in node_order
    assert original.status is WorkflowStatus.RUNNING


async def test_unattributed_group_fails_closed_without_success_transition() -> None:
    original = _state()
    attributed = _chained_failure(
        AgentName.MARKET_MONITORING,
        InvalidRequestError("market request is invalid"),
    )
    group = ExceptionGroup(
        "phase 2 failed",
        [attributed, RuntimeError(_SENTINEL_TEXT)],
    )
    step = _RecordingParallelIngestionStep(error=group)
    compiled, _injected, _handler = _compile(step, _real_runtime_handler())
    node_order: list[str] = []
    with pytest.raises(InvalidRequestError) as captured:
        async for chunk in compiled.astream(original, stream_mode="updates"):
            node_order.extend(chunk.keys())
    assert captured.value.message == _UNATTRIBUTED_FAILURE_MESSAGE
    assert _SENTINEL_TEXT not in str(captured.value)
    assert "RuntimeError" not in str(captured.value)
    assert "parallel_ingestion_success_transition" not in node_order
    assert original.status is WorkflowStatus.RUNNING


async def test_unexpected_post_phase2_state_fails_closed_without_success_or_failure_route() -> None:
    original = _state(phase=WorkflowPhase.CONTRACT, status=WorkflowStatus.PENDING)
    compiled, step, handler = _compile()
    node_order: list[str] = []
    with pytest.raises(InvalidRequestError) as captured:
        async for chunk in compiled.astream(original, stream_mode="updates"):
            node_order.extend(chunk.keys())
    assert captured.value.code == "invalid_request"
    assert captured.value.message == _INVALID_POST_PHASE2_ROUTE_MESSAGE
    assert step.calls == 1
    assert isinstance(handler, _RecordingParallelIngestionFailureRuntimeHandler)
    assert handler.calls == 0
    assert "parallel_ingestion_success_transition" not in node_order
    assert original.phase is WorkflowPhase.CONTRACT
    assert original.status is WorkflowStatus.PENDING
