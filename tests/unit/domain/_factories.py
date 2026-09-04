"""Shared constructors for domain unit tests."""

from datetime import UTC, datetime
from decimal import Decimal

from energy_trading.domain.models import (
    AdapterDiagnostic,
    BidSide,
    ClearingStatus,
    ConsumptionRecord,
    DiagnosticSeverity,
    DLQRecord,
    GenerationAvailabilityRecord,
    GenerationStatus,
    MarketBid,
    MarketClearingResult,
    RegulatoryConstraint,
    SettlementResult,
)
from energy_trading.domain.value_objects import EnergyPrice, MoneyAmount


def utc(year: int = 2026, month: int = 10, day: int = 1, hour: int = 10) -> datetime:
    return datetime(year, month, day, hour, 0, 0, tzinfo=UTC)


def amd_price(amount: str = "12.50") -> EnergyPrice:
    return EnergyPrice(amount_per_mwh=Decimal(amount), currency="AMD")


def amd_money(amount: str) -> MoneyAmount:
    return MoneyAmount(amount=Decimal(amount), currency="AMD")


def consumption(**overrides: object) -> ConsumptionRecord:
    values: dict[str, object] = {
        "consumer_id": "consumer-1",
        "timestamp": utc(),
        "value_mw": 1.5,
    }
    values.update(overrides)
    return ConsumptionRecord.model_validate(values)


def availability(**overrides: object) -> GenerationAvailabilityRecord:
    values: dict[str, object] = {
        "asset_id": "asset-1",
        "timestamp": utc(),
        "status": GenerationStatus.AVAILABLE,
        "available_capacity_mw": 10.0,
        "total_capacity_mw": 20.0,
    }
    values.update(overrides)
    return GenerationAvailabilityRecord.model_validate(values)


def constraint(**overrides: object) -> RegulatoryConstraint:
    values: dict[str, object] = {
        "constraint_id": "constraint-1",
        "constraint_type": "capacity_limit",
        "description": "Generic numeric bound",
        "effective_from": "2026-01-01",
    }
    values.update(overrides)
    return RegulatoryConstraint.model_validate(values)


def bid(**overrides: object) -> MarketBid:
    values: dict[str, object] = {
        "bid_id": "bid-1",
        "created_at": utc(),
        "delivery_timestamp": utc(hour=16),
        "side": BidSide.SELL,
        "quantity_mw": 5.0,
        "limit_price": amd_price(),
    }
    values.update(overrides)
    return MarketBid.model_validate(values)


def clearing(**overrides: object) -> MarketClearingResult:
    values: dict[str, object] = {
        "bid_id": "bid-1",
        "delivery_timestamp": utc(hour=16),
        "cleared_at": utc(hour=18),
        "status": ClearingStatus.CLEARED,
        "cleared_quantity_mw": 5.0,
        "clearing_price": amd_price("11.00"),
    }
    values.update(overrides)
    return MarketClearingResult.model_validate(values)


def settlement(**overrides: object) -> SettlementResult:
    values: dict[str, object] = {
        "settlement_id": "settle-1",
        "period_start": utc(),
        "period_end": utc(hour=11),
        "delivered_energy_mwh": 4.0,
        "revenue": amd_money("100.00"),
        "procurement_cost": amd_money("60.00"),
        "balancing_cost": amd_money("5.00"),
        "profit": amd_money("35.00"),
    }
    values.update(overrides)
    return SettlementResult.model_validate(values)


def diagnostic(**overrides: object) -> AdapterDiagnostic:
    values: dict[str, object] = {
        "code": "VALIDATION_FAILED",
        "message": "row could not be normalized",
        "severity": DiagnosticSeverity.ERROR,
    }
    values.update(overrides)
    return AdapterDiagnostic.model_validate(values)


def dlq(**overrides: object) -> DLQRecord:
    values: dict[str, object] = {
        "record_id": "dlq-1",
        "failed_at": utc(),
        "source_name": "operator-file",
        "adapter_name": "structured.csv",
        "diagnostics": (diagnostic(),),
        "payload_reference": "blob://ingestion/dlq-1",
    }
    values.update(overrides)
    return DLQRecord.model_validate(values)
