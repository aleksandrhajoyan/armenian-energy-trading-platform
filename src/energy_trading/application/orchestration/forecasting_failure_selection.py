"""Application-owned Phase 3 failure-fact selection boundary.

This module defines the typed seam that resolves an already-sanitized
tuple of ``ForecastingFailureFact`` values into one fact before a
single-failure policy context can later be built.

Ownership:

* Application: owns ``ForecastingFailureSelectionPort``.
* Existing ``ForecastingFailureFact``: reused unchanged as input and
  output.
* Concrete selection policy, attempt tracking, policy-context
  construction, policy/action handling, and graph routing remain deferred.

This is a Phase-3-specific Protocol only. There is no production selector
and no winner semantics in this module.
"""

from typing import Protocol

from energy_trading.application.orchestration.forecasting_failure_fact import (
    ForecastingFailureFact,
)


class ForecastingFailureSelectionPort(Protocol):
    """Framework-neutral Phase 3 failure-fact selection contract.

    Implementations satisfy this protocol structurally. There is no
    application base class and no concrete production selector.

    ``select`` accepts only already-sanitized failure facts. It must not
    accept exceptions, workflow snapshots, attempt counters, policy context,
    or retry/fallback callbacks. Concrete winner semantics are not defined
    here.
    """

    def select(self, facts: tuple[ForecastingFailureFact, ...]) -> ForecastingFailureFact:
        """Return one sanitized Phase 3 failure fact from classified facts."""
        ...
