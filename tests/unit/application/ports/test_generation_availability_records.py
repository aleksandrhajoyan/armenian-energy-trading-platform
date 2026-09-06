"""Canonical generation availability source application-port contract."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime

import pytest

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports import GenerationAvailabilityRecordSourcePort
from energy_trading.domain.models.observations import (
    GenerationAvailabilityRecord,
    GenerationStatus,
)


class _FakeGenerationAvailabilityRecordSource:
    """Test-only fake that structurally satisfies ``GenerationAvailabilityRecordSourcePort``.

    Not a production adapter. Does not inherit a production or infrastructure
    base class.
    """

    def __init__(
        self,
        records: tuple[GenerationAvailabilityRecord, ...] = (),
        *,
        unavailable: bool = False,
    ) -> None:
        self.records = records
        self.unavailable = unavailable
        self.calls: list[tuple[str, datetime, datetime]] = []

    async def fetch(
        self,
        *,
        asset_id: str,
        horizon_start: datetime,
        horizon_end: datetime,
    ) -> tuple[GenerationAvailabilityRecord, ...]:
        self.calls.append((asset_id, horizon_start, horizon_end))
        if self.unavailable:
            msg = "generation availability source unavailable"
            raise DependencyUnavailableError(msg)
        return self.records


def _as_generation_source(
    source: _FakeGenerationAvailabilityRecordSource,
) -> GenerationAvailabilityRecordSourcePort:
    return source


def _generation(**overrides: object) -> GenerationAvailabilityRecord:
    values: dict[str, object] = {
        "asset_id": "asset-1",
        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
        "status": GenerationStatus.AVAILABLE,
        "available_capacity_mw": 100.0,
    }
    values.update(overrides)
    return GenerationAvailabilityRecord.model_validate(values)


def test_structural_fake_does_not_inherit_production_base() -> None:
    assert (
        GenerationAvailabilityRecordSourcePort
        not in _FakeGenerationAvailabilityRecordSource.__mro__
    )
    assert not any(
        base.__name__ in {"GenerationAvailabilityRecordSourcePort", "Protocol"}
        for base in _FakeGenerationAvailabilityRecordSource.__bases__
    )


def test_fake_provides_async_fetch() -> None:
    fake = _FakeGenerationAvailabilityRecordSource()
    port = _as_generation_source(fake)
    assert inspect.iscoroutinefunction(port.fetch)
    parameters = inspect.signature(_FakeGenerationAvailabilityRecordSource.fetch).parameters
    assert tuple(parameters) == ("self", "asset_id", "horizon_start", "horizon_end")
    assert parameters["asset_id"].kind is inspect.Parameter.KEYWORD_ONLY


async def test_canonical_asset_id_and_horizons_are_accepted() -> None:
    fake = _FakeGenerationAvailabilityRecordSource()
    port = _as_generation_source(fake)
    start = datetime(2026, 10, 1, 0, tzinfo=UTC)
    end = datetime(2026, 10, 2, 0, tzinfo=UTC)
    result = await port.fetch(
        asset_id="asset-1",
        horizon_start=start,
        horizon_end=end,
    )
    assert result == ()
    assert fake.calls == [("asset-1", start, end)]


async def test_empty_tuple_is_valid() -> None:
    port = _as_generation_source(_FakeGenerationAvailabilityRecordSource())
    result = await port.fetch(
        asset_id="asset-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == ()
    assert isinstance(result, tuple)


async def test_one_canonical_record_is_valid() -> None:
    record = _generation()
    port = _as_generation_source(_FakeGenerationAvailabilityRecordSource((record,)))
    result = await port.fetch(
        asset_id="asset-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == (record,)
    assert all(isinstance(item, GenerationAvailabilityRecord) for item in result)


async def test_multiple_canonical_records_preserve_order() -> None:
    first = _generation(timestamp=datetime(2026, 10, 1, 10, tzinfo=UTC))
    second = _generation(
        timestamp=datetime(2026, 10, 1, 11, tzinfo=UTC),
        status=GenerationStatus.MAINTENANCE,
        available_capacity_mw=40.0,
    )
    port = _as_generation_source(_FakeGenerationAvailabilityRecordSource((first, second)))
    result = await port.fetch(
        asset_id="asset-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == (first, second)


async def test_status_values_pass_through_unchanged() -> None:
    records = tuple(
        _generation(
            timestamp=datetime(2026, 10, 1, hour, tzinfo=UTC),
            status=status,
        )
        for hour, status in enumerate(
            (
                GenerationStatus.AVAILABLE,
                GenerationStatus.MAINTENANCE,
                GenerationStatus.OUTAGE,
                GenerationStatus.UNKNOWN,
            ),
            start=10,
        )
    )
    port = _as_generation_source(_FakeGenerationAvailabilityRecordSource(records))
    result = await port.fetch(
        asset_id="asset-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == records
    assert tuple(item.status for item in result) == (
        GenerationStatus.AVAILABLE,
        GenerationStatus.MAINTENANCE,
        GenerationStatus.OUTAGE,
        GenerationStatus.UNKNOWN,
    )


async def test_available_and_optional_total_capacity_pass_through_unchanged() -> None:
    record = _generation(
        available_capacity_mw=75.0,
        total_capacity_mw=120.0,
    )
    port = _as_generation_source(_FakeGenerationAvailabilityRecordSource((record,)))
    result = await port.fetch(
        asset_id="asset-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == (record,)
    passed = result[0]
    assert passed.available_capacity_mw == 75.0
    assert passed.total_capacity_mw == 120.0
    assert passed.status is GenerationStatus.AVAILABLE


async def test_fake_can_represent_dependency_unavailable() -> None:
    fake = _FakeGenerationAvailabilityRecordSource(unavailable=True)
    port = _as_generation_source(fake)
    with pytest.raises(
        DependencyUnavailableError, match="generation availability source unavailable"
    ):
        await port.fetch(
            asset_id="asset-1",
            horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
            horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
        )
    assert len(fake.calls) == 1
