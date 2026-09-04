"""Filesystem Dead Letter Queue metadata persistence."""

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
from typing import cast

import pytest

from energy_trading.application.errors import ConflictError, DependencyUnavailableError
from energy_trading.application.ports import DeadLetterQueuePort
from energy_trading.domain.models import AdapterDiagnostic, DiagnosticSeverity, DLQRecord
from energy_trading.infrastructure.persistence.dlq import FilesystemDeadLetterQueue
from tests.unit.domain._factories import diagnostic, dlq, utc

_SECRET_SENTINEL = "SECRET-DLQ-PAYLOAD-9f3c2a"
_UNSAFE_RECORD_ID = r"..\..\outside.json|/etc/passwd|C:\Windows\temp"


def _queue(tmp_path: Path) -> FilesystemDeadLetterQueue:
    return FilesystemDeadLetterQueue(root_directory=tmp_path / "dlq")


def _expected_path(root: Path, record_id: str) -> Path:
    digest = hashlib.sha256(record_id.encode("utf-8")).hexdigest()
    return root / f"{digest}.json"


def _canonical_record(*, with_correlation: bool = False) -> DLQRecord:
    diagnostics = (
        diagnostic(),
        AdapterDiagnostic(
            code="ROW_INVALID",
            message="canonical diagnostic only",
            severity=DiagnosticSeverity.ERROR,
            field_name="timestamp",
        ),
    )
    values: dict[str, object] = {
        "record_id": "dlq-1",
        "failed_at": utc(),
        "source_name": "operator-file",
        "adapter_name": "structured.csv",
        "diagnostics": diagnostics,
        "payload_reference": "csv://operator-file/row/2",
    }
    if with_correlation:
        values["correlation_id"] = "corr-11"
    return DLQRecord.model_validate(values)


def _load_json(path: Path) -> dict[str, object]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return cast(dict[str, object], loaded)


async def test_enqueue_creates_json_artifact_for_canonical_record(tmp_path: Path) -> None:
    root = tmp_path / "dlq"
    queue: DeadLetterQueuePort = FilesystemDeadLetterQueue(root_directory=root)
    record = _canonical_record()

    await queue.enqueue(record)

    stored = _expected_path(root, record.record_id)
    assert stored.is_file()
    assert list(root.glob("*.json")) == [stored]


async def test_enqueue_creates_persistence_directory_when_absent(tmp_path: Path) -> None:
    root = tmp_path / "nested" / "dlq"
    assert not root.exists()
    queue = FilesystemDeadLetterQueue(root_directory=root)

    await queue.enqueue(_canonical_record())

    assert root.is_dir()
    assert _expected_path(root, "dlq-1").is_file()


async def test_stored_json_validates_back_into_canonical_record(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    record = _canonical_record(with_correlation=True)

    await queue.enqueue(record)

    restored = DLQRecord.model_validate_json(
        _expected_path(tmp_path / "dlq", record.record_id).read_text(encoding="utf-8")
    )
    assert restored == record
    assert restored.correlation_id == "corr-11"
    assert restored.diagnostics == record.diagnostics
    assert restored.payload_reference == "csv://operator-file/row/2"


async def test_persisted_keys_are_canonical_dlq_fields_only(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    record = _canonical_record(with_correlation=True)

    await queue.enqueue(record)

    payload = _load_json(_expected_path(tmp_path / "dlq", record.record_id))
    assert set(payload) == set(DLQRecord.model_fields)
    assert "payload" not in payload
    assert "raw_payload" not in payload
    diagnostics = payload["diagnostics"]
    assert isinstance(diagnostics, list)
    for item in diagnostics:
        assert isinstance(item, dict)
        assert set(item) == set(AdapterDiagnostic.model_fields)


async def test_optional_correlation_id_absence_is_preserved(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    record = _canonical_record(with_correlation=False)

    await queue.enqueue(record)

    restored = DLQRecord.model_validate_json(
        _expected_path(tmp_path / "dlq", record.record_id).read_text(encoding="utf-8")
    )
    assert restored.correlation_id is None
    assert restored == record


async def test_identical_retry_is_idempotent_and_does_not_duplicate(tmp_path: Path) -> None:
    root = tmp_path / "dlq"
    queue = FilesystemDeadLetterQueue(root_directory=root)
    record = _canonical_record()

    await queue.enqueue(record)
    stored = _expected_path(root, record.record_id)
    original = stored.read_bytes()

    await queue.enqueue(record)

    assert stored.read_bytes() == original
    assert list(root.glob("*.json")) == [stored]


async def test_same_id_different_metadata_raises_conflict_without_overwrite(
    tmp_path: Path,
) -> None:
    root = tmp_path / "dlq"
    queue = FilesystemDeadLetterQueue(root_directory=root)
    original = _canonical_record()
    await queue.enqueue(original)
    stored = _expected_path(root, original.record_id)
    original_bytes = stored.read_bytes()
    conflicting = original.model_copy(update={"payload_reference": "csv://operator-file/row/99"})

    with pytest.raises(ConflictError, match="conflicting DLQ record already exists") as caught:
        await queue.enqueue(conflicting)

    assert stored.read_bytes() == original_bytes
    assert list(root.glob("*.json")) == [stored]
    message = caught.value.message
    assert str(root) not in message
    assert _SECRET_SENTINEL not in message
    assert "csv://operator-file/row/99" not in message


async def test_filename_unsafe_record_id_stays_inside_configured_root(tmp_path: Path) -> None:
    root = tmp_path / "dlq"
    queue = FilesystemDeadLetterQueue(root_directory=root)
    record = dlq(record_id=_UNSAFE_RECORD_ID, payload_reference="csv://operator-file/row/7")

    await queue.enqueue(record)

    stored = _expected_path(root, _UNSAFE_RECORD_ID)
    assert stored.is_file()
    assert stored.parent == root
    assert ".." not in stored.name
    assert "/" not in stored.name
    assert "\\" not in stored.name
    assert list(root.glob("*.json")) == [stored]
    assert not (tmp_path / "outside.json").exists()
    restored = DLQRecord.model_validate_json(stored.read_text(encoding="utf-8"))
    assert restored.record_id == _UNSAFE_RECORD_ID


async def test_directory_creation_failure_is_sanitized_dependency_error(tmp_path: Path) -> None:
    blocked = tmp_path / "blocked"
    blocked.write_text("not-a-directory", encoding="utf-8")
    queue = FilesystemDeadLetterQueue(root_directory=blocked)

    with pytest.raises(
        DependencyUnavailableError, match="DLQ persistence is unavailable"
    ) as caught:
        await queue.enqueue(_canonical_record())

    _assert_sanitized(caught.value, root=blocked, secret=_SECRET_SENTINEL)


async def test_write_failure_is_sanitized_dependency_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "dlq"
    queue = FilesystemDeadLetterQueue(root_directory=root)
    original_open = Path.open

    def fail_exclusive(
        self: Path,
        mode: str = "r",
        *args: object,
        **kwargs: object,
    ) -> object:
        if "x" in mode:
            raise OSError(f"disk I/O error at {root} containing {_SECRET_SENTINEL}")
        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_exclusive)

    with pytest.raises(
        DependencyUnavailableError, match="DLQ persistence is unavailable"
    ) as caught:
        await queue.enqueue(_canonical_record())

    _assert_sanitized(caught.value, root=root, secret=_SECRET_SENTINEL)
    assert "disk I/O error" not in caught.value.message


async def test_corrupt_existing_record_is_sanitized_dependency_error(tmp_path: Path) -> None:
    root = tmp_path / "dlq"
    root.mkdir()
    record = _canonical_record()
    stored = _expected_path(root, record.record_id)
    stored.write_text(f'{{"corrupt": "{_SECRET_SENTINEL}"}}', encoding="utf-8")
    queue = FilesystemDeadLetterQueue(root_directory=root)

    with pytest.raises(
        DependencyUnavailableError, match="DLQ persistence is unavailable"
    ) as caught:
        await queue.enqueue(record)

    _assert_sanitized(caught.value, root=root, secret=_SECRET_SENTINEL)
    assert stored.read_text(encoding="utf-8") == f'{{"corrupt": "{_SECRET_SENTINEL}"}}'


async def test_enqueue_offloads_blocking_filesystem_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: list[object] = []
    queue = _queue(tmp_path)
    record = _canonical_record()

    async def tracking_to_thread(func: object, /, *args: object, **kwargs: object) -> object:
        recorded.append(func)
        assert not inspect.iscoroutinefunction(func)
        return func(*args, **kwargs)

    monkeypatch.setattr(
        "energy_trading.infrastructure.persistence.dlq.asyncio.to_thread",
        tracking_to_thread,
    )

    await queue.enqueue(record)

    assert recorded
    assert not inspect.iscoroutinefunction(recorded[0])
    assert inspect.iscoroutinefunction(FilesystemDeadLetterQueue.enqueue)
    assert _expected_path(tmp_path / "dlq", record.record_id).is_file()


def _assert_sanitized(error: Exception, *, root: Path, secret: str) -> None:
    message = getattr(error, "message", str(error))
    rendered = str(error)
    assert secret not in message
    assert secret not in rendered
    assert str(root) not in message
    assert str(root) not in rendered
    assert str(root.parent) not in message
    assert "OSError" not in message
    assert "Traceback" not in message
    assert "corrupt" not in message
