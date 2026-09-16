"""Phase 3 tuple-level classification composes sanitized failure facts."""

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
    ForecastingAgentFailure,
    ForecastingFailureFact,
    classify_forecasting_agent_failure,
    classify_forecasting_agent_failures,
)
from energy_trading.application.orchestration import (
    forecasting_failure_classification as classification_module,
)

_UNEXPECTED_FAILURE_CODE = "forecasting_unexpected_failure"
_SENTINEL_TEXT = "secret provider payload"


class _CustomApplicationError(ApplicationError):
    """Test-only subclass proving published ``code`` is reused, not remapped."""

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


def _expected(
    failures: tuple[ForecastingAgentFailure, ...],
) -> tuple[ForecastingFailureFact, ...]:
    return tuple(classify_forecasting_agent_failure(failure) for failure in failures)


def test_classify_signature_accepts_attributed_failure_tuple() -> None:
    signature = inspect.signature(classify_forecasting_agent_failures)
    assert tuple(signature.parameters) == ("failures",)
    parameter = signature.parameters["failures"]
    assert parameter.annotation in {
        tuple[ForecastingAgentFailure, ...],
        "tuple[ForecastingAgentFailure, ...]",
    }
    assert signature.return_annotation in {
        tuple[ForecastingFailureFact, ...],
        "tuple[ForecastingFailureFact, ...]",
    }
    assert not inspect.iscoroutinefunction(classify_forecasting_agent_failures)


def test_empty_tuple_returns_empty_tuple() -> None:
    assert classify_forecasting_agent_failures(()) == ()


def test_single_consumer_failure_preserves_agent_and_existing_code() -> None:
    cause = DependencyUnavailableError("source unavailable")
    failure = _chained_failure(AgentName.CONSUMER_LOAD_FORECAST, cause)
    facts = classify_forecasting_agent_failures((failure,))
    assert len(facts) == 1
    assert isinstance(facts[0], ForecastingFailureFact)
    assert facts == _expected((failure,))
    assert facts[0].agent_name is AgentName.CONSUMER_LOAD_FORECAST
    assert facts[0].error_code == cause.code
    assert facts[0].error_code != _UNEXPECTED_FAILURE_CODE


def test_single_dam_failure_preserves_agent_and_existing_code() -> None:
    cause = InvalidRequestError("request is invalid")
    failure = _chained_failure(AgentName.DAM_PRICE_FORECAST, cause)
    facts = classify_forecasting_agent_failures((failure,))
    assert len(facts) == 1
    assert isinstance(facts[0], ForecastingFailureFact)
    assert facts == _expected((failure,))
    assert facts[0].agent_name is AgentName.DAM_PRICE_FORECAST
    assert facts[0].error_code == cause.code
    assert facts[0].error_code != _UNEXPECTED_FAILURE_CODE


def test_multiple_failures_preserve_encounter_order() -> None:
    consumer = _chained_failure(
        AgentName.CONSUMER_LOAD_FORECAST,
        InvalidRequestError("consumer request is invalid"),
    )
    dam = _chained_failure(
        AgentName.DAM_PRICE_FORECAST,
        DependencyUnavailableError("dam source unavailable"),
    )
    failures = (consumer, dam)
    facts = classify_forecasting_agent_failures(failures)
    assert facts == _expected(failures)
    assert [fact.agent_name for fact in facts] == [
        AgentName.CONSUMER_LOAD_FORECAST,
        AgentName.DAM_PRICE_FORECAST,
    ]
    assert [fact.error_code for fact in facts] == [
        "invalid_request",
        "dependency_unavailable",
    ]


def test_duplicate_agent_identities_are_not_collapsed() -> None:
    first = _chained_failure(
        AgentName.CONSUMER_LOAD_FORECAST,
        InvalidRequestError("first consumer failure"),
    )
    second = _chained_failure(
        AgentName.CONSUMER_LOAD_FORECAST,
        DependencyUnavailableError("second consumer failure"),
    )
    failures = (first, second)
    facts = classify_forecasting_agent_failures(failures)
    assert facts == _expected(failures)
    assert len(facts) == 2
    assert facts[0].agent_name is AgentName.CONSUMER_LOAD_FORECAST
    assert facts[1].agent_name is AgentName.CONSUMER_LOAD_FORECAST
    assert facts[0] is not facts[1]
    assert facts[0].error_code == "invalid_request"
    assert facts[1].error_code == "dependency_unavailable"


def test_mixed_error_codes_are_classified_independently() -> None:
    failures = (
        _chained_failure(
            AgentName.CONSUMER_LOAD_FORECAST,
            InvalidRequestError("consumer request is invalid"),
        ),
        _chained_failure(
            AgentName.DAM_PRICE_FORECAST,
            ResourceNotFoundError("dam resource missing"),
        ),
        _chained_failure(
            AgentName.CONSUMER_LOAD_FORECAST,
            _CustomApplicationError("custom consumer failure"),
        ),
        _chained_failure(
            AgentName.DAM_PRICE_FORECAST,
            RuntimeError(_SENTINEL_TEXT),
        ),
        ForecastingAgentFailure(AgentName.CONSUMER_LOAD_FORECAST),
    )
    facts = classify_forecasting_agent_failures(failures)
    assert facts == _expected(failures)
    assert [fact.error_code for fact in facts] == [
        "invalid_request",
        "resource_not_found",
        "custom_application_code",
        _UNEXPECTED_FAILURE_CODE,
        _UNEXPECTED_FAILURE_CODE,
    ]
    assert all(isinstance(fact, ForecastingFailureFact) for fact in facts)


def test_unexpected_non_application_causes_collapse_through_singular_classifier() -> None:
    failures = (
        _chained_failure(AgentName.CONSUMER_LOAD_FORECAST, RuntimeError(_SENTINEL_TEXT)),
        _chained_failure(AgentName.DAM_PRICE_FORECAST, ValueError(_SENTINEL_TEXT)),
        _chained_failure(AgentName.CONSUMER_LOAD_FORECAST, _VendorPayloadError(_SENTINEL_TEXT)),
    )
    facts = classify_forecasting_agent_failures(failures)
    assert facts == _expected(failures)
    assert all(fact.error_code == _UNEXPECTED_FAILURE_CODE for fact in facts)
    for fact in facts:
        assert _SENTINEL_TEXT not in fact.error_code
        assert _SENTINEL_TEXT not in repr(fact)


def test_missing_causes_collapse_to_unexpected_failure() -> None:
    consumer = ForecastingAgentFailure(AgentName.CONSUMER_LOAD_FORECAST)
    dam = ForecastingAgentFailure(AgentName.DAM_PRICE_FORECAST)
    assert consumer.__cause__ is None
    assert dam.__cause__ is None
    failures = (consumer, dam)
    facts = classify_forecasting_agent_failures(failures)
    assert facts == _expected(failures)
    assert facts[0].agent_name is AgentName.CONSUMER_LOAD_FORECAST
    assert facts[1].agent_name is AgentName.DAM_PRICE_FORECAST
    assert facts[0].error_code == _UNEXPECTED_FAILURE_CODE
    assert facts[1].error_code == _UNEXPECTED_FAILURE_CODE


def test_classifier_does_not_mutate_failures_or_causes() -> None:
    first_cause = RuntimeError(_SENTINEL_TEXT)
    second_cause = DependencyUnavailableError("source unavailable")
    first = _chained_failure(AgentName.CONSUMER_LOAD_FORECAST, first_cause)
    second = _chained_failure(AgentName.DAM_PRICE_FORECAST, second_cause)
    failures = (first, second)
    classify_forecasting_agent_failures(failures)
    assert failures[0] is first
    assert failures[1] is second
    assert first.__cause__ is first_cause
    assert second.__cause__ is second_cause
    assert first.agent_name is AgentName.CONSUMER_LOAD_FORECAST
    assert second.agent_name is AgentName.DAM_PRICE_FORECAST


def test_equivalent_input_tuples_produce_value_equivalent_facts() -> None:
    first = _chained_failure(
        AgentName.CONSUMER_LOAD_FORECAST,
        InvalidRequestError("request is invalid"),
    )
    second = _chained_failure(
        AgentName.DAM_PRICE_FORECAST,
        RuntimeError(_SENTINEL_TEXT),
    )
    first_facts = classify_forecasting_agent_failures((first, second))
    second_facts = classify_forecasting_agent_failures((first, second))
    assert first_facts == second_facts
    assert first_facts == _expected((first, second))
    assert first_facts is not second_facts


def test_cardinality_is_preserved_without_selection() -> None:
    failures = (
        _chained_failure(
            AgentName.CONSUMER_LOAD_FORECAST,
            ConflictError("consumer state conflict"),
        ),
        _chained_failure(
            AgentName.DAM_PRICE_FORECAST,
            DependencyUnavailableError("dam source unavailable"),
        ),
        _chained_failure(
            AgentName.CONSUMER_LOAD_FORECAST,
            RuntimeError(_SENTINEL_TEXT),
        ),
    )
    facts = classify_forecasting_agent_failures(failures)
    assert len(facts) == len(failures)
    assert facts == _expected(failures)
    assert [fact.agent_name for fact in facts] == [failure.agent_name for failure in failures]


def test_tuple_classifier_delegates_each_element_to_singular_classifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[ForecastingAgentFailure] = []
    original = classification_module.classify_forecasting_agent_failure

    def tracking(failure: ForecastingAgentFailure) -> ForecastingFailureFact:
        calls.append(failure)
        return original(failure)

    monkeypatch.setattr(
        classification_module,
        "classify_forecasting_agent_failure",
        tracking,
    )
    consumer = _chained_failure(
        AgentName.CONSUMER_LOAD_FORECAST,
        InvalidRequestError("consumer request is invalid"),
    )
    dam = _chained_failure(
        AgentName.DAM_PRICE_FORECAST,
        DependencyUnavailableError("dam source unavailable"),
    )
    failures = (consumer, dam)
    facts = classify_forecasting_agent_failures(failures)
    assert calls == [consumer, dam]
    assert facts == _expected(failures)
