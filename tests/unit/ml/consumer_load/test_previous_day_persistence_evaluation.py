"""Exact previous-day persistence Consumer Load MAE evaluation."""

from __future__ import annotations

from dataclasses import fields

import pytest

from energy_trading.application.errors import InvalidRequestError
from energy_trading.ml.consumer_load.previous_day_persistence_backtest import (
    PreviousDayPersistenceBacktestCase,
)
from energy_trading.ml.consumer_load.previous_day_persistence_evaluation import (
    PreviousDayPersistenceMAEResult,
    evaluate_previous_day_persistence_mae,
)
from tests.unit.domain._factories import utc

_EMPTY_CASES_MESSAGE = (
    "Previous-day persistence MAE evaluation requires at least one backtest case."
)


def _case(
    *,
    predicted_value_mw: float,
    actual_value_mw: float,
    hour: int = 16,
) -> PreviousDayPersistenceBacktestCase:
    return PreviousDayPersistenceBacktestCase(
        consumer_id="consumer-1",
        target_timestamp=utc(hour=hour),
        predicted_value_mw=predicted_value_mw,
        actual_value_mw=actual_value_mw,
    )


def test_empty_tuple_raises_invalid_request_error() -> None:
    with pytest.raises(InvalidRequestError, match=_EMPTY_CASES_MESSAGE) as captured:
        evaluate_previous_day_persistence_mae(cases=())
    assert captured.value.code == "invalid_request"
    assert captured.value.message == _EMPTY_CASES_MESSAGE


def test_one_exact_match_case_gives_mae_zero() -> None:
    result = evaluate_previous_day_persistence_mae(
        cases=(_case(predicted_value_mw=7.25, actual_value_mw=7.25),),
    )
    assert result.case_count == 1
    assert result.mae_mw == 0.0


def test_one_nonzero_error_case_gives_exact_absolute_mw_error() -> None:
    result = evaluate_previous_day_persistence_mae(
        cases=(_case(predicted_value_mw=4.5, actual_value_mw=7.25),),
    )
    assert result.case_count == 1
    assert result.mae_mw == abs(4.5 - 7.25)
    assert result.mae_mw == 2.75


def test_several_cases_calculate_arithmetic_mean_of_absolute_errors() -> None:
    cases = (
        _case(predicted_value_mw=1.0, actual_value_mw=2.0, hour=10),
        _case(predicted_value_mw=5.0, actual_value_mw=3.0, hour=11),
        _case(predicted_value_mw=8.0, actual_value_mw=11.0, hour=12),
    )
    result = evaluate_previous_day_persistence_mae(cases=cases)
    expected = (abs(1.0 - 2.0) + abs(5.0 - 3.0) + abs(8.0 - 11.0)) / 3
    assert result.case_count == 3
    assert result.mae_mw == expected
    assert result.mae_mw == 2.0


def test_positive_and_negative_signed_errors_become_absolute_error() -> None:
    cases = (
        _case(predicted_value_mw=10.0, actual_value_mw=7.0, hour=10),
        _case(predicted_value_mw=4.0, actual_value_mw=7.0, hour=11),
    )
    result = evaluate_previous_day_persistence_mae(cases=cases)
    assert result.mae_mw == 3.0
    assert result.mae_mw == (abs(10.0 - 7.0) + abs(4.0 - 7.0)) / 2


def test_case_count_equals_number_supplied() -> None:
    cases = tuple(
        _case(predicted_value_mw=1.0, actual_value_mw=1.5, hour=hour) for hour in (10, 11, 12, 13)
    )
    result = evaluate_previous_day_persistence_mae(cases=cases)
    assert result.case_count == 4
    assert result.case_count == len(cases)


def test_mae_mw_remains_mw_semantics() -> None:
    result = evaluate_previous_day_persistence_mae(
        cases=(_case(predicted_value_mw=4.5, actual_value_mw=7.25),),
    )
    assert isinstance(result.mae_mw, float)
    assert result.mae_mw == 2.75


def test_no_mw_mwh_conversion() -> None:
    result = evaluate_previous_day_persistence_mae(
        cases=(_case(predicted_value_mw=4.5, actual_value_mw=7.25),),
    )
    assert result.mae_mw == 2.75
    assert result.mae_mw != 2.75 * 1000
    assert result.mae_mw != 2.75 / 1000


def test_supplied_case_order_does_not_change_result() -> None:
    first = _case(predicted_value_mw=1.0, actual_value_mw=4.0, hour=10)
    second = _case(predicted_value_mw=2.0, actual_value_mw=2.5, hour=11)
    forward = evaluate_previous_day_persistence_mae(cases=(first, second))
    reversed_order = evaluate_previous_day_persistence_mae(cases=(second, first))
    assert forward == reversed_order
    assert forward.mae_mw == 1.75


def test_input_tuple_and_cases_are_not_mutated() -> None:
    original = (
        _case(predicted_value_mw=4.5, actual_value_mw=7.25, hour=16),
        _case(predicted_value_mw=3.0, actual_value_mw=3.0, hour=17),
    )
    snapshot = tuple(original)
    evaluate_previous_day_persistence_mae(cases=original)
    assert original == snapshot
    assert original[0] is snapshot[0]
    assert original[1] is snapshot[1]
    assert original[0].predicted_value_mw == 4.5
    assert original[0].actual_value_mw == 7.25


def test_repeated_equal_input_returns_value_equal_result() -> None:
    cases = (_case(predicted_value_mw=4.5, actual_value_mw=7.25),)
    first = evaluate_previous_day_persistence_mae(cases=cases)
    second = evaluate_previous_day_persistence_mae(cases=cases)
    assert first == second
    assert first is not second


def test_evaluator_does_not_drop_zero_error_cases() -> None:
    cases = (
        _case(predicted_value_mw=5.0, actual_value_mw=5.0, hour=10),
        _case(predicted_value_mw=1.0, actual_value_mw=5.0, hour=11),
    )
    result = evaluate_previous_day_persistence_mae(cases=cases)
    assert result.case_count == 2
    assert result.mae_mw == 2.0


def test_result_contract_contains_only_case_count_and_mae_mw() -> None:
    names = tuple(field.name for field in fields(PreviousDayPersistenceMAEResult))
    assert names == ("case_count", "mae_mw")
    result = evaluate_previous_day_persistence_mae(
        cases=(_case(predicted_value_mw=4.5, actual_value_mw=7.25),),
    )
    assert set(result.__slots__) == {"case_count", "mae_mw"}


def test_result_has_no_rmse_mse_mape_or_residual_fields() -> None:
    names = {field.name for field in fields(PreviousDayPersistenceMAEResult)}
    assert "rmse" not in names
    assert "rmse_mw" not in names
    assert "mse" not in names
    assert "mse_mw" not in names
    assert "mape" not in names
    assert "residual" not in names
    assert "residuals" not in names


def test_no_rounding_behavior_is_introduced() -> None:
    cases = (
        _case(predicted_value_mw=1.0, actual_value_mw=2.0, hour=10),
        _case(predicted_value_mw=2.0, actual_value_mw=2.0, hour=11),
        _case(predicted_value_mw=3.0, actual_value_mw=3.0, hour=12),
    )
    result = evaluate_previous_day_persistence_mae(cases=cases)
    expected = 1.0 / 3.0
    assert result.mae_mw == expected
    assert result.mae_mw != round(expected, 2)
    assert result.mae_mw != round(expected, 4)


def test_evaluator_uses_provided_cases_directly() -> None:
    supplied = _case(predicted_value_mw=9.0, actual_value_mw=6.0)
    result = evaluate_previous_day_persistence_mae(cases=(supplied,))
    assert result.case_count == 1
    assert result.mae_mw == abs(supplied.predicted_value_mw - supplied.actual_value_mw)
    assert result.mae_mw == 3.0
