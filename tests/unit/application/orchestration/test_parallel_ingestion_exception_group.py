"""Phase 2 ExceptionGroup extraction returns attributed leaves only."""

from __future__ import annotations

import asyncio
import inspect

import pytest

from energy_trading.application.agents import AgentName
from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration import (
    ParallelIngestionAgentFailure,
    extract_parallel_ingestion_agent_failures,
)

_UNATTRIBUTED_FAILURE_MESSAGE = "Parallel-ingestion failure group contains an unattributed failure."
_SENTINEL_TEXT = "sensitive-unattributed-failure-text-not-for-clients"
_CAUSE_SENTINEL_TEXT = "sentinel-cause-text-not-for-clients"


def _failure(agent_name: AgentName) -> ParallelIngestionAgentFailure:
    return ParallelIngestionAgentFailure(agent_name)


def _chained_failure(
    agent_name: AgentName,
    cause: Exception,
) -> ParallelIngestionAgentFailure:
    try:
        raise ParallelIngestionAgentFailure(agent_name) from cause
    except ParallelIngestionAgentFailure as exc:
        return exc


def test_extract_signature_accepts_base_exception_group() -> None:
    signature = inspect.signature(extract_parallel_ingestion_agent_failures)
    assert tuple(signature.parameters) == ("failure",)
    annotation = signature.parameters["failure"].annotation
    assert annotation in {BaseExceptionGroup, BaseExceptionGroup[BaseException]}
    assert signature.return_annotation == tuple[ParallelIngestionAgentFailure, ...]


def test_single_attributed_leaf_is_returned_by_identity() -> None:
    leaf = _failure(AgentName.WEATHER_AND_RENEWABLE_FORECAST)
    group = ExceptionGroup("group", [leaf])
    extracted = extract_parallel_ingestion_agent_failures(group)
    assert len(extracted) == 1
    assert extracted[0] is leaf
    assert extracted[0].agent_name is AgentName.WEATHER_AND_RENEWABLE_FORECAST


def test_multiple_flat_attributed_leaves_preserve_left_to_right_identity() -> None:
    weather = _failure(AgentName.WEATHER_AND_RENEWABLE_FORECAST)
    hydro = _failure(AgentName.HYDRO_RESOURCES)
    market = _failure(AgentName.MARKET_MONITORING)
    group = ExceptionGroup("group", [weather, hydro, market])
    extracted = extract_parallel_ingestion_agent_failures(group)
    assert extracted == (weather, hydro, market)
    assert extracted[0] is weather
    assert extracted[1] is hydro
    assert extracted[2] is market


def test_nested_exception_groups_preserve_depth_first_left_to_right_order() -> None:
    weather = _failure(AgentName.WEATHER_AND_RENEWABLE_FORECAST)
    hydro = _failure(AgentName.HYDRO_RESOURCES)
    news = _failure(AgentName.NEWS_INTELLIGENCE)
    market = _failure(AgentName.MARKET_MONITORING)
    group = ExceptionGroup(
        "outer",
        [
            weather,
            ExceptionGroup("inner", [hydro, news]),
            market,
        ],
    )
    extracted = extract_parallel_ingestion_agent_failures(group)
    assert extracted == (weather, hydro, news, market)
    assert extracted[0] is weather
    assert extracted[1] is hydro
    assert extracted[2] is news
    assert extracted[3] is market


def test_same_agent_failures_are_not_deduplicated() -> None:
    first = _failure(AgentName.HYDRO_RESOURCES)
    second = _failure(AgentName.HYDRO_RESOURCES)
    group = ExceptionGroup("group", [first, second])
    extracted = extract_parallel_ingestion_agent_failures(group)
    assert extracted == (first, second)
    assert extracted[0] is first
    assert extracted[1] is second
    assert extracted[0] is not extracted[1]
    assert extracted[0].agent_name is AgentName.HYDRO_RESOURCES
    assert extracted[1].agent_name is AgentName.HYDRO_RESOURCES


def test_extraction_preserves_chained_cause_identity() -> None:
    sentinel = RuntimeError(_CAUSE_SENTINEL_TEXT)
    wrapper = _chained_failure(AgentName.GENERATION_AVAILABILITY, sentinel)
    group = ExceptionGroup("group", [wrapper])
    extracted = extract_parallel_ingestion_agent_failures(group)
    assert extracted[0] is wrapper
    assert extracted[0].__cause__ is sentinel
    assert _CAUSE_SENTINEL_TEXT not in str(extracted[0])


def test_unexpected_raw_exception_leaf_fails_closed_without_partial_result() -> None:
    attributed = _failure(AgentName.NEWS_INTELLIGENCE)
    group = ExceptionGroup(
        "group",
        [
            attributed,
            RuntimeError(_SENTINEL_TEXT),
        ],
    )
    with pytest.raises(InvalidRequestError) as caught:
        extract_parallel_ingestion_agent_failures(group)
    assert caught.value.message == _UNATTRIBUTED_FAILURE_MESSAGE
    assert str(caught.value) == _UNATTRIBUTED_FAILURE_MESSAGE
    assert _SENTINEL_TEXT not in str(caught.value)
    assert "RuntimeError" not in str(caught.value)


def test_unexpected_leaf_nested_deeply_fails_closed() -> None:
    weather = _failure(AgentName.WEATHER_AND_RENEWABLE_FORECAST)
    hydro = _failure(AgentName.HYDRO_RESOURCES)
    group = ExceptionGroup(
        "outer",
        [
            weather,
            ExceptionGroup(
                "middle",
                [
                    ExceptionGroup(
                        "inner",
                        [hydro, RuntimeError(_SENTINEL_TEXT)],
                    )
                ],
            ),
        ],
    )
    with pytest.raises(InvalidRequestError) as caught:
        extract_parallel_ingestion_agent_failures(group)
    assert caught.value.message == _UNATTRIBUTED_FAILURE_MESSAGE
    assert _SENTINEL_TEXT not in str(caught.value)


def test_only_unexpected_leaf_fails_closed() -> None:
    group = ExceptionGroup("group", [RuntimeError(_SENTINEL_TEXT)])
    with pytest.raises(InvalidRequestError) as caught:
        extract_parallel_ingestion_agent_failures(group)
    assert caught.value.message == _UNATTRIBUTED_FAILURE_MESSAGE
    assert _SENTINEL_TEXT not in str(caught.value)


def test_nested_base_exception_group_of_attributed_leaves_is_traversed() -> None:
    weather = _failure(AgentName.WEATHER_AND_RENEWABLE_FORECAST)
    hydro = _failure(AgentName.HYDRO_RESOURCES)
    inner = BaseExceptionGroup("inner", [hydro])
    outer = BaseExceptionGroup("outer", [weather, inner])
    assert isinstance(outer, BaseExceptionGroup)
    extracted = extract_parallel_ingestion_agent_failures(outer)
    assert extracted == (weather, hydro)
    assert extracted[0] is weather
    assert extracted[1] is hydro


def test_cancelled_error_leaf_is_unattributed_and_fails_closed() -> None:
    attributed = _failure(AgentName.MARKET_MONITORING)
    group = BaseExceptionGroup(
        "group",
        [
            attributed,
            asyncio.CancelledError(),
        ],
    )
    assert type(group) is BaseExceptionGroup
    with pytest.raises(InvalidRequestError) as caught:
        extract_parallel_ingestion_agent_failures(group)
    assert caught.value.message == _UNATTRIBUTED_FAILURE_MESSAGE
    assert "CancelledError" not in str(caught.value)
    assert "cancelled" not in str(caught.value).lower()
