"""Consumption CSV adapter: the first concrete structured source reader.

CSV acquisition, schema interpretation, optional explicit unit/timezone
normalization, row validation, and batch time-series structural validation
stay inside infrastructure. The application receives only
``StructuredIngestionResult``. Units, timezones, and interval cadence are
never inferred.
"""

from __future__ import annotations

import asyncio
import csv
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports.structured_ingestion import StructuredIngestionResult
from energy_trading.domain.models.ingestion import AdapterDiagnostic, DiagnosticSeverity, DLQRecord
from energy_trading.domain.models.observations import ConsumptionRecord
from energy_trading.infrastructure.adapters.structured.consumption_mapping import (
    apply_consumption_unit_safety,
    canonical_column_index,
    default_consumption_field_specs,
    validated_consumption_field_specs,
)
from energy_trading.infrastructure.adapters.structured.consumption_values import (
    UnrecognizedConsumptionSourceValue,
    consumption_timestamp_from_csv,
)
from energy_trading.infrastructure.adapters.structured.normalization import (
    NormalizationConfigurationError,
    PowerUnit,
    SourceValueNormalizationError,
    normalize_power_to_mw,
    normalize_timestamp_to_utc,
    resolve_source_timezone,
)
from energy_trading.infrastructure.adapters.structured.schema_mapping import (
    CanonicalFieldSpec,
    DeterministicFieldResolver,
    FieldResolutionMethod,
    FieldResolutionStatus,
    SchemaResolution,
)
from energy_trading.infrastructure.adapters.structured.time_series import (
    ConsumptionRecordCandidate,
    ConsumptionSeriesIssue,
    IntervalGrid,
    validate_consumption_series,
)

_ADAPTER_NAME = "consumption_csv"

_MSG_MISSING_REQUIRED = "CSV schema is missing a required canonical field."
_MSG_AMBIGUOUS = "CSV schema contains an ambiguous header mapping."
_MSG_COLLISION = "CSV schema maps multiple columns to the same canonical field."
_MSG_UNRESOLVED = "CSV schema contains an unresolved extra column."
_MSG_FUZZY = "CSV header was resolved with deterministic fuzzy matching."
_MSG_ROW_SHAPE = "CSV row does not match the resolved header width."
_MSG_ROW_VALIDATION = "CSV row could not be converted to ConsumptionRecord."
_MSG_PARSE = "CSV source could not be parsed."
_MSG_DECODE = "CSV source is not valid UTF-8."
_MSG_UNAVAILABLE = "CSV source is unavailable"


class ConsumptionCsvAdapter:
    """Infrastructure adapter that structurally satisfies ``StructuredIngestionPort``.

    Source path and field-mapping configuration are constructor-injected. They
    are not part of the application-facing ``ingest()`` signature.
    """

    def __init__(
        self,
        *,
        path: Path,
        source_name: str,
        field_specs: tuple[CanonicalFieldSpec, ...] | None = None,
        clock: Callable[[], datetime] | None = None,
        source_power_unit: PowerUnit = PowerUnit.MW,
        source_timezone: str | None = None,
        interval_grid: IntervalGrid | None = None,
    ) -> None:
        self._path = _require_path(path)
        cleaned_source = source_name.strip()
        if not cleaned_source:
            msg = "source_name must be a non-empty string"
            raise ValueError(msg)
        if not isinstance(source_power_unit, PowerUnit):
            raise NormalizationConfigurationError("source_power_unit must be a PowerUnit")
        self._source_power_unit = source_power_unit
        self._source_timezone = resolve_source_timezone(source_timezone)
        self._interval_grid = _optional_interval_grid(interval_grid)
        specs = (
            default_consumption_field_specs(source_power_unit)
            if field_specs is None
            else field_specs
        )
        self._source_name = cleaned_source
        self._clock = clock if clock is not None else _utc_now
        self._resolver = DeterministicFieldResolver(validated_consumption_field_specs(specs))

    @property
    def source_name(self) -> str:
        return self._source_name

    async def ingest(self) -> StructuredIngestionResult[ConsumptionRecord]:
        return await asyncio.to_thread(self._ingest_sync)

    def _ingest_sync(self) -> StructuredIngestionResult[ConsumptionRecord]:
        try:
            return self._read_and_normalize()
        except OSError as exc:
            raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc

    def _read_and_normalize(self) -> StructuredIngestionResult[ConsumptionRecord]:
        candidates: list[ConsumptionRecordCandidate] = []
        diagnostics: list[AdapterDiagnostic] = []
        dlq_records: list[DLQRecord] = []
        try:
            with self._path.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle, strict=True)
                header: list[str] | None = None
                column_index: dict[str, int] = {}
                expected_width = 0
                logical_row = 0
                for raw_row in reader:
                    if _is_blank_row(raw_row):
                        continue
                    logical_row += 1
                    if header is None:
                        header = list(raw_row)
                        schema = apply_consumption_unit_safety(
                            self._resolver.resolve_schema(header),
                            source_power_unit=self._source_power_unit,
                        )
                        schema_diagnostics, fatal_errors = _schema_diagnostics(schema)
                        diagnostics.extend(schema_diagnostics)
                        if fatal_errors:
                            dlq_records.append(self._schema_dlq(fatal_errors))
                            return self._result([], diagnostics, dlq_records)
                        column_index = canonical_column_index(schema)
                        expected_width = len(header)
                        continue
                    self._ingest_data_row(
                        row=raw_row,
                        logical_row=logical_row,
                        expected_width=expected_width,
                        column_index=column_index,
                        candidates=candidates,
                        diagnostics=diagnostics,
                        dlq_records=dlq_records,
                    )
        except UnicodeDecodeError:
            diagnostic = _error("csv_decode_failed", _MSG_DECODE)
            diagnostics.append(diagnostic)
            dlq_records.append(self._source_dlq((diagnostic,)))
        except csv.Error:
            diagnostic = _error("csv_parse_failed", _MSG_PARSE)
            diagnostics.append(diagnostic)
            dlq_records.append(self._source_dlq((diagnostic,)))
        return self._with_series_validation(candidates, diagnostics, dlq_records)

    def _ingest_data_row(
        self,
        *,
        row: list[str],
        logical_row: int,
        expected_width: int,
        column_index: dict[str, int],
        candidates: list[ConsumptionRecordCandidate],
        diagnostics: list[AdapterDiagnostic],
        dlq_records: list[DLQRecord],
    ) -> None:
        if len(row) != expected_width:
            diagnostic = _error("csv_row_shape_invalid", _MSG_ROW_SHAPE)
            diagnostics.append(diagnostic)
            dlq_records.append(self._row_dlq(logical_row, (diagnostic,)))
            return
        try:
            payload = {
                "consumer_id": row[column_index["consumer_id"]],
                "timestamp": normalize_timestamp_to_utc(
                    consumption_timestamp_from_csv(row[column_index["timestamp"]]),
                    self._source_timezone,
                ),
                "value_mw": normalize_power_to_mw(
                    row[column_index["value_mw"]],
                    self._source_power_unit,
                ),
            }
            candidates.append(
                ConsumptionRecordCandidate(
                    record=ConsumptionRecord.model_validate(payload),
                    source_position=logical_row,
                )
            )
        except (
            UnrecognizedConsumptionSourceValue,
            SourceValueNormalizationError,
            ValidationError,
        ):
            diagnostic = _error("csv_row_validation_failed", _MSG_ROW_VALIDATION)
            diagnostics.append(diagnostic)
            dlq_records.append(self._row_dlq(logical_row, (diagnostic,)))

    def _with_series_validation(
        self,
        candidates: list[ConsumptionRecordCandidate],
        diagnostics: list[AdapterDiagnostic],
        dlq_records: list[DLQRecord],
    ) -> StructuredIngestionResult[ConsumptionRecord]:
        series = validate_consumption_series(candidates, self._interval_grid)
        for issue in series.issues:
            diagnostic = _series_diagnostic(issue)
            diagnostics.append(diagnostic)
            dlq_records.append(self._row_dlq(issue.source_position, (diagnostic,)))
        return self._result(
            [candidate.record for candidate in series.valid_candidates],
            diagnostics,
            dlq_records,
        )

    def _result(
        self,
        records: list[ConsumptionRecord],
        diagnostics: list[AdapterDiagnostic],
        dlq_records: list[DLQRecord],
    ) -> StructuredIngestionResult[ConsumptionRecord]:
        return StructuredIngestionResult(
            source_name=self._source_name,
            records=tuple(records),
            diagnostics=tuple(diagnostics),
            dlq_records=tuple(dlq_records),
        )

    def _schema_dlq(self, diagnostics: tuple[AdapterDiagnostic, ...]) -> DLQRecord:
        return self._dlq(
            record_id=f"{self._source_name}:schema",
            payload_reference=f"csv://{self._source_name}/schema",
            diagnostics=diagnostics,
        )

    def _source_dlq(self, diagnostics: tuple[AdapterDiagnostic, ...]) -> DLQRecord:
        return self._dlq(
            record_id=f"{self._source_name}:source",
            payload_reference=f"csv://{self._source_name}/source",
            diagnostics=diagnostics,
        )

    def _row_dlq(self, logical_row: int, diagnostics: tuple[AdapterDiagnostic, ...]) -> DLQRecord:
        return self._dlq(
            record_id=f"{self._source_name}:row:{logical_row}",
            payload_reference=f"csv://{self._source_name}/row/{logical_row}",
            diagnostics=diagnostics,
        )

    def _dlq(
        self,
        *,
        record_id: str,
        payload_reference: str,
        diagnostics: tuple[AdapterDiagnostic, ...],
    ) -> DLQRecord:
        return DLQRecord(
            record_id=record_id,
            failed_at=self._clock(),
            source_name=self._source_name,
            adapter_name=_ADAPTER_NAME,
            diagnostics=diagnostics,
            payload_reference=payload_reference,
        )


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _require_path(value: object) -> Path:
    if not isinstance(value, Path):
        msg = "path must be a pathlib.Path"
        raise TypeError(msg)
    return value


def _optional_interval_grid(value: IntervalGrid | None) -> IntervalGrid | None:
    if value is None:
        return None
    if not isinstance(value, IntervalGrid):
        raise NormalizationConfigurationError("interval_grid must be an IntervalGrid")
    return value


def _is_blank_row(row: Sequence[str]) -> bool:
    return all(not cell.strip() for cell in row)


def _schema_diagnostics(
    schema: SchemaResolution,
) -> tuple[list[AdapterDiagnostic], tuple[AdapterDiagnostic, ...]]:
    diagnostics: list[AdapterDiagnostic] = []
    fatal: list[AdapterDiagnostic] = []
    for canonical in schema.missing_required_fields:
        diagnostic = AdapterDiagnostic(
            code="csv_missing_required_field",
            message=_MSG_MISSING_REQUIRED,
            severity=DiagnosticSeverity.ERROR,
            field_name=canonical,
        )
        diagnostics.append(diagnostic)
        fatal.append(diagnostic)
    for resolution in schema.field_resolutions:
        if resolution.status is FieldResolutionStatus.AMBIGUOUS:
            diagnostic = _error("csv_schema_ambiguous", _MSG_AMBIGUOUS)
            diagnostics.append(diagnostic)
            fatal.append(diagnostic)
        elif resolution.status is FieldResolutionStatus.UNRESOLVED:
            diagnostics.append(
                AdapterDiagnostic(
                    code="csv_unresolved_column",
                    message=_MSG_UNRESOLVED,
                    severity=DiagnosticSeverity.WARNING,
                    field_name=None,
                )
            )
        elif (
            resolution.status is FieldResolutionStatus.RESOLVED
            and resolution.method is FieldResolutionMethod.FUZZY
            and resolution.canonical_field is not None
        ):
            diagnostics.append(
                AdapterDiagnostic(
                    code="csv_fuzzy_field_resolution",
                    message=_MSG_FUZZY,
                    severity=DiagnosticSeverity.WARNING,
                    field_name=resolution.canonical_field,
                )
            )
    for collision in schema.collisions:
        diagnostic = AdapterDiagnostic(
            code="csv_schema_collision",
            message=_MSG_COLLISION,
            severity=DiagnosticSeverity.ERROR,
            field_name=collision.canonical_field,
        )
        diagnostics.append(diagnostic)
        fatal.append(diagnostic)
    return diagnostics, tuple(fatal)


def _error(code: str, message: str) -> AdapterDiagnostic:
    return AdapterDiagnostic(
        code=code,
        message=message,
        severity=DiagnosticSeverity.ERROR,
        field_name=None,
    )


def _series_diagnostic(issue: ConsumptionSeriesIssue) -> AdapterDiagnostic:
    return AdapterDiagnostic(
        code=issue.code,
        message=issue.message,
        severity=DiagnosticSeverity.ERROR,
        field_name=issue.field_name,
    )
