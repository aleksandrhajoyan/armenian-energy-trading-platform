"""Process-local in-memory ForecastingWorkflowContextPort adapter.

This module is a local/dev reference implementation. It stores prepared
plans and recorded successes in process memory only. It is not durable
storage, a cache adapter, or filesystem persistence, and it is not wired
into LangGraph or ``create_app()``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping

from energy_trading.application.errors import ConflictError, ResourceNotFoundError
from energy_trading.application.orchestration.forecasting_plan import ForecastingPlan
from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.application.orchestration.state import WorkflowState

_MSG_PLAN_NOT_FOUND = "Forecasting plan was not found."
_MSG_SUCCESS_CONFLICT = "Forecasting success conflicts with the recorded result."


class InMemoryForecastingWorkflowContext:
    """In-memory structural implementation of the Phase 3 context port.

    Constructor copies the prepared-plan mapping. Plan objects are kept
    by identity and keyed by ``WorkflowState.workflow_id``. Success writes
    are process-local, idempotent for equal retries, and fail closed on
    conflicting content.
    """

    def __init__(self, plans: Mapping[str, ForecastingPlan]) -> None:
        self._plans: dict[str, ForecastingPlan] = dict(plans)
        self._successes: dict[str, ForecastingSuccess] = {}
        self._write_lock = asyncio.Lock()

    async def resolve_plan(self, *, state: WorkflowState) -> ForecastingPlan:
        """Return the prepared plan for ``state.workflow_id``."""

        try:
            return self._plans[state.workflow_id]
        except KeyError:
            raise ResourceNotFoundError(_MSG_PLAN_NOT_FOUND) from None

    async def record_success(
        self,
        *,
        state: WorkflowState,
        success: ForecastingSuccess,
    ) -> None:
        """Record all-two-success output for ``state.workflow_id``."""

        async with self._write_lock:
            existing = self._successes.get(state.workflow_id)
            if existing is None:
                self._successes[state.workflow_id] = success
                return
            if existing == success:
                return
            raise ConflictError(_MSG_SUCCESS_CONFLICT)
