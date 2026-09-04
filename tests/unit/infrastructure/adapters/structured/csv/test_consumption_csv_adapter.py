"""Consumption CSV adapter unit tests."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports import StructuredIngestionPort, StructuredIngestionResult
from energy_trading.domain.models import ConsumptionRecord, DiagnosticSeverity
from energy_trading.infrastructure.adapters.structured.csv import ConsumptionCsvAdapter
from energy_trading.infrastructure.adapters.structured.normalization import (
    NormalizationConfigurationError,
    PowerUnit,
)
from energy_trading.infrastructure.adapters.structured.schema_mapping import CanonicalFieldSpec
from energy_trading.infrastructure.adapters.structured.time_series import IntervalGrid

_FIXED_TIME = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
_SOURCE = "test-consumption"
_LEAK_TOKEN = "RAW-LEAK-TOKEN-9f3c1a"
_VALID_TS = "2026-09-05T00:00:00+04:00"
_VALID_TS_UTC = datetime(2026, 9, 4, 20, 0, tzinfo=UTC)
_HOURLY_UTC = IntervalGrid(
    interval=timedelta(hours=1),
    anchor=datetime(2026, 9, 5, 0, 0, tzinfo=UTC),
)

_AMBIGUOUS_SPECS = (
    CanonicalFieldSpec(canonical_name="consumer_id", aliases=("load_mw",), required=True),
    CanonicalFieldSpec(canonical_name="timestamp", aliases=("load_kw",), required=True),
    CanonicalFieldSpec(canonical_name="value_mw", aliases=("Consumption_MW",), required=True),
)

_ARMENIAN_SPECS = (
    CanonicalFieldSpec(canonical_name="consumer_id", aliases=("սպառող",), required=True),
    CanonicalFieldSpec(canonical_name="timestamp", aliases=(), required=True),
    CanonicalFieldSpec(canonical_name="value_mw", aliases=("Consumption_MW",), required=True),
)


def _write(tmp_path: Path, content: str, *, name: str = "consumption.csv") -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def _adapter(
    path: Path,
    *,
    field_specs: tuple[CanonicalFieldSpec, ...] | None = None,
    source_power_unit: PowerUnit = PowerUnit.MW,
    source_timezone: str | None = None,
    interval_grid: IntervalGrid | None = None,
) -> ConsumptionCsvAdapter:
    return ConsumptionCsvAdapter(
        path=path,
        source_name=_SOURCE,
        field_specs=field_specs,
        clock=lambda: _FIXED_TIME,
        source_power_unit=source_power_unit,
        source_timezone=source_timezone,
        interval_grid=interval_grid,
    )


def _outward_text(result: StructuredIngestionResult[ConsumptionRecord]) -> str:
    parts = [result.source_name]
    for diagnostic in result.diagnostics:
        parts.extend(
            [
                diagnostic.code,
                diagnostic.message,
                diagnostic.field_name or "",
            ]
        )
    for record in result.dlq_records:
        parts.extend(
            [
                record.record_id,
                record.source_name,
                record.adapter_name,
                record.payload_reference,
                record.correlation_id or "",
            ]
        )
        for diagnostic in record.diagnostics:
            parts.extend(
                [
                    diagnostic.code,
                    diagnostic.message,
                    diagnostic.field_name or "",
                ]
            )
    return "\n".join(parts)


async def test_exact_ingestion_preserves_order_and_normalizes_timestamps(
    tmp_path: Path,
) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        "customer-1,2026-09-05T00:00:00+04:00,12.5\n"
        "customer-2,2026-09-05T01:00:00+04:00,8.0\n",
    )
    adapter = _adapter(path)
    port: StructuredIngestionPort[ConsumptionRecord] = adapter
    result = await port.ingest()

    assert result.source_name == _SOURCE
    assert len(result.records) == 2
    assert result.dlq_records == ()
    assert result.records[0].consumer_id == "customer-1"
    assert result.records[0].value_mw == 12.5
    assert result.records[0].timestamp == _VALID_TS_UTC
    assert result.records[1].consumer_id == "customer-2"
    assert result.records[1].timestamp == datetime(2026, 9, 4, 21, 0, tzinfo=UTC)
    assert result.records[1].timestamp.tzinfo is UTC


async def test_consumption_mw_alias_is_accepted_without_unit_conversion(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        f"consumer_id,timestamp,Consumption_MW\ncustomer-1,{_VALID_TS},12.5\n",
    )
    result = await _adapter(path).ingest()
    assert len(result.records) == 1
    assert result.records[0].value_mw == 12.5
    assert result.dlq_records == ()
    assert all(item.code != "csv_fuzzy_field_resolution" for item in result.diagnostics)


async def test_fuzzy_mw_header_emits_canonical_warning_without_raw_typo(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        f"consumer_id,timestamp,Consumpton_MW\ncustomer-1,{_VALID_TS},12.5\n",
    )
    result = await _adapter(path).ingest()
    assert len(result.records) == 1
    assert result.records[0].value_mw == 12.5
    warnings = [item for item in result.diagnostics if item.code == "csv_fuzzy_field_resolution"]
    assert len(warnings) == 1
    assert warnings[0].severity is DiagnosticSeverity.WARNING
    assert warnings[0].field_name == "value_mw"
    outward = _outward_text(result)
    assert "Consumpton_MW" not in outward
    assert "Consumpton" not in warnings[0].message


async def test_naive_timestamp_is_isolated_without_timezone_inference(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        f"customer-1,{_VALID_TS},12.5\n"
        "customer-2,2026-09-05T00:00:00,9.0\n",
    )
    result = await _adapter(path).ingest()
    assert len(result.records) == 1
    assert result.records[0].consumer_id == "customer-1"
    assert len(result.dlq_records) == 1
    assert result.diagnostics[0].code == "csv_row_validation_failed"
    assert result.diagnostics[0].field_name is None
    assert "Asia/Yerevan" not in _outward_text(result)
    assert "+04:00" not in result.diagnostics[0].message


async def test_bare_numeric_timestamp_string_is_not_unix_epoch(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        f"good-1,{_VALID_TS},1.5\n"
        "numeric-ts,1710000000,9.0\n"
        f"good-2,{_VALID_TS},2.5\n",
    )
    result = await _adapter(path).ingest()
    assert [record.consumer_id for record in result.records] == ["good-1", "good-2"]
    assert len(result.dlq_records) == 1
    assert result.diagnostics[0].code == "csv_row_validation_failed"
    coerced = datetime.fromtimestamp(1_710_000_000, tz=UTC)
    assert all(record.timestamp != coerced for record in result.records)
    outward = _outward_text(result)
    assert "1710000000" not in outward
    assert "numeric-ts" not in outward
    assert "Unix" not in outward
    assert "epoch" not in outward
    assert "1710000000" not in repr(result)


async def test_invalid_mw_values_are_isolated(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        f"ok-1,{_VALID_TS},1.0\n"
        f"neg,{_VALID_TS},-0.1\n"
        f"text,{_VALID_TS},not-a-number\n"
        f"nan,{_VALID_TS},NaN\n"
        f"inf,{_VALID_TS},inf\n"
        f"ok-2,{_VALID_TS},2.0\n",
    )
    result = await _adapter(path).ingest()
    assert [record.consumer_id for record in result.records] == ["ok-1", "ok-2"]
    assert len(result.dlq_records) == 4
    assert all(item.code == "csv_row_validation_failed" for item in result.diagnostics)


async def test_partial_success_keeps_valid_rows(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        f"good-1,{_VALID_TS},1.5\n"
        f"bad,{_VALID_TS},-9\n"
        f"good-2,{_VALID_TS},2.5\n",
    )
    result = await _adapter(path).ingest()
    assert [record.consumer_id for record in result.records] == ["good-1", "good-2"]
    assert len(result.diagnostics) == 1
    assert len(result.dlq_records) == 1
    assert result.dlq_records[0].record_id == f"{_SOURCE}:row:3"
    assert result.dlq_records[0].payload_reference == f"csv://{_SOURCE}/row/3"
    assert result.dlq_records[0].failed_at == _FIXED_TIME
    assert result.dlq_records[0].adapter_name == "consumption_csv"


async def test_complete_normalization_failure_has_no_records(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        f"consumer_id,timestamp,value_mw\nbad-1,{_VALID_TS},-1\nbad-2,{_VALID_TS},-2\n",
    )
    result = await _adapter(path).ingest()
    assert result.records == ()
    assert len(result.dlq_records) == 2
    assert len(result.diagnostics) == 2


async def test_empty_source_returns_empty_collections(tmp_path: Path) -> None:
    path = _write(tmp_path, "")
    result = await _adapter(path).ingest()
    assert result.records == ()
    assert result.diagnostics == ()
    assert result.dlq_records == ()


async def test_header_only_source_is_successful_empty_batch(tmp_path: Path) -> None:
    path = _write(tmp_path, "consumer_id,timestamp,value_mw\n")
    result = await _adapter(path).ingest()
    assert result.records == ()
    assert result.dlq_records == ()
    assert result.source_name == _SOURCE


async def test_missing_required_field_is_fatal_schema_failure(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        f"consumer_id,timestamp\ncustomer-1,{_VALID_TS}\n",
    )
    result = await _adapter(path).ingest()
    assert result.records == ()
    assert len(result.dlq_records) == 1
    assert result.dlq_records[0].record_id == f"{_SOURCE}:schema"
    assert result.dlq_records[0].payload_reference == f"csv://{_SOURCE}/schema"
    missing = [item for item in result.diagnostics if item.code == "csv_missing_required_field"]
    assert len(missing) == 1
    assert missing[0].field_name == "value_mw"
    assert missing[0].severity is DiagnosticSeverity.ERROR
    assert "timestamp" not in missing[0].message or missing[0].field_name == "value_mw"
    outward = _outward_text(result)
    assert "consumer_id,timestamp" not in outward


@pytest.mark.parametrize(
    "unsafe_header",
    (
        "Consumption_kW",
        "Consumption_kWh",
        "Consumption_W",
        "Consumption_MWh",
        "Consumption_MW_h",
        "Consumption_MW-hour",
    ),
)
async def test_unsafe_power_or_energy_headers_are_not_accepted_as_canonical_mw(
    tmp_path: Path,
    unsafe_header: str,
) -> None:
    path = _write(
        tmp_path,
        f"consumer_id,timestamp,{unsafe_header}\ncustomer-1,{_VALID_TS},12500\n",
    )
    result = await _adapter(path).ingest()
    assert result.records == ()
    assert any(item.code == "csv_missing_required_field" for item in result.diagnostics)
    assert any(item.field_name == "value_mw" for item in result.diagnostics)
    outward = _outward_text(result)
    assert unsafe_header not in outward
    assert "12500" not in outward
    assert result.dlq_records[0].payload_reference.endswith("/schema")


async def test_duplicate_value_mw_mapping_is_fatal_collision(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        f"consumer_id,timestamp,value_mw,Consumption_MW\ncustomer-1,{_VALID_TS},12.5,12.5\n",
    )
    result = await _adapter(path).ingest()
    assert result.records == ()
    collisions = [item for item in result.diagnostics if item.code == "csv_schema_collision"]
    assert len(collisions) == 1
    assert collisions[0].field_name == "value_mw"
    assert "Consumption_MW" not in _outward_text(result)


async def test_ambiguous_header_fails_schema_closed(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        f"load_xw,timestamp,value_mw\ncustomer-1,{_VALID_TS},12.5\n",
    )
    result = await _adapter(path, field_specs=_AMBIGUOUS_SPECS).ingest()
    assert result.records == ()
    assert any(item.code == "csv_schema_ambiguous" for item in result.diagnostics)
    assert all(
        item.field_name is None or item.field_name != "load_xw" for item in result.diagnostics
    )
    assert "load_xw" not in _outward_text(result)


async def test_unresolved_extra_column_warns_and_continues(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        f"consumer_id,timestamp,value_mw,wind_speed_knots\ncustomer-1,{_VALID_TS},12.5,18\n",
    )
    result = await _adapter(path).ingest()
    assert len(result.records) == 1
    assert result.records[0].value_mw == 12.5
    warnings = [item for item in result.diagnostics if item.code == "csv_unresolved_column"]
    assert len(warnings) == 1
    assert warnings[0].severity is DiagnosticSeverity.WARNING
    assert warnings[0].field_name is None
    outward = _outward_text(result)
    assert "wind_speed_knots" not in outward
    assert "wind_speed" not in outward


async def test_row_length_mismatch_is_isolated(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        f"short,{_VALID_TS}\n"
        f"good,{_VALID_TS},1.5\n"
        f"long,{_VALID_TS},2.0,extra\n",
    )
    result = await _adapter(path).ingest()
    assert [record.consumer_id for record in result.records] == ["good"]
    assert len(result.dlq_records) == 2
    assert all(item.code == "csv_row_shape_invalid" for item in result.diagnostics)
    assert "extra" not in _outward_text(result)


async def test_missing_file_raises_sanitized_dependency_error(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.csv"
    adapter = _adapter(missing)
    with pytest.raises(DependencyUnavailableError, match="CSV source is unavailable") as caught:
        await adapter.ingest()
    message = caught.value.message
    assert "does-not-exist.csv" not in message
    assert str(missing) not in message
    assert str(tmp_path) not in message


async def test_directory_path_raises_sanitized_dependency_error(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path)
    with pytest.raises(DependencyUnavailableError, match="CSV source is unavailable") as caught:
        await adapter.ingest()
    assert str(tmp_path) not in caught.value.message


async def test_armenian_consumer_id_and_alias_survive_utf8(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        f"սպառող,timestamp,value_mw\nՍպառող-1,{_VALID_TS},3.25\n",
    )
    result = await _adapter(path, field_specs=_ARMENIAN_SPECS).ingest()
    assert len(result.records) == 1
    assert result.records[0].consumer_id == "Սպառող-1"
    assert result.records[0].value_mw == 3.25
    assert result.dlq_records == ()


async def test_raw_bad_value_does_not_cross_application_boundary(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        f"customer-1,{_VALID_TS},1.0\n"
        f"{_LEAK_TOKEN},{_VALID_TS},not-a-mw\n",
    )
    result = await _adapter(path).ingest()
    assert len(result.records) == 1
    assert result.records[0].consumer_id != _LEAK_TOKEN
    outward = _outward_text(result)
    assert _LEAK_TOKEN not in outward
    assert _LEAK_TOKEN not in repr(result)
    dumped = [item.model_dump() for item in result.diagnostics]
    dumped.extend(item.model_dump(mode="json") for item in result.dlq_records)
    assert _LEAK_TOKEN not in str(dumped)


async def test_malformed_csv_syntax_is_normalization_failure(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        'consumer_id,timestamp,value_mw\n"unterminated quote,2026-09-05T00:00:00+04:00,1.0\n',
    )
    result = await _adapter(path).ingest()
    assert any(item.code == "csv_parse_failed" for item in result.diagnostics)
    assert result.dlq_records[0].payload_reference == f"csv://{_SOURCE}/source"
    assert "unterminated" not in _outward_text(result)


async def test_invalid_utf8_is_normalization_failure_not_unavailable(tmp_path: Path) -> None:
    path = tmp_path / "broken.csv"
    path.write_bytes(b"consumer_id,timestamp,value_mw\n\xff\xfe")
    adapter = _adapter(path)
    result = await adapter.ingest()
    assert result.records == ()
    assert any(item.code == "csv_decode_failed" for item in result.diagnostics)
    assert result.dlq_records[0].record_id == f"{_SOURCE}:source"


async def test_blank_lines_are_skipped(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        "\n"
        f"customer-1,{_VALID_TS},1.0\n"
        "\n"
        f"customer-2,{_VALID_TS},2.0\n",
    )
    result = await _adapter(path).ingest()
    assert [record.consumer_id for record in result.records] == ["customer-1", "customer-2"]
    assert result.dlq_records == ()


def test_constructor_rejects_unrelated_canonical_fields() -> None:
    with pytest.raises(ValueError, match="exactly consumer_id, timestamp, and value_mw"):
        ConsumptionCsvAdapter(
            path=Path("unused.csv"),
            source_name=_SOURCE,
            field_specs=(
                CanonicalFieldSpec("consumer_id", aliases=(), required=True),
                CanonicalFieldSpec("timestamp", aliases=(), required=True),
                CanonicalFieldSpec("volume_mwh", aliases=(), required=True),
            ),
        )


def test_constructor_rejects_empty_source_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="source_name"):
        ConsumptionCsvAdapter(path=tmp_path / "x.csv", source_name="  ")


def test_constructor_rejects_unknown_timezone(tmp_path: Path) -> None:
    with pytest.raises(NormalizationConfigurationError, match="IANA timezone"):
        ConsumptionCsvAdapter(
            path=tmp_path / "x.csv",
            source_name=_SOURCE,
            source_timezone="Not/AZone",
        )


async def test_explicit_kw_converts_to_canonical_mw(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        f"consumer_id,timestamp,Consumption_kW\ncustomer-1,{_VALID_TS},12500\n",
    )
    result = await _adapter(path, source_power_unit=PowerUnit.KW).ingest()
    assert len(result.records) == 1
    assert result.records[0].value_mw == 12.5
    assert result.records[0].timestamp == _VALID_TS_UTC
    assert result.dlq_records == ()


async def test_kw_header_still_fails_under_default_mw_profile(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        f"consumer_id,timestamp,Consumption_kW\ncustomer-1,{_VALID_TS},12500\n",
    )
    result = await _adapter(path).ingest()
    assert result.records == ()
    assert any(item.code == "csv_missing_required_field" for item in result.diagnostics)
    assert "Consumption_kW" not in _outward_text(result)
    assert "12500" not in _outward_text(result)


async def test_kw_config_rejects_explicit_mw_header(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        f"consumer_id,timestamp,value_mw\ncustomer-1,{_VALID_TS},12.5\n",
    )
    result = await _adapter(path, source_power_unit=PowerUnit.KW).ingest()
    assert result.records == ()
    assert any(item.code == "csv_missing_required_field" for item in result.diagnostics)
    assert "value_mw" in {item.field_name for item in result.diagnostics}


async def test_fuzzy_kw_header_converts_with_warning(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        f"consumer_id,timestamp,Consumpton_kW\ncustomer-1,{_VALID_TS},12500\n",
    )
    result = await _adapter(path, source_power_unit=PowerUnit.KW).ingest()
    assert len(result.records) == 1
    assert result.records[0].value_mw == 12.5
    warnings = [item for item in result.diagnostics if item.code == "csv_fuzzy_field_resolution"]
    assert len(warnings) == 1
    assert warnings[0].field_name == "value_mw"
    assert "Consumpton" not in _outward_text(result)


async def test_naive_timestamp_with_explicit_timezone_succeeds(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\ncustomer-1,2026-01-15T12:00:00,12.5\n",
    )
    result = await _adapter(path, source_timezone="Europe/Berlin").ingest()
    assert len(result.records) == 1
    assert result.records[0].timestamp == datetime(2026, 1, 15, 11, 0, tzinfo=UTC)
    assert result.dlq_records == ()


async def test_naive_timestamp_without_timezone_still_fails(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\ncustomer-1,2026-01-15T12:00:00,12.5\n",
    )
    result = await _adapter(path).ingest()
    assert result.records == ()
    assert result.diagnostics[0].code == "csv_row_validation_failed"
    assert "Europe/Berlin" not in _outward_text(result)
    assert "2026-01-15" not in _outward_text(result)


async def test_aware_timestamp_is_not_overwritten_by_configured_zone(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        f"consumer_id,timestamp,value_mw\ncustomer-1,{_VALID_TS},12.5\n",
    )
    result = await _adapter(path, source_timezone="UTC").ingest()
    assert len(result.records) == 1
    assert result.records[0].timestamp == _VALID_TS_UTC


async def test_dst_ambiguous_and_nonexistent_rows_are_isolated(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        f"good-1,{_VALID_TS},1.5\n"
        "ambiguous,2026-10-25T02:30:00,2.0\n"
        "missing,2026-03-29T02:30:00,3.0\n"
        f"good-2,{_VALID_TS},4.0\n",
    )
    result = await _adapter(path, source_timezone="Europe/Berlin").ingest()
    assert [record.consumer_id for record in result.records] == ["good-1", "good-2"]
    assert len(result.dlq_records) == 2
    outward = _outward_text(result)
    assert "2026-10-25" not in outward
    assert "2026-03-29" not in outward
    assert "Berlin" not in outward
    assert "ambiguous" not in outward
    assert "fold" not in outward


def test_constructor_rejects_non_interval_grid(tmp_path: Path) -> None:
    with pytest.raises(NormalizationConfigurationError, match="IntervalGrid"):
        ConsumptionCsvAdapter(
            path=tmp_path / "x.csv",
            source_name=_SOURCE,
            interval_grid="hourly",  # type: ignore[arg-type]
        )


async def test_default_duplicate_detection_fails_all_members(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        f"keep,{_VALID_TS},1.0\n"
        "consumer-1,2026-09-05T03:00:00+00:00,12.5\n"
        "other,2026-09-05T04:00:00+00:00,2.0\n"
        "consumer-1,2026-09-05T03:00:00+00:00,12.5\n",
    )
    result = await _adapter(path).ingest()
    assert [record.consumer_id for record in result.records] == ["keep", "other"]
    duplicates = [
        item for item in result.diagnostics if item.code == "consumption_duplicate_timestamp"
    ]
    assert len(duplicates) == 2
    assert all(item.severity is DiagnosticSeverity.ERROR for item in duplicates)
    assert all(item.field_name == "timestamp" for item in duplicates)
    assert {record.payload_reference for record in result.dlq_records} == {
        f"csv://{_SOURCE}/row/3",
        f"csv://{_SOURCE}/row/5",
    }


async def test_conflicting_duplicate_values_fail_closed(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        "consumer-1,2026-09-05T03:00:00+00:00,12.5\n"
        "consumer-1,2026-09-05T03:00:00+00:00,13.0\n"
        "keep,2026-09-05T04:00:00+00:00,2.0\n",
    )
    result = await _adapter(path).ingest()
    assert [record.consumer_id for record in result.records] == ["keep"]
    assert all(item.code == "consumption_duplicate_timestamp" for item in result.diagnostics)
    assert len(result.dlq_records) == 2
    assert all(record.value_mw != 12.5 for record in result.records)
    assert all(record.value_mw != 13.0 for record in result.records)


async def test_same_timestamp_different_consumers_remain_valid(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        f"consumer-a,{_VALID_TS},12.5\n"
        f"consumer-b,{_VALID_TS},8.0\n",
    )
    result = await _adapter(path).ingest()
    assert [record.consumer_id for record in result.records] == ["consumer-a", "consumer-b"]
    assert result.dlq_records == ()
    assert all(item.code != "consumption_duplicate_timestamp" for item in result.diagnostics)


async def test_offset_equivalent_timestamps_are_duplicates(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        "same,2026-09-05T00:00:00+04:00,12.5\n"
        "same,2026-09-04T20:00:00+00:00,12.5\n",
    )
    result = await _adapter(path).ingest()
    assert result.records == ()
    assert len(result.dlq_records) == 2
    assert all(item.code == "consumption_duplicate_timestamp" for item in result.diagnostics)


async def test_nonadjacent_duplicates_are_detected(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        "dup,2026-09-05T03:00:00+00:00,1.0\n"
        "keep,2026-09-05T04:00:00+00:00,2.0\n"
        "dup,2026-09-05T03:00:00+00:00,1.0\n",
    )
    result = await _adapter(path).ingest()
    assert [record.consumer_id for record in result.records] == ["keep"]
    assert {record.payload_reference for record in result.dlq_records} == {
        f"csv://{_SOURCE}/row/2",
        f"csv://{_SOURCE}/row/4",
    }


async def test_explicit_hourly_grid_accepts_aligned_rows(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        "c1,2026-09-05T00:00:00+00:00,1.0\n"
        "c1,2026-09-05T01:00:00+00:00,2.0\n"
        "c1,2026-09-05T02:00:00+00:00,3.0\n",
    )
    result = await _adapter(path, interval_grid=_HOURLY_UTC).ingest()
    assert [record.value_mw for record in result.records] == [1.0, 2.0, 3.0]
    assert result.dlq_records == ()


async def test_off_grid_row_is_isolated(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        "keep-1,2026-09-05T00:00:00+00:00,1.0\n"
        "off,2026-09-05T00:30:00+00:00,2.0\n"
        "keep-2,2026-09-05T01:00:00+00:00,3.0\n",
    )
    result = await _adapter(path, interval_grid=_HOURLY_UTC).ingest()
    assert [record.consumer_id for record in result.records] == ["keep-1", "keep-2"]
    assert result.diagnostics[0].code == "consumption_interval_misaligned"
    assert result.diagnostics[0].field_name == "timestamp"
    assert result.dlq_records[0].payload_reference == f"csv://{_SOURCE}/row/3"


async def test_hourly_internal_gap_reports_diagnostic_without_dlq(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        "c1,2026-09-05T00:00:00+00:00,1.0\n"
        "c1,2026-09-05T02:00:00+00:00,2.0\n",
    )
    result = await _adapter(path, interval_grid=_HOURLY_UTC).ingest()
    assert [record.timestamp for record in result.records] == [
        datetime(2026, 9, 5, 0, 0, tzinfo=UTC),
        datetime(2026, 9, 5, 2, 0, tzinfo=UTC),
    ]
    assert result.dlq_records == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "consumption_missing_interval_gap"
    assert result.diagnostics[0].severity is DiagnosticSeverity.ERROR
    assert result.diagnostics[0].field_name == "timestamp"
    assert result.diagnostics[0].message == (
        "Consumption series is missing 1 interval on the configured grid."
    )


async def test_out_of_order_aligned_source_order_is_preserved(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        "c1,2026-09-05T02:00:00+00:00,2.0\n"
        "c1,2026-09-05T00:00:00+00:00,0.0\n"
        "c1,2026-09-05T01:00:00+00:00,1.0\n",
    )
    result = await _adapter(path, interval_grid=_HOURLY_UTC).ingest()
    assert [record.timestamp for record in result.records] == [
        datetime(2026, 9, 5, 2, 0, tzinfo=UTC),
        datetime(2026, 9, 5, 0, 0, tzinfo=UTC),
        datetime(2026, 9, 5, 1, 0, tzinfo=UTC),
    ]
    assert result.dlq_records == ()


async def test_off_grid_without_interval_grid_remains_valid(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\nc1,2026-09-05T00:30:00+00:00,1.0\n",
    )
    result = await _adapter(path).ingest()
    assert len(result.records) == 1
    assert result.dlq_records == ()


async def test_kw_and_timezone_paths_still_work_with_structural_validation(
    tmp_path: Path,
) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,Consumption_kW\n"
        "keep,2026-01-15T12:00:00,12500\n"
        "dup,2026-01-15T13:00:00,1000\n"
        "dup,2026-01-15T13:00:00,2000\n",
    )
    result = await _adapter(
        path,
        source_power_unit=PowerUnit.KW,
        source_timezone="Europe/Berlin",
        interval_grid=IntervalGrid(
            interval=timedelta(hours=1),
            anchor=datetime(2026, 1, 15, 0, 0, tzinfo=UTC),
        ),
    ).ingest()
    assert len(result.records) == 1
    assert result.records[0].consumer_id == "keep"
    assert result.records[0].value_mw == 12.5
    assert result.records[0].timestamp == datetime(2026, 1, 15, 11, 0, tzinfo=UTC)
    assert len(result.dlq_records) == 2
    assert all(item.code == "consumption_duplicate_timestamp" for item in result.diagnostics)


async def test_structural_diagnostics_do_not_leak_source_sentinels(tmp_path: Path) -> None:
    consumer = "SENTINEL-CONSUMER-c9k2"
    stamp = "2026-11-17T13:41:08+04:00"
    value = "64.017"
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        f"{consumer},{stamp},{value}\n"
        f"{consumer},{stamp},65.0\n"
        "keep,2026-09-05T00:30:00+00:00,1.0\n",
    )
    result = await _adapter(path, interval_grid=_HOURLY_UTC).ingest()
    assert [record.consumer_id for record in result.records] == []
    outward = _outward_text(result)
    assert consumer not in outward
    assert stamp not in outward
    assert value not in outward
    assert "64.017" not in outward
    assert "2026-11-17" not in outward
    assert "2026-09-05T00:00:00" not in outward
    assert "Asia/Yerevan" not in outward
    codes = {item.code for item in result.diagnostics}
    assert "consumption_duplicate_timestamp" in codes
    assert "consumption_interval_misaligned" in codes


async def test_no_grid_does_not_report_internal_gaps(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        "c1,2026-09-05T00:00:00+00:00,1.0\n"
        "c1,2026-09-05T05:00:00+00:00,2.0\n",
    )
    result = await _adapter(path).ingest()
    assert len(result.records) == 2
    assert result.dlq_records == ()
    assert all(item.code != "consumption_missing_interval_gap" for item in result.diagnostics)


async def test_multi_slot_gap_emits_one_compact_diagnostic(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        "c1,2026-09-05T00:00:00+00:00,1.0\n"
        "c1,2026-09-05T05:00:00+00:00,2.0\n",
    )
    result = await _adapter(path, interval_grid=_HOURLY_UTC).ingest()
    assert len(result.records) == 2
    assert result.dlq_records == ()
    gaps = [item for item in result.diagnostics if item.code == "consumption_missing_interval_gap"]
    assert len(gaps) == 1
    assert gaps[0].message == "Consumption series is missing 4 intervals on the configured grid."


async def test_multiple_gaps_emit_separate_diagnostics(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        "c1,2026-09-05T00:00:00+00:00,1.0\n"
        "c1,2026-09-05T02:00:00+00:00,2.0\n"
        "c1,2026-09-05T03:00:00+00:00,3.0\n"
        "c1,2026-09-05T06:00:00+00:00,4.0\n",
    )
    result = await _adapter(path, interval_grid=_HOURLY_UTC).ingest()
    assert len(result.records) == 4
    gaps = [item for item in result.diagnostics if item.code == "consumption_missing_interval_gap"]
    assert len(gaps) == 2
    assert result.dlq_records == ()


async def test_gap_detection_is_independent_per_consumer(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        "consumer-a,2026-09-05T00:00:00+00:00,1.0\n"
        "consumer-b,2026-09-05T00:00:00+00:00,2.0\n"
        "consumer-a,2026-09-05T02:00:00+00:00,3.0\n"
        "consumer-b,2026-09-05T01:00:00+00:00,4.0\n"
        "consumer-b,2026-09-05T02:00:00+00:00,5.0\n",
    )
    result = await _adapter(path, interval_grid=_HOURLY_UTC).ingest()
    assert len(result.records) == 5
    gaps = [item for item in result.diagnostics if item.code == "consumption_missing_interval_gap"]
    assert len(gaps) == 1
    assert "consumer-a" not in _outward_text(result)
    assert "consumer-b" not in _outward_text(result)


async def test_duplicate_induced_gap_has_row_dlq_but_no_gap_dlq(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        "c1,2026-09-05T00:00:00+00:00,1.0\n"
        "c1,2026-09-05T01:00:00+00:00,2.0\n"
        "c1,2026-09-05T01:00:00+00:00,3.0\n"
        "c1,2026-09-05T02:00:00+00:00,4.0\n",
    )
    result = await _adapter(path, interval_grid=_HOURLY_UTC).ingest()
    assert [record.value_mw for record in result.records] == [1.0, 4.0]
    assert len(result.dlq_records) == 2
    assert all("row/" in record.payload_reference for record in result.dlq_records)
    assert all("missing" not in record.payload_reference for record in result.dlq_records)
    codes = [item.code for item in result.diagnostics]
    assert codes.count("consumption_duplicate_timestamp") == 2
    assert codes.count("consumption_missing_interval_gap") == 1


async def test_off_grid_induced_gap_keeps_row_dlq_and_gap_diagnostic(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        "c1,2026-09-05T00:00:00+00:00,1.0\n"
        "c1,2026-09-05T00:30:00+00:00,2.0\n"
        "c1,2026-09-05T02:00:00+00:00,3.0\n",
    )
    result = await _adapter(path, interval_grid=_HOURLY_UTC).ingest()
    assert [record.value_mw for record in result.records] == [1.0, 3.0]
    assert len(result.dlq_records) == 1
    assert result.dlq_records[0].payload_reference == f"csv://{_SOURCE}/row/3"
    codes = [item.code for item in result.diagnostics]
    assert codes == [
        "consumption_interval_misaligned",
        "consumption_missing_interval_gap",
    ]


async def test_out_of_order_source_preserves_order_and_reports_gap(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        "c1,2026-09-05T03:00:00+00:00,3.0\n"
        "c1,2026-09-05T00:00:00+00:00,0.0\n"
        "c1,2026-09-05T02:00:00+00:00,2.0\n",
    )
    result = await _adapter(path, interval_grid=_HOURLY_UTC).ingest()
    assert [record.timestamp for record in result.records] == [
        datetime(2026, 9, 5, 3, 0, tzinfo=UTC),
        datetime(2026, 9, 5, 0, 0, tzinfo=UTC),
        datetime(2026, 9, 5, 2, 0, tzinfo=UTC),
    ]
    assert result.dlq_records == ()
    assert result.diagnostics[0].code == "consumption_missing_interval_gap"


async def test_kw_timezone_path_still_reports_internal_gap(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,Consumption_kW\n"
        "keep,2026-01-15T11:00:00,12500\n"
        "keep,2026-01-15T13:00:00,1000\n",
    )
    result = await _adapter(
        path,
        source_power_unit=PowerUnit.KW,
        source_timezone="UTC",
        interval_grid=IntervalGrid(
            interval=timedelta(hours=1),
            anchor=datetime(2026, 1, 15, 0, 0, tzinfo=UTC),
        ),
    ).ingest()
    assert [record.value_mw for record in result.records] == [12.5, 1.0]
    assert result.dlq_records == ()
    assert result.diagnostics[0].code == "consumption_missing_interval_gap"


async def test_gap_diagnostics_do_not_leak_source_or_gap_sentinels(tmp_path: Path) -> None:
    consumer = "GAP-CONSUMER-SENTINEL-m4q8"
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        f"{consumer},2026-04-11T07:13:00+00:00,11.017\n"
        f"{consumer},2026-04-11T12:13:00+00:00,22.019\n",
    )
    grid = IntervalGrid(
        interval=timedelta(hours=1),
        anchor=datetime(2026, 4, 11, 7, 13, tzinfo=UTC),
    )
    result = await _adapter(path, interval_grid=grid).ingest()
    assert len(result.records) == 2
    assert result.dlq_records == ()
    outward = _outward_text(result)
    assert consumer not in outward
    assert "11.017" not in outward
    assert "22.019" not in outward
    assert "2026-04-11T08:13:00" not in outward
    assert "07:13" not in outward
    assert "GAP-CONSUMER" not in outward
    assert result.diagnostics[0].code == "consumption_missing_interval_gap"
    assert "4 intervals" in result.diagnostics[0].message


async def test_gap_does_not_insert_synthetic_records(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "consumer_id,timestamp,value_mw\n"
        "c1,2026-09-05T00:00:00+00:00,1.0\n"
        "c1,2026-09-05T02:00:00+00:00,2.0\n",
    )
    result = await _adapter(path, interval_grid=_HOURLY_UTC).ingest()
    assert len(result.records) == 2
    assert datetime(2026, 9, 5, 1, 0, tzinfo=UTC) not in {
        record.timestamp for record in result.records
    }
