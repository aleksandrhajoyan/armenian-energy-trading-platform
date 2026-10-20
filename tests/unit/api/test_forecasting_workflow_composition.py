"""Forecasting workflow-step composition wires published application objects."""

from __future__ import annotations

import inspect

import pytest

from energy_trading.api.composition import forecasting_workflow
from energy_trading.api.composition.forecasting_workflow import build_forecasting_workflow_step
from energy_trading.application.orchestration.forecasting_context import (
    ForecastingWorkflowContextPort,
)
from energy_trading.application.orchestration.forecasting_execution import (
    ForecastingExecutionPort,
)
from energy_trading.application.orchestration.forecasting_plan import ForecastingPlan
from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.application.orchestration.forecasting_workflow import (
    ForecastingWorkflowStep,
)
from energy_trading.application.orchestration.state import WorkflowState


class _FakeContext:
    """Test-only fake that structurally satisfies ``ForecastingWorkflowContextPort``."""

    def __init__(self) -> None:
        self.resolve_calls = 0
        self.record_calls = 0

    async def resolve_plan(self, *, state: WorkflowState) -> ForecastingPlan:
        self.resolve_calls += 1
        raise AssertionError("builder must not resolve a plan")

    async def record_success(
        self,
        *,
        state: WorkflowState,
        success: ForecastingSuccess,
    ) -> None:
        self.record_calls += 1
        raise AssertionError("builder must not record success")


class _FakeExecutor:
    """Test-only fake that structurally satisfies ``ForecastingExecutionPort``."""

    def __init__(self) -> None:
        self.execute_calls = 0

    async def execute(self, *, plan: ForecastingPlan) -> ForecastingSuccess:
        self.execute_calls += 1
        raise AssertionError("builder must not execute a plan")


def _as_context_port(context: _FakeContext) -> ForecastingWorkflowContextPort:
    return context


def _as_executor_port(executor: _FakeExecutor) -> ForecastingExecutionPort:
    return executor


def _build(context: _FakeContext, executor: _FakeExecutor) -> ForecastingWorkflowStep:
    return build_forecasting_workflow_step(
        context=_as_context_port(context),
        executor=_as_executor_port(executor),
    )


class _RecordingForecastingWorkflowStep(ForecastingWorkflowStep):
    instances: list[_RecordingForecastingWorkflowStep] = []
    run_calls: int = 0

    def __init__(
        self,
        context: ForecastingWorkflowContextPort,
        executor: ForecastingExecutionPort,
    ) -> None:
        super().__init__(context, executor)
        self.received_context = context
        self.received_executor = executor
        type(self).instances.append(self)

    async def run(self, state: WorkflowState) -> WorkflowState:
        type(self).run_calls += 1
        return await super().run(state)


@pytest.fixture
def recording_step(monkeypatch: pytest.MonkeyPatch) -> None:
    _RecordingForecastingWorkflowStep.instances = []
    _RecordingForecastingWorkflowStep.run_calls = 0
    monkeypatch.setattr(
        forecasting_workflow,
        "ForecastingWorkflowStep",
        _RecordingForecastingWorkflowStep,
    )


def test_builder_signature_is_keyword_only_context_and_executor_ports() -> None:
    signature = inspect.signature(build_forecasting_workflow_step)
    assert tuple(signature.parameters) == ("context", "executor")
    for parameter in signature.parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    assert signature.parameters["context"].annotation is ForecastingWorkflowContextPort
    assert signature.parameters["executor"].annotation is ForecastingExecutionPort
    assert signature.return_annotation is ForecastingWorkflowStep
    assert not inspect.iscoroutinefunction(build_forecasting_workflow_step)


def test_builder_accepts_structural_fakes_and_returns_existing_workflow_step() -> None:
    step = _build(_FakeContext(), _FakeExecutor())
    assert type(step) is ForecastingWorkflowStep
    assert ForecastingWorkflowContextPort not in _FakeContext.__mro__
    assert ForecastingExecutionPort not in _FakeExecutor.__mro__


def test_builder_wires_the_exact_supplied_context_and_executor() -> None:
    context = _FakeContext()
    executor = _FakeExecutor()
    step = _build(context, executor)
    assert step._context is context
    assert step._executor is executor


def test_builder_constructs_exactly_one_step_and_returns_it(recording_step: None) -> None:
    context = _FakeContext()
    executor = _FakeExecutor()
    step = _build(context, executor)

    assert len(_RecordingForecastingWorkflowStep.instances) == 1
    constructed = _RecordingForecastingWorkflowStep.instances[0]
    assert constructed.received_context is context
    assert constructed.received_executor is executor
    assert step is constructed


def test_builder_does_not_resolve_execute_record_or_run(recording_step: None) -> None:
    context = _FakeContext()
    executor = _FakeExecutor()
    _build(context, executor)

    assert context.resolve_calls == 0
    assert context.record_calls == 0
    assert executor.execute_calls == 0
    assert _RecordingForecastingWorkflowStep.run_calls == 0


def test_independent_builds_construct_independent_steps() -> None:
    first_context = _FakeContext()
    first_executor = _FakeExecutor()
    second_context = _FakeContext()
    second_executor = _FakeExecutor()

    first = _build(first_context, first_executor)
    second = _build(second_context, second_executor)

    assert first is not second
    assert first._context is first_context
    assert first._executor is first_executor
    assert second._context is second_context
    assert second._executor is second_executor


def test_repeated_builds_with_same_ports_still_construct_new_steps() -> None:
    context = _FakeContext()
    executor = _FakeExecutor()

    first = _build(context, executor)
    second = _build(context, executor)

    assert first is not second
    assert second._context is context
    assert second._executor is executor
