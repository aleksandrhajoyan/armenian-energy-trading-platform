"""Forecasting stack composition delegates to the two published builders."""

from __future__ import annotations

import inspect

import pytest

from energy_trading.api.composition import forecasting_stack
from energy_trading.api.composition.forecasting_execution import (
    build_parallel_forecasting_execution_service,
)
from energy_trading.api.composition.forecasting_stack import (
    build_forecasting_workflow_step_from_model_ports,
)
from energy_trading.api.composition.forecasting_workflow import build_forecasting_workflow_step
from energy_trading.application.agents.consumer_load_forecast import ConsumerLoadForecastAgent
from energy_trading.application.agents.dam_price_forecast import DAMPriceForecastAgent
from energy_trading.application.orchestration.forecasting_context import (
    ForecastingWorkflowContextPort,
)
from energy_trading.application.orchestration.forecasting_execution import (
    ForecastingExecutionPort,
)
from energy_trading.application.orchestration.forecasting_executor import (
    ParallelForecastingExecutionService,
)
from energy_trading.application.orchestration.forecasting_plan import ForecastingPlan
from energy_trading.application.orchestration.forecasting_success import ForecastingSuccess
from energy_trading.application.orchestration.forecasting_workflow import (
    ForecastingWorkflowStep,
)
from energy_trading.application.orchestration.state import WorkflowState
from energy_trading.application.ports.consumer_load_forecast_model import (
    ConsumerLoadForecastModelPort,
    ConsumerLoadForecastModelRequest,
)
from energy_trading.application.ports.dam_price_forecast_model import (
    DAMPriceForecastModelPort,
    DAMPriceForecastModelRequest,
)
from energy_trading.domain.models.forecasting import LoadForecastPoint, PriceForecastPoint


class _FakeConsumerLoadModel:
    """Test-only fake that structurally satisfies ``ConsumerLoadForecastModelPort``."""

    def __init__(self) -> None:
        self.calls: list[ConsumerLoadForecastModelRequest] = []

    async def forecast(
        self,
        *,
        request: ConsumerLoadForecastModelRequest,
    ) -> tuple[LoadForecastPoint, ...]:
        self.calls.append(request)
        raise AssertionError("builder must not forecast consumer load")


class _FakeDAMPriceModel:
    """Test-only fake that structurally satisfies ``DAMPriceForecastModelPort``."""

    def __init__(self) -> None:
        self.calls: list[DAMPriceForecastModelRequest] = []

    async def forecast(
        self,
        *,
        request: DAMPriceForecastModelRequest,
    ) -> tuple[PriceForecastPoint, ...]:
        self.calls.append(request)
        raise AssertionError("builder must not forecast DAM prices")


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
    """Test-only fake executor returned by the spied Chunk 188 builder."""

    def __init__(self) -> None:
        self.execute_calls = 0

    async def execute(self, *, plan: ForecastingPlan) -> ForecastingSuccess:
        self.execute_calls += 1
        raise AssertionError("builder must not execute a plan")


class _FakeStep:
    """Test-only sentinel step returned by the spied Chunk 189 builder."""

    def __init__(self) -> None:
        self.run_calls = 0

    async def run(self, state: WorkflowState) -> WorkflowState:
        self.run_calls += 1
        raise AssertionError("builder must not run the step")


class _BuilderSpy:
    """Records calls to both delegated builders and returns fresh sentinels."""

    def __init__(self) -> None:
        self.events: list[str] = []
        self.execution_calls: list[dict[str, object]] = []
        self.workflow_calls: list[dict[str, object]] = []
        self.executors: list[_FakeExecutor] = []
        self.steps: list[_FakeStep] = []
        self.execution_error: Exception | None = None
        self.workflow_error: Exception | None = None

    def build_execution(
        self,
        *,
        consumer_load_model: ConsumerLoadForecastModelPort,
        dam_price_model: DAMPriceForecastModelPort,
    ) -> _FakeExecutor:
        self.events.append("execution")
        self.execution_calls.append(
            {"consumer_load_model": consumer_load_model, "dam_price_model": dam_price_model}
        )
        if self.execution_error is not None:
            raise self.execution_error
        executor = _FakeExecutor()
        self.executors.append(executor)
        return executor

    def build_workflow(
        self,
        *,
        context: ForecastingWorkflowContextPort,
        executor: ForecastingExecutionPort,
    ) -> _FakeStep:
        self.events.append("workflow")
        self.workflow_calls.append({"context": context, "executor": executor})
        if self.workflow_error is not None:
            raise self.workflow_error
        step = _FakeStep()
        self.steps.append(step)
        return step


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> _BuilderSpy:
    builder_spy = _BuilderSpy()
    monkeypatch.setattr(
        forecasting_stack,
        "build_parallel_forecasting_execution_service",
        builder_spy.build_execution,
    )
    monkeypatch.setattr(
        forecasting_stack,
        "build_forecasting_workflow_step",
        builder_spy.build_workflow,
    )
    return builder_spy


def _as_consumer_port(model: _FakeConsumerLoadModel) -> ConsumerLoadForecastModelPort:
    return model


def _as_dam_port(model: _FakeDAMPriceModel) -> DAMPriceForecastModelPort:
    return model


def _as_context_port(context: _FakeContext) -> ForecastingWorkflowContextPort:
    return context


def _build(
    consumer_model: _FakeConsumerLoadModel,
    dam_model: _FakeDAMPriceModel,
    context: _FakeContext,
) -> object:
    return build_forecasting_workflow_step_from_model_ports(
        consumer_load_model=_as_consumer_port(consumer_model),
        dam_price_model=_as_dam_port(dam_model),
        context=_as_context_port(context),
    )


def test_builder_signature_is_keyword_only_model_and_context_ports() -> None:
    signature = inspect.signature(build_forecasting_workflow_step_from_model_ports)
    assert tuple(signature.parameters) == ("consumer_load_model", "dam_price_model", "context")
    for parameter in signature.parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    assert signature.parameters["consumer_load_model"].annotation is ConsumerLoadForecastModelPort
    assert signature.parameters["dam_price_model"].annotation is DAMPriceForecastModelPort
    assert signature.parameters["context"].annotation is ForecastingWorkflowContextPort
    assert signature.return_annotation is ForecastingWorkflowStep
    assert not inspect.iscoroutinefunction(build_forecasting_workflow_step_from_model_ports)


def test_module_delegates_to_the_published_builders() -> None:
    assert (
        forecasting_stack.build_parallel_forecasting_execution_service
        is build_parallel_forecasting_execution_service
    )
    assert forecasting_stack.build_forecasting_workflow_step is build_forecasting_workflow_step


def test_each_builder_is_called_exactly_once_in_order(spy: _BuilderSpy) -> None:
    _build(_FakeConsumerLoadModel(), _FakeDAMPriceModel(), _FakeContext())
    assert spy.events == ["execution", "workflow"]
    assert len(spy.execution_calls) == 1
    assert len(spy.workflow_calls) == 1


def test_models_context_and_executor_are_forwarded_by_identity(spy: _BuilderSpy) -> None:
    consumer_model = _FakeConsumerLoadModel()
    dam_model = _FakeDAMPriceModel()
    context = _FakeContext()
    step = _build(consumer_model, dam_model, context)

    execution_call = spy.execution_calls[0]
    assert set(execution_call) == {"consumer_load_model", "dam_price_model"}
    assert execution_call["consumer_load_model"] is consumer_model
    assert execution_call["dam_price_model"] is dam_model
    workflow_call = spy.workflow_calls[0]
    assert set(workflow_call) == {"context", "executor"}
    assert workflow_call["context"] is context
    assert workflow_call["executor"] is spy.executors[0]
    assert step is spy.steps[0]


def test_builder_does_not_forecast_execute_run_resolve_or_record(spy: _BuilderSpy) -> None:
    consumer_model = _FakeConsumerLoadModel()
    dam_model = _FakeDAMPriceModel()
    context = _FakeContext()
    _build(consumer_model, dam_model, context)

    assert consumer_model.calls == []
    assert dam_model.calls == []
    assert spy.executors[0].execute_calls == 0
    assert spy.steps[0].run_calls == 0
    assert context.resolve_calls == 0
    assert context.record_calls == 0


def test_execution_builder_error_propagates_and_skips_workflow_builder(
    spy: _BuilderSpy,
) -> None:
    error = RuntimeError("execution builder failed")
    spy.execution_error = error
    with pytest.raises(RuntimeError) as raised:
        _build(_FakeConsumerLoadModel(), _FakeDAMPriceModel(), _FakeContext())
    assert raised.value is error
    assert spy.events == ["execution"]
    assert spy.workflow_calls == []


def test_workflow_builder_error_propagates_unchanged(spy: _BuilderSpy) -> None:
    error = RuntimeError("workflow builder failed")
    spy.workflow_error = error
    with pytest.raises(RuntimeError) as raised:
        _build(_FakeConsumerLoadModel(), _FakeDAMPriceModel(), _FakeContext())
    assert raised.value is error
    assert spy.events == ["execution", "workflow"]


def test_independent_builds_do_not_reuse_dependencies_or_results(spy: _BuilderSpy) -> None:
    first_consumer, first_dam, first_context = (
        _FakeConsumerLoadModel(),
        _FakeDAMPriceModel(),
        _FakeContext(),
    )
    second_consumer, second_dam, second_context = (
        _FakeConsumerLoadModel(),
        _FakeDAMPriceModel(),
        _FakeContext(),
    )
    first = _build(first_consumer, first_dam, first_context)
    second = _build(second_consumer, second_dam, second_context)

    assert spy.events == ["execution", "workflow", "execution", "workflow"]
    assert first is spy.steps[0]
    assert second is spy.steps[1]
    assert first is not second
    assert spy.executors[0] is not spy.executors[1]
    assert spy.execution_calls[1]["consumer_load_model"] is second_consumer
    assert spy.execution_calls[1]["dam_price_model"] is second_dam
    assert spy.workflow_calls[1]["context"] is second_context
    assert spy.workflow_calls[1]["executor"] is spy.executors[1]


def test_repeated_builds_with_same_ports_still_delegate_each_time(spy: _BuilderSpy) -> None:
    consumer_model = _FakeConsumerLoadModel()
    dam_model = _FakeDAMPriceModel()
    context = _FakeContext()
    first = _build(consumer_model, dam_model, context)
    second = _build(consumer_model, dam_model, context)

    assert len(spy.execution_calls) == 2
    assert len(spy.workflow_calls) == 2
    assert first is not second
    assert spy.workflow_calls[1]["executor"] is spy.executors[1]


def test_published_builders_compose_a_real_stack_from_structural_fakes() -> None:
    consumer_model = _FakeConsumerLoadModel()
    dam_model = _FakeDAMPriceModel()
    context = _FakeContext()
    step = build_forecasting_workflow_step_from_model_ports(
        consumer_load_model=_as_consumer_port(consumer_model),
        dam_price_model=_as_dam_port(dam_model),
        context=_as_context_port(context),
    )

    assert type(step) is ForecastingWorkflowStep
    assert step._context is context
    executor = step._executor
    assert type(executor) is ParallelForecastingExecutionService
    assert isinstance(executor, ParallelForecastingExecutionService)
    consumer_agent = executor._consumer_load_forecast
    dam_agent = executor._dam_price_forecast
    assert type(consumer_agent) is ConsumerLoadForecastAgent
    assert type(dam_agent) is DAMPriceForecastAgent
    assert consumer_agent._model is consumer_model
    assert dam_agent._model is dam_model
    assert consumer_model.calls == []
    assert dam_model.calls == []
    assert context.resolve_calls == 0
    assert context.record_calls == 0
