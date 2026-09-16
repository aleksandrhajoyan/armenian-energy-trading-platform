"""Phase 3 one-leaf classification produces sanitized failure facts."""

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
    ForecastingAgentFailure,
    ForecastingFailureFact,
    classify_forecasting_agent_failure,
)

_PHASE3_AGENT_NAMES = (
    AgentName.CONSUMER_LOAD_FORECAST,
    AgentName.DAM_PRICE_FORECAST,
)
_SENTINEL_TEXT = "secret provider payload"
_UNEXPECTED_FAILURE_CODE = "forecasting_unexpected_failure"
_FACT_FIELDS = ("agent_name", "error_code")


class _CustomApplicationError(ApplicationError):
    """Test-only subclass proving published ``code`` is reused, not mapped."""

    code = "custom_application_code"


class _VendorPayloadError(Exception):
    """Test-only third-party-shaped failure. Not an application error."""


def _chained_failure(
    agent_name: AgentName,
    cause: BaseException,
) -> ForecastingAgentFailure:
    try:
        raise ForecastingAgentFailure(agent_name) from cause
    except ForecastingAgentFailure as exc:
        return exc


def test_failure_fact_is_frozen_with_exact_fields() -> None:
    fact = ForecastingFailureFact(
        agent_name=AgentName.CONSUMER_LOAD_FORECAST,
        error_code="dependency_unavailable",
    )
    assert tuple(item.name for item in fields(fact)) == _FACT_FIELDS
    assert fact.agent_name is AgentName.CONSUMER_LOAD_FORECAST
    assert fact.error_code == "dependency_unavailable"
    with pytest.raises(FrozenInstanceError):
        fact.error_code = "mutated"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        fact.agent_name = AgentName.DAM_PRICE_FORECAST  # type: ignore[misc]


def test_failure_fact_strips_error_code_whitespace() -> None:
    fact = ForecastingFailureFact(
        agent_name=AgentName.DAM_PRICE_FORECAST,
        error_code="  invalid_request  ",
    )
    assert fact.error_code == "invalid_request"


@pytest.mark.parametrize("error_code", ["", "   "])
def test_failure_fact_rejects_blank_error_code(error_code: str) -> None:
    with pytest.raises(ValueError, match="error_code must be a non-empty string"):
        ForecastingFailureFact(
            agent_name=AgentName.CONSUMER_LOAD_FORECAST,
            error_code=error_code,
        )


@pytest.mark.parametrize("error_code", [None, 1, b"opaque", True])
def test_failure_fact_rejects_non_string_error_code(error_code: object) -> None:
    with pytest.raises(TypeError, match="error_code must be a string"):
        ForecastingFailureFact(
            agent_name=AgentName.CONSUMER_LOAD_FORECAST,
            error_code=error_code,  # type: ignore[arg-type]
        )


def test_failure_fact_requires_canonical_agent_name() -> None:
    with pytest.raises(TypeError, match="agent_name must be an AgentName"):
        ForecastingFailureFact(
            agent_name="Consumer Load Forecast Agent",  # type: ignore[arg-type]
            error_code="dependency_unavailable",
        )


def test_failure_fact_rejects_unexpected_public_fields() -> None:
    with pytest.raises(TypeError):
        ForecastingFailureFact(
            agent_name=AgentName.CONSUMER_LOAD_FORECAST,
            error_code="dependency_unavailable",
            attempt_number=1,  # type: ignore[call-arg]
        )


def test_classify_signature_accepts_one_attributed_failure() -> None:
    signature = inspect.signature(classify_forecasting_agent_failure)
    assert tuple(signature.parameters) == ("failure",)
    parameter = signature.parameters["failure"]
    assert parameter.annotation in {
        ForecastingAgentFailure,
        "ForecastingAgentFailure",
    }
    assert signature.return_annotation in {
        ForecastingFailureFact,
        "ForecastingFailureFact",
    }
    assert not inspect.iscoroutinefunction(classify_forecasting_agent_failure)


def test_consumer_application_error_reuses_published_code() -> None:
    cause = DependencyUnavailableError("source unavailable")
    failure = _chained_failure(AgentName.CONSUMER_LOAD_FORECAST, cause)
    fact = classify_forecasting_agent_failure(failure)
    assert type(fact) is ForecastingFailureFact
    assert fact.agent_name is AgentName.CONSUMER_LOAD_FORECAST
    assert fact.error_code == cause.code
    assert fact.error_code == "dependency_unavailable"
    assert cause.message not in fact.error_code
    assert cause.message not in repr(fact)
    assert not hasattr(fact, "cause")
    assert not hasattr(fact, "exception")
    assert not hasattr(fact, "original_exception")
    assert not hasattr(fact, "traceback")


def test_dam_application_error_reuses_published_code() -> None:
    cause = DependencyUnavailableError("source unavailable")
    failure = _chained_failure(AgentName.DAM_PRICE_FORECAST, cause)
    fact = classify_forecasting_agent_failure(failure)
    assert type(fact) is ForecastingFailureFact
    assert fact.agent_name is AgentName.DAM_PRICE_FORECAST
    assert fact.error_code == cause.code
    assert cause.message not in fact.error_code
    assert cause.message not in repr(fact)


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
    failure = _chained_failure(AgentName.CONSUMER_LOAD_FORECAST, cause)
    fact = classify_forecasting_agent_failure(failure)
    assert fact.agent_name is AgentName.CONSUMER_LOAD_FORECAST
    assert fact.error_code == cause.code
    assert fact.error_code != _UNEXPECTED_FAILURE_CODE
    assert cause.message not in fact.error_code
    assert cause.message not in repr(fact)


def test_unexpected_standard_exception_collapses_without_leaking_text() -> None:
    cause = RuntimeError(_SENTINEL_TEXT)
    failure = _chained_failure(AgentName.CONSUMER_LOAD_FORECAST, cause)
    fact = classify_forecasting_agent_failure(failure)
    assert fact.agent_name is AgentName.CONSUMER_LOAD_FORECAST
    assert fact.error_code == _UNEXPECTED_FAILURE_CODE
    assert _SENTINEL_TEXT not in fact.error_code
    assert _SENTINEL_TEXT not in repr(fact)
    assert _SENTINEL_TEXT not in str(fact)
    assert "RuntimeError" not in fact.error_code
    assert not hasattr(fact, "cause")
    assert not hasattr(fact, "exception")
    assert not hasattr(fact, "original_exception")
    assert not hasattr(fact, "traceback")


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
    failure = _chained_failure(AgentName.DAM_PRICE_FORECAST, cause)
    fact = classify_forecasting_agent_failure(failure)
    assert fact.error_code == _UNEXPECTED_FAILURE_CODE
    assert type(cause).__name__ not in fact.error_code
    assert _SENTINEL_TEXT not in fact.error_code
    assert _SENTINEL_TEXT not in repr(fact)


def test_missing_cause_collapses_to_unexpected_failure() -> None:
    failure = ForecastingAgentFailure(AgentName.DAM_PRICE_FORECAST)
    assert failure.__cause__ is None
    fact = classify_forecasting_agent_failure(failure)
    assert fact.agent_name is AgentName.DAM_PRICE_FORECAST
    assert fact.error_code == _UNEXPECTED_FAILURE_CODE


def test_classifier_does_not_mutate_causal_identity() -> None:
    cause = RuntimeError(_SENTINEL_TEXT)
    failure = _chained_failure(AgentName.CONSUMER_LOAD_FORECAST, cause)
    assert failure.__cause__ is cause
    classify_forecasting_agent_failure(failure)
    assert failure.__cause__ is cause
    assert failure.agent_name is AgentName.CONSUMER_LOAD_FORECAST


@pytest.mark.parametrize("agent_name", _PHASE3_AGENT_NAMES)
def test_classifier_preserves_each_phase3_agent_identity(agent_name: AgentName) -> None:
    cause = DependencyUnavailableError("source unavailable")
    failure = _chained_failure(agent_name, cause)
    fact = classify_forecasting_agent_failure(failure)
    assert fact.agent_name is agent_name
    assert fact.error_code == cause.code
