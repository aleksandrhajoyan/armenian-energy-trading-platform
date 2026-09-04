"""Filesystem-backed Dead Letter Queue metadata persistence.

This is an interim local/development implementation of
``DeadLetterQueuePort``. It stores canonical ``DLQRecord`` metadata only.
It does not store or dereference failed raw payloads, and it is not the
PostgreSQL/TimescaleDB system of record.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

from energy_trading.application.errors import ConflictError, DependencyUnavailableError
from energy_trading.domain.models.ingestion import DLQRecord

_MSG_UNAVAILABLE = "DLQ persistence is unavailable"
_MSG_CONFLICT = "A conflicting DLQ record already exists"


class FilesystemDeadLetterQueue:
    """Persist one canonical DLQ metadata JSON file per ``record_id``.

    The application-facing ``enqueue`` signature accepts only a canonical
    ``DLQRecord``. The storage root is constructor-injected and is not part
    of the application port. Blocking filesystem I/O runs in a worker thread.
    """

    def __init__(self, *, root_directory: Path) -> None:
        self._root = _require_path(root_directory)

    async def enqueue(self, record: DLQRecord) -> None:
        """Persist one canonical DLQ metadata record.

        Retrying the exact same canonical record is idempotent. A different
        canonical record with the same ``record_id`` is a conflict.
        """

        await asyncio.to_thread(self._enqueue_sync, record)

    def _enqueue_sync(self, record: DLQRecord) -> None:
        try:
            self._root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc

        path = _record_path(self._root, record.record_id)
        serialized = _serialize(record)
        created = False
        try:
            with path.open("x", encoding="utf-8", newline="\n") as handle:
                created = True
                handle.write(serialized)
        except FileExistsError:
            _reconcile_existing(path, record)
        except OSError as exc:
            if created:
                _best_effort_unlink(path)
            raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc


def _require_path(value: object) -> Path:
    if not isinstance(value, Path):
        msg = "root_directory must be a pathlib.Path"
        raise TypeError(msg)
    return value


def _record_path(root: Path, record_id: str) -> Path:
    digest = hashlib.sha256(record_id.encode("utf-8")).hexdigest()
    return root / f"{digest}.json"


def _serialize(record: DLQRecord) -> str:
    return json.dumps(
        record.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _reconcile_existing(path: Path, record: DLQRecord) -> None:
    try:
        existing = DLQRecord.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DependencyUnavailableError(_MSG_UNAVAILABLE) from exc

    if existing == record:
        return
    if existing.record_id == record.record_id:
        raise ConflictError(_MSG_CONFLICT)
    raise DependencyUnavailableError(_MSG_UNAVAILABLE)


def _best_effort_unlink(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        return
