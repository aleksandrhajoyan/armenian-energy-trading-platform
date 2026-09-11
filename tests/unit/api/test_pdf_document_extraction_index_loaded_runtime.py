"""Settings-loaded PDF extraction-to-index runtime delegates to Chunks 91 and 102."""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from energy_trading.api.composition.document_vector_index_loaded_runtime import (
    loaded_document_vector_index_runtime,
)
from energy_trading.api.composition.pdf_document_extraction_index_loaded_runtime import (
    loaded_pdf_document_extraction_index_runtime,
)

_LOADED_MODULE = "energy_trading.api.composition.pdf_document_extraction_index_loaded_runtime"
_EXPLICIT_ENV_FILE = Path("sentinel-chunk103.env")
_PATH = Path("missing-chunk-103-does-not-exist.pdf")
_DOCUMENT_ID = "doc-chunk-103"
_SOURCE_NAME = "chunk-103-regulatory-pdf"


@dataclass
class _RecordingService:
    calls: list[str] = field(default_factory=list)

    async def extract(self) -> None:
        self.calls.append("extract")

    async def execute(self, **_kwargs: object) -> None:
        self.calls.append("execute")

    async def embed(self, **_kwargs: object) -> None:
        self.calls.append("embed")

    async def index(self, **_kwargs: object) -> None:
        self.calls.append("index")

    async def prepare(self, **_kwargs: object) -> None:
        self.calls.append("prepare")

    async def close(self) -> None:
        self.calls.append("close")


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


@dataclass
class _BuilderSpy:
    service: object
    calls: list[dict[str, object]] = field(default_factory=list)
    error: BaseException | None = None

    def __call__(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.service


def _patch_loaded_pdf_runtime(
    monkeypatch: pytest.MonkeyPatch,
    *,
    loaded: _LoadedRuntimeSpy | None = None,
    builder: _BuilderSpy | None = None,
) -> tuple[_LoadedRuntimeSpy, _BuilderSpy]:
    loaded_spy = loaded or _LoadedRuntimeSpy(service=object())
    builder_spy = builder or _BuilderSpy(service=object())
    monkeypatch.setattr(f"{_LOADED_MODULE}.loaded_document_vector_index_runtime", loaded_spy)
    monkeypatch.setattr(
        f"{_LOADED_MODULE}.build_pdf_document_extraction_index_execution",
        builder_spy,
    )
    return loaded_spy, builder_spy


def test_callable_is_async_context_manager_factory() -> None:
    assert inspect.iscoroutinefunction(loaded_pdf_document_extraction_index_runtime) is False
    assert inspect.isasyncgenfunction(loaded_pdf_document_extraction_index_runtime) is False
    manager = loaded_pdf_document_extraction_index_runtime(
        path=_PATH,
        document_id=_DOCUMENT_ID,
        source_name=_SOURCE_NAME,
        env_file=None,
    )
    assert isinstance(manager, AbstractAsyncContextManager)


def test_signature_is_keyword_only_with_existing_env_file_contract() -> None:
    signature = inspect.signature(loaded_pdf_document_extraction_index_runtime)
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
    loaded_env = inspect.signature(loaded_document_vector_index_runtime).parameters["env_file"]
    parameter = signature.parameters["env_file"]
    assert parameter.annotation == loaded_env.annotation
    assert parameter.default == loaded_env.default
    assert parameter.default == ".env"
    assert "index_execution_service" not in signature.parameters
    assert "openai_settings" not in signature.parameters
    assert "qdrant_settings" not in signature.parameters
    assert "document_vector_index_settings" not in signature.parameters
    assert "openai_client" not in signature.parameters
    assert "qdrant_client" not in signature.parameters
    assert "create_openai_client" not in signature.parameters
    assert "create_qdrant_client" not in signature.parameters
    assert "load_openai_settings" not in signature.parameters
    assert "load_qdrant_settings" not in signature.parameters
    assert "load_document_vector_index_runtime_settings" not in signature.parameters
    assert "clock" not in signature.parameters


async def test_successful_composition_forwards_exact_values_and_identities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index_service = object()
    composed_service = object()
    loaded = _LoadedRuntimeSpy(service=index_service)
    builder = _BuilderSpy(service=composed_service)
    _patch_loaded_pdf_runtime(monkeypatch, loaded=loaded, builder=builder)
    async with loaded_pdf_document_extraction_index_runtime(
        path=_PATH,
        document_id=_DOCUMENT_ID,
        source_name=_SOURCE_NAME,
        env_file=_EXPLICIT_ENV_FILE,
    ) as yielded:
        assert yielded is composed_service
        assert loaded.events == ["enter"]
        assert loaded.calls == [{"env_file": _EXPLICIT_ENV_FILE}]
        assert loaded.calls[0]["env_file"] is _EXPLICIT_ENV_FILE
        assert builder.calls == [
            {
                "path": _PATH,
                "document_id": _DOCUMENT_ID,
                "source_name": _SOURCE_NAME,
                "index_execution_service": index_service,
            }
        ]
        assert builder.calls[0]["path"] is _PATH
        assert builder.calls[0]["index_execution_service"] is index_service
        assert builder.calls[0]["document_id"] == _DOCUMENT_ID
        assert builder.calls[0]["source_name"] == _SOURCE_NAME
    assert loaded.events == ["enter", "exit"]
    assert len(loaded.calls) == 1
    assert len(builder.calls) == 1


async def test_default_env_file_is_forwarded_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded, builder = _patch_loaded_pdf_runtime(monkeypatch)
    async with loaded_pdf_document_extraction_index_runtime(
        path=_PATH,
        document_id=_DOCUMENT_ID,
        source_name=_SOURCE_NAME,
    ):
        pass
    assert loaded.calls == [{"env_file": ".env"}]
    assert len(builder.calls) == 1


async def test_none_env_file_is_forwarded_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded, builder = _patch_loaded_pdf_runtime(monkeypatch)
    async with loaded_pdf_document_extraction_index_runtime(
        path=_PATH,
        document_id=_DOCUMENT_ID,
        source_name=_SOURCE_NAME,
        env_file=None,
    ):
        pass
    assert loaded.calls == [{"env_file": None}]
    assert loaded.calls[0]["env_file"] is None
    assert len(builder.calls) == 1


async def test_context_entry_does_not_extract_index_or_touch_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index_service = _RecordingService()
    composed_service = _RecordingService()
    loaded = _LoadedRuntimeSpy(service=index_service)
    builder = _BuilderSpy(service=composed_service)
    _patch_loaded_pdf_runtime(monkeypatch, loaded=loaded, builder=builder)

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

    async with loaded_pdf_document_extraction_index_runtime(
        path=_PATH,
        document_id=_DOCUMENT_ID,
        source_name=_SOURCE_NAME,
        env_file=None,
    ) as yielded:
        assert yielded is composed_service
        assert index_service.calls == []
        assert composed_service.calls == []
    assert index_service.calls == []
    assert composed_service.calls == []
    assert loaded.events == ["enter", "exit"]


async def test_loaded_runtime_entry_failure_does_not_call_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("loaded-entry-failed")
    loaded = _LoadedRuntimeSpy(service=object(), entry_error=error)
    builder = _BuilderSpy(service=object())
    _patch_loaded_pdf_runtime(monkeypatch, loaded=loaded, builder=builder)
    with pytest.raises(RuntimeError) as captured:
        async with loaded_pdf_document_extraction_index_runtime(
            path=_PATH,
            document_id=_DOCUMENT_ID,
            source_name=_SOURCE_NAME,
            env_file=None,
        ):
            raise AssertionError("context body must not run")
    assert captured.value is error
    assert type(captured.value) is RuntimeError
    assert str(captured.value) == "loaded-entry-failed"
    assert loaded.calls == [{"env_file": None}]
    assert loaded.events == ["enter-failed"]
    assert builder.calls == []


async def test_builder_failure_propagates_and_tears_down_loaded_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("builder-failed")
    loaded = _LoadedRuntimeSpy(service=object())
    builder = _BuilderSpy(service=object(), error=error)
    _patch_loaded_pdf_runtime(monkeypatch, loaded=loaded, builder=builder)
    with pytest.raises(RuntimeError) as captured:
        async with loaded_pdf_document_extraction_index_runtime(
            path=_PATH,
            document_id=_DOCUMENT_ID,
            source_name=_SOURCE_NAME,
            env_file=None,
        ):
            raise AssertionError("context body must not run")
    assert captured.value is error
    assert type(captured.value) is RuntimeError
    assert str(captured.value) == "builder-failed"
    assert len(loaded.calls) == 1
    assert len(builder.calls) == 1
    assert loaded.events == ["enter", "exit"]


async def test_consumer_exception_exits_inner_context_and_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded, builder = _patch_loaded_pdf_runtime(monkeypatch)
    with pytest.raises(RuntimeError, match="consumer-failed") as captured:
        async with loaded_pdf_document_extraction_index_runtime(
            path=_PATH,
            document_id=_DOCUMENT_ID,
            source_name=_SOURCE_NAME,
            env_file=None,
        ):
            raise RuntimeError("consumer-failed")
    assert type(captured.value) is RuntimeError
    assert str(captured.value) == "consumer-failed"
    assert loaded.events == ["enter", "exit"]
    assert len(builder.calls) == 1


def test_module_does_not_construct_clients_or_invoke_runtime_methods() -> None:
    import energy_trading.api.composition.pdf_document_extraction_index_loaded_runtime as module

    source = inspect.getsource(module)
    assert "create_openai_client" not in source
    assert "create_qdrant_client" not in source
    assert "load_openai_settings" not in source
    assert "load_qdrant_settings" not in source
    assert "load_document_vector_index_runtime_settings" not in source
    assert "PdfTextExtractionAdapter" not in source
    assert "AsyncOpenAI(" not in source
    assert "AsyncQdrantClient(" not in source
    assert "AsyncExitStack" not in source
    assert ".close(" not in source
    assert ".extract(" not in source
    assert ".execute(" not in source
    assert ".embed(" not in source
    assert ".index(" not in source
    assert ".exists(" not in source
    assert ".open(" not in source
    assert "os.environ" not in source
    assert "getenv" not in source
    assert "dotenv" not in source
    assert not hasattr(module, "openai_client")
    assert not hasattr(module, "qdrant_client")
    assert not hasattr(module, "create_openai_client")
    assert not hasattr(module, "create_qdrant_client")
    assert not hasattr(module, "PdfTextExtractionAdapter")
    assert not hasattr(module, "AsyncOpenAI")
    assert not hasattr(module, "AsyncQdrantClient")
