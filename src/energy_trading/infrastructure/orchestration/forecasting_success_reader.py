"""Process-local in-memory ForecastingSuccessReadPort adapter.

This module is a local/dev reference implementation. It serves explicitly
caller-supplied, already-completed ``ForecastingSuccess`` snapshots from
process memory only. It is not durable storage, a cache adapter, or a
production storage decision. It is not connected to the success writes of
``InMemoryForecastingWorkflowContext`` and is not wired into LangGraph or
``create_app()``.
"""

from __future__ import annotations

from collections.abc import Mapping

from energy_trading.application.errors import ResourceNotFoundError
from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess

_MSG_SUCCESS_NOT_FOUND = "Forecasting success was not found."


class InMemoryForecastingSuccessReader:
    """In-memory structural implementation of the Phase 3 success read port.

    Constructor copies the supplied snapshot mapping so later caller-side
    mapping changes do not alter the available entries. Success objects
    are kept by identity and keyed by exact workflow identity. Unknown
    identities fail closed; no result is fabricated.
    """

    def __init__(self, *, successes: Mapping[str, ForecastingSuccess]) -> None:
        self._successes: dict[str, ForecastingSuccess] = dict(successes)

    async def get_success(self, *, workflow_id: str) -> ForecastingSuccess:
        """Return the seeded success for exactly ``workflow_id``."""

        try:
            return self._successes[workflow_id]
        except KeyError:
            raise ResourceNotFoundError(_MSG_SUCCESS_NOT_FOUND) from None
