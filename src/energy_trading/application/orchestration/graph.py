"""LangGraph runtime over application-owned workflow state.

This module compiles the current executable graph. It consumes the
already-published ``WorkflowState`` contract, routes a
contract/running snapshot to the injected Regulatory node adapter,
delegates Phase 2 ingestion to an injected
``ParallelIngestionWorkflowStep``, and delegates Phase 3 forecasting
to an injected ``ForecastingWorkflowStep``. After Phase 2 it either
applies the published successful control-state transition or
delegates a caught ``BaseExceptionGroup`` to the injected
``ParallelIngestionFailureRuntimeHandlingService``.

Ownership:

* Application orchestration: owns graph construction.
* Chunk 27 ``WorkflowState``: remains the authoritative state schema.
* Chunk 116 ``RegulatoryIntelligenceWorkflowNodeAdapter``: owns
  resolve → step → record. The graph does not reconstruct that
  sequence and does not import context or step internals.
* Chunk 40 ``ParallelIngestionWorkflowStep``: owns resolve → execute →
  record. The graph does not reconstruct that sequence.
* Chunk 42 ``advance_after_parallel_ingestion``: owns the
  ingestion/running → forecasting/running replacement. The graph does
  not reimplement that policy.
* Chunk 61 ``ParallelIngestionFailureRuntimeHandlingService``: owns
  ExceptionGroup preparation through terminal FAIL. The graph does not
  reconstruct that pipeline.
* Chunk 126 ``ForecastingWorkflowStep``: owns resolve → execute →
  record. The graph does not reconstruct that sequence and does not
  choose forecasting execution order.

The topology is ``START → workflow_entry``, then conditional routing:

* contract/running → ``regulatory_intelligence`` → ``END``
* ingestion/running → ``parallel_ingestion``, then
  ingestion/running → ``parallel_ingestion_success_transition`` → ``END``
  or ingestion/failed → ``END``
* forecasting/running → ``forecasting`` → ``END``

``workflow_entry`` remains an async no-op. There is no Pricing & Sales
node, no contract-to-ingestion phase transition, no persistence, retry,
fallback, or Phase-3 success-transition wiring in this module.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration.forecasting_workflow import (
    ForecastingWorkflowStep,
)
from energy_trading.application.orchestration.parallel_ingestion_failure_runtime_handling import (
    ParallelIngestionFailureRuntimeHandlingService,
)
from energy_trading.application.orchestration.parallel_ingestion_transition import (
    advance_after_parallel_ingestion,
)
from energy_trading.application.orchestration.parallel_ingestion_workflow import (
    ParallelIngestionWorkflowStep,
)
from energy_trading.application.orchestration.regulatory_intelligence_workflow_node import (
    RegulatoryIntelligenceWorkflowNodeAdapter,
)
from energy_trading.application.orchestration.state import (
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)

_WORKFLOW_ENTRY_NODE = "workflow_entry"
_REGULATORY_INTELLIGENCE_NODE = "regulatory_intelligence"
_PARALLEL_INGESTION_NODE = "parallel_ingestion"
_PARALLEL_INGESTION_SUCCESS_TRANSITION_NODE = "parallel_ingestion_success_transition"
_FORECASTING_NODE = "forecasting"
_INVALID_ENTRY_ROUTE_MESSAGE = (
    "Workflow entry routing requires contract running, ingestion running, "
    "or forecasting running status."
)
_INVALID_POST_PHASE2_ROUTE_MESSAGE = (
    "Parallel-ingestion routing requires ingestion phase and running or failed status."
)


async def _workflow_entry(_state: WorkflowState) -> dict[str, object]:
    """Internal no-op boundary node.

    Accepts the current ``WorkflowState`` and returns an empty LangGraph
    state update. The update changes no application state. The node performs
    no I/O and does not call agents, use cases, or infrastructure.
    """

    return {}


async def _parallel_ingestion_success_transition(state: WorkflowState) -> WorkflowState:
    """Thin node that applies the published Phase 2 success transition."""

    return advance_after_parallel_ingestion(state)


def _route_after_workflow_entry(state: WorkflowState) -> str:
    """Return the contract-phase, Phase 2, or Phase 3 destination.

    Valid only for ``contract`` / ``running``, ``ingestion`` / ``running``,
    and ``forecasting`` / ``running``. Any other phase/status combination
    fails closed.
    """

    if state.phase is WorkflowPhase.CONTRACT and state.status is WorkflowStatus.RUNNING:
        return _REGULATORY_INTELLIGENCE_NODE
    if state.phase is WorkflowPhase.INGESTION and state.status is WorkflowStatus.RUNNING:
        return _PARALLEL_INGESTION_NODE
    if state.phase is WorkflowPhase.FORECASTING and state.status is WorkflowStatus.RUNNING:
        return _FORECASTING_NODE
    raise InvalidRequestError(_INVALID_ENTRY_ROUTE_MESSAGE)


def _route_after_parallel_ingestion(state: WorkflowState) -> str:
    """Return the Phase 2 success or terminal-failure destination.

    Valid only for ``ingestion`` / ``running`` and ``ingestion`` / ``failed``.
    Any other phase/status combination fails closed.
    """

    if state.phase is WorkflowPhase.INGESTION and state.status is WorkflowStatus.RUNNING:
        return _PARALLEL_INGESTION_SUCCESS_TRANSITION_NODE
    if state.phase is WorkflowPhase.INGESTION and state.status is WorkflowStatus.FAILED:
        return END
    raise InvalidRequestError(_INVALID_POST_PHASE2_ROUTE_MESSAGE)


def build_workflow_graph(
    *,
    regulatory_intelligence_node: RegulatoryIntelligenceWorkflowNodeAdapter,
    parallel_ingestion_step: ParallelIngestionWorkflowStep,
    parallel_ingestion_failure_runtime_handler: ParallelIngestionFailureRuntimeHandlingService,
    forecasting_step: ForecastingWorkflowStep,
) -> CompiledStateGraph[WorkflowState, None, WorkflowState, WorkflowState]:
    """Compile a fresh workflow graph over ``WorkflowState``.

    Every call constructs and compiles a new graph. The Regulatory node
    adapter, Phase 2 workflow step, outer runtime failure handler, and
    Phase 3 forecasting step are required through keyword-only
    dependency injection. Compilation is plain: no checkpointer, store,
    cache, interrupt, or durability configuration.
    """

    graph = StateGraph(WorkflowState)

    class _WorkflowEntryNode:
        async def __call__(self, state: WorkflowState) -> dict[str, object]:
            return await _workflow_entry(state)

    class _RegulatoryIntelligenceNode:
        async def __call__(self, state: WorkflowState) -> WorkflowState:
            return await regulatory_intelligence_node.run(state)

    class _ParallelIngestionNode:
        async def __call__(self, state: WorkflowState) -> WorkflowState:
            try:
                return await parallel_ingestion_step.run(state)
            except BaseExceptionGroup as failure_group:
                return await parallel_ingestion_failure_runtime_handler.handle(
                    state=state,
                    failure_group=failure_group,
                )

    class _Phase2SuccessTransitionNode:
        async def __call__(self, state: WorkflowState) -> WorkflowState:
            return await _parallel_ingestion_success_transition(state)

    class _ForecastingNode:
        async def __call__(self, state: WorkflowState) -> WorkflowState:
            return await forecasting_step.run(state)

    graph.add_node(_WORKFLOW_ENTRY_NODE, _WorkflowEntryNode())
    graph.add_node(_REGULATORY_INTELLIGENCE_NODE, _RegulatoryIntelligenceNode())
    graph.add_node(_PARALLEL_INGESTION_NODE, _ParallelIngestionNode())
    graph.add_node(
        _PARALLEL_INGESTION_SUCCESS_TRANSITION_NODE,
        _Phase2SuccessTransitionNode(),
    )
    graph.add_node(_FORECASTING_NODE, _ForecastingNode())
    graph.add_edge(START, _WORKFLOW_ENTRY_NODE)
    graph.add_conditional_edges(
        _WORKFLOW_ENTRY_NODE,
        _route_after_workflow_entry,
        {
            _REGULATORY_INTELLIGENCE_NODE: _REGULATORY_INTELLIGENCE_NODE,
            _PARALLEL_INGESTION_NODE: _PARALLEL_INGESTION_NODE,
            _FORECASTING_NODE: _FORECASTING_NODE,
        },
    )
    graph.add_edge(_REGULATORY_INTELLIGENCE_NODE, END)
    graph.add_conditional_edges(
        _PARALLEL_INGESTION_NODE,
        _route_after_parallel_ingestion,
        {
            _PARALLEL_INGESTION_SUCCESS_TRANSITION_NODE: (
                _PARALLEL_INGESTION_SUCCESS_TRANSITION_NODE
            ),
            END: END,
        },
    )
    graph.add_edge(_PARALLEL_INGESTION_SUCCESS_TRANSITION_NODE, END)
    graph.add_edge(_FORECASTING_NODE, END)
    return graph.compile()
