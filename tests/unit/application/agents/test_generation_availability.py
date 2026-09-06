"""Generation Availability Agent application contract."""

from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta, timezone

import pytest

from energy_trading.application.agents.base import AgentName, AgentPort
from energy_trading.application.agents.generation_availability import (
    GenerationAvailabilityAgent,
    GenerationAvailabilityRequest,
    GenerationAvailabilityResult,
)
from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.domain.models.observations import (
    GenerationAvailabilityRecord,
    GenerationStatus,
)


class _FakeGenerationAvailabilityRecordSource:
    """Test-only source fake. Not a production adapter."""

    def __init__(
        self,
        records: tuple[GenerationAvailabilityRecord, ...] = (),
        *,
        error: Exception | None = None,
    ) -> None:
        self.records = records
        self.error = error
        self.calls: list[tuple[str, datetime, datetime]] = []

    async def fetch(
        self,
        *,
        asset_id: str,
        horizon_start: datetime,
        horizon_end: datetime,
    ) -> tuple[GenerationAvailabilityRecord, ...]:
        self.calls.append((asset_id, horizon_start, horizon_end))
        if self.error is not None:
            raise self.error
        return self.records


def _as_agent_port(
    agent: GenerationAvailabilityAgent,
) -> AgentPort[GenerationAvailabilityRequest, GenerationAvailabilityResult]:
    """Mypy-visible structural assignment to the shared agent port."""

    return agent


def _generation(**overrides: object) -> GenerationAvailabilityRecord:
    values: dict[str, object] = {
        "asset_id": "asset-1",
        "timestamp": datetime(2026, 10, 1, 10, tzinfo=UTC),
        "status": GenerationStatus.AVAILABLE,
        "available_capacity_mw": 100.0,
    }
    values.update(overrides)
    return GenerationAvailabilityRecord.model_validate(values)


def _request(**overrides: object) -> GenerationAvailabilityRequest:
    values: dict[str, object] = {
        "asset_id": "asset-1",
        "horizon_start": datetime(2026, 10, 1, 0, tzinfo=UTC),
        "horizon_end": datetime(2026, 10, 2, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return GenerationAvailabilityRequest(**values)  # type: ignore[arg-type]


def test_request_accepts_asset_and_utc_horizon() -> None:
    request = _request()
    assert request.asset_id == "asset-1"
    assert request.horizon_start == datetime(2026, 10, 1, 0, tzinfo=UTC)
    assert request.horizon_end == datetime(2026, 10, 2, 0, tzinfo=UTC)
    assert request.horizon_start.tzinfo is UTC
    assert request.horizon_end.tzinfo is UTC


def test_request_strips_asset_whitespace() -> None:
    request = _request(asset_id="  asset-1  ")
    assert request.asset_id == "asset-1"


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


def test_request_rejects_blank_asset_id() -> None:
    with pytest.raises(ValueError, match="asset_id must be a non-empty string"):
        _request(asset_id="")
    with pytest.raises(ValueError, match="asset_id must be a non-empty string"):
        _request(asset_id="   ")


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
    assert hasattr(GenerationAvailabilityRequest, "__slots__")
    with pytest.raises(FrozenInstanceError):
        request.asset_id = "mutated"  # type: ignore[misc]
    field_names = tuple(item.name for item in fields(GenerationAvailabilityRequest))
    assert field_names == ("asset_id", "horizon_start", "horizon_end")


def test_request_rejects_unrequested_fields() -> None:
    with pytest.raises(TypeError):
        GenerationAvailabilityRequest(
            asset_id="asset-1",
            horizon_start=datetime(2026, 10, 1, 0, tzinfo=UTC),
            horizon_end=datetime(2026, 10, 2, 0, tzinfo=UTC),
            provider="outage-api",  # type: ignore[call-arg]
        )


def test_result_empty_tuple_is_valid() -> None:
    result = GenerationAvailabilityResult(records=())
    assert result.records == ()
    assert isinstance(result.records, tuple)


def test_result_accepts_one_generation_record() -> None:
    record = _generation()
    result = GenerationAvailabilityResult(records=(record,))
    assert result.records == (record,)


def test_result_preserves_multiple_record_order() -> None:
    first = _generation(timestamp=datetime(2026, 10, 1, 11, tzinfo=UTC))
    second = _generation(
        timestamp=datetime(2026, 10, 1, 10, tzinfo=UTC),
        status=GenerationStatus.OUTAGE,
        available_capacity_mw=0.0,
    )
    result = GenerationAvailabilityResult(records=(first, second))
    assert result.records == (first, second)


def test_result_status_and_capacity_remain_unchanged() -> None:
    record = _generation(
        status=GenerationStatus.MAINTENANCE,
        available_capacity_mw=55.0,
        total_capacity_mw=110.0,
    )
    result = GenerationAvailabilityResult(records=(record,))
    passed = result.records[0]
    assert passed is record
    assert passed.status is GenerationStatus.MAINTENANCE
    assert passed.available_capacity_mw == 55.0
    assert passed.total_capacity_mw == 110.0


def test_result_rejects_mutable_records_collection() -> None:
    with pytest.raises(TypeError, match="records must be an immutable tuple"):
        GenerationAvailabilityResult(records=[_generation()])  # type: ignore[arg-type]


def test_result_rejects_non_generation_record_values() -> None:
    with pytest.raises(TypeError, match="records must contain GenerationAvailabilityRecord values"):
        GenerationAvailabilityResult(records=("not-generation",))  # type: ignore[arg-type]


def test_result_is_frozen() -> None:
    result = GenerationAvailabilityResult(records=())
    assert hasattr(GenerationAvailabilityResult, "__slots__")
    with pytest.raises(FrozenInstanceError):
        result.records = ()  # type: ignore[misc]


def test_agent_does_not_inherit_agent_port() -> None:
    assert AgentPort not in GenerationAvailabilityAgent.__mro__
    assert not any(base.__name__ == "AgentPort" for base in GenerationAvailabilityAgent.__bases__)


def test_agent_name_is_canonical_generation_identity() -> None:
    agent = GenerationAvailabilityAgent(_FakeGenerationAvailabilityRecordSource())
    port = _as_agent_port(agent)
    assert port.name is AgentName.GENERATION_AVAILABILITY
    assert port.name.value == "Generation Availability Agent"


def test_agent_module_has_no_hydro_interaction() -> None:
    names = set(vars(sys.modules[GenerationAvailabilityAgent.__module__]))
    assert "HydroResourcesAgent" not in names
    assert "HydroRecord" not in names
    assert "HydroRecordSourcePort" not in names
    assert "HydroResourcesRequest" not in names
    assert "HydroResourcesResult" not in names


async def test_run_invokes_source_once_with_normalized_values() -> None:
    source = _FakeGenerationAvailabilityRecordSource()
    agent = GenerationAvailabilityAgent(source)
    offset = timezone(timedelta(hours=4))
    result = await _as_agent_port(agent).run(
        GenerationAvailabilityRequest(
            asset_id="  asset-1  ",
            horizon_start=datetime(2026, 10, 1, 4, tzinfo=offset),
            horizon_end=datetime(2026, 10, 1, 8, tzinfo=offset),
        )
    )
    assert result.records == ()
    assert len(source.calls) == 1
    asset_id, horizon_start, horizon_end = source.calls[0]
    assert asset_id == "asset-1"
    assert horizon_start == datetime(2026, 10, 1, 0, tzinfo=UTC)
    assert horizon_end == datetime(2026, 10, 1, 4, tzinfo=UTC)


async def test_run_wraps_source_tuple_without_reordering() -> None:
    first = _generation(timestamp=datetime(2026, 10, 1, 12, tzinfo=UTC))
    second = _generation(
        timestamp=datetime(2026, 10, 1, 8, tzinfo=UTC),
        status=GenerationStatus.UNKNOWN,
        available_capacity_mw=12.0,
    )
    source = _FakeGenerationAvailabilityRecordSource((first, second))
    result = await GenerationAvailabilityAgent(source).run(_request())
    assert result.records == (first, second)
    assert result.records is source.records or result.records == source.records
    assert len(source.calls) == 1


async def test_run_empty_source_result_is_valid() -> None:
    result = await GenerationAvailabilityAgent(_FakeGenerationAvailabilityRecordSource()).run(
        _request()
    )
    assert result == GenerationAvailabilityResult(records=())


async def test_run_propagates_dependency_unavailable_without_retry() -> None:
    error = DependencyUnavailableError("generation availability source unavailable")
    source = _FakeGenerationAvailabilityRecordSource(error=error)
    agent = GenerationAvailabilityAgent(source)
    with pytest.raises(
        DependencyUnavailableError, match="generation availability source unavailable"
    ) as caught:
        await agent.run(_request())
    assert caught.value is error
    assert len(source.calls) == 1
