"""Consumption CSV adapter: the first concrete structured source reader.

CSV acquisition, schema interpretation, and row validation stay inside
infrastructure. The application receives only ``StructuredIngestionResult``.
This adapter performs no unit conversion and no timezone inference.
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
from energy_trading.infrastructure.adapters.structured.schema_mapping import (
    CanonicalFieldCollision,
    CanonicalFieldSpec,
    DeterministicFieldResolver,
    FieldResolution,
    FieldResolutionMethod,
    FieldResolutionStatus,
    SchemaResolution,
)

_ADAPTER_NAME = "consumption_csv"
_REQUIRED_CANONICAL_FIELDS = frozenset({"consumer_id", "timestamp", "value_mw"})
_REQUIRED_CANONICAL_ORDER = ("consumer_id", "timestamp", "value_mw")
_MW_TOKEN = "mw"
_DEFAULT_FIELD_SPECS = (
    CanonicalFieldSpec(canonical_name="consumer_id", aliases=(), required=True),
    CanonicalFieldSpec(canonical_name="timestamp", aliases=(), required=True),
    CanonicalFieldSpec(canonical_name="value_mw", aliases=("Consumption_MW",), required=True),
)

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
    ) -> None:
        self._path = _require_path(path)
        cleaned_source = source_name.strip()
        if not cleaned_source:
            msg = "source_name must be a non-empty string"
            raise ValueError(msg)
        specs = _DEFAULT_FIELD_SPECS if field_specs is None else field_specs
        self._source_name = cleaned_source
        self._clock = clock if clock is not None else _utc_now
        self._resolver = DeterministicFieldResolver(_validated_consumption_specs(specs))

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
        records: list[ConsumptionRecord] = []
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
                        schema = _apply_consumption_unit_safety(
                            self._resolver.resolve_schema(header)
                        )
                        schema_diagnostics, fatal_errors = _schema_diagnostics(schema)
                        diagnostics.extend(schema_diagnostics)
                        if fatal_errors:
                            dlq_records.append(self._schema_dlq(fatal_errors))
                            return self._result(records, diagnostics, dlq_records)
                        column_index = _canonical_column_index(schema)
                        expected_width = len(header)
                        continue
                    self._ingest_data_row(
                        row=raw_row,
                        logical_row=logical_row,
                        expected_width=expected_width,
                        column_index=column_index,
                        records=records,
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
        return self._result(records, diagnostics, dlq_records)

    def _ingest_data_row(
        self,
        *,
        row: list[str],
        logical_row: int,
        expected_width: int,
        column_index: dict[str, int],
        records: list[ConsumptionRecord],
        diagnostics: list[AdapterDiagnostic],
        dlq_records: list[DLQRecord],
    ) -> None:
        if len(row) != expected_width:
            diagnostic = _error("csv_row_shape_invalid", _MSG_ROW_SHAPE)
            diagnostics.append(diagnostic)
            dlq_records.append(self._row_dlq(logical_row, (diagnostic,)))
            return
        payload = {
            "consumer_id": row[column_index["consumer_id"]],
            "timestamp": row[column_index["timestamp"]],
            "value_mw": row[column_index["value_mw"]],
        }
        try:
            records.append(ConsumptionRecord.model_validate(payload))
        except ValidationError:
            diagnostic = _error("csv_row_validation_failed", _MSG_ROW_VALIDATION)
            diagnostics.append(diagnostic)
            dlq_records.append(self._row_dlq(logical_row, (diagnostic,)))

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


def _validated_consumption_specs(
    field_specs: Sequence[CanonicalFieldSpec],
) -> tuple[CanonicalFieldSpec, ...]:
    specs = tuple(field_specs)
    names = tuple(spec.canonical_name for spec in specs)
    if frozenset(names) != _REQUIRED_CANONICAL_FIELDS or len(names) != len(
        _REQUIRED_CANONICAL_FIELDS
    ):
        msg = "Consumption CSV field specs must be exactly consumer_id, timestamp, and value_mw"
        raise ValueError(msg)
    if not all(spec.required for spec in specs):
        msg = "Consumption CSV canonical fields must all be required"
        raise ValueError(msg)
    return specs


def _is_blank_row(row: Sequence[str]) -> bool:
    return all(not cell.strip() for cell in row)


def _apply_consumption_unit_safety(schema: SchemaResolution) -> SchemaResolution:
    """Reject fuzzy value_mw mappings that are not standalone MW.

    Chunk 5 may fuzzy-match energy-like headers to the MW alias. This adapter
    accepts a fuzzy ``value_mw`` mapping only when the normalized source's
    final token is exactly ``mw``. Exact ``Consumption_MW`` is unchanged.
    """

    resolutions = tuple(_downgrade_unsafe_fuzzy_mw(item) for item in schema.field_resolutions)
    resolved_sources: dict[str, list[str]] = {}
    for resolution in resolutions:
        if (
            resolution.status is FieldResolutionStatus.RESOLVED
            and resolution.canonical_field is not None
        ):
            resolved_sources.setdefault(resolution.canonical_field, []).append(
                resolution.source_field
            )
    missing = tuple(name for name in _REQUIRED_CANONICAL_ORDER if name not in resolved_sources)
    collisions = tuple(
        CanonicalFieldCollision(
            canonical_field=canonical_field,
            source_fields=tuple(source_fields),
        )
        for canonical_field, source_fields in sorted(resolved_sources.items())
        if len(source_fields) > 1
    )
    return SchemaResolution(
        field_resolutions=resolutions,
        missing_required_fields=missing,
        collisions=collisions,
    )


def _downgrade_unsafe_fuzzy_mw(resolution: FieldResolution) -> FieldResolution:
    if (
        resolution.status is not FieldResolutionStatus.RESOLVED
        or resolution.canonical_field != "value_mw"
        or resolution.method is not FieldResolutionMethod.FUZZY
    ):
        return resolution
    if _normalized_source_is_mw_safe(resolution.normalized_source_field):
        return resolution
    return FieldResolution(
        source_field=resolution.source_field,
        normalized_source_field=resolution.normalized_source_field,
        status=FieldResolutionStatus.UNRESOLVED,
        canonical_field=None,
        method=None,
        confidence=resolution.confidence,
        candidates=resolution.candidates,
    )


def _normalized_source_is_mw_safe(normalized_source: str) -> bool:
    tokens = normalized_source.split()
    return bool(tokens) and tokens[-1] == _MW_TOKEN


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


def _canonical_column_index(schema: SchemaResolution) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, resolution in enumerate(schema.field_resolutions):
        if (
            resolution.status is FieldResolutionStatus.RESOLVED
            and resolution.canonical_field is not None
        ):
            mapping[resolution.canonical_field] = index
    return mapping


def _error(code: str, message: str) -> AdapterDiagnostic:
    return AdapterDiagnostic(
        code=code,
        message=message,
        severity=DiagnosticSeverity.ERROR,
        field_name=None,
    )
