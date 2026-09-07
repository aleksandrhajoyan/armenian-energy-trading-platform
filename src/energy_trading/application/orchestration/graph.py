"""LangGraph runtime over application-owned workflow state.

This module compiles the current executable graph. It consumes the
already-published ``WorkflowState`` contract and delegates Phase 2
ingestion to an injected ``ParallelIngestionWorkflowStep``.

Ownership:

* Application orchestration: owns graph construction.
* Chunk 27 ``WorkflowState``: remains the authoritative state schema.
* Chunk 40 ``ParallelIngestionWorkflowStep``: owns resolve → execute →
  record. The graph does not reconstruct that sequence.
* Future chunks: add routing, retries, persistence, and phase/status
  transitions separately.

The topology is ``START → workflow_entry → parallel_ingestion → END``.
``workflow_entry`` remains an async no-op. ``parallel_ingestion`` only
awaits the injected step. There is no persistence, retry, fallback, or
phase movement in this module.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from energy_trading.application.orchestration.parallel_ingestion_workflow import (
    ParallelIngestionWorkflowStep,
)
from energy_trading.application.orchestration.state import WorkflowState

_WORKFLOW_ENTRY_NODE = "workflow_entry"
_PARALLEL_INGESTION_NODE = "parallel_ingestion"


async def _workflow_entry(_state: WorkflowState) -> dict[str, object]:
    """Internal no-op boundary node.

    Accepts the current ``WorkflowState`` and returns an empty LangGraph
    state update. The update changes no application state. The node performs
    no I/O and does not call agents, use cases, or infrastructure.
    """

    return {}


def build_workflow_graph(
    *,
    parallel_ingestion_step: ParallelIngestionWorkflowStep,
) -> CompiledStateGraph[WorkflowState, None, WorkflowState, WorkflowState]:
    """Compile a fresh workflow graph over ``WorkflowState``.

    Every call constructs and compiles a new graph. The Phase 2 workflow
    step is required through keyword-only dependency injection. Compilation
    is plain: no checkpointer, store, cache, interrupt, or durability
    configuration.
    """

    graph = StateGraph(WorkflowState)

    class _WorkflowEntryNode:
        async def __call__(self, state: WorkflowState) -> dict[str, object]:
            return await _workflow_entry(state)

    class _ParallelIngestionNode:
        async def __call__(self, state: WorkflowState) -> WorkflowState:
            return await parallel_ingestion_step.run(state)

    graph.add_node(_WORKFLOW_ENTRY_NODE, _WorkflowEntryNode())
    graph.add_node(_PARALLEL_INGESTION_NODE, _ParallelIngestionNode())
    graph.add_edge(START, _WORKFLOW_ENTRY_NODE)
    graph.add_edge(_WORKFLOW_ENTRY_NODE, _PARALLEL_INGESTION_NODE)
    graph.add_edge(_PARALLEL_INGESTION_NODE, END)
    return graph.compile()
