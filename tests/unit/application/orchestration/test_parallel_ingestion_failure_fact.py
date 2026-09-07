"""Phase 2 one-leaf classification produces sanitized failure facts."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, fields

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
)

_PHASE2_AGENT_NAMES = (
    AgentName.WEATHER_AND_RENEWABLE_FORECAST,
    AgentName.HYDRO_RESOURCES,
    AgentName.GENERATION_AVAILABILITY,
    AgentName.NEWS_INTELLIGENCE,
    AgentName.MARKET_MONITORING,
)
_SENTINEL_TEXT = "secret provider payload"
_UNEXPECTED_FAILURE_CODE = "parallel_ingestion_unexpected_failure"
_FACT_FIELDS = ("agent_name", "error_code")


class _CustomApplicationError(ApplicationError):
    """Test-only subclass proving published ``code`` is reused, not mapped."""

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


def test_failure_fact_is_frozen_with_exact_fields() -> None:
    fact = ParallelIngestionFailureFact(
        agent_name=AgentName.HYDRO_RESOURCES,
        error_code="dependency_unavailable",
    )
    assert tuple(item.name for item in fields(fact)) == _FACT_FIELDS
    assert fact.agent_name is AgentName.HYDRO_RESOURCES
    assert fact.error_code == "dependency_unavailable"
    with pytest.raises(FrozenInstanceError):
        fact.error_code = "mutated"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        fact.agent_name = AgentName.MARKET_MONITORING  # type: ignore[misc]


def test_failure_fact_strips_error_code_whitespace() -> None:
    fact = ParallelIngestionFailureFact(
        agent_name=AgentName.NEWS_INTELLIGENCE,
        error_code="  invalid_request  ",
    )
    assert fact.error_code == "invalid_request"


@pytest.mark.parametrize("error_code", ["", "   "])
def test_failure_fact_rejects_blank_error_code(error_code: str) -> None:
    with pytest.raises(ValueError, match="error_code must be a non-empty string"):
        ParallelIngestionFailureFact(
            agent_name=AgentName.MARKET_MONITORING,
            error_code=error_code,
        )


@pytest.mark.parametrize("error_code", [None, 1, b"opaque", True])
def test_failure_fact_rejects_non_string_error_code(error_code: object) -> None:
    with pytest.raises(TypeError, match="error_code must be a string"):
        ParallelIngestionFailureFact(
            agent_name=AgentName.MARKET_MONITORING,
            error_code=error_code,  # type: ignore[arg-type]
        )


def test_failure_fact_requires_canonical_agent_name() -> None:
    with pytest.raises(TypeError, match="agent_name must be an AgentName"):
        ParallelIngestionFailureFact(
            agent_name="Weather & Renewable Forecast Agent",  # type: ignore[arg-type]
            error_code="dependency_unavailable",
        )


def test_failure_fact_rejects_unexpected_public_fields() -> None:
    with pytest.raises(TypeError):
        ParallelIngestionFailureFact(
            agent_name=AgentName.HYDRO_RESOURCES,
            error_code="dependency_unavailable",
            attempt_number=1,  # type: ignore[call-arg]
        )


def test_classify_signature_accepts_one_attributed_failure() -> None:
    signature = inspect.signature(classify_parallel_ingestion_agent_failure)
    assert tuple(signature.parameters) == ("failure",)
    parameter = signature.parameters["failure"]
    assert parameter.annotation in {
        ParallelIngestionAgentFailure,
        "ParallelIngestionAgentFailure",
    }
    assert signature.return_annotation in {
        ParallelIngestionFailureFact,
        "ParallelIngestionFailureFact",
    }
    assert not inspect.iscoroutinefunction(classify_parallel_ingestion_agent_failure)


@pytest.mark.parametrize(
    "cause",
    [
        ApplicationError("generic application failure"),
        InvalidRequestError("request is invalid"),
        ResourceNotFoundError("resource is missing"),
        ConflictError("state conflict"),
        DependencyUnavailableError("dependency is down"),
        _CustomApplicationError("custom application failure"),
    ],
)
def test_application_error_cause_reuses_published_code(cause: ApplicationError) -> None:
    failure = _chained_failure(AgentName.GENERATION_AVAILABILITY, cause)
    fact = classify_parallel_ingestion_agent_failure(failure)
    assert fact.agent_name is AgentName.GENERATION_AVAILABILITY
    assert fact.error_code == cause.code
    assert fact.error_code != _UNEXPECTED_FAILURE_CODE
    assert cause.message not in fact.error_code
    assert cause.message not in repr(fact)


def test_unexpected_standard_exception_collapses_without_leaking_text() -> None:
    cause = RuntimeError(_SENTINEL_TEXT)
    failure = _chained_failure(AgentName.WEATHER_AND_RENEWABLE_FORECAST, cause)
    fact = classify_parallel_ingestion_agent_failure(failure)
    assert fact.agent_name is AgentName.WEATHER_AND_RENEWABLE_FORECAST
    assert fact.error_code == _UNEXPECTED_FAILURE_CODE
    assert _SENTINEL_TEXT not in fact.error_code
    assert _SENTINEL_TEXT not in repr(fact)
    assert _SENTINEL_TEXT not in str(fact)
    assert "RuntimeError" not in fact.error_code


@pytest.mark.parametrize(
    "cause",
    [
        RuntimeError(_SENTINEL_TEXT),
        ValueError(_SENTINEL_TEXT),
        KeyError(_SENTINEL_TEXT),
        OSError(_SENTINEL_TEXT),
        _VendorPayloadError(_SENTINEL_TEXT),
    ],
)
def test_unrelated_unexpected_exception_classes_share_stable_code(
    cause: BaseException,
) -> None:
    failure = _chained_failure(AgentName.MARKET_MONITORING, cause)
    fact = classify_parallel_ingestion_agent_failure(failure)
    assert fact.error_code == _UNEXPECTED_FAILURE_CODE
    assert type(cause).__name__ not in fact.error_code
    assert _SENTINEL_TEXT not in fact.error_code
    assert _SENTINEL_TEXT not in repr(fact)


def test_missing_cause_collapses_to_unexpected_failure() -> None:
    failure = ParallelIngestionAgentFailure(AgentName.NEWS_INTELLIGENCE)
    assert failure.__cause__ is None
    fact = classify_parallel_ingestion_agent_failure(failure)
    assert fact.agent_name is AgentName.NEWS_INTELLIGENCE
    assert fact.error_code == _UNEXPECTED_FAILURE_CODE


def test_classifier_does_not_mutate_causal_identity() -> None:
    cause = RuntimeError(_SENTINEL_TEXT)
    failure = _chained_failure(AgentName.HYDRO_RESOURCES, cause)
    assert failure.__cause__ is cause
    classify_parallel_ingestion_agent_failure(failure)
    assert failure.__cause__ is cause
    assert failure.agent_name is AgentName.HYDRO_RESOURCES


@pytest.mark.parametrize("agent_name", _PHASE2_AGENT_NAMES)
def test_classifier_preserves_each_phase2_agent_identity(agent_name: AgentName) -> None:
    cause = DependencyUnavailableError("source unavailable")
    failure = _chained_failure(agent_name, cause)
    fact = classify_parallel_ingestion_agent_failure(failure)
    assert fact.agent_name is agent_name
    assert fact.error_code == cause.code
