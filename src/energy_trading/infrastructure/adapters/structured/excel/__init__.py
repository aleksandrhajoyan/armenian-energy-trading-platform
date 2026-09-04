"""Excel structured adapters. Concrete readers live beside this package."""

from energy_trading.infrastructure.adapters.structured.excel.consumption import (
    ConsumptionExcelAdapter,
)

__all__ = ["ConsumptionExcelAdapter"]
