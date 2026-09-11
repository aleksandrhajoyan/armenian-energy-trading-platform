"""PDF text-extraction adapter unit tests."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports import DocumentExtractionPort, DocumentExtractionResult
from energy_trading.infrastructure.adapters.unstructured import PdfTextExtractionAdapter
from energy_trading.infrastructure.adapters.unstructured.pdf_text_extraction import (
    _ADAPTER_NAME,
)

_FIXED_TIME = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
_SOURCE = "test-regulatory-pdf"
_DOCUMENT_ID = "doc-1"
_LEAK_TOKEN = "RAW-PDF-LEAK-9f3c1a"


def _single_page_pdf_bytes(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET\n".encode("ascii")
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        ),
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"endstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    objects[3] = b"4 0 obj\n" + objects[3]
    header = b"%PDF-1.4\n"
    body = b"".join(objects)
    offsets: list[int] = []
    position = len(header)
    for obj in objects:
        offsets.append(position)
        position += len(obj)
    xref = [b"xref\n0 6\n0000000000 65535 f \n"]
    xref.extend(f"{offset:010d} 00000 n \n".encode("ascii") for offset in offsets)
    trailer = f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{position}\n%%EOF\n".encode()
    return header + body + b"".join(xref) + trailer


def _write_pdf(tmp_path: Path, pages: tuple[str | None, ...], *, name: str = "source.pdf") -> Path:
    writer = PdfWriter()
    for page_text in pages:
        if page_text is None:
            writer.add_blank_page(width=612, height=792)
            continue
        page_pdf = PdfReader(BytesIO(_single_page_pdf_bytes(page_text)))
        writer.add_page(page_pdf.pages[0])
    path = tmp_path / name
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def _adapter(
    path: Path,
    *,
    document_id: str = _DOCUMENT_ID,
    source_name: str = _SOURCE,
) -> PdfTextExtractionAdapter:
    return PdfTextExtractionAdapter(
        path=path,
        document_id=document_id,
        source_name=source_name,
        clock=lambda: _FIXED_TIME,
    )


def _outward_text(result: DocumentExtractionResult) -> str:
    parts = [result.source_name, result.document_id]
    for chunk in result.chunks:
        parts.extend(
            [
                chunk.document_id,
                chunk.chunk_id,
                str(chunk.ordinal),
                chunk.text,
                "" if chunk.page_number is None else str(chunk.page_number),
            ]
        )
    for diagnostic in result.diagnostics:
        parts.extend([diagnostic.code, diagnostic.message, diagnostic.field_name or ""])
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


async def test_multi_page_pdf_emits_one_chunk_per_textual_page(tmp_path: Path) -> None:
    path = _write_pdf(tmp_path, ("First page text", "Second page text"))
    adapter = _adapter(path)
    port: DocumentExtractionPort = adapter
    result = await port.extract()

    assert result.source_name == _SOURCE
    assert result.document_id == _DOCUMENT_ID
    assert result.diagnostics == ()
    assert result.dlq_records == ()
    assert len(result.chunks) == 2
    assert [chunk.ordinal for chunk in result.chunks] == [0, 1]
    assert [chunk.page_number for chunk in result.chunks] == [1, 2]
    assert [chunk.chunk_id for chunk in result.chunks] == [
        "doc-1:page:1",
        "doc-1:page:2",
    ]
    assert [chunk.document_id for chunk in result.chunks] == [_DOCUMENT_ID, _DOCUMENT_ID]
    assert result.chunks[0].text == "First page text"
    assert result.chunks[1].text == "Second page text"
    assert all(type(chunk) is type(result.chunks[0]) for chunk in result.chunks)


async def test_blank_page_is_skipped_and_ordinals_stay_contiguous(tmp_path: Path) -> None:
    path = _write_pdf(tmp_path, ("Keep first", None, "Keep third"))
    result = await _adapter(path).extract()

    assert [chunk.text for chunk in result.chunks] == ["Keep first", "Keep third"]
    assert [chunk.ordinal for chunk in result.chunks] == [0, 1]
    assert [chunk.page_number for chunk in result.chunks] == [1, 3]
    assert [chunk.chunk_id for chunk in result.chunks] == [
        "doc-1:page:1",
        "doc-1:page:3",
    ]
    assert result.dlq_records == ()


async def test_extraction_is_deterministic_for_equivalent_configuration(
    tmp_path: Path,
) -> None:
    path = _write_pdf(tmp_path, ("Alpha", None, "Gamma"))
    first = await _adapter(path).extract()
    second = await _adapter(path).extract()

    assert first == second
    assert [chunk.chunk_id for chunk in first.chunks] == [chunk.chunk_id for chunk in second.chunks]
    assert [chunk.ordinal for chunk in first.chunks] == [chunk.ordinal for chunk in second.chunks]


async def test_readable_pdf_with_no_extractable_text_emits_diagnostic_without_dlq(
    tmp_path: Path,
) -> None:
    path = _write_pdf(tmp_path, (None, None))
    result = await _adapter(path).extract()

    assert result.chunks == ()
    assert [item.code for item in result.diagnostics] == ["pdf_no_extractable_text"]
    assert result.diagnostics[0].message == "PDF contains no extractable text."
    assert result.dlq_records == ()
    assert "ocr" not in _outward_text(result).lower()
    assert str(path) not in _outward_text(result)


async def test_invalid_pdf_is_sanitized_extraction_failure(tmp_path: Path) -> None:
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"this is not a valid pdf " + _LEAK_TOKEN.encode("ascii"))
    result = await _adapter(path).extract()

    assert result.chunks == ()
    assert [item.code for item in result.diagnostics] == ["pdf_invalid"]
    assert result.dlq_records[0].record_id == f"{_SOURCE}:source"
    assert result.dlq_records[0].payload_reference == f"pdf://{_SOURCE}/source"
    assert result.dlq_records[0].adapter_name == _ADAPTER_NAME
    assert result.dlq_records[0].failed_at == _FIXED_TIME
    outward = _outward_text(result)
    assert _LEAK_TOKEN not in outward
    assert _LEAK_TOKEN not in repr(result)
    assert str(path) not in outward
    assert "PdfStreamError" not in outward
    assert "Traceback" not in outward
    dumped = [item.model_dump() for item in result.diagnostics]
    dumped.extend(item.model_dump(mode="json") for item in result.dlq_records)
    assert _LEAK_TOKEN not in str(dumped)
    assert str(path) not in str(dumped)


async def test_missing_file_raises_sanitized_dependency_error(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.pdf"
    adapter = _adapter(missing)
    with pytest.raises(DependencyUnavailableError, match="PDF source is unavailable") as caught:
        await adapter.extract()
    message = caught.value.message
    assert "does-not-exist.pdf" not in message
    assert str(missing) not in message
    assert str(tmp_path) not in message
    assert "OSError" not in message
    assert "FileNotFoundError" not in message
    assert "Traceback" not in message


async def test_directory_path_raises_sanitized_dependency_error(tmp_path: Path) -> None:
    directory = tmp_path / "not-a-file.pdf"
    directory.mkdir()
    adapter = _adapter(directory)
    with pytest.raises(DependencyUnavailableError, match="PDF source is unavailable") as caught:
        await adapter.extract()
    assert str(directory) not in caught.value.message
    assert "not-a-file.pdf" not in caught.value.message


async def test_extract_offloads_blocking_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: list[object] = []
    path = _write_pdf(tmp_path, ("Offloaded page",))
    adapter = _adapter(path)

    async def tracking_to_thread(func: object, /, *args: object, **kwargs: object) -> object:
        recorded.append(func)
        assert not inspect.iscoroutinefunction(func)
        return func(*args, **kwargs)

    monkeypatch.setattr(
        "energy_trading.infrastructure.adapters.unstructured.pdf_text_extraction.asyncio.to_thread",
        tracking_to_thread,
    )

    result = await adapter.extract()

    assert recorded
    assert not inspect.iscoroutinefunction(recorded[0])
    assert inspect.iscoroutinefunction(PdfTextExtractionAdapter.extract)
    assert result.chunks[0].text == "Offloaded page"


async def test_page_extraction_failure_fails_closed_without_partial_chunks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write_pdf(tmp_path, ("Keep this", "Also this"))

    def boom(self: PageObject, *args: object, **kwargs: object) -> str:
        raise PdfReadError("parser exploded")

    monkeypatch.setattr(PageObject, "extract_text", boom)
    result = await _adapter(path).extract()

    assert result.chunks == ()
    assert [item.code for item in result.diagnostics] == ["pdf_page_extraction_failed"]
    assert result.dlq_records[0].payload_reference == f"pdf://{_SOURCE}/source"
    outward = _outward_text(result)
    assert "parser exploded" not in outward
    assert "PdfReadError" not in outward
    assert str(path) not in outward


async def test_extracted_text_normalizes_line_endings_and_surrounding_whitespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write_pdf(tmp_path, ("placeholder",))

    def noisy(_self: PageObject, *args: object, **kwargs: object) -> str:
        return "  hello\r\nworld\ragain  "

    monkeypatch.setattr(PageObject, "extract_text", noisy)
    result = await _adapter(path).extract()

    assert result.chunks[0].text == "hello\nworld\nagain"


def test_constructor_rejects_non_path_and_non_pdf_suffix(tmp_path: Path) -> None:
    pdf_path = _write_pdf(tmp_path, ("Body",))
    with pytest.raises(TypeError, match="pathlib.Path"):
        PdfTextExtractionAdapter(
            path=str(pdf_path),  # type: ignore[arg-type]
            document_id=_DOCUMENT_ID,
            source_name=_SOURCE,
        )
    with pytest.raises(ValueError, match=r"\.pdf"):
        PdfTextExtractionAdapter(
            path=tmp_path / "notes.txt",
            document_id=_DOCUMENT_ID,
            source_name=_SOURCE,
        )


@pytest.mark.parametrize("document_id", ["", "   "])
def test_constructor_rejects_empty_document_id(tmp_path: Path, document_id: str) -> None:
    path = _write_pdf(tmp_path, ("Body",))
    with pytest.raises(ValueError, match="document_id"):
        PdfTextExtractionAdapter(
            path=path,
            document_id=document_id,
            source_name=_SOURCE,
        )


@pytest.mark.parametrize("source_name", ["", "   "])
def test_constructor_rejects_empty_source_name(tmp_path: Path, source_name: str) -> None:
    path = _write_pdf(tmp_path, ("Body",))
    with pytest.raises(ValueError, match="source_name"):
        PdfTextExtractionAdapter(
            path=path,
            document_id=_DOCUMENT_ID,
            source_name=source_name,
        )


async def test_result_does_not_expose_raw_source_types(tmp_path: Path) -> None:
    path = _write_pdf(tmp_path, ("Canonical only",))
    result = await _adapter(path).extract()
    dumped = repr(result)
    assert "PdfReader" not in dumped
    assert "PageObject" not in dumped
    assert "pathlib" not in dumped
    assert str(path) not in dumped
    assert not any(isinstance(chunk.text, bytes) for chunk in result.chunks)
