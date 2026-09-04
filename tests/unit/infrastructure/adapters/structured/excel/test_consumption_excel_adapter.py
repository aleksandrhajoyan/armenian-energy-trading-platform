"""Consumption Excel adapter unit tests."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from openpyxl import Workbook

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports import StructuredIngestionPort, StructuredIngestionResult
from energy_trading.domain.models import ConsumptionRecord, DiagnosticSeverity
from energy_trading.infrastructure.adapters.structured.excel import ConsumptionExcelAdapter
from energy_trading.infrastructure.adapters.structured.normalization import (
    NormalizationConfigurationError,
    PowerUnit,
)
from energy_trading.infrastructure.adapters.structured.schema_mapping import CanonicalFieldSpec

_FIXED_TIME = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
_SOURCE = "test-consumption"
_LEAK_TOKEN = "RAW-LEAK-TOKEN-9f3c1a"
_VALID_TS = "2026-09-05T00:00:00+04:00"
_VALID_TS_UTC = datetime(2026, 9, 4, 20, 0, tzinfo=UTC)
_EXACT_HEADERS = ["consumer_id", "timestamp", "value_mw"]

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


def _write(
    tmp_path: Path,
    rows: list[list[object]],
    *,
    name: str = "consumption.xlsx",
    sheet_title: str | None = None,
    extra_sheets: dict[str, list[list[object]]] | None = None,
) -> Path:
    path = tmp_path / name
    workbook = Workbook()
    worksheet = workbook.active
    assert worksheet is not None
    if sheet_title is not None:
        worksheet.title = sheet_title
    for row in rows:
        worksheet.append(row)
    if extra_sheets:
        for title, extra_rows in extra_sheets.items():
            extra = workbook.create_sheet(title)
            for row in extra_rows:
                extra.append(row)
    workbook.save(path)
    workbook.close()
    return path


def _adapter(
    path: Path,
    *,
    sheet_name: str | None = None,
    field_specs: tuple[CanonicalFieldSpec, ...] | None = None,
    source_power_unit: PowerUnit = PowerUnit.MW,
    source_timezone: str | None = None,
) -> ConsumptionExcelAdapter:
    return ConsumptionExcelAdapter(
        path=path,
        source_name=_SOURCE,
        sheet_name=sheet_name,
        field_specs=field_specs,
        clock=lambda: _FIXED_TIME,
        source_power_unit=source_power_unit,
        source_timezone=source_timezone,
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
        [
            _EXACT_HEADERS,
            ["customer-1", "2026-09-05T00:00:00+04:00", 12.5],
            ["customer-2", "2026-09-05T01:00:00+04:00", 8.0],
        ],
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
        [
            ["consumer_id", "timestamp", "Consumption_MW"],
            ["customer-1", _VALID_TS, 12.5],
        ],
    )
    result = await _adapter(path).ingest()
    assert len(result.records) == 1
    assert result.records[0].value_mw == 12.5
    assert result.dlq_records == ()
    assert all(item.code != "excel_fuzzy_field_resolution" for item in result.diagnostics)


async def test_fuzzy_mw_header_emits_canonical_warning_without_raw_typo(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            ["consumer_id", "timestamp", "Consumpton_MW"],
            ["customer-1", _VALID_TS, 12.5],
        ],
    )
    result = await _adapter(path).ingest()
    assert len(result.records) == 1
    assert result.records[0].value_mw == 12.5
    warnings = [item for item in result.diagnostics if item.code == "excel_fuzzy_field_resolution"]
    assert len(warnings) == 1
    assert warnings[0].severity is DiagnosticSeverity.WARNING
    assert warnings[0].field_name == "value_mw"
    outward = _outward_text(result)
    assert "Consumpton_MW" not in outward
    assert "Consumpton" not in warnings[0].message


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
        [
            ["consumer_id", "timestamp", unsafe_header],
            ["customer-1", _VALID_TS, 12500],
        ],
    )
    result = await _adapter(path).ingest()
    assert result.records == ()
    assert any(item.code == "excel_missing_required_field" for item in result.diagnostics)
    assert any(item.field_name == "value_mw" for item in result.diagnostics)
    outward = _outward_text(result)
    assert unsafe_header not in outward
    assert "12500" not in outward
    assert result.dlq_records[0].payload_reference.endswith("/schema")


async def test_timezone_aware_timestamp_string_normalizes_to_utc(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            _EXACT_HEADERS,
            ["customer-1", _VALID_TS, 12.5],
        ],
    )
    result = await _adapter(path).ingest()
    assert len(result.records) == 1
    assert result.records[0].timestamp == _VALID_TS_UTC
    assert result.records[0].timestamp.tzinfo is UTC
    assert result.dlq_records == ()


async def test_excel_typed_naive_datetime_fails_without_timezone_inference(
    tmp_path: Path,
) -> None:
    naive = datetime(2026, 9, 5, 0, 0, 0)
    assert naive.tzinfo is None
    path = _write(
        tmp_path,
        [
            _EXACT_HEADERS,
            ["customer-1", _VALID_TS, 12.5],
            ["customer-2", naive, 9.0],
            ["customer-3", "2026-09-05T01:00:00+04:00", 8.0],
        ],
    )
    result = await _adapter(path).ingest()
    assert [record.consumer_id for record in result.records] == ["customer-1", "customer-3"]
    assert len(result.dlq_records) == 1
    assert result.dlq_records[0].record_id == f"{_SOURCE}:row:3"
    assert result.diagnostics[0].code == "excel_row_validation_failed"
    assert result.diagnostics[0].field_name is None
    outward = _outward_text(result)
    assert "Asia/Yerevan" not in outward
    assert "+04:00" not in result.diagnostics[0].message
    assert "2026-09-05" not in result.diagnostics[0].message


@pytest.mark.parametrize("numeric_timestamp", (1, 45200, 1710000000, 1710000000.0))
async def test_numeric_timestamp_cells_are_not_unix_epoch(
    tmp_path: Path,
    numeric_timestamp: int | float,
) -> None:
    path = _write(
        tmp_path,
        [
            _EXACT_HEADERS,
            ["good-1", _VALID_TS, 1.5],
            ["numeric-ts", numeric_timestamp, 9.0],
            ["good-2", "2026-09-05T01:00:00+04:00", 2.5],
        ],
    )
    result = await _adapter(path).ingest()
    assert [record.consumer_id for record in result.records] == ["good-1", "good-2"]
    assert len(result.dlq_records) == 1
    assert result.dlq_records[0].record_id == f"{_SOURCE}:row:3"
    assert result.diagnostics[0].code == "excel_row_validation_failed"
    coerced = datetime.fromtimestamp(float(numeric_timestamp), tz=UTC)
    assert all(record.timestamp != coerced for record in result.records)
    outward = _outward_text(result)
    assert str(numeric_timestamp) not in outward
    assert "1710000000" not in outward
    assert "45200" not in outward
    assert "Unix" not in outward
    assert "epoch" not in outward


@pytest.mark.parametrize("boolean_mw", (True, False))
async def test_boolean_mw_cells_are_not_coerced_to_numeric_mw(
    tmp_path: Path,
    boolean_mw: bool,
) -> None:
    path = _write(
        tmp_path,
        [
            _EXACT_HEADERS,
            ["good-1", _VALID_TS, 1.5],
            ["bool-mw", _VALID_TS, boolean_mw],
            ["good-2", _VALID_TS, 2.5],
        ],
    )
    result = await _adapter(path).ingest()
    assert [record.consumer_id for record in result.records] == ["good-1", "good-2"]
    assert [record.value_mw for record in result.records] == [1.5, 2.5]
    assert len(result.dlq_records) == 1
    assert result.dlq_records[0].record_id == f"{_SOURCE}:row:3"
    assert result.diagnostics[0].code == "excel_row_validation_failed"
    outward = _outward_text(result)
    assert "True" not in outward
    assert "False" not in outward
    assert "bool-mw" not in outward


async def test_invalid_mw_values_are_isolated(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            _EXACT_HEADERS,
            ["ok-1", _VALID_TS, 1.0],
            ["neg", _VALID_TS, -0.1],
            ["text", _VALID_TS, "not-a-number"],
            ["nan", _VALID_TS, "NaN"],
            ["inf", _VALID_TS, "inf"],
            ["ok-2", _VALID_TS, 2.0],
        ],
    )
    result = await _adapter(path).ingest()
    assert [record.consumer_id for record in result.records] == ["ok-1", "ok-2"]
    assert len(result.dlq_records) == 4
    assert all(item.code == "excel_row_validation_failed" for item in result.diagnostics)


async def test_partial_success_keeps_valid_rows(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            _EXACT_HEADERS,
            ["good-1", _VALID_TS, 1.5],
            ["bad", _VALID_TS, -9],
            ["good-2", _VALID_TS, 2.5],
        ],
    )
    result = await _adapter(path).ingest()
    assert [record.consumer_id for record in result.records] == ["good-1", "good-2"]
    assert len(result.diagnostics) == 1
    assert len(result.dlq_records) == 1
    assert result.dlq_records[0].record_id == f"{_SOURCE}:row:3"
    assert result.dlq_records[0].payload_reference == f"excel://{_SOURCE}/row/3"
    assert result.dlq_records[0].failed_at == _FIXED_TIME
    assert result.dlq_records[0].adapter_name == "consumption_excel"


async def test_empty_worksheet_returns_empty_collections(tmp_path: Path) -> None:
    path = _write(tmp_path, [])
    result = await _adapter(path).ingest()
    assert result.records == ()
    assert result.diagnostics == ()
    assert result.dlq_records == ()


async def test_header_only_worksheet_is_successful_empty_batch(tmp_path: Path) -> None:
    path = _write(tmp_path, [_EXACT_HEADERS])
    result = await _adapter(path).ingest()
    assert result.records == ()
    assert result.dlq_records == ()
    assert result.source_name == _SOURCE


async def test_missing_required_field_is_fatal_schema_failure(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            ["consumer_id", "timestamp"],
            ["customer-1", _VALID_TS],
        ],
    )
    result = await _adapter(path).ingest()
    assert result.records == ()
    assert len(result.dlq_records) == 1
    assert result.dlq_records[0].record_id == f"{_SOURCE}:schema"
    assert result.dlq_records[0].payload_reference == f"excel://{_SOURCE}/schema"
    missing = [item for item in result.diagnostics if item.code == "excel_missing_required_field"]
    assert len(missing) == 1
    assert missing[0].field_name == "value_mw"
    assert missing[0].severity is DiagnosticSeverity.ERROR
    outward = _outward_text(result)
    assert "consumer_id,timestamp" not in outward
    assert "customer-1" not in outward


async def test_duplicate_value_mw_mapping_is_fatal_collision(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            ["consumer_id", "timestamp", "value_mw", "Consumption_MW"],
            ["customer-1", _VALID_TS, 12.5, 12.5],
        ],
    )
    result = await _adapter(path).ingest()
    assert result.records == ()
    collisions = [item for item in result.diagnostics if item.code == "excel_schema_collision"]
    assert len(collisions) == 1
    assert collisions[0].field_name == "value_mw"
    assert "Consumption_MW" not in _outward_text(result)


async def test_ambiguous_header_fails_schema_closed(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            ["load_xw", "timestamp", "value_mw"],
            ["customer-1", _VALID_TS, 12.5],
        ],
    )
    result = await _adapter(path, field_specs=_AMBIGUOUS_SPECS).ingest()
    assert result.records == ()
    assert any(item.code == "excel_schema_ambiguous" for item in result.diagnostics)
    assert all(
        item.field_name is None or item.field_name != "load_xw" for item in result.diagnostics
    )
    assert "load_xw" not in _outward_text(result)


async def test_unresolved_extra_column_warns_and_continues(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            ["consumer_id", "timestamp", "value_mw", "wind_speed_knots"],
            ["customer-1", _VALID_TS, 12.5, 18],
        ],
    )
    result = await _adapter(path).ingest()
    assert len(result.records) == 1
    assert result.records[0].value_mw == 12.5
    warnings = [item for item in result.diagnostics if item.code == "excel_unresolved_column"]
    assert len(warnings) == 1
    assert warnings[0].severity is DiagnosticSeverity.WARNING
    assert warnings[0].field_name is None
    outward = _outward_text(result)
    assert "wind_speed_knots" not in outward
    assert "wind_speed" not in outward


async def test_missing_mapped_cell_is_isolated(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            _EXACT_HEADERS,
            ["short", _VALID_TS],
            ["good", _VALID_TS, 1.5],
        ],
    )
    result = await _adapter(path).ingest()
    assert [record.consumer_id for record in result.records] == ["good"]
    assert len(result.dlq_records) == 1
    # openpyxl yields None for unused trailing cells in the used range; the
    # adapter must not invent a MW value and must isolate the row.
    assert result.diagnostics[0].code == "excel_row_validation_failed"
    assert result.dlq_records[0].payload_reference == f"excel://{_SOURCE}/row/2"


async def test_missing_file_raises_sanitized_dependency_error(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.xlsx"
    adapter = _adapter(missing)
    with pytest.raises(DependencyUnavailableError, match="Excel source is unavailable") as caught:
        await adapter.ingest()
    message = caught.value.message
    assert "does-not-exist.xlsx" not in message
    assert str(missing) not in message
    assert str(tmp_path) not in message


async def test_corrupt_workbook_is_normalization_failure_not_unavailable(tmp_path: Path) -> None:
    path = tmp_path / "broken.xlsx"
    path.write_bytes(b"this is not a valid xlsx workbook")
    result = await _adapter(path).ingest()
    assert result.records == ()
    assert any(item.code == "excel_workbook_invalid" for item in result.diagnostics)
    assert result.dlq_records[0].record_id == f"{_SOURCE}:source"
    assert result.dlq_records[0].payload_reference == f"excel://{_SOURCE}/source"
    outward = _outward_text(result)
    assert "zip" not in outward.lower()
    assert str(path) not in outward


async def test_missing_configured_worksheet_fails_without_active_fallback(
    tmp_path: Path,
) -> None:
    path = _write(
        tmp_path,
        [
            _EXACT_HEADERS,
            ["active-row", _VALID_TS, 12.5],
        ],
        sheet_title="ActiveData",
        extra_sheets={
            "Other": [
                _EXACT_HEADERS,
                ["other-row", _VALID_TS, 3.0],
            ]
        },
    )
    result = await _adapter(path, sheet_name="MissingSheet").ingest()
    assert result.records == ()
    assert any(item.code == "excel_worksheet_missing" for item in result.diagnostics)
    assert result.dlq_records[0].record_id == f"{_SOURCE}:schema"
    outward = _outward_text(result)
    assert "MissingSheet" not in outward
    assert "ActiveData" not in outward
    assert "Other" not in outward
    assert "active-row" not in outward
    assert "other-row" not in outward


async def test_explicit_sheet_name_is_used_instead_of_active(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            _EXACT_HEADERS,
            ["active-row", _VALID_TS, 1.0],
        ],
        extra_sheets={
            "Load": [
                _EXACT_HEADERS,
                ["sheet-row", _VALID_TS, 4.5],
            ]
        },
    )
    result = await _adapter(path, sheet_name="Load").ingest()
    assert [record.consumer_id for record in result.records] == ["sheet-row"]
    assert result.records[0].value_mw == 4.5
    assert result.dlq_records == ()


async def test_armenian_consumer_id_and_alias_survive(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            ["սպառող", "timestamp", "value_mw"],
            ["Սպառող-1", _VALID_TS, 3.25],
        ],
    )
    result = await _adapter(path, field_specs=_ARMENIAN_SPECS).ingest()
    assert len(result.records) == 1
    assert result.records[0].consumer_id == "Սպառող-1"
    assert result.records[0].value_mw == 3.25
    assert result.dlq_records == ()


async def test_raw_bad_value_does_not_cross_application_boundary(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            _EXACT_HEADERS,
            ["customer-1", _VALID_TS, 1.0],
            [_LEAK_TOKEN, _VALID_TS, "not-a-mw"],
        ],
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


async def test_blank_rows_are_skipped(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            _EXACT_HEADERS,
            [],
            ["customer-1", _VALID_TS, 1.0],
            [None, None, None],
            ["customer-2", _VALID_TS, 2.0],
        ],
    )
    result = await _adapter(path).ingest()
    assert [record.consumer_id for record in result.records] == ["customer-1", "customer-2"]
    assert result.dlq_records == ()


def test_constructor_rejects_unrelated_canonical_fields() -> None:
    with pytest.raises(ValueError, match="exactly consumer_id, timestamp, and value_mw"):
        ConsumptionExcelAdapter(
            path=Path("unused.xlsx"),
            source_name=_SOURCE,
            field_specs=(
                CanonicalFieldSpec("consumer_id", aliases=(), required=True),
                CanonicalFieldSpec("timestamp", aliases=(), required=True),
                CanonicalFieldSpec("volume_mwh", aliases=(), required=True),
            ),
        )


def test_constructor_rejects_empty_source_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="source_name"):
        ConsumptionExcelAdapter(path=tmp_path / "x.xlsx", source_name="  ")


def test_constructor_rejects_empty_sheet_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="sheet_name"):
        ConsumptionExcelAdapter(
            path=tmp_path / "x.xlsx",
            source_name=_SOURCE,
            sheet_name="  ",
        )


def test_constructor_rejects_non_xlsx_suffix(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="xlsx"):
        ConsumptionExcelAdapter(path=tmp_path / "file.xls", source_name=_SOURCE)


def test_constructor_rejects_unknown_timezone(tmp_path: Path) -> None:
    with pytest.raises(NormalizationConfigurationError, match="IANA timezone"):
        ConsumptionExcelAdapter(
            path=tmp_path / "x.xlsx",
            source_name=_SOURCE,
            source_timezone="Not/AZone",
        )


async def test_explicit_kw_numeric_cell_converts_to_canonical_mw(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            ["consumer_id", "timestamp", "Consumption_kW"],
            ["customer-1", _VALID_TS, 12500],
        ],
    )
    result = await _adapter(path, source_power_unit=PowerUnit.KW).ingest()
    assert len(result.records) == 1
    assert result.records[0].value_mw == 12.5
    assert result.records[0].timestamp == _VALID_TS_UTC


async def test_kw_header_still_fails_under_default_mw_profile(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            ["consumer_id", "timestamp", "Consumption_kW"],
            ["customer-1", _VALID_TS, 12500],
        ],
    )
    result = await _adapter(path).ingest()
    assert result.records == ()
    assert any(item.code == "excel_missing_required_field" for item in result.diagnostics)
    assert "Consumption_kW" not in _outward_text(result)


async def test_kw_config_rejects_explicit_mw_header(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            _EXACT_HEADERS,
            ["customer-1", _VALID_TS, 12.5],
        ],
    )
    result = await _adapter(path, source_power_unit=PowerUnit.KW).ingest()
    assert result.records == ()
    assert any(item.field_name == "value_mw" for item in result.diagnostics)


async def test_typed_naive_datetime_with_explicit_timezone_succeeds(tmp_path: Path) -> None:
    naive = datetime(2026, 1, 15, 12, 0, 0)
    path = _write(
        tmp_path,
        [
            _EXACT_HEADERS,
            ["customer-1", naive, 12.5],
        ],
    )
    result = await _adapter(path, source_timezone="Europe/Berlin").ingest()
    assert len(result.records) == 1
    assert result.records[0].timestamp == datetime(2026, 1, 15, 11, 0, tzinfo=UTC)
    assert result.dlq_records == ()


async def test_aware_timestamp_string_is_not_overwritten_by_configured_zone(
    tmp_path: Path,
) -> None:
    path = _write(
        tmp_path,
        [
            _EXACT_HEADERS,
            ["customer-1", _VALID_TS, 12.5],
        ],
    )
    result = await _adapter(path, source_timezone="Europe/Berlin").ingest()
    assert result.records[0].timestamp == _VALID_TS_UTC


async def test_numeric_excel_timestamp_still_rejected_with_timezone(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            _EXACT_HEADERS,
            ["customer-1", 1710000000, 12.5],
        ],
    )
    result = await _adapter(path, source_timezone="UTC").ingest()
    assert result.records == ()
    assert result.diagnostics[0].code == "excel_row_validation_failed"
    assert "1710000000" not in _outward_text(result)


async def test_boolean_measurement_still_rejected_for_kw(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            ["consumer_id", "timestamp", "Consumption_kW"],
            ["good-1", _VALID_TS, 1000],
            ["bool-row", _VALID_TS, True],
            ["good-2", _VALID_TS, 2000],
        ],
    )
    result = await _adapter(path, source_power_unit=PowerUnit.KW).ingest()
    assert [record.consumer_id for record in result.records] == ["good-1", "good-2"]
    assert [record.value_mw for record in result.records] == [1.0, 2.0]
    assert "True" not in _outward_text(result)


async def test_dst_ambiguous_and_nonexistent_excel_rows_are_isolated(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            _EXACT_HEADERS,
            ["good-1", _VALID_TS, 1.5],
            ["ambiguous", datetime(2026, 10, 25, 2, 30, 0), 2.0],
            ["missing", datetime(2026, 3, 29, 2, 30, 0), 3.0],
            ["good-2", _VALID_TS, 4.0],
        ],
    )
    result = await _adapter(path, source_timezone="Europe/Berlin").ingest()
    assert [record.consumer_id for record in result.records] == ["good-1", "good-2"]
    assert len(result.dlq_records) == 2
    outward = _outward_text(result)
    assert "Berlin" not in outward
    assert "2026-10-25" not in outward
    assert "ambiguous" not in outward
