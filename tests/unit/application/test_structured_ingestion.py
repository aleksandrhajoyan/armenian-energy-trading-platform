"""Structured ingestion application-port contracts."""

import inspect
from dataclasses import FrozenInstanceError

import pytest

from energy_trading.application.ports import StructuredIngestionPort, StructuredIngestionResult
from energy_trading.domain.models import ConsumptionRecord, DLQRecord
from tests.unit.application.fakes import FakeConsumptionAdapter, as_consumption_port
from tests.unit.domain._factories import consumption, diagnostic, dlq


def _success_result() -> StructuredIngestionResult[ConsumptionRecord]:
    return StructuredIngestionResult(
        source_name="fake-consumption",
        records=(consumption(),),
        diagnostics=(),
        dlq_records=(),
    )


def _partial_result() -> StructuredIngestionResult[ConsumptionRecord]:
    return StructuredIngestionResult(
        source_name="fake-consumption",
        records=(consumption(),),
        diagnostics=(diagnostic(),),
        dlq_records=(dlq(),),
    )


def test_result_is_frozen_generic_envelope() -> None:
    result = _success_result()
    record = result.records[0]

    assert result.source_name == "fake-consumption"
    assert isinstance(result.records, tuple)
    assert isinstance(result.diagnostics, tuple)
    assert isinstance(result.dlq_records, tuple)
    assert isinstance(record, ConsumptionRecord)
    assert record.consumer_id == "consumer-1"

    with pytest.raises(FrozenInstanceError):
        result.source_name = "mutated"  # type: ignore[misc]


def test_result_rejects_mutable_collections() -> None:
    record = consumption()
    with pytest.raises(TypeError, match="records must be an immutable tuple"):
        StructuredIngestionResult(
            source_name="fake-consumption",
            records=[record],  # type: ignore[arg-type]
            diagnostics=(),
            dlq_records=(),
        )


def test_result_rejects_non_canonical_records() -> None:
    with pytest.raises(TypeError, match="canonical domain models"):
        StructuredIngestionResult(
            source_name="fake-consumption",
            records=({"consumer_id": "consumer-1", "value_mw": 1.5},),  # type: ignore[arg-type]
            diagnostics=(),
            dlq_records=(),
        )


def test_result_rejects_empty_source_name() -> None:
    with pytest.raises(ValueError, match="source_name"):
        StructuredIngestionResult(
            source_name="   ",
            records=(),
            diagnostics=(),
            dlq_records=(),
        )


async def test_fake_adapter_structurally_satisfies_async_port() -> None:
    adapter = FakeConsumptionAdapter(records=(consumption(),))
    port: StructuredIngestionPort[ConsumptionRecord] = as_consumption_port(adapter)

    assert inspect.iscoroutinefunction(port.ingest)
    result = await port.ingest()

    assert result.source_name == "fake-consumption"
    assert len(result.records) == 1
    assert isinstance(result.records[0], ConsumptionRecord)
    assert result.diagnostics == ()
    assert result.dlq_records == ()
    assert list(inspect.signature(FakeConsumptionAdapter.ingest).parameters) == ["self"]


async def test_canonical_success() -> None:
    port = as_consumption_port(FakeConsumptionAdapter(records=(consumption(),)))
    result = await port.ingest()

    assert len(result.records) == 1
    assert result.dlq_records == ()
    assert isinstance(result.records[0], ConsumptionRecord)


async def test_partial_success_is_first_class() -> None:
    adapter = FakeConsumptionAdapter(
        records=(consumption(),),
        diagnostics=(diagnostic(),),
        dlq_records=(dlq(),),
    )
    result = await adapter.ingest()

    assert isinstance(result.records, tuple)
    assert isinstance(result.diagnostics, tuple)
    assert isinstance(result.dlq_records, tuple)
    assert len(result.records) == 1
    assert isinstance(result.records[0], ConsumptionRecord)
    assert len(result.diagnostics) == 1
    assert len(result.dlq_records) == 1
    assert result.dlq_records[0].payload_reference == "blob://ingestion/dlq-1"
    assert not hasattr(result, "raw_payload")
    assert not hasattr(result, "payload")
    assert "payload" not in DLQRecord.model_fields
    assert result.dlq_records[0].model_dump()["payload_reference"] == "blob://ingestion/dlq-1"


async def test_complete_normalization_failure_is_valid() -> None:
    adapter = FakeConsumptionAdapter(
        records=(),
        diagnostics=(diagnostic(),),
        dlq_records=(dlq(),),
    )
    result = await adapter.ingest()

    assert result.records == ()
    assert len(result.diagnostics) == 1
    assert len(result.dlq_records) == 1
    assert result.dlq_records[0].payload_reference == "blob://ingestion/dlq-1"


async def test_empty_source_is_valid() -> None:
    result = await FakeConsumptionAdapter().ingest()

    assert result.records == ()
    assert result.diagnostics == ()
    assert result.dlq_records == ()


def test_partial_success_does_not_embed_raw_payload() -> None:
    result = _partial_result()
    dumped = result.dlq_records[0].model_dump()

    assert set(dumped) == {
        "record_id",
        "failed_at",
        "source_name",
        "adapter_name",
        "diagnostics",
        "payload_reference",
        "correlation_id",
    }
    assert not any(isinstance(item, (bytes, bytearray, dict)) for item in result.records)
    assert not any(isinstance(item, (bytes, bytearray, dict)) for item in result.dlq_records)
