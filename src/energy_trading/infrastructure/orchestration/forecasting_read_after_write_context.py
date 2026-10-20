"""Process-local in-memory read-after-write forecasting context adapter.

This module is a local/dev reference implementation. It wraps an
explicitly supplied ``InMemoryForecastingWorkflowContext``, delegates plan
resolution and success recording to it, and exposes successes recorded
through this wrapper for exact-identity reads. It is not durable storage,
a cache adapter, or a production storage decision, and it is not wired
into LangGraph or ``create_app()``.
"""

from __future__ import annotations

import asyncio

from energy_trading.application.errors import ResourceNotFoundError
from energy_trading.application.orchestration.forecasting_plan import ForecastingPlan
from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.application.orchestration.state import WorkflowState
from energy_trading.infrastructure.orchestration.forecasting_context import (
    InMemoryForecastingWorkflowContext,
)

_MSG_SUCCESS_NOT_FOUND = "Forecasting success was not found."


class InMemoryForecastingReadAfterWriteContext:
    """In-memory read-after-write view over the Phase 3 context adapter.

    Structurally satisfies both the forecasting workflow-context port and
    the forecasting-success read port. The wrapped context remains the sole
    authority for plan resolution and success-recording validity. A success
    becomes readable only after the delegated record completes, keyed by
    ``WorkflowState.workflow_id``; the first published object is kept by
    identity. Writes made directly on the wrapped context are not visible
    here.
    """

    def __init__(self, *, context: InMemoryForecastingWorkflowContext) -> None:
        self._context = context
        self._successes: dict[str, ForecastingSuccess] = {}
        self._lock = asyncio.Lock()

    async def resolve_plan(self, *, state: WorkflowState) -> ForecastingPlan:
        """Return the wrapped context's plan for ``state`` unchanged."""

        return await self._context.resolve_plan(state=state)

    async def record_success(
        self,
        *,
        state: WorkflowState,
        success: ForecastingSuccess,
    ) -> None:
        """Delegate the record, then publish the first accepted success."""

        async with self._lock:
            await self._context.record_success(state=state, success=success)
            if state.workflow_id not in self._successes:
                self._successes[state.workflow_id] = success

    async def get_success(self, *, workflow_id: str) -> ForecastingSuccess:
        """Return the success recorded through this wrapper for ``workflow_id``."""

        async with self._lock:
            try:
                return self._successes[workflow_id]
            except KeyError:
                raise ResourceNotFoundError(_MSG_SUCCESS_NOT_FOUND) from None
