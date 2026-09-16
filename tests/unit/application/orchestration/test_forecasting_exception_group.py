"""Phase 3 ExceptionGroup extraction returns attributed leaves only."""

from __future__ import annotations

import asyncio
import inspect

import pytest

from energy_trading.application.agents import AgentName
from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration import (
    ForecastingAgentFailure,
    extract_forecasting_agent_failures,
)

_UNATTRIBUTED_FAILURE_MESSAGE = "Forecasting failure group contains an unattributed failure."
_SENTINEL_TEXT = "sensitive-unattributed-failure-text-not-for-clients"
_CAUSE_SENTINEL_TEXT = "sentinel-cause-text-not-for-clients"


def _failure(agent_name: AgentName) -> ForecastingAgentFailure:
    return ForecastingAgentFailure(agent_name)


def _chained_failure(
    agent_name: AgentName,
    cause: Exception,
) -> ForecastingAgentFailure:
    try:
        raise ForecastingAgentFailure(agent_name) from cause
    except ForecastingAgentFailure as exc:
        return exc


def test_extract_signature_accepts_base_exception_group() -> None:
    signature = inspect.signature(extract_forecasting_agent_failures)
    assert tuple(signature.parameters) == ("failure",)
    annotation = signature.parameters["failure"].annotation
    assert annotation in {BaseExceptionGroup, BaseExceptionGroup[BaseException]}
    assert signature.return_annotation == tuple[ForecastingAgentFailure, ...]


def test_single_attributed_leaf_is_returned_by_identity() -> None:
    leaf = _failure(AgentName.CONSUMER_LOAD_FORECAST)
    group = ExceptionGroup("group", [leaf])
    extracted = extract_forecasting_agent_failures(group)
    assert len(extracted) == 1
    assert extracted[0] is leaf
    assert extracted[0].agent_name is AgentName.CONSUMER_LOAD_FORECAST


@pytest.mark.parametrize(
    "agent_name",
    (
        AgentName.CONSUMER_LOAD_FORECAST,
        AgentName.DAM_PRICE_FORECAST,
    ),
)
def test_canonical_phase_3_agent_names_are_accepted(agent_name: AgentName) -> None:
    leaf = _failure(agent_name)
    group = ExceptionGroup("group", [leaf])
    extracted = extract_forecasting_agent_failures(group)
    assert extracted == (leaf,)
    assert extracted[0] is leaf
    assert extracted[0].agent_name is agent_name


def test_multiple_flat_attributed_leaves_preserve_left_to_right_identity() -> None:
    consumer = _failure(AgentName.CONSUMER_LOAD_FORECAST)
    dam = _failure(AgentName.DAM_PRICE_FORECAST)
    group = ExceptionGroup("group", [consumer, dam])
    extracted = extract_forecasting_agent_failures(group)
    assert extracted == (consumer, dam)
    assert extracted[0] is consumer
    assert extracted[1] is dam
    assert extracted[0] is not extracted[1]


def test_same_agent_failures_are_not_deduplicated() -> None:
    first = _failure(AgentName.CONSUMER_LOAD_FORECAST)
    second = _failure(AgentName.CONSUMER_LOAD_FORECAST)
    group = ExceptionGroup("group", [first, second])
    extracted = extract_forecasting_agent_failures(group)
    assert extracted == (first, second)
    assert extracted[0] is first
    assert extracted[1] is second
    assert extracted[0] is not extracted[1]
    assert extracted[0].agent_name is AgentName.CONSUMER_LOAD_FORECAST
    assert extracted[1].agent_name is AgentName.CONSUMER_LOAD_FORECAST


def test_nested_exception_groups_preserve_depth_first_left_to_right_order() -> None:
    consumer = _failure(AgentName.CONSUMER_LOAD_FORECAST)
    dam = _failure(AgentName.DAM_PRICE_FORECAST)
    second_consumer = _failure(AgentName.CONSUMER_LOAD_FORECAST)
    group = ExceptionGroup(
        "outer",
        [
            consumer,
            ExceptionGroup("inner", [dam]),
            second_consumer,
        ],
    )
    extracted = extract_forecasting_agent_failures(group)
    assert extracted == (consumer, dam, second_consumer)
    assert extracted[0] is consumer
    assert extracted[1] is dam
    assert extracted[2] is second_consumer


def test_extraction_preserves_chained_cause_identity() -> None:
    sentinel = RuntimeError(_CAUSE_SENTINEL_TEXT)
    wrapper = _chained_failure(AgentName.DAM_PRICE_FORECAST, sentinel)
    group = ExceptionGroup("group", [wrapper])
    extracted = extract_forecasting_agent_failures(group)
    assert extracted[0] is wrapper
    assert extracted[0].__cause__ is sentinel
    assert _CAUSE_SENTINEL_TEXT not in str(extracted[0])


def test_unexpected_raw_exception_leaf_fails_closed_without_partial_result() -> None:
    attributed = _failure(AgentName.CONSUMER_LOAD_FORECAST)
    group = ExceptionGroup(
        "group",
        [
            attributed,
            RuntimeError(_SENTINEL_TEXT),
        ],
    )
    with pytest.raises(InvalidRequestError) as caught:
        extract_forecasting_agent_failures(group)
    assert caught.value.message == _UNATTRIBUTED_FAILURE_MESSAGE
    assert str(caught.value) == _UNATTRIBUTED_FAILURE_MESSAGE
    assert _SENTINEL_TEXT not in str(caught.value)
    assert "RuntimeError" not in str(caught.value)


def test_unexpected_leaf_nested_deeply_fails_closed() -> None:
    consumer = _failure(AgentName.CONSUMER_LOAD_FORECAST)
    dam = _failure(AgentName.DAM_PRICE_FORECAST)
    group = ExceptionGroup(
        "outer",
        [
            consumer,
            ExceptionGroup(
                "middle",
                [
                    ExceptionGroup(
                        "inner",
                        [dam, RuntimeError(_SENTINEL_TEXT)],
                    )
                ],
            ),
        ],
    )
    with pytest.raises(InvalidRequestError) as caught:
        extract_forecasting_agent_failures(group)
    assert caught.value.message == _UNATTRIBUTED_FAILURE_MESSAGE
    assert _SENTINEL_TEXT not in str(caught.value)


def test_only_unexpected_leaf_fails_closed() -> None:
    group = ExceptionGroup("group", [RuntimeError(_SENTINEL_TEXT)])
    with pytest.raises(InvalidRequestError) as caught:
        extract_forecasting_agent_failures(group)
    assert caught.value.message == _UNATTRIBUTED_FAILURE_MESSAGE
    assert _SENTINEL_TEXT not in str(caught.value)


def test_nested_base_exception_group_of_attributed_leaves_is_traversed() -> None:
    consumer = _failure(AgentName.CONSUMER_LOAD_FORECAST)
    dam = _failure(AgentName.DAM_PRICE_FORECAST)
    inner = BaseExceptionGroup("inner", [dam])
    outer = BaseExceptionGroup("outer", [consumer, inner])
    assert isinstance(outer, BaseExceptionGroup)
    extracted = extract_forecasting_agent_failures(outer)
    assert extracted == (consumer, dam)
    assert extracted[0] is consumer
    assert extracted[1] is dam


def test_cancelled_error_leaf_is_unattributed_and_fails_closed() -> None:
    attributed = _failure(AgentName.DAM_PRICE_FORECAST)
    group = BaseExceptionGroup(
        "group",
        [
            attributed,
            asyncio.CancelledError(),
        ],
    )
    assert type(group) is BaseExceptionGroup
    with pytest.raises(InvalidRequestError) as caught:
        extract_forecasting_agent_failures(group)
    assert caught.value.message == _UNATTRIBUTED_FAILURE_MESSAGE
    assert "CancelledError" not in str(caught.value)
    assert "cancelled" not in str(caught.value).lower()


def test_equivalent_group_structure_yields_equivalent_extraction_order() -> None:
    first_consumer = _failure(AgentName.CONSUMER_LOAD_FORECAST)
    first_dam = _failure(AgentName.DAM_PRICE_FORECAST)
    second_consumer = _failure(AgentName.CONSUMER_LOAD_FORECAST)
    second_dam = _failure(AgentName.DAM_PRICE_FORECAST)
    first_group = ExceptionGroup(
        "outer",
        [
            first_consumer,
            ExceptionGroup("inner", [first_dam]),
        ],
    )
    second_group = ExceptionGroup(
        "outer",
        [
            second_consumer,
            ExceptionGroup("inner", [second_dam]),
        ],
    )
    first_extracted = extract_forecasting_agent_failures(first_group)
    second_extracted = extract_forecasting_agent_failures(second_group)
    assert [leaf.agent_name for leaf in first_extracted] == [
        AgentName.CONSUMER_LOAD_FORECAST,
        AgentName.DAM_PRICE_FORECAST,
    ]
    assert [leaf.agent_name for leaf in second_extracted] == [
        leaf.agent_name for leaf in first_extracted
    ]
    assert extract_forecasting_agent_failures(first_group) == first_extracted
    assert extract_forecasting_agent_failures(first_group)[0] is first_consumer
    assert extract_forecasting_agent_failures(first_group)[1] is first_dam
