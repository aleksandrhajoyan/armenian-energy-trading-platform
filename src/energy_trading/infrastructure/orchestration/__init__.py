"""Process-local orchestration adapters.

This package is local/dev reference infrastructure. It is not the
production workflow-context persistence decision.
"""

from energy_trading.infrastructure.orchestration.parallel_ingestion_context import (
    InMemoryParallelIngestionWorkflowContext,
)

__all__ = ["InMemoryParallelIngestionWorkflowContext"]
