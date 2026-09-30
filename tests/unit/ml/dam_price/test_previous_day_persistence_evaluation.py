"""Exact previous-day persistence DAM Price MAE evaluation."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from energy_trading.application.errors import InvalidRequestError

# ``energy_trading.domain.models`` must initialize before
# ``energy_trading.domain.value_objects.money`` because the domain models
# package imports ``EnergyPrice`` from it during its own initialization.
# Importing the models package explicitly keeps that pre-existing order.
from energy_trading.domain.models.observations import MarketPriceRecord  # noqa: F401
from energy_trading.domain.value_objects.money import EnergyPrice
from energy_trading.ml.dam_price.previous_day_persistence_backtest import (
    PreviousDayPersistenceBacktestCase,
)
from energy_trading.ml.dam_price.previous_day_persistence_evaluation import (
    PreviousDayPersistenceMAEResult,
    evaluate_previous_day_persistence_mae,
)

_EMPTY_CASES_MESSAGE = (
    "Previous-day persistence MAE evaluation requires at least one backtest case."
)
_MIXED_MARKET_MESSAGE = (
    "Previous-day persistence MAE evaluation requires cases from exactly one market."
)
_MIXED_CURRENCY_MESSAGE = (
    "Previous-day persistence MAE evaluation requires cases in exactly one currency."
)
_CASE_CURRENCY_MISMATCH_MESSAGE = (
    "Previous-day persistence MAE evaluation requires matching predicted and actual case currency."
)
_DUPLICATE_TIMESTAMP_MESSAGE = (
    "Previous-day persistence MAE evaluation requires unique target timestamps."
)
_OUT_OF_ORDER_MESSAGE = (
    "Previous-day persistence MAE evaluation requires strictly increasing target timestamps."
)


def _ts(day: int, hour: int = 16) -> datetime:
    return datetime(2026, 10, day, hour, 0, 0, tzinfo=UTC)


def _price(amount: str, *, currency: str = "AMD") -> EnergyPrice:
    return EnergyPrice(amount_per_mwh=Decimal(amount), currency=currency)


def _case(
    *,
    day: int,
    predicted: str,
    actual: str,
    market_id: str = "market-1",
    predicted_currency: str = "AMD",
    actual_currency: str = "AMD",
) -> PreviousDayPersistenceBacktestCase:
    return PreviousDayPersistenceBacktestCase(
        market_id=market_id,
        target_timestamp=_ts(day),
        predicted_price=_price(predicted, currency=predicted_currency),
        actual_price=_price(actual, currency=actual_currency),
    )


def _evaluate(
    cases: tuple[PreviousDayPersistenceBacktestCase, ...],
) -> PreviousDayPersistenceMAEResult:
    return evaluate_previous_day_persistence_mae(cases=cases)


def test_empty_case_tuple_fails_closed() -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate(())
    assert captured.value.message == _EMPTY_CASES_MESSAGE


def test_single_zero_error_case_has_exact_zero_mae() -> None:
    result = _evaluate((_case(day=1, predicted="42.50", actual="42.50"),))
    assert result.case_count == 1
    assert result.currency == "AMD"
    assert result.mae_amount_per_mwh == Decimal("0")
    assert isinstance(result.mae_amount_per_mwh, Decimal)


def test_single_non_zero_error_uses_exact_absolute_difference() -> None:
    result = _evaluate((_case(day=1, predicted="10.25", actual="13.75"),))
    assert result.case_count == 1
    assert result.mae_amount_per_mwh == Decimal("3.50")


def test_multiple_cases_average_absolute_errors_exactly() -> None:
    cases = (
        _case(day=1, predicted="10.00", actual="12.00"),
        _case(day=2, predicted="20.00", actual="17.00"),
        _case(day=3, predicted="30.00", actual="30.00"),
    )
    result = _evaluate(cases)
    assert result.case_count == 3
    assert result.mae_amount_per_mwh == (Decimal("2") + Decimal("3") + Decimal("0")) / 3


def test_positive_and_negative_residuals_both_become_absolute_errors() -> None:
    cases = (
        _case(day=1, predicted="100.00", actual="80.00"),
        _case(day=2, predicted="80.00", actual="100.00"),
    )
    result = _evaluate(cases)
    assert result.case_count == 2
    assert result.mae_amount_per_mwh == Decimal("20")


def test_negative_canonical_market_prices_are_scored_normally() -> None:
    result = _evaluate((_case(day=1, predicted="-10.00", actual="5.00"),))
    assert result.mae_amount_per_mwh == Decimal("15")


def test_both_prices_negative_uses_ordinary_absolute_difference() -> None:
    result = _evaluate((_case(day=1, predicted="-10.00", actual="-15.00"),))
    assert result.mae_amount_per_mwh == Decimal("5")


def test_all_negative_cohort_scores_without_clamping() -> None:
    cases = (
        _case(day=1, predicted="-10.00", actual="-15.00"),
        _case(day=2, predicted="-20.00", actual="-18.00"),
    )
    result = _evaluate(cases)
    assert result.case_count == 2
    assert result.mae_amount_per_mwh == (Decimal("5") + Decimal("2")) / 2


def test_negative_actual_with_positive_predicted_is_not_rejected() -> None:
    result = _evaluate((_case(day=1, predicted="25.00", actual="-25.00"),))
    assert result.mae_amount_per_mwh == Decimal("50")


def test_shared_cohort_currency_is_returned_exactly() -> None:
    cases = (
        PreviousDayPersistenceBacktestCase(
            market_id="market-7",
            target_timestamp=_ts(1),
            predicted_price=_price("11.00", currency="EUR"),
            actual_price=_price("13.00", currency="EUR"),
        ),
        PreviousDayPersistenceBacktestCase(
            market_id="market-7",
            target_timestamp=_ts(2),
            predicted_price=_price("21.00", currency="EUR"),
            actual_price=_price("19.00", currency="EUR"),
        ),
    )
    result = _evaluate(cases)
    assert result.currency == "EUR"
    assert result.mae_amount_per_mwh == Decimal("2")


def test_within_case_currency_mismatch_fails_closed() -> None:
    case = _case(day=1, predicted="10.00", actual="12.00", actual_currency="EUR")
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate((case,))
    assert captured.value.message == _CASE_CURRENCY_MISMATCH_MESSAGE
    assert "AMD" not in captured.value.message
    assert "EUR" not in captured.value.message


def test_across_case_currency_mismatch_fails_closed() -> None:
    first = PreviousDayPersistenceBacktestCase(
        market_id="market-1",
        target_timestamp=_ts(1),
        predicted_price=_price("10.00", currency="AMD"),
        actual_price=_price("12.00", currency="AMD"),
    )
    second = PreviousDayPersistenceBacktestCase(
        market_id="market-1",
        target_timestamp=_ts(2),
        predicted_price=_price("20.00", currency="EUR"),
        actual_price=_price("22.00", currency="EUR"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate((first, second))
    assert captured.value.message == _MIXED_CURRENCY_MESSAGE
    assert "AMD" not in captured.value.message
    assert "EUR" not in captured.value.message


def test_mixed_markets_fail_closed_without_leaking_ids() -> None:
    cases = (
        _case(day=1, predicted="10.00", actual="12.00", market_id="market-alpha"),
        _case(day=2, predicted="20.00", actual="22.00", market_id="market-beta"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate(cases)
    assert captured.value.message == _MIXED_MARKET_MESSAGE
    assert "market-alpha" not in captured.value.message
    assert "market-beta" not in captured.value.message


def test_duplicate_target_timestamps_fail_closed() -> None:
    cases = (
        _case(day=1, predicted="10.00", actual="12.00"),
        _case(day=1, predicted="20.00", actual="22.00"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate(cases)
    assert captured.value.message == _DUPLICATE_TIMESTAMP_MESSAGE


def test_out_of_order_target_timestamps_fail_closed() -> None:
    cases = (
        _case(day=3, predicted="10.00", actual="12.00"),
        _case(day=1, predicted="20.00", actual="22.00"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _evaluate(cases)
    assert captured.value.message == _OUT_OF_ORDER_MESSAGE


def test_malformed_order_is_not_silently_repaired() -> None:
    malformed = (
        _case(day=2, predicted="10.00", actual="12.00"),
        _case(day=1, predicted="20.00", actual="22.00"),
    )
    with pytest.raises(InvalidRequestError):
        _evaluate(malformed)
    ordered = (
        _case(day=1, predicted="20.00", actual="22.00"),
        _case(day=2, predicted="10.00", actual="12.00"),
    )
    assert _evaluate(ordered).case_count == 2


def test_case_count_equals_supplied_count_including_zero_error_cases() -> None:
    cases = (
        _case(day=1, predicted="10.00", actual="10.00"),
        _case(day=2, predicted="10.00", actual="10.00"),
        _case(day=3, predicted="10.00", actual="14.00"),
    )
    result = _evaluate(cases)
    assert result.case_count == 3
    assert result.mae_amount_per_mwh == Decimal("4") / 3


def test_zero_error_cases_reduce_the_mean() -> None:
    cases = (
        _case(day=1, predicted="10.00", actual="10.00"),
        _case(day=2, predicted="10.00", actual="14.00"),
    )
    assert _evaluate(cases).mae_amount_per_mwh == Decimal("2")


def test_result_is_not_integer_or_cent_rounded() -> None:
    cases = (
        _case(day=1, predicted="1.00", actual="2.00"),
        _case(day=2, predicted="5.00", actual="5.00"),
        _case(day=3, predicted="7.00", actual="7.00"),
    )
    result = _evaluate(cases)
    assert result.mae_amount_per_mwh == Decimal("1") / 3
    assert result.mae_amount_per_mwh != Decimal("0")
    assert result.mae_amount_per_mwh != Decimal("0.33")
    assert result.mae_amount_per_mwh != Decimal("0.333")
    assert isinstance(result.mae_amount_per_mwh, Decimal)


def test_decimal_arithmetic_does_not_introduce_float_values() -> None:
    result = _evaluate((_case(day=1, predicted="100.10", actual="200.33"),))
    assert isinstance(result.mae_amount_per_mwh, Decimal)
    assert not isinstance(result.mae_amount_per_mwh, float)
    assert result.mae_amount_per_mwh == Decimal("100.23")


def test_input_cases_and_prices_are_not_mutated() -> None:
    case = _case(day=1, predicted="10.00", actual="12.00")
    cases = (case,)
    _evaluate(cases)
    assert cases == (case,)
    assert case.market_id == "market-1"
    assert case.target_timestamp == _ts(1)
    assert case.predicted_price.amount_per_mwh == Decimal("10.00")
    assert case.actual_price.amount_per_mwh == Decimal("12.00")
    assert case.predicted_price.currency == "AMD"


def test_repeated_equal_inputs_are_value_equivalent() -> None:
    cases = (
        _case(day=1, predicted="10.00", actual="12.00"),
        _case(day=2, predicted="20.00", actual="17.00"),
    )
    assert _evaluate(cases) == _evaluate(cases)


def test_result_contract_is_frozen_slotted_and_exactly_three_fields() -> None:
    names = tuple(item.name for item in fields(PreviousDayPersistenceMAEResult))
    assert names == ("case_count", "currency", "mae_amount_per_mwh")
    assert PreviousDayPersistenceMAEResult.__slots__ == names
    result = _evaluate((_case(day=1, predicted="10.00", actual="12.00"),))
    with pytest.raises(FrozenInstanceError):
        result.case_count = 99  # type: ignore[misc]


def test_result_exposes_no_other_metric_or_identity_fields() -> None:
    names = {item.name for item in fields(PreviousDayPersistenceMAEResult)}
    forbidden = {
        "market_id",
        "mse",
        "rmse",
        "mape",
        "smape",
        "r2",
        "bias",
        "median_absolute_error",
        "max_error",
        "residual",
        "residuals",
        "percentage_error",
        "directional_accuracy",
        "standard_deviation",
        "model_name",
        "model_version",
        "provider",
        "total_amount",
    }
    assert forbidden.isdisjoint(names)
    assert len(names) == 3


def test_evaluator_is_synchronous_and_keyword_only() -> None:
    assert not inspect.iscoroutinefunction(evaluate_previous_day_persistence_mae)
    parameters = inspect.signature(evaluate_previous_day_persistence_mae).parameters
    assert tuple(parameters) == ("cases",)
    assert parameters["cases"].kind is inspect.Parameter.KEYWORD_ONLY
