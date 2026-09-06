"""Hydro Resources Agent application contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta, timezone

import pytest

from energy_trading.application.agents.base import AgentName, AgentPort
from energy_trading.application.agents.hydro_resources import (
    HydroResourcesAgent,
    HydroResourcesRequest,
    HydroResourcesResult,
)
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.domain.models.observations import HydroRecord


class _FakeHydroRecordSource:
    """Test-only source fake. Not a production adapter."""

    def __init__(
        self,
        records: tuple[HydroRecord, ...] = (),
        *,
        error: Exception | None = None,
    ) -> None:
        self.records = records
        self.error = error
        self.calls: list[tuple[str, datetime, datetime]] = []

    async def fetch(
        self,
        *,
        resource_id: str,
        horizon_start: datetime,
        horizon_end: datetime,
    ) -> tuple[HydroRecord, ...]:
        self.calls.append((resource_id, horizon_start, horizon_end))
        if self.error is not None:
            raise self.error
        return self.records


def _as_agent_port(
    agent: HydroResourcesAgent,
) -> AgentPort[HydroResourcesRequest, HydroResourcesResult]:
    """Mypy-visible structural assignment to the shared agent port."""

    return agent


def _hydro(**overrides: object) -> HydroRecord:
    values: dict[str, object] = {
        "resource_id": "res-1",
        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
    }
    values.update(overrides)
    return HydroRecord.model_validate(values)


def _request(**overrides: object) -> HydroResourcesRequest:
    values: dict[str, object] = {
        "resource_id": "res-1",
        "horizon_start": datetime(2026, 10, 1, 0, tzinfo=UTC),
        "horizon_end": datetime(2026, 10, 2, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return HydroResourcesRequest(**values)  # type: ignore[arg-type]


def test_request_accepts_resource_and_utc_horizon() -> None:
    request = _request()
    assert request.resource_id == "res-1"
    assert request.horizon_start == datetime(2026, 10, 1, 0, tzinfo=UTC)
    assert request.horizon_end == datetime(2026, 10, 2, 0, tzinfo=UTC)
    assert request.horizon_start.tzinfo is UTC
    assert request.horizon_end.tzinfo is UTC


def test_request_strips_resource_whitespace() -> None:
    request = _request(resource_id="  res-1  ")
    assert request.resource_id == "res-1"


def test_request_normalizes_aware_non_utc_horizons_to_utc() -> None:
    offset = timezone(timedelta(hours=4))
    request = _request(
        horizon_start=datetime(2026, 10, 1, 4, tzinfo=offset),
        horizon_end=datetime(2026, 10, 1, 8, tzinfo=offset),
    )
    assert request.horizon_start == datetime(2026, 10, 1, 0, tzinfo=UTC)
    assert request.horizon_end == datetime(2026, 10, 1, 4, tzinfo=UTC)
    assert request.horizon_start.tzinfo is UTC
    assert request.horizon_end.tzinfo is UTC


def test_request_rejects_naive_horizon_start() -> None:
    with pytest.raises(ValueError, match="horizon_start must be timezone-aware"):
        _request(horizon_start=datetime(2026, 10, 1, 0))


def test_request_rejects_naive_horizon_end() -> None:
    with pytest.raises(ValueError, match="horizon_end must be timezone-aware"):
        _request(horizon_end=datetime(2026, 10, 2, 0))


def test_request_rejects_blank_resource_id() -> None:
    with pytest.raises(ValueError, match="resource_id must be a non-empty string"):
        _request(resource_id="")
    with pytest.raises(ValueError, match="resource_id must be a non-empty string"):
        _request(resource_id="   ")


def test_request_rejects_equal_horizon_bounds() -> None:
    instant = datetime(2026, 10, 1, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="horizon_end must be later than horizon_start"):
        _request(horizon_start=instant, horizon_end=instant)


def test_request_rejects_reversed_horizon() -> None:
    with pytest.raises(ValueError, match="horizon_end must be later than horizon_start"):
        _request(
            horizon_start=datetime(2026, 10, 2, 0, tzinfo=UTC),
            horizon_end=datetime(2026, 10, 1, 0, tzinfo=UTC),
        )


def test_request_is_frozen_and_slotted() -> None:
    request = _request()
    assert hasattr(HydroResourcesRequest, "__slots__")
    with pytest.raises(FrozenInstanceError):
        request.resource_id = "mutated"  # type: ignore[misc]
    field_names = tuple(item.name for item in fields(HydroResourcesRequest))
    assert field_names == ("resource_id", "horizon_start", "horizon_end")


def test_request_rejects_unrequested_fields() -> None:
    with pytest.raises(TypeError):
        HydroResourcesRequest(
            resource_id="res-1",
            horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
            horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
            provider="operator-scada",  # type: ignore[call-arg]
        )


def test_result_empty_tuple_is_valid() -> None:
    result = HydroResourcesResult(records=())
    assert result.records == ()
    assert isinstance(result.records, tuple)


def test_result_accepts_one_hydro_record() -> None:
    record = _hydro()
    result = HydroResourcesResult(records=(record,))
    assert result.records == (record,)


def test_result_preserves_multiple_record_order() -> None:
    first = _hydro(timestamp=datetime(2026, 10, 1, 11, tzinfo=UTC))
    second = _hydro(timestamp=datetime(2026, 10, 1, 10, tzinfo=UTC), reservoir_level_m=9.0)
    result = HydroResourcesResult(records=(first, second))
    assert result.records == (first, second)


def test_result_optional_canonical_hydro_fields_remain_unchanged() -> None:
    record = _hydro(
        reservoir_level_m=42.5,
        river_flow_m3_s=11.0,
        available_generation_mw=80.0,
    )
    result = HydroResourcesResult(records=(record,))
    passed = result.records[0]
    assert passed is record
    assert passed.reservoir_level_m == 42.5
    assert passed.river_flow_m3_s == 11.0
    assert passed.available_generation_mw == 80.0


def test_result_rejects_mutable_records_collection() -> None:
    with pytest.raises(TypeError, match="records must be an immutable tuple"):
        HydroResourcesResult(records=[_hydro()])  # type: ignore[arg-type]


def test_result_rejects_non_hydro_record_values() -> None:
    with pytest.raises(TypeError, match="records must contain HydroRecord values"):
        HydroResourcesResult(records=("not-hydro",))  # type: ignore[arg-type]


def test_result_is_frozen() -> None:
    result = HydroResourcesResult(records=())
    assert hasattr(HydroResourcesResult, "__slots__")
    with pytest.raises(FrozenInstanceError):
        result.records = ()  # type: ignore[misc]


def test_agent_does_not_inherit_agent_port() -> None:
    assert AgentPort not in HydroResourcesAgent.__mro__
    assert not any(base.__name__ == "AgentPort" for base in HydroResourcesAgent.__bases__)


def test_agent_name_is_canonical_hydro_identity() -> None:
    agent = HydroResourcesAgent(_FakeHydroRecordSource())
    port = _as_agent_port(agent)
    assert port.name is AgentName.HYDRO_RESOURCES
    assert port.name.value == "Hydro Resources Agent"


async def test_run_invokes_source_once_with_normalized_values() -> None:
    source = _FakeHydroRecordSource()
    agent = HydroResourcesAgent(source)
    offset = timezone(timedelta(hours=4))
    result = await _as_agent_port(agent).run(
        HydroResourcesRequest(
            resource_id="  res-1  ",
            horizon_start=datetime(2026, 10, 1, 4, tzinfo=offset),
            horizon_end=datetime(2026, 10, 1, 8, tzinfo=offset),
        )
    )
    assert result.records == ()
    assert len(source.calls) == 1
    resource_id, horizon_start, horizon_end = source.calls[0]
    assert resource_id == "res-1"
    assert horizon_start == datetime(2026, 10, 1, 0, tzinfo=UTC)
    assert horizon_end == datetime(2026, 10, 1, 4, tzinfo=UTC)


async def test_run_wraps_source_tuple_without_reordering() -> None:
    first = _hydro(timestamp=datetime(2026, 10, 1, 12, tzinfo=UTC))
    second = _hydro(timestamp=datetime(2026, 10, 1, 8, tzinfo=UTC), river_flow_m3_s=4.0)
    source = _FakeHydroRecordSource((first, second))
    result = await HydroResourcesAgent(source).run(_request())
    assert result.records == (first, second)
    assert result.records is source.records or result.records == source.records
    assert len(source.calls) == 1


async def test_run_empty_source_result_is_valid() -> None:
    result = await HydroResourcesAgent(_FakeHydroRecordSource()).run(_request())
    assert result == HydroResourcesResult(records=())


async def test_run_propagates_dependency_unavailable_without_retry() -> None:
    error = DependencyUnavailableError("hydro source unavailable")
    source = _FakeHydroRecordSource(error=error)
    agent = HydroResourcesAgent(source)
    with pytest.raises(DependencyUnavailableError, match="hydro source unavailable") as caught:
        await agent.run(_request())
    assert caught.value is error
    assert len(source.calls) == 1
