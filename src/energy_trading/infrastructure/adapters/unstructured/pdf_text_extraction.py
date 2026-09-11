"""Local PDF text-layer extraction adapter.

This adapter implements the application ``DocumentExtractionPort`` for PDFs
that already contain extractable text. Acquisition, parsing, and page-based
chunking stay inside infrastructure. The application receives only
``DocumentExtractionResult``. Raw PDF bytes, filesystem paths, parser objects,
and OCR never cross that boundary.

OCR, scanned-image support, URL acquisition, and vector indexing are out of
scope.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import ParseError, PdfReadError

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports.document_extraction import (
    DocumentExtractionResult,
    ExtractedDocumentChunk,
)
from energy_trading.domain.models.ingestion import AdapterDiagnostic, DiagnosticSeverity, DLQRecord

_ADAPTER_NAME = "pdf_text_extraction"
_PDF_FORMAT_ERRORS = (PdfReadError, ParseError)

_MSG_UNAVAILABLE = "PDF source is unavailable"
_MSG_INVALID = "PDF source could not be parsed."
_MSG_NO_TEXT = "PDF contains no extractable text."
_MSG_PAGE = "PDF page text could not be extracted."


class PdfTextExtractionAdapter:
    """Infrastructure adapter that structurally satisfies ``DocumentExtractionPort``.

    Source path, document identity, and source name are constructor-injected.
    They are not part of the application-facing ``extract()`` signature.
    """

    def __init__(
        self,
        *,
        path: Path,
        document_id: str,
        source_name: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._path = _require_pdf_path(path)
        self._document_id = _require_non_empty("document_id", document_id)
        self._source_name = _require_non_empty("source_name", source_name)
        self._clock = clock if clock is not None else _utc_now

    @property
    def source_name(self) -> str:
        return self._source_name

    async def extract(self) -> DocumentExtractionResult:
        return await asyncio.to_thread(self._extract_sync)

    def _extract_sync(self) -> DocumentExtractionResult:
        try:
            return self._read_and_extract()
        except OSError as exc:
            raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc

    def _read_and_extract(self) -> DocumentExtractionResult:
        try:
            with self._path.open("rb") as handle:
                reader = PdfReader(handle)
                return self._extract_from_reader(reader)
        except _PDF_FORMAT_ERRORS:
            return self._parse_failure()

    def _extract_from_reader(self, reader: PdfReader) -> DocumentExtractionResult:
        if reader.is_encrypted:
            return self._parse_failure()
        chunks: list[ExtractedDocumentChunk] = []
        for index, page in enumerate(reader.pages):
            page_number = index + 1
            try:
                raw_text = page.extract_text()
            except _PDF_FORMAT_ERRORS:
                return self._page_failure()
            text = _normalize_extracted_text(raw_text)
            if not text:
                continue
            chunks.append(
                ExtractedDocumentChunk(
                    document_id=self._document_id,
                    chunk_id=_chunk_id(self._document_id, page_number),
                    ordinal=len(chunks),
                    text=text,
                    page_number=page_number,
                )
            )
        if not chunks:
            diagnostic = _error("pdf_no_extractable_text", _MSG_NO_TEXT)
            return self._result((), (diagnostic,), ())
        return self._result(tuple(chunks), (), ())

    def _parse_failure(self) -> DocumentExtractionResult:
        diagnostic = _error("pdf_invalid", _MSG_INVALID)
        return self._result((), (diagnostic,), (self._source_dlq((diagnostic,)),))

    def _page_failure(self) -> DocumentExtractionResult:
        diagnostic = _error("pdf_page_extraction_failed", _MSG_PAGE)
        return self._result((), (diagnostic,), (self._source_dlq((diagnostic,)),))

    def _result(
        self,
        chunks: tuple[ExtractedDocumentChunk, ...],
        diagnostics: tuple[AdapterDiagnostic, ...],
        dlq_records: tuple[DLQRecord, ...],
    ) -> DocumentExtractionResult:
        return DocumentExtractionResult(
            source_name=self._source_name,
            document_id=self._document_id,
            chunks=chunks,
            diagnostics=diagnostics,
            dlq_records=dlq_records,
        )

    def _source_dlq(self, diagnostics: tuple[AdapterDiagnostic, ...]) -> DLQRecord:
        return DLQRecord(
            record_id=f"{self._source_name}:source",
            failed_at=self._clock(),
            source_name=self._source_name,
            adapter_name=_ADAPTER_NAME,
            diagnostics=diagnostics,
            payload_reference=f"pdf://{self._source_name}/source",
        )


def _chunk_id(document_id: str, page_number: int) -> str:
    return f"{document_id}:page:{page_number}"


def _normalize_extracted_text(raw: str | None) -> str:
    if raw is None:
        return ""
    return raw.replace("\r\n", "\n").replace("\r", "\n").strip()


def _error(code: str, message: str) -> AdapterDiagnostic:
    return AdapterDiagnostic(
        code=code,
        message=message,
        severity=DiagnosticSeverity.ERROR,
        field_name=None,
    )


def _require_pdf_path(value: object) -> Path:
    if not isinstance(value, Path):
        msg = "path must be a pathlib.Path"
        raise TypeError(msg)
    if value.suffix.lower() != ".pdf":
        msg = "PDF adapter accepts .pdf sources only"
        raise ValueError(msg)
    return value


def _require_non_empty(field_name: str, value: object) -> str:
    if not isinstance(value, str):
        msg = f"{field_name} must be a string"
        raise TypeError(msg)
    cleaned = value.strip()
    if not cleaned:
        msg = f"{field_name} must be a non-empty string"
        raise ValueError(msg)
    return cleaned


def _utc_now() -> datetime:
    return datetime.now(UTC)
