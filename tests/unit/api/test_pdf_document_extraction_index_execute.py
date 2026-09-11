"""One-shot loaded PDF extraction-to-index execution delegates to Chunk 103."""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from energy_trading.api.composition.pdf_document_extraction_index_execute import (
    execute_loaded_pdf_document_extraction_index,
)
from energy_trading.api.composition.pdf_document_extraction_index_loaded_runtime import (
    loaded_pdf_document_extraction_index_runtime,
)
from energy_trading.application.ports.document_extraction import DocumentExtractionResult

_EXECUTE_MODULE = "energy_trading.api.composition.pdf_document_extraction_index_execute"
_EXPLICIT_ENV_FILE = Path("sentinel-chunk104.env")
_PATH = Path("missing-chunk-104-does-not-exist.pdf")
_DOCUMENT_ID = "doc-chunk-104"
_SOURCE_NAME = "chunk-104-regulatory-pdf"


@dataclass
class _RecordingService:
    result: object
    calls: list[str] = field(default_factory=list)
    error: BaseException | None = None

    async def execute(self) -> object:
        self.calls.append("execute")
        if self.error is not None:
            raise self.error
        return self.result

    async def extract(self) -> None:
        self.calls.append("extract")


@dataclass
class _LoadedRuntimeSpy:
    service: object
    calls: list[dict[str, object]] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    entry_error: BaseException | None = None

    def __call__(self, **kwargs: object) -> AbstractAsyncContextManager[object]:
        self.calls.append(kwargs)
        return self._context()

    @asynccontextmanager
    async def _context(self) -> AsyncIterator[object]:
        if self.entry_error is not None:
            self.events.append("enter-failed")
            raise self.entry_error
        self.events.append("enter")
        try:
            yield self.service
        finally:
            self.events.append("exit")


def _patch_loaded_runtime(
    monkeypatch: pytest.MonkeyPatch,
    *,
    loaded: _LoadedRuntimeSpy | None = None,
) -> _LoadedRuntimeSpy:
    spy = loaded or _LoadedRuntimeSpy(service=_RecordingService(result=object()))
    monkeypatch.setattr(f"{_EXECUTE_MODULE}.loaded_pdf_document_extraction_index_runtime", spy)
    return spy


def test_callable_is_coroutine_function() -> None:
    assert inspect.iscoroutinefunction(execute_loaded_pdf_document_extraction_index) is True
    assert inspect.isasyncgenfunction(execute_loaded_pdf_document_extraction_index) is False


def test_signature_is_keyword_only_with_existing_env_file_contract() -> None:
    signature = inspect.signature(execute_loaded_pdf_document_extraction_index)
    assert tuple(signature.parameters) == (
        "path",
        "document_id",
        "source_name",
        "env_file",
    )
    for name in signature.parameters:
        parameter = signature.parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["path"].annotation is Path
    assert signature.parameters["document_id"].annotation is str
    assert signature.parameters["source_name"].annotation is str
    loaded_env = inspect.signature(loaded_pdf_document_extraction_index_runtime).parameters[
        "env_file"
    ]
    parameter = signature.parameters["env_file"]
    assert parameter.annotation == loaded_env.annotation
    assert parameter.default == loaded_env.default
    assert parameter.default == ".env"
    assert signature.return_annotation is DocumentExtractionResult
    assert "index_execution_service" not in signature.parameters
    assert "openai_settings" not in signature.parameters
    assert "qdrant_settings" not in signature.parameters
    assert "openai_client" not in signature.parameters
    assert "qdrant_client" not in signature.parameters
    assert "create_openai_client" not in signature.parameters
    assert "create_qdrant_client" not in signature.parameters
    assert "load_openai_settings" not in signature.parameters
    assert "clock" not in signature.parameters


async def test_successful_execution_forwards_exact_values_and_result_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    service = _RecordingService(result=sentinel)
    loaded = _LoadedRuntimeSpy(service=service)
    _patch_loaded_runtime(monkeypatch, loaded=loaded)
    returned = await execute_loaded_pdf_document_extraction_index(
        path=_PATH,
        document_id=_DOCUMENT_ID,
        source_name=_SOURCE_NAME,
        env_file=_EXPLICIT_ENV_FILE,
    )
    assert returned is sentinel
    assert loaded.calls == [
        {
            "path": _PATH,
            "document_id": _DOCUMENT_ID,
            "source_name": _SOURCE_NAME,
            "env_file": _EXPLICIT_ENV_FILE,
        }
    ]
    assert loaded.calls[0]["path"] is _PATH
    assert loaded.calls[0]["env_file"] is _EXPLICIT_ENV_FILE
    assert loaded.calls[0]["document_id"] == _DOCUMENT_ID
    assert loaded.calls[0]["source_name"] == _SOURCE_NAME
    assert service.calls == ["execute"]
    assert loaded.events == ["enter", "exit"]
    assert len(loaded.calls) == 1


async def test_default_env_file_is_forwarded_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded = _patch_loaded_runtime(monkeypatch)
    await execute_loaded_pdf_document_extraction_index(
        path=_PATH,
        document_id=_DOCUMENT_ID,
        source_name=_SOURCE_NAME,
    )
    assert loaded.calls == [
        {
            "path": _PATH,
            "document_id": _DOCUMENT_ID,
            "source_name": _SOURCE_NAME,
            "env_file": ".env",
        }
    ]


async def test_none_env_file_is_forwarded_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded = _patch_loaded_runtime(monkeypatch)
    await execute_loaded_pdf_document_extraction_index(
        path=_PATH,
        document_id=_DOCUMENT_ID,
        source_name=_SOURCE_NAME,
        env_file=None,
    )
    assert loaded.calls == [
        {
            "path": _PATH,
            "document_id": _DOCUMENT_ID,
            "source_name": _SOURCE_NAME,
            "env_file": None,
        }
    ]
    assert loaded.calls[0]["env_file"] is None


async def test_runtime_entry_failure_does_not_execute_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("loaded-entry-failed")
    service = _RecordingService(result=object())
    loaded = _LoadedRuntimeSpy(service=service, entry_error=error)
    _patch_loaded_runtime(monkeypatch, loaded=loaded)
    with pytest.raises(RuntimeError) as captured:
        await execute_loaded_pdf_document_extraction_index(
            path=_PATH,
            document_id=_DOCUMENT_ID,
            source_name=_SOURCE_NAME,
            env_file=None,
        )
    assert captured.value is error
    assert type(captured.value) is RuntimeError
    assert str(captured.value) == "loaded-entry-failed"
    assert loaded.calls == [
        {
            "path": _PATH,
            "document_id": _DOCUMENT_ID,
            "source_name": _SOURCE_NAME,
            "env_file": None,
        }
    ]
    assert loaded.events == ["enter-failed"]
    assert service.calls == []


async def test_execute_failure_propagates_and_tears_down_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("execute-failed")
    service = _RecordingService(result=object(), error=error)
    loaded = _LoadedRuntimeSpy(service=service)
    _patch_loaded_runtime(monkeypatch, loaded=loaded)
    with pytest.raises(RuntimeError) as captured:
        await execute_loaded_pdf_document_extraction_index(
            path=_PATH,
            document_id=_DOCUMENT_ID,
            source_name=_SOURCE_NAME,
            env_file=None,
        )
    assert captured.value is error
    assert type(captured.value) is RuntimeError
    assert str(captured.value) == "execute-failed"
    assert service.calls == ["execute"]
    assert loaded.events == ["enter", "exit"]
    assert len(loaded.calls) == 1


async def test_execution_does_not_call_extract_or_touch_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    service = _RecordingService(result=sentinel)
    loaded = _LoadedRuntimeSpy(service=service)
    _patch_loaded_runtime(monkeypatch, loaded=loaded)

    def fail_exists(self: Path) -> bool:
        raise AssertionError("path.exists must not be called")

    def fail_is_file(self: Path) -> bool:
        raise AssertionError("path.is_file must not be called")

    def fail_open(self: Path, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("path.open must not be called")

    def fail_stat(self: Path, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("path.stat must not be called")

    monkeypatch.setattr(Path, "exists", fail_exists)
    monkeypatch.setattr(Path, "is_file", fail_is_file)
    monkeypatch.setattr(Path, "open", fail_open)
    monkeypatch.setattr(Path, "stat", fail_stat)

    returned = await execute_loaded_pdf_document_extraction_index(
        path=_PATH,
        document_id=_DOCUMENT_ID,
        source_name=_SOURCE_NAME,
        env_file=None,
    )
    assert returned is sentinel
    assert service.calls == ["execute"]
    assert loaded.events == ["enter", "exit"]


def test_module_does_not_duplicate_orchestration_or_construct_providers() -> None:
    import energy_trading.api.composition.pdf_document_extraction_index_execute as module

    source = inspect.getsource(module)
    assert "PdfTextExtractionAdapter" not in source
    assert "DocumentVectorIndexExecutionService" not in source
    assert "DocumentEmbeddingPort" not in source
    assert "DocumentVectorIndexPort" not in source
    assert "create_openai_client" not in source
    assert "create_qdrant_client" not in source
    assert "load_openai_settings" not in source
    assert "load_qdrant_settings" not in source
    assert "AsyncOpenAI(" not in source
    assert "AsyncQdrantClient(" not in source
    assert ".extract(" not in source
    assert ".embed(" not in source
    assert ".index(" not in source
    assert "create_task" not in source
    assert "asyncio.gather" not in source
    assert "os.environ" not in source
    assert "getenv" not in source
    assert not hasattr(module, "PdfTextExtractionAdapter")
    assert not hasattr(module, "DocumentVectorIndexExecutionService")
    assert not hasattr(module, "create_openai_client")
    assert not hasattr(module, "AsyncOpenAI")
    assert not hasattr(module, "AsyncQdrantClient")
    assert source.count(".execute(") == 1
