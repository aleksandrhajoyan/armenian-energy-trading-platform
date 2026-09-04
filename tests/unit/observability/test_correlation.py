"""Unit tests for correlation ID context and validation."""

import asyncio

from energy_trading.shared.observability.correlation import (
    correlation_id_scope,
    generate_correlation_id,
    get_correlation_id,
    is_valid_correlation_id,
)


def test_correlation_scope_binds_and_resets() -> None:
    assert get_correlation_id() is None
    with correlation_id_scope("portfolio-demo-123"):
        assert get_correlation_id() == "portfolio-demo-123"
        with correlation_id_scope("nested-id"):
            assert get_correlation_id() == "nested-id"
        assert get_correlation_id() == "portfolio-demo-123"
    assert get_correlation_id() is None


def test_generated_correlation_id_is_valid() -> None:
    generated = generate_correlation_id()
    assert is_valid_correlation_id(generated)


def test_correlation_id_validation_rules() -> None:
    assert is_valid_correlation_id("portfolio-demo-123")
    assert is_valid_correlation_id("abc.def_ghi:123-xyz")
    assert not is_valid_correlation_id("")
    assert not is_valid_correlation_id("has spaces")
    assert not is_valid_correlation_id("bad/slash")
    assert not is_valid_correlation_id("x" * 129)
    assert not is_valid_correlation_id("<script>")


async def test_async_tasks_do_not_leak_correlation_ids() -> None:
    async def bound(correlation_id: str) -> str | None:
        with correlation_id_scope(correlation_id):
            await asyncio.sleep(0.01)
            return get_correlation_id()

    first, second = await asyncio.gather(bound("task-one"), bound("task-two"))
    assert first == "task-one"
    assert second == "task-two"
    assert get_correlation_id() is None
