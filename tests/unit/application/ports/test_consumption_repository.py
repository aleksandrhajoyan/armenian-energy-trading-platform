"""Consumption persistence application-port contract."""

from __future__ import annotations

import inspect

import pytest

from energy_trading.application.errors import ConflictError
from energy_trading.application.ports import ConsumptionRepositoryPort
from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
)
from tests.unit.application.fakes import (
    FakeConsumptionRepository,
    as_consumption_repository_port,
)
from tests.unit.domain._factories import consumption

PORT_FILE = SRC_ROOT / "energy_trading" / "application" / "ports" / "consumption_repository.py"

FORBIDDEN_PORT_TYPES = frozenset(
    {
        "Any",
        "AsyncSession",
        "Session",
        "Engine",
        "AsyncEngine",
        "Table",
        "MetaData",
        "Connection",
        "Path",
        "bytes",
        "bytearray",
        "dict",
        "Dict",
        "Mapping",
        "DataFrame",
        "Workbook",
    }
)


def test_fake_structurally_satisfies_consumption_repository_port() -> None:
    repository = FakeConsumptionRepository()
    port: ConsumptionRepositoryPort = as_consumption_repository_port(repository)
    assert inspect.iscoroutinefunction(port.save_many)


def test_save_many_signature_accepts_tuple_of_canonical_records() -> None:
    assert async_function_arg_names(PORT_FILE, "save_many") == ("self", "records")
    names = annotation_type_names(PORT_FILE)
    assert "ConsumptionRecord" in names
    leaked = sorted(name for name in names if name in FORBIDDEN_PORT_TYPES)
    assert leaked == []


async def test_empty_tuple_is_valid() -> None:
    port = as_consumption_repository_port(FakeConsumptionRepository())
    await port.save_many(())


async def test_fake_can_represent_success() -> None:
    fake = FakeConsumptionRepository()
    port = as_consumption_repository_port(fake)
    record = consumption()
    await port.save_many((record,))
    assert fake.records == (record,)


async def test_fake_can_represent_conflict_error() -> None:
    fake = FakeConsumptionRepository()
    fake.raise_conflict = True
    port = as_consumption_repository_port(fake)
    with pytest.raises(ConflictError, match="conflicting consumption observation"):
        await port.save_many((consumption(),))
