"""Phase 2 failure-policy context builder constructs the published contract."""

from __future__ import annotations

import inspect

import pytest

from energy_trading.application.agents import AgentName
from energy_trading.application.orchestration import (
    FailurePolicyContext,
    WorkflowPhase,
    build_parallel_ingestion_failure_policy_context,
)


def test_builder_constructs_published_context_with_exact_field_values() -> None:
    phase = WorkflowPhase.FORECASTING
    error_code = "sentinel-dependency-unavailable"
    attempt_number = 7
    agent_name = AgentName.HYDRO_RESOURCES

    context = build_parallel_ingestion_failure_policy_context(
        phase=phase,
        error_code=error_code,
        attempt_number=attempt_number,
        agent_name=agent_name,
    )

    assert isinstance(context, FailurePolicyContext)
    assert context.phase is phase
    assert context.error_code == error_code
    assert context.attempt_number == attempt_number
    assert context.agent_name is agent_name


def test_builder_preserves_published_optional_agent_name_default() -> None:
    context = build_parallel_ingestion_failure_policy_context(
        phase=WorkflowPhase.INGESTION,
        error_code="dependency_unavailable",
        attempt_number=1,
    )
    assert context.agent_name is None
    assert context.phase is WorkflowPhase.INGESTION


def test_builder_does_not_fabricate_an_agent_identity() -> None:
    context = build_parallel_ingestion_failure_policy_context(
        phase=WorkflowPhase.INGESTION,
        error_code="dependency_unavailable",
        attempt_number=1,
        agent_name=None,
    )
    assert context.agent_name is None
    assert context.agent_name is not AgentName.CHIEF_ORCHESTRATOR
    assert context.agent_name is not AgentName.MARKET_MONITORING


def test_builder_is_deterministic_for_equivalent_typed_inputs() -> None:
    first = build_parallel_ingestion_failure_policy_context(
        phase=WorkflowPhase.CONTRACT,
        error_code="schema_invalid",
        attempt_number=3,
        agent_name=AgentName.NEWS_INTELLIGENCE,
    )
    second = build_parallel_ingestion_failure_policy_context(
        phase=WorkflowPhase.CONTRACT,
        error_code="schema_invalid",
        attempt_number=3,
        agent_name=AgentName.NEWS_INTELLIGENCE,
    )
    assert first == second
    assert first is not second


def test_builder_lets_published_constructor_strip_error_code_whitespace() -> None:
    context = build_parallel_ingestion_failure_policy_context(
        phase=WorkflowPhase.INGESTION,
        error_code="  dependency_unavailable  ",
        attempt_number=1,
    )
    assert context.error_code == "dependency_unavailable"


@pytest.mark.parametrize("error_code", ["", "   "])
def test_builder_preserves_published_blank_error_code_rejection(error_code: str) -> None:
    with pytest.raises(ValueError, match="error_code"):
        build_parallel_ingestion_failure_policy_context(
            phase=WorkflowPhase.INGESTION,
            error_code=error_code,
            attempt_number=1,
        )


def test_builder_preserves_published_phase_type_rejection() -> None:
    with pytest.raises(TypeError, match="phase must be a WorkflowPhase"):
        build_parallel_ingestion_failure_policy_context(
            phase="ingestion",  # type: ignore[arg-type]
            error_code="dependency_unavailable",
            attempt_number=1,
        )


def test_builder_preserves_published_attempt_number_rejection() -> None:
    with pytest.raises(ValueError, match="attempt_number must be greater than 0"):
        build_parallel_ingestion_failure_policy_context(
            phase=WorkflowPhase.INGESTION,
            error_code="dependency_unavailable",
            attempt_number=0,
        )


def test_builder_preserves_published_agent_name_type_rejection() -> None:
    with pytest.raises(TypeError, match="agent_name must be an AgentName or None"):
        build_parallel_ingestion_failure_policy_context(
            phase=WorkflowPhase.INGESTION,
            error_code="dependency_unavailable",
            attempt_number=1,
            agent_name="Market Monitoring Agent",  # type: ignore[arg-type]
        )


def test_builder_signature_is_keyword_only_without_speculative_defaults() -> None:
    signature = inspect.signature(build_parallel_ingestion_failure_policy_context)
    assert tuple(signature.parameters) == ("phase", "error_code", "attempt_number", "agent_name")
    for name in ("phase", "error_code", "attempt_number"):
        parameter = signature.parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    agent_parameter = signature.parameters["agent_name"]
    assert agent_parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert agent_parameter.default is None
    assert signature.return_annotation is FailurePolicyContext or (
        signature.return_annotation == "FailurePolicyContext"
    )
    assert not inspect.iscoroutinefunction(build_parallel_ingestion_failure_policy_context)


def test_builder_parameter_annotations_match_published_context_fields() -> None:
    builder = inspect.signature(build_parallel_ingestion_failure_policy_context)
    context = inspect.signature(FailurePolicyContext)
    assert builder.parameters["phase"].annotation == context.parameters["phase"].annotation or (
        builder.parameters["phase"].annotation is WorkflowPhase
    )
    assert builder.parameters["error_code"].annotation in {str, "str"}
    assert builder.parameters["attempt_number"].annotation in {int, "int"}
    assert builder.parameters["agent_name"].annotation in {
        AgentName | None,
        "AgentName | None",
    }
