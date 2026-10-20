"""Forecasting failure runtime composition wires the five published services."""

from __future__ import annotations

import inspect
from datetime import date

import pytest

from energy_trading.api.composition import forecasting_failure_runtime
from energy_trading.api.composition.forecasting_failure_runtime import (
    build_forecasting_failure_runtime_handler,
)
from energy_trading.application.agents.base import AgentName
from energy_trading.application.errors import InvalidRequestError
from energy_trading.application.orchestration.failure_policy import (
    FailureAction,
    FailurePolicyContext,
    FailurePolicyPort,
)
from energy_trading.application.orchestration.forecasting_agent_failure import (
    ForecastingAgentFailure,
)
from energy_trading.application.orchestration.forecasting_attempt_number import (
    ForecastingAttemptNumberPort,
)
from energy_trading.application.orchestration.forecasting_failure_context_preparation import (
    ForecastingFailureContextPreparationService,
)
from energy_trading.application.orchestration.forecasting_failure_context_resolution import (
    ForecastingFailureContextResolutionService,
)
from energy_trading.application.orchestration.forecasting_failure_decision import (
    ForecastingFailureDecisionService,
)
from energy_trading.application.orchestration.forecasting_failure_fact import (
    ForecastingFailureFact,
)
from energy_trading.application.orchestration.forecasting_failure_handling import (
    ForecastingFailureHandlingService,
)
from energy_trading.application.orchestration.forecasting_failure_runtime_handling import (
    ForecastingFailureRuntimeHandlingService,
)
from energy_trading.application.orchestration.forecasting_failure_selection import (
    ForecastingFailureSelectionPort,
)
from energy_trading.application.orchestration.forecasting_failure_transition import (
    fail_after_forecasting,
)
from energy_trading.application.orchestration.forecasting_initial_attempt_number_source import (
    InitialForecastingAttemptNumberSource,
)
from energy_trading.application.orchestration.forecasting_initial_failure_policy import (
    InitialForecastingFailurePolicy,
)
from energy_trading.application.orchestration.forecasting_strict_single_failure_selector import (
    StrictSingleForecastingFailureSelector,
)
from energy_trading.application.orchestration.state import (
    WorkflowPhase,
    WorkflowState,
    WorkflowStatus,
)


class _FakeSelector:
    """Test-only fake that structurally satisfies ``ForecastingFailureSelectionPort``."""

    def __init__(self, *, permit_calls: bool = False) -> None:
        self.calls: list[tuple[ForecastingFailureFact, ...]] = []
        self._permit_calls = permit_calls

    def select(self, facts: tuple[ForecastingFailureFact, ...]) -> ForecastingFailureFact:
        self.calls.append(facts)
        if not self._permit_calls:
            raise AssertionError("builder must not select a failure fact")
        (fact,) = facts
        return fact


class _FakeAttemptNumberSource:
    """Test-only fake that structurally satisfies ``ForecastingAttemptNumberPort``."""

    def __init__(self, *, permit_calls: bool = False) -> None:
        self.calls: list[str] = []
        self._permit_calls = permit_calls

    async def get_attempt_number(self, workflow_id: str) -> int:
        self.calls.append(workflow_id)
        if not self._permit_calls:
            raise AssertionError("builder must not look up an attempt number")
        return 1


class _FakePolicy:
    """Test-only fake that structurally satisfies ``FailurePolicyPort``."""

    def __init__(self, *, permit_calls: bool = False) -> None:
        self.calls: list[FailurePolicyContext] = []
        self._permit_calls = permit_calls

    async def decide(self, context: FailurePolicyContext) -> FailureAction:
        self.calls.append(context)
        if not self._permit_calls:
            raise AssertionError("builder must not decide a failure action")
        return FailureAction.FAIL


class _ConstructionSpy:
    """Records constructor calls for the five services and returns fresh sentinels."""

    def __init__(self) -> None:
        self.events: list[str] = []
        self.calls: dict[str, list[tuple[object, ...]]] = {
            "resolution": [],
            "preparation": [],
            "decision": [],
            "handling": [],
            "runtime": [],
        }
        self.instances: dict[str, list[_Sentinel]] = {key: [] for key in self.calls}

    def factory(self, key: str) -> type[_Sentinel]:
        spy = self

        class _Spied(_Sentinel):
            def __init__(self, *args: object, **kwargs: object) -> None:
                assert kwargs == {}
                super().__init__()
                spy.events.append(key)
                spy.calls[key].append(args)
                spy.instances[key].append(self)

        return _Spied


class _Sentinel:
    """Test-only sentinel whose runtime methods must never be invoked."""

    def __init__(self) -> None:
        self.method_calls = 0

    def _forbidden(self, *args: object, **kwargs: object) -> None:
        self.method_calls += 1
        raise AssertionError("builder must not invoke constructed services")

    resolve = _forbidden
    prepare = _forbidden
    decide = _forbidden
    handle = _forbidden


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> _ConstructionSpy:
    construction_spy = _ConstructionSpy()
    for attribute, key in (
        ("ForecastingFailureContextResolutionService", "resolution"),
        ("ForecastingFailureContextPreparationService", "preparation"),
        ("ForecastingFailureDecisionService", "decision"),
        ("ForecastingFailureHandlingService", "handling"),
        ("ForecastingFailureRuntimeHandlingService", "runtime"),
    ):
        monkeypatch.setattr(forecasting_failure_runtime, attribute, construction_spy.factory(key))
    return construction_spy


def _as_selector_port(selector: _FakeSelector) -> ForecastingFailureSelectionPort:
    return selector


def _as_attempt_port(source: _FakeAttemptNumberSource) -> ForecastingAttemptNumberPort:
    return source


def _as_policy_port(policy: _FakePolicy) -> FailurePolicyPort:
    return policy


def _build(
    selector: _FakeSelector,
    attempt_number_source: _FakeAttemptNumberSource,
    policy: _FakePolicy,
) -> object:
    return build_forecasting_failure_runtime_handler(
        selector=_as_selector_port(selector),
        attempt_number_source=_as_attempt_port(attempt_number_source),
        policy=_as_policy_port(policy),
    )


def _state() -> WorkflowState:
    return WorkflowState(
        workflow_id="workflow-1",
        portfolio_id="portfolio-1",
        delivery_date=date(2026, 9, 7),
        correlation_id="corr-1",
        phase=WorkflowPhase.FORECASTING,
        status=WorkflowStatus.RUNNING,
        diagnostics=(),
    )


def _chained_failure(agent_name: AgentName, cause: BaseException) -> ForecastingAgentFailure:
    try:
        raise ForecastingAgentFailure(agent_name) from cause
    except ForecastingAgentFailure as exc:
        return exc


def test_builder_signature_is_keyword_only_policy_ports() -> None:
    signature = inspect.signature(build_forecasting_failure_runtime_handler)
    assert tuple(signature.parameters) == ("selector", "attempt_number_source", "policy")
    for parameter in signature.parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
    assert signature.parameters["selector"].annotation is ForecastingFailureSelectionPort
    assert signature.parameters["attempt_number_source"].annotation is (
        ForecastingAttemptNumberPort
    )
    assert signature.parameters["policy"].annotation is FailurePolicyPort
    assert signature.return_annotation is ForecastingFailureRuntimeHandlingService
    assert not inspect.iscoroutinefunction(build_forecasting_failure_runtime_handler)


def test_module_references_the_published_service_classes() -> None:
    module = forecasting_failure_runtime
    assert module.ForecastingFailureContextResolutionService is (
        ForecastingFailureContextResolutionService
    )
    assert module.ForecastingFailureContextPreparationService is (
        ForecastingFailureContextPreparationService
    )
    assert module.ForecastingFailureDecisionService is ForecastingFailureDecisionService
    assert module.ForecastingFailureHandlingService is ForecastingFailureHandlingService
    assert module.ForecastingFailureRuntimeHandlingService is (
        ForecastingFailureRuntimeHandlingService
    )


def test_each_service_is_constructed_exactly_once_in_order(spy: _ConstructionSpy) -> None:
    _build(_FakeSelector(), _FakeAttemptNumberSource(), _FakePolicy())
    assert spy.events == ["resolution", "preparation", "decision", "handling", "runtime"]
    for key, calls in spy.calls.items():
        assert len(calls) == 1, key


def test_ports_and_services_are_forwarded_by_identity(spy: _ConstructionSpy) -> None:
    selector = _FakeSelector()
    attempt_number_source = _FakeAttemptNumberSource()
    policy = _FakePolicy()
    handler = _build(selector, attempt_number_source, policy)

    (resolution_args,) = spy.calls["resolution"]
    assert len(resolution_args) == 2
    assert resolution_args[0] is selector
    assert resolution_args[1] is attempt_number_source
    (preparation_args,) = spy.calls["preparation"]
    assert len(preparation_args) == 1
    assert preparation_args[0] is spy.instances["resolution"][0]
    (decision_args,) = spy.calls["decision"]
    assert len(decision_args) == 1
    assert decision_args[0] is policy
    (handling_args,) = spy.calls["handling"]
    assert len(handling_args) == 1
    assert handling_args[0] is spy.instances["decision"][0]
    (runtime_args,) = spy.calls["runtime"]
    assert len(runtime_args) == 2
    assert runtime_args[0] is spy.instances["preparation"][0]
    assert runtime_args[1] is spy.instances["handling"][0]
    assert handler is spy.instances["runtime"][0]


def test_builder_invokes_no_port_or_service_method(spy: _ConstructionSpy) -> None:
    selector = _FakeSelector()
    attempt_number_source = _FakeAttemptNumberSource()
    policy = _FakePolicy()
    _build(selector, attempt_number_source, policy)

    assert selector.calls == []
    assert attempt_number_source.calls == []
    assert policy.calls == []
    for key, instances in spy.instances.items():
        assert [instance.method_calls for instance in instances] == [0], key


def test_builder_constructs_no_concrete_selector_attempt_source_or_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructed: list[str] = []
    for concrete in (
        StrictSingleForecastingFailureSelector,
        InitialForecastingAttemptNumberSource,
        InitialForecastingFailurePolicy,
    ):

        def _record(self: object, *, _name: str = concrete.__name__) -> None:
            constructed.append(_name)

        monkeypatch.setattr(concrete, "__init__", _record)

    handler = _build(_FakeSelector(), _FakeAttemptNumberSource(), _FakePolicy())

    assert type(handler) is ForecastingFailureRuntimeHandlingService
    assert constructed == []
    for attribute in (
        "StrictSingleForecastingFailureSelector",
        "InitialForecastingAttemptNumberSource",
        "InitialForecastingFailurePolicy",
    ):
        assert not hasattr(forecasting_failure_runtime, attribute)


def test_independent_builds_create_independent_service_graphs(spy: _ConstructionSpy) -> None:
    first_ports = (_FakeSelector(), _FakeAttemptNumberSource(), _FakePolicy())
    second_ports = (_FakeSelector(), _FakeAttemptNumberSource(), _FakePolicy())
    first = _build(*first_ports)
    second = _build(*second_ports)

    assert first is spy.instances["runtime"][0]
    assert second is spy.instances["runtime"][1]
    assert first is not second
    for key, instances in spy.instances.items():
        assert len(instances) == 2, key
        assert instances[0] is not instances[1], key
    assert spy.calls["resolution"][1] == (second_ports[0], second_ports[1])
    assert spy.calls["decision"][1] == (second_ports[2],)
    assert spy.calls["preparation"][1] == (spy.instances["resolution"][1],)
    assert spy.calls["handling"][1] == (spy.instances["decision"][1],)
    assert spy.calls["runtime"][1] == (
        spy.instances["preparation"][1],
        spy.instances["handling"][1],
    )


def test_repeated_builds_with_same_ports_rebuild_every_service(spy: _ConstructionSpy) -> None:
    ports = (_FakeSelector(), _FakeAttemptNumberSource(), _FakePolicy())
    first = _build(*ports)
    second = _build(*ports)

    assert first is not second
    assert spy.events == ["resolution", "preparation", "decision", "handling", "runtime"] * 2
    assert spy.calls["resolution"][0] == spy.calls["resolution"][1]
    assert spy.calls["decision"][0] == spy.calls["decision"][1]


def test_service_constructor_error_propagates_and_stops_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("decision construction failed")
    later: list[str] = []

    def _failing_decision(policy: FailurePolicyPort) -> ForecastingFailureDecisionService:
        raise error

    def _later(*args: object) -> object:
        later.append("constructed")
        return object()

    monkeypatch.setattr(
        forecasting_failure_runtime, "ForecastingFailureDecisionService", _failing_decision
    )
    monkeypatch.setattr(forecasting_failure_runtime, "ForecastingFailureHandlingService", _later)
    monkeypatch.setattr(
        forecasting_failure_runtime, "ForecastingFailureRuntimeHandlingService", _later
    )

    with pytest.raises(RuntimeError) as raised:
        _build(_FakeSelector(), _FakeAttemptNumberSource(), _FakePolicy())
    assert raised.value is error
    assert later == []


def test_published_constructors_compose_a_real_handler_from_structural_fakes() -> None:
    selector = _FakeSelector()
    attempt_number_source = _FakeAttemptNumberSource()
    policy = _FakePolicy()
    handler = build_forecasting_failure_runtime_handler(
        selector=_as_selector_port(selector),
        attempt_number_source=_as_attempt_port(attempt_number_source),
        policy=_as_policy_port(policy),
    )

    assert type(handler) is ForecastingFailureRuntimeHandlingService
    preparation = handler._context_preparation_service
    handling = handler._failure_handling_service
    assert type(preparation) is ForecastingFailureContextPreparationService
    assert type(handling) is ForecastingFailureHandlingService
    resolution = preparation._context_resolution_service
    assert type(resolution) is ForecastingFailureContextResolutionService
    assert resolution._selection_port is selector
    assert resolution._attempt_number_port is attempt_number_source
    decision = handling._decision_service
    assert type(decision) is ForecastingFailureDecisionService
    assert decision._policy is policy
    assert selector.calls == []
    assert attempt_number_source.calls == []
    assert policy.calls == []


async def test_returned_handler_handles_one_attributed_failure_with_test_ports() -> None:
    selector = _FakeSelector(permit_calls=True)
    attempt_number_source = _FakeAttemptNumberSource(permit_calls=True)
    policy = _FakePolicy(permit_calls=True)
    handler = build_forecasting_failure_runtime_handler(
        selector=_as_selector_port(selector),
        attempt_number_source=_as_attempt_port(attempt_number_source),
        policy=_as_policy_port(policy),
    )
    state = _state()
    leaf = _chained_failure(
        AgentName.CONSUMER_LOAD_FORECAST,
        InvalidRequestError("consumer load request is invalid"),
    )

    failed = await handler.handle(state=state, failure_group=ExceptionGroup("group", [leaf]))

    assert failed == fail_after_forecasting(state)
    assert failed.status is WorkflowStatus.FAILED
    assert len(selector.calls) == 1
    assert attempt_number_source.calls == ["workflow-1"]
    (context,) = policy.calls
    assert context.phase is WorkflowPhase.FORECASTING
    assert context.agent_name is AgentName.CONSUMER_LOAD_FORECAST
    assert context.attempt_number == 1
