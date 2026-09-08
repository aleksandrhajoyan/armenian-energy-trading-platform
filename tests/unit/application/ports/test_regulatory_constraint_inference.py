"""Canonical regulatory-constraint inference application-port contract."""

from __future__ import annotations

import inspect

import pytest

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports import (
    ExtractedDocumentChunk,
    RegulatoryConstraintInferencePort,
)
from energy_trading.domain.models.regulatory import RegulatoryConstraint
from tests.unit.domain._factories import constraint


class _FakeRegulatoryConstraintInference:
    """Test-only fake that structurally satisfies ``RegulatoryConstraintInferencePort``.

    Not a production adapter. Does not inherit a production or infrastructure
    base class.
    """

    def __init__(
        self,
        constraints: tuple[RegulatoryConstraint, ...] = (),
        *,
        unavailable: bool = False,
    ) -> None:
        self.constraints = constraints
        self.unavailable = unavailable
        self.calls: list[tuple[ExtractedDocumentChunk, ...]] = []

    async def infer(
        self,
        *,
        chunks: tuple[ExtractedDocumentChunk, ...],
    ) -> tuple[RegulatoryConstraint, ...]:
        self.calls.append(chunks)
        if self.unavailable:
            msg = "regulatory inference unavailable"
            raise DependencyUnavailableError(msg)
        return self.constraints


def _as_inference_port(
    inference: _FakeRegulatoryConstraintInference,
) -> RegulatoryConstraintInferencePort:
    return inference


def _chunk(**overrides: object) -> ExtractedDocumentChunk:
    values: dict[str, object] = {
        "document_id": "doc-1",
        "chunk_id": "chunk-1",
        "ordinal": 0,
        "text": "Normalized extracted regulatory text.",
        "page_number": 1,
    }
    values.update(overrides)
    return ExtractedDocumentChunk(**values)  # type: ignore[arg-type]


def test_structural_fake_does_not_inherit_production_base() -> None:
    assert RegulatoryConstraintInferencePort not in _FakeRegulatoryConstraintInference.__mro__
    assert not any(
        base.__name__ in {"RegulatoryConstraintInferencePort", "Protocol"}
        for base in _FakeRegulatoryConstraintInference.__bases__
    )


def test_fake_provides_async_infer() -> None:
    fake = _FakeRegulatoryConstraintInference()
    port = _as_inference_port(fake)
    assert inspect.iscoroutinefunction(port.infer)
    parameters = inspect.signature(_FakeRegulatoryConstraintInference.infer).parameters
    assert tuple(parameters) == ("self", "chunks")
    assert parameters["chunks"].kind is inspect.Parameter.KEYWORD_ONLY


async def test_exact_chunk_tuple_is_accepted() -> None:
    fake = _FakeRegulatoryConstraintInference()
    port = _as_inference_port(fake)
    chunks = (_chunk(),)
    result = await port.infer(chunks=chunks)
    assert result == ()
    assert fake.calls == [chunks]
    assert fake.calls[0] is chunks


async def test_empty_constraint_tuple_is_valid() -> None:
    port = _as_inference_port(_FakeRegulatoryConstraintInference())
    result = await port.infer(chunks=(_chunk(),))
    assert result == ()
    assert isinstance(result, tuple)


async def test_one_canonical_constraint_is_valid() -> None:
    record = constraint()
    port = _as_inference_port(_FakeRegulatoryConstraintInference((record,)))
    result = await port.infer(chunks=(_chunk(),))
    assert result == (record,)
    assert all(isinstance(item, RegulatoryConstraint) for item in result)


async def test_multiple_canonical_constraints_preserve_order() -> None:
    first = constraint(constraint_id="constraint-1")
    second = constraint(
        constraint_id="constraint-2",
        constraint_type="license_window",
        description="Generic effective window",
    )
    port = _as_inference_port(_FakeRegulatoryConstraintInference((first, second)))
    result = await port.infer(chunks=(_chunk(), _chunk(chunk_id="chunk-2", ordinal=1)))
    assert result == (first, second)


async def test_canonical_constraint_fields_pass_through_unchanged() -> None:
    record = constraint(
        constraint_id="constraint-keep",
        constraint_type="capacity_limit",
        description="Generic numeric bound",
        minimum_value=1.0,
        maximum_value=10.0,
        unit="MW",
    )
    port = _as_inference_port(_FakeRegulatoryConstraintInference((record,)))
    result = await port.infer(chunks=(_chunk(),))
    assert result == (record,)
    passed = result[0]
    assert passed is record
    assert passed.constraint_id == "constraint-keep"
    assert passed.constraint_type == "capacity_limit"
    assert passed.description == "Generic numeric bound"
    assert passed.minimum_value == 1.0
    assert passed.maximum_value == 10.0
    assert passed.unit == "MW"


async def test_fake_can_represent_dependency_unavailable() -> None:
    fake = _FakeRegulatoryConstraintInference(unavailable=True)
    port = _as_inference_port(fake)
    with pytest.raises(DependencyUnavailableError, match="regulatory inference unavailable"):
        await port.infer(chunks=(_chunk(),))
    assert len(fake.calls) == 1
