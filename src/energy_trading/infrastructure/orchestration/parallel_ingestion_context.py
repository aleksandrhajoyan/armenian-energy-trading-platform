"""Process-local in-memory ParallelIngestionWorkflowContextPort adapter.

This module is a local/dev reference implementation. It stores prepared
plans and recorded successes in process memory only. It is not durable
storage, a cache adapter, or filesystem persistence, and it is not wired
into LangGraph or ``create_app()``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping

from energy_trading.application.errors import ConflictError, ResourceNotFoundError
from energy_trading.application.orchestration.parallel_ingestion import (
    ParallelIngestionPlan,
    ParallelIngestionSuccess,
)

_MSG_PLAN_NOT_FOUND = "Parallel-ingestion plan was not found."
_MSG_SUCCESS_CONFLICT = "Parallel-ingestion success conflicts with the recorded result."


class InMemoryParallelIngestionWorkflowContext:
    """In-memory structural implementation of the Phase 2 context port.

    Constructor copies the prepared-plan mapping. Plan objects are kept
    by identity. Success writes are process-local, idempotent for equal
    retries, and fail closed on conflicting content.
    """

    def __init__(self, plans: Mapping[str, ParallelIngestionPlan]) -> None:
        self._plans: dict[str, ParallelIngestionPlan] = dict(plans)
        self._successes: dict[str, ParallelIngestionSuccess] = {}
        self._write_lock = asyncio.Lock()

    async def resolve_plan(self, workflow_id: str) -> ParallelIngestionPlan:
        """Return the prepared plan for ``workflow_id``."""

        try:
            return self._plans[workflow_id]
        except KeyError:
            raise ResourceNotFoundError(_MSG_PLAN_NOT_FOUND) from None

    async def record_success(
        self,
        workflow_id: str,
        success: ParallelIngestionSuccess,
    ) -> None:
        """Record all-five-success output for ``workflow_id``."""

        async with self._write_lock:
            existing = self._successes.get(workflow_id)
            if existing is None:
                self._successes[workflow_id] = success
                return
            if existing == success:
                return
            raise ConflictError(_MSG_SUCCESS_CONFLICT)
