"""Phase 2 tuple-level classification composes sanitized failure facts."""

from __future__ import annotations

import inspect

import pytest

from energy_trading.application.agents import AgentName
from energy_trading.application.errors import (
    ApplicationError,
    ConflictError,
    DependencyUnavailableError,
    InvalidRequestError,
    ResourceNotFoundError,
)
from energy_trading.application.orchestration import (
    ParallelIngestionAgentFailure,
    ParallelIngestionFailureFact,
    classify_parallel_ingestion_agent_failure,
    classify_parallel_ingestion_agent_failures,
)
from energy_trading.application.orchestration import (
    parallel_ingestion_failure_classification as classification_module,
)

_UNEXPECTED_FAILURE_CODE = "parallel_ingestion_unexpected_failure"
_SENTINEL_TEXT = "secret provider payload"


class _CustomApplicationError(ApplicationError):
    """Test-only subclass proving published ``code`` is reused, not remapped."""

    code = "custom_application_code"


class _VendorPayloadError(Exception):
    """Test-only third-party-shaped failure. Not an application error."""


def _chained_failure(
    agent_name: AgentName,
    cause: BaseException,
) -> ParallelIngestionAgentFailure:
    try:
        raise ParallelIngestionAgentFailure(agent_name) from cause
    except ParallelIngestionAgentFailure as exc:
        return exc


def _expected(
    failures: tuple[ParallelIngestionAgentFailure, ...],
) -> tuple[ParallelIngestionFailureFact, ...]:
    return tuple(classify_parallel_ingestion_agent_failure(failure) for failure in failures)


def test_classify_signature_accepts_attributed_failure_tuple() -> None:
    signature = inspect.signature(classify_parallel_ingestion_agent_failures)
    assert tuple(signature.parameters) == ("failures",)
    parameter = signature.parameters["failures"]
    assert parameter.annotation in {
        tuple[ParallelIngestionAgentFailure, ...],
        "tuple[ParallelIngestionAgentFailure, ...]",
    }
    assert signature.return_annotation in {
        tuple[ParallelIngestionFailureFact, ...],
        "tuple[ParallelIngestionFailureFact, ...]",
    }
    assert not inspect.iscoroutinefunction(classify_parallel_ingestion_agent_failures)


def test_empty_tuple_returns_empty_tuple() -> None:
    assert classify_parallel_ingestion_agent_failures(()) == ()


def test_single_attributed_failure_preserves_agent_and_existing_code() -> None:
    cause = DependencyUnavailableError("source unavailable")
    failure = _chained_failure(AgentName.GENERATION_AVAILABILITY, cause)
    facts = classify_parallel_ingestion_agent_failures((failure,))
    assert len(facts) == 1
    assert isinstance(facts[0], ParallelIngestionFailureFact)
    assert facts == _expected((failure,))
    assert facts[0].agent_name is AgentName.GENERATION_AVAILABILITY
    assert facts[0].error_code == cause.code
    assert facts[0].error_code != _UNEXPECTED_FAILURE_CODE


def test_multiple_failures_preserve_encounter_order() -> None:
    weather = _chained_failure(
        AgentName.WEATHER_AND_RENEWABLE_FORECAST,
        InvalidRequestError("weather request is invalid"),
    )
    hydro = _chained_failure(
        AgentName.HYDRO_RESOURCES,
        DependencyUnavailableError("hydro source unavailable"),
    )
    market = _chained_failure(
        AgentName.MARKET_MONITORING,
        ConflictError("market state conflict"),
    )
    failures = (weather, hydro, market)
    facts = classify_parallel_ingestion_agent_failures(failures)
    assert facts == _expected(failures)
    assert [fact.agent_name for fact in facts] == [
        AgentName.WEATHER_AND_RENEWABLE_FORECAST,
        AgentName.HYDRO_RESOURCES,
        AgentName.MARKET_MONITORING,
    ]
    assert [fact.error_code for fact in facts] == [
        "invalid_request",
        "dependency_unavailable",
        "conflict",
    ]


def test_duplicate_agent_identities_are_not_collapsed() -> None:
    first = _chained_failure(
        AgentName.HYDRO_RESOURCES,
        InvalidRequestError("first hydro failure"),
    )
    second = _chained_failure(
        AgentName.HYDRO_RESOURCES,
        DependencyUnavailableError("second hydro failure"),
    )
    failures = (first, second)
    facts = classify_parallel_ingestion_agent_failures(failures)
    assert facts == _expected(failures)
    assert len(facts) == 2
    assert facts[0].agent_name is AgentName.HYDRO_RESOURCES
    assert facts[1].agent_name is AgentName.HYDRO_RESOURCES
    assert facts[0] is not facts[1]
    assert facts[0].error_code == "invalid_request"
    assert facts[1].error_code == "dependency_unavailable"


def test_mixed_error_codes_are_classified_independently() -> None:
    failures = (
        _chained_failure(
            AgentName.WEATHER_AND_RENEWABLE_FORECAST,
            InvalidRequestError("weather request is invalid"),
        ),
        _chained_failure(
            AgentName.HYDRO_RESOURCES,
            ResourceNotFoundError("hydro resource missing"),
        ),
        _chained_failure(
            AgentName.GENERATION_AVAILABILITY,
            _CustomApplicationError("custom generation failure"),
        ),
        _chained_failure(
            AgentName.NEWS_INTELLIGENCE,
            RuntimeError(_SENTINEL_TEXT),
        ),
        ParallelIngestionAgentFailure(AgentName.MARKET_MONITORING),
    )
    facts = classify_parallel_ingestion_agent_failures(failures)
    assert facts == _expected(failures)
    assert [fact.error_code for fact in facts] == [
        "invalid_request",
        "resource_not_found",
        "custom_application_code",
        _UNEXPECTED_FAILURE_CODE,
        _UNEXPECTED_FAILURE_CODE,
    ]


def test_unexpected_non_application_causes_collapse_through_singular_classifier() -> None:
    failures = (
        _chained_failure(AgentName.NEWS_INTELLIGENCE, RuntimeError(_SENTINEL_TEXT)),
        _chained_failure(AgentName.MARKET_MONITORING, ValueError(_SENTINEL_TEXT)),
        _chained_failure(AgentName.HYDRO_RESOURCES, _VendorPayloadError(_SENTINEL_TEXT)),
    )
    facts = classify_parallel_ingestion_agent_failures(failures)
    assert facts == _expected(failures)
    assert all(fact.error_code == _UNEXPECTED_FAILURE_CODE for fact in facts)
    for fact in facts:
        assert _SENTINEL_TEXT not in fact.error_code
        assert _SENTINEL_TEXT not in repr(fact)


def test_missing_causes_collapse_to_unexpected_failure() -> None:
    weather = ParallelIngestionAgentFailure(AgentName.WEATHER_AND_RENEWABLE_FORECAST)
    news = ParallelIngestionAgentFailure(AgentName.NEWS_INTELLIGENCE)
    assert weather.__cause__ is None
    assert news.__cause__ is None
    failures = (weather, news)
    facts = classify_parallel_ingestion_agent_failures(failures)
    assert facts == _expected(failures)
    assert facts[0].agent_name is AgentName.WEATHER_AND_RENEWABLE_FORECAST
    assert facts[1].agent_name is AgentName.NEWS_INTELLIGENCE
    assert facts[0].error_code == _UNEXPECTED_FAILURE_CODE
    assert facts[1].error_code == _UNEXPECTED_FAILURE_CODE


def test_classifier_does_not_mutate_failures_or_causes() -> None:
    first_cause = RuntimeError(_SENTINEL_TEXT)
    second_cause = DependencyUnavailableError("source unavailable")
    first = _chained_failure(AgentName.HYDRO_RESOURCES, first_cause)
    second = _chained_failure(AgentName.MARKET_MONITORING, second_cause)
    failures = (first, second)
    classify_parallel_ingestion_agent_failures(failures)
    assert failures[0] is first
    assert failures[1] is second
    assert first.__cause__ is first_cause
    assert second.__cause__ is second_cause
    assert first.agent_name is AgentName.HYDRO_RESOURCES
    assert second.agent_name is AgentName.MARKET_MONITORING


def test_equivalent_input_tuples_produce_value_equivalent_facts() -> None:
    first = _chained_failure(
        AgentName.GENERATION_AVAILABILITY,
        InvalidRequestError("request is invalid"),
    )
    second = _chained_failure(
        AgentName.NEWS_INTELLIGENCE,
        RuntimeError(_SENTINEL_TEXT),
    )
    first_facts = classify_parallel_ingestion_agent_failures((first, second))
    second_facts = classify_parallel_ingestion_agent_failures((first, second))
    assert first_facts == second_facts
    assert first_facts == _expected((first, second))
    assert first_facts is not second_facts


def test_tuple_classifier_delegates_each_element_to_singular_classifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[ParallelIngestionAgentFailure] = []
    original = classification_module.classify_parallel_ingestion_agent_failure

    def tracking(failure: ParallelIngestionAgentFailure) -> ParallelIngestionFailureFact:
        calls.append(failure)
        return original(failure)

    monkeypatch.setattr(
        classification_module,
        "classify_parallel_ingestion_agent_failure",
        tracking,
    )
    weather = _chained_failure(
        AgentName.WEATHER_AND_RENEWABLE_FORECAST,
        InvalidRequestError("weather request is invalid"),
    )
    hydro = _chained_failure(
        AgentName.HYDRO_RESOURCES,
        DependencyUnavailableError("hydro source unavailable"),
    )
    failures = (weather, hydro)
    facts = classify_parallel_ingestion_agent_failures(failures)
    assert calls == [weather, hydro]
    assert facts == _expected(failures)
