"""Minimal LangGraph runtime skeleton over application-owned workflow state.

This module is the first executable graph seam. It compiles a one-node
graph that consumes the already-published ``WorkflowState`` contract and
performs no business work.

Ownership:

* Application orchestration: owns graph construction.
* Chunk 27 ``WorkflowState``: remains the authoritative state schema.
* Future chunks: add routing, retries, agents, and persistence separately.

The topology is only ``START → workflow_entry → END``. The entry node is an
async no-op. There is no persistence, agent call, or phase movement.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from energy_trading.application.orchestration.state import WorkflowState

_WORKFLOW_ENTRY_NODE = "workflow_entry"


async def _workflow_entry(_state: WorkflowState) -> dict[str, object]:
    """Internal no-op boundary node.

    Accepts the current ``WorkflowState`` and returns an empty LangGraph
    state update. The update changes no application state. The node performs
    no I/O and does not call agents, use cases, or infrastructure.
    """

    return {}


def build_workflow_graph() -> CompiledStateGraph[WorkflowState, None, WorkflowState, WorkflowState]:
    """Compile a fresh no-op workflow graph over ``WorkflowState``.

    Every call constructs and compiles a new graph. Compilation is plain:
    no checkpointer, store, cache, interrupt, or durability configuration.
    """

    graph = StateGraph(WorkflowState)

    class _WorkflowEntryNode:
        async def __call__(self, state: WorkflowState) -> dict[str, object]:
            return await _workflow_entry(state)

    graph.add_node(_WORKFLOW_ENTRY_NODE, _WorkflowEntryNode())
    graph.add_edge(START, _WORKFLOW_ENTRY_NODE)
    graph.add_edge(_WORKFLOW_ENTRY_NODE, END)
    return graph.compile()
