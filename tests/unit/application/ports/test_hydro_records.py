"""Canonical hydro source application-port contract."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime

import pytest

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports import HydroRecordSourcePort
from energy_trading.domain.models.observations import HydroRecord


class _FakeHydroRecordSource:
    """Test-only fake that structurally satisfies ``HydroRecordSourcePort``.

    Not a production adapter. Does not inherit a production or infrastructure
    base class.
    """

    def __init__(
        self,
        records: tuple[HydroRecord, ...] = (),
        *,
        unavailable: bool = False,
    ) -> None:
        self.records = records
        self.unavailable = unavailable
        self.calls: list[tuple[str, datetime, datetime]] = []

    async def fetch(
        self,
        *,
        resource_id: str,
        horizon_start: datetime,
        horizon_end: datetime,
    ) -> tuple[HydroRecord, ...]:
        self.calls.append((resource_id, horizon_start, horizon_end))
        if self.unavailable:
            msg = "hydro source unavailable"
            raise DependencyUnavailableError(msg)
        return self.records


def _as_hydro_source(source: _FakeHydroRecordSource) -> HydroRecordSourcePort:
    return source


def _hydro(**overrides: object) -> HydroRecord:
    values: dict[str, object] = {
        "resource_id": "res-1",
        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
    }
    values.update(overrides)
    return HydroRecord.model_validate(values)


def test_structural_fake_does_not_inherit_production_base() -> None:
    assert HydroRecordSourcePort not in _FakeHydroRecordSource.__mro__
    assert not any(
        base.__name__ in {"HydroRecordSourcePort", "Protocol"}
        for base in _FakeHydroRecordSource.__bases__
    )


def test_fake_provides_async_fetch() -> None:
    fake = _FakeHydroRecordSource()
    port = _as_hydro_source(fake)
    assert inspect.iscoroutinefunction(port.fetch)
    parameters = inspect.signature(_FakeHydroRecordSource.fetch).parameters
    assert tuple(parameters) == ("self", "resource_id", "horizon_start", "horizon_end")
    assert parameters["resource_id"].kind is inspect.Parameter.KEYWORD_ONLY


async def test_empty_tuple_is_valid() -> None:
    port = _as_hydro_source(_FakeHydroRecordSource())
    result = await port.fetch(
        resource_id="res-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == ()
    assert isinstance(result, tuple)


async def test_one_canonical_record_is_valid() -> None:
    record = _hydro()
    port = _as_hydro_source(_FakeHydroRecordSource((record,)))
    result = await port.fetch(
        resource_id="res-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == (record,)
    assert all(isinstance(item, HydroRecord) for item in result)


async def test_multiple_canonical_records_preserve_order() -> None:
    first = _hydro(timestamp=datetime(2026, 10, 1, 10, tzinfo=UTC))
    second = _hydro(timestamp=datetime(2026, 10, 1, 11, tzinfo=UTC), reservoir_level_m=18.0)
    port = _as_hydro_source(_FakeHydroRecordSource((first, second)))
    result = await port.fetch(
        resource_id="res-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == (first, second)


async def test_optional_canonical_hydro_fields_pass_through_unchanged() -> None:
    record = _hydro(
        reservoir_level_m=42.5,
        river_flow_m3_s=11.0,
        available_generation_mw=80.0,
    )
    port = _as_hydro_source(_FakeHydroRecordSource((record,)))
    result = await port.fetch(
        resource_id="res-1",
        horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
        horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
    )
    assert result == (record,)
    passed = result[0]
    assert passed.reservoir_level_m == 42.5
    assert passed.river_flow_m3_s == 11.0
    assert passed.available_generation_mw == 80.0


async def test_fake_can_represent_dependency_unavailable() -> None:
    fake = _FakeHydroRecordSource(unavailable=True)
    port = _as_hydro_source(fake)
    with pytest.raises(DependencyUnavailableError, match="hydro source unavailable"):
        await port.fetch(
            resource_id="res-1",
            horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
            horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
        )
    assert len(fake.calls) == 1
