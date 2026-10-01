"""Aligned persistence-versus-trained OLS DAM Price MAE comparison."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime
from decimal import Decimal

import pytest

# ``energy_trading.domain.models`` must initialize before
# ``energy_trading.domain.value_objects`` because value-object modules import
# canonical models during their own initialization. Importing the models
# package explicitly keeps that pre-existing order.
import energy_trading.domain.models  # noqa: F401
from energy_trading.application.errors import InvalidRequestError
from energy_trading.domain.value_objects.money import EnergyPrice
from energy_trading.ml.dam_price.lag_24h_linear_regression_prediction import (
    DAMPriceLag24hLinearRegressionPrediction,
)
from energy_trading.ml.dam_price.persistence_vs_trained_ols_comparison import (
    DAMPricePersistenceVsTrainedOLSMAEComparison,
    compare_dam_price_persistence_vs_trained_ols_mae,
)
from energy_trading.ml.dam_price.previous_day_persistence_backtest import (
    PreviousDayPersistenceBacktestCase,
)

_EMPTY_BOTH_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires a non-empty aligned cohort."
)
_EMPTY_PERSISTENCE_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires a non-empty persistence "
    "cohort."
)
_EMPTY_TRAINED_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires a non-empty trained OLS "
    "cohort."
)
_UNEQUAL_LENGTH_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires equal persistence and "
    "trained case counts."
)
_MIXED_PERSISTENCE_MARKET_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires persistence cases from "
    "exactly one market."
)
_MIXED_TRAINED_MARKET_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires trained predictions from "
    "exactly one market."
)
_MARKET_MISMATCH_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires persistence cases and "
    "trained predictions from the same market."
)
_PERSISTENCE_CURRENCY_COHERENCE_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires matching predicted and "
    "actual persistence currency."
)
_MIXED_PERSISTENCE_CURRENCY_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires persistence cases in "
    "exactly one currency."
)
_MIXED_TRAINED_CURRENCY_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires trained predictions in "
    "exactly one currency."
)
_CURRENCY_MISMATCH_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires persistence cases and "
    "trained predictions in the same currency."
)
_DUPLICATE_PERSISTENCE_TIMESTAMP_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires unique persistence target "
    "timestamps."
)
_DUPLICATE_TRAINED_TIMESTAMP_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires unique trained target "
    "timestamps."
)
_OUT_OF_ORDER_PERSISTENCE_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires strictly increasing "
    "persistence target timestamps."
)
_OUT_OF_ORDER_TRAINED_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires strictly increasing "
    "trained target timestamps."
)
_TIMESTAMP_MISMATCH_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires matching target timestamps "
    "at each aligned index."
)
_ACTUAL_MISMATCH_MESSAGE = (
    "DAM Price persistence-versus-trained OLS MAE comparison requires matching actual price "
    "amounts at each aligned index."
)

FOUR_FIELDS = (
    "case_count",
    "currency",
    "persistence_mae_amount_per_mwh",
    "trained_ols_mae_amount_per_mwh",
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


def _prediction(
    *,
    day: int,
    predicted: str,
    actual: str,
    market_id: str = "market-1",
    currency: str = "AMD",
) -> DAMPriceLag24hLinearRegressionPrediction:
    return DAMPriceLag24hLinearRegressionPrediction(
        market_id=market_id,
        currency=currency,
        target_timestamp=_ts(day),
        predicted_amount_per_mwh=Decimal(predicted),
        actual_amount_per_mwh=Decimal(actual),
    )


def _compare(
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    trained_predictions: tuple[DAMPriceLag24hLinearRegressionPrediction, ...],
) -> DAMPricePersistenceVsTrainedOLSMAEComparison:
    return compare_dam_price_persistence_vs_trained_ols_mae(
        persistence_cases=persistence_cases,
        trained_predictions=trained_predictions,
    )


def test_valid_aligned_single_case() -> None:
    result = _compare(
        (_case(day=1, predicted="10.00", actual="12.00"),),
        (_prediction(day=1, predicted="11.00", actual="12.00"),),
    )
    assert result.case_count == 1
    assert result.currency == "AMD"
    assert result.persistence_mae_amount_per_mwh == Decimal("2.00")
    assert result.trained_ols_mae_amount_per_mwh == Decimal("1.00")


def test_valid_aligned_multiple_cases() -> None:
    persistence_cases = (
        _case(day=1, predicted="10.00", actual="12.00"),
        _case(day=2, predicted="17.00", actual="20.00"),
        _case(day=3, predicted="30.00", actual="30.00"),
    )
    trained_predictions = (
        _prediction(day=1, predicted="11.00", actual="12.00"),
        _prediction(day=2, predicted="19.00", actual="20.00"),
        _prediction(day=3, predicted="31.00", actual="30.00"),
    )
    result = _compare(persistence_cases, trained_predictions)
    assert result.case_count == 3
    assert result.persistence_mae_amount_per_mwh == (Decimal("2") + Decimal("3") + Decimal("0")) / 3
    assert result.trained_ols_mae_amount_per_mwh == (Decimal("1") + Decimal("1") + Decimal("1")) / 3


def test_exact_case_count_matches_supplied_cohort() -> None:
    persistence_cases = (
        _case(day=1, predicted="1.00", actual="2.00"),
        _case(day=2, predicted="3.00", actual="4.00"),
    )
    trained_predictions = (
        _prediction(day=1, predicted="1.50", actual="2.00"),
        _prediction(day=2, predicted="3.50", actual="4.00"),
    )
    assert _compare(persistence_cases, trained_predictions).case_count == 2


def test_shared_currency_is_returned_exactly() -> None:
    persistence_cases = (
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
    trained_predictions = (
        _prediction(day=1, predicted="12.00", actual="13.00", market_id="market-7", currency="EUR"),
        _prediction(day=2, predicted="18.00", actual="19.00", market_id="market-7", currency="EUR"),
    )
    result = _compare(persistence_cases, trained_predictions)
    assert result.currency == "EUR"
    assert result.persistence_mae_amount_per_mwh == Decimal("2")
    assert result.trained_ols_mae_amount_per_mwh == Decimal("1")


def test_published_persistence_evaluator_mae_is_exposed() -> None:
    persistence_cases = (_case(day=1, predicted="10.25", actual="13.75"),)
    trained_predictions = (_prediction(day=1, predicted="13.75", actual="13.75"),)
    result = _compare(persistence_cases, trained_predictions)
    assert result.persistence_mae_amount_per_mwh == Decimal("3.50")


def test_published_trained_evaluator_mae_is_exposed() -> None:
    persistence_cases = (_case(day=1, predicted="13.75", actual="13.75"),)
    trained_predictions = (_prediction(day=1, predicted="10.25", actual="13.75"),)
    result = _compare(persistence_cases, trained_predictions)
    assert result.trained_ols_mae_amount_per_mwh == Decimal("3.50")


def test_lower_trained_mae_only_changes_numeric_fields() -> None:
    persistence_cases = (_case(day=1, predicted="10.00", actual="14.00"),)
    trained_predictions = (_prediction(day=1, predicted="13.00", actual="14.00"),)
    result = _compare(persistence_cases, trained_predictions)
    assert result.persistence_mae_amount_per_mwh == Decimal("4")
    assert result.trained_ols_mae_amount_per_mwh == Decimal("1")
    assert not hasattr(result, "winner")
    assert {item.name for item in fields(result)} == set(FOUR_FIELDS)


def test_lower_persistence_mae_only_changes_numeric_fields() -> None:
    persistence_cases = (_case(day=1, predicted="13.00", actual="14.00"),)
    trained_predictions = (_prediction(day=1, predicted="10.00", actual="14.00"),)
    result = _compare(persistence_cases, trained_predictions)
    assert result.persistence_mae_amount_per_mwh == Decimal("1")
    assert result.trained_ols_mae_amount_per_mwh == Decimal("4")
    assert not hasattr(result, "preferred_model")


def test_equal_mae_values_produce_no_tie_policy() -> None:
    persistence_cases = (_case(day=1, predicted="10.00", actual="14.00"),)
    trained_predictions = (_prediction(day=1, predicted="18.00", actual="14.00"),)
    result = _compare(persistence_cases, trained_predictions)
    assert result.persistence_mae_amount_per_mwh == result.trained_ols_mae_amount_per_mwh
    assert {item.name for item in fields(result)} == set(FOUR_FIELDS)


def test_negative_trained_prediction_is_valid() -> None:
    persistence_cases = (_case(day=1, predicted="5.00", actual="5.00"),)
    trained_predictions = (_prediction(day=1, predicted="-15.00", actual="5.00"),)
    result = _compare(persistence_cases, trained_predictions)
    assert result.persistence_mae_amount_per_mwh == Decimal("0")
    assert result.trained_ols_mae_amount_per_mwh == Decimal("20")


def test_negative_persistence_prediction_is_valid() -> None:
    persistence_cases = (_case(day=1, predicted="-15.00", actual="5.00"),)
    trained_predictions = (_prediction(day=1, predicted="5.00", actual="5.00"),)
    result = _compare(persistence_cases, trained_predictions)
    assert result.persistence_mae_amount_per_mwh == Decimal("20")
    assert result.trained_ols_mae_amount_per_mwh == Decimal("0")


def test_negative_actual_values_are_valid() -> None:
    persistence_cases = (_case(day=1, predicted="-10.00", actual="-12.00"),)
    trained_predictions = (_prediction(day=1, predicted="-11.00", actual="-12.00"),)
    result = _compare(persistence_cases, trained_predictions)
    assert result.persistence_mae_amount_per_mwh == Decimal("2")
    assert result.trained_ols_mae_amount_per_mwh == Decimal("1")


def test_both_negative_predictions_and_actuals_are_valid() -> None:
    persistence_cases = (_case(day=1, predicted="-20.00", actual="-15.00"),)
    trained_predictions = (_prediction(day=1, predicted="-18.00", actual="-15.00"),)
    result = _compare(persistence_cases, trained_predictions)
    assert result.persistence_mae_amount_per_mwh == Decimal("5")
    assert result.trained_ols_mae_amount_per_mwh == Decimal("3")


def test_zero_actual_values_are_valid() -> None:
    persistence_cases = (_case(day=1, predicted="4.00", actual="0.00"),)
    trained_predictions = (_prediction(day=1, predicted="2.00", actual="0.00"),)
    result = _compare(persistence_cases, trained_predictions)
    assert result.persistence_mae_amount_per_mwh == Decimal("4")
    assert result.trained_ols_mae_amount_per_mwh == Decimal("2")


def test_empty_both_cohorts_fail_closed() -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _compare((), ())
    assert captured.value.message == _EMPTY_BOTH_MESSAGE


def test_empty_persistence_cohort_fails_closed() -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _compare((), (_prediction(day=1, predicted="1.00", actual="1.00"),))
    assert captured.value.message == _EMPTY_PERSISTENCE_MESSAGE


def test_empty_trained_cohort_fails_closed() -> None:
    with pytest.raises(InvalidRequestError) as captured:
        _compare((_case(day=1, predicted="1.00", actual="1.00"),), ())
    assert captured.value.message == _EMPTY_TRAINED_MESSAGE


def test_unequal_cohort_lengths_fail_closed() -> None:
    persistence_cases = (
        _case(day=1, predicted="1.00", actual="1.00"),
        _case(day=2, predicted="2.00", actual="2.00"),
    )
    trained_predictions = (_prediction(day=1, predicted="1.00", actual="1.00"),)
    with pytest.raises(InvalidRequestError) as captured:
        _compare(persistence_cases, trained_predictions)
    assert captured.value.message == _UNEQUAL_LENGTH_MESSAGE


def test_mixed_persistence_markets_fail_closed() -> None:
    persistence_cases = (
        _case(day=1, predicted="1.00", actual="1.00", market_id="market-alpha"),
        _case(day=2, predicted="2.00", actual="2.00", market_id="market-beta"),
    )
    trained_predictions = (
        _prediction(day=1, predicted="1.00", actual="1.00", market_id="market-alpha"),
        _prediction(day=2, predicted="2.00", actual="2.00", market_id="market-beta"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _compare(persistence_cases, trained_predictions)
    assert captured.value.message == _MIXED_PERSISTENCE_MARKET_MESSAGE
    assert "market-alpha" not in captured.value.message
    assert "market-beta" not in captured.value.message


def test_mixed_trained_markets_fail_closed() -> None:
    persistence_cases = (
        _case(day=1, predicted="1.00", actual="1.00"),
        _case(day=2, predicted="2.00", actual="2.00"),
    )
    trained_predictions = (
        _prediction(day=1, predicted="1.00", actual="1.00", market_id="market-alpha"),
        _prediction(day=2, predicted="2.00", actual="2.00", market_id="market-beta"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _compare(persistence_cases, trained_predictions)
    assert captured.value.message == _MIXED_TRAINED_MARKET_MESSAGE


def test_cross_cohort_market_mismatch_fails_closed_without_leaking_ids() -> None:
    persistence_cases = (_case(day=1, predicted="1.00", actual="1.00", market_id="market-alpha"),)
    trained_predictions = (
        _prediction(day=1, predicted="1.00", actual="1.00", market_id="market-beta"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _compare(persistence_cases, trained_predictions)
    assert captured.value.message == _MARKET_MISMATCH_MESSAGE
    assert "market-alpha" not in captured.value.message
    assert "market-beta" not in captured.value.message


def test_persistence_predicted_actual_currency_mismatch_fails_closed() -> None:
    persistence_cases = (_case(day=1, predicted="1.00", actual="1.00", actual_currency="EUR"),)
    trained_predictions = (_prediction(day=1, predicted="1.00", actual="1.00"),)
    with pytest.raises(InvalidRequestError) as captured:
        _compare(persistence_cases, trained_predictions)
    assert captured.value.message == _PERSISTENCE_CURRENCY_COHERENCE_MESSAGE
    assert "AMD" not in captured.value.message
    assert "EUR" not in captured.value.message


def test_mixed_persistence_cohort_currencies_fail_closed() -> None:
    persistence_cases = (
        PreviousDayPersistenceBacktestCase(
            market_id="market-1",
            target_timestamp=_ts(1),
            predicted_price=_price("1.00", currency="AMD"),
            actual_price=_price("1.00", currency="AMD"),
        ),
        PreviousDayPersistenceBacktestCase(
            market_id="market-1",
            target_timestamp=_ts(2),
            predicted_price=_price("2.00", currency="EUR"),
            actual_price=_price("2.00", currency="EUR"),
        ),
    )
    trained_predictions = (
        _prediction(day=1, predicted="1.00", actual="1.00"),
        _prediction(day=2, predicted="2.00", actual="2.00"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _compare(persistence_cases, trained_predictions)
    assert captured.value.message == _MIXED_PERSISTENCE_CURRENCY_MESSAGE
    assert "AMD" not in captured.value.message
    assert "EUR" not in captured.value.message


def test_mixed_trained_currencies_fail_closed() -> None:
    persistence_cases = (
        _case(day=1, predicted="1.00", actual="1.00"),
        _case(day=2, predicted="2.00", actual="2.00"),
    )
    trained_predictions = (
        _prediction(day=1, predicted="1.00", actual="1.00", currency="AMD"),
        _prediction(day=2, predicted="2.00", actual="2.00", currency="EUR"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _compare(persistence_cases, trained_predictions)
    assert captured.value.message == _MIXED_TRAINED_CURRENCY_MESSAGE
    assert "AMD" not in captured.value.message
    assert "EUR" not in captured.value.message


def test_cross_cohort_currency_mismatch_fails_closed() -> None:
    persistence_cases = (
        PreviousDayPersistenceBacktestCase(
            market_id="market-1",
            target_timestamp=_ts(1),
            predicted_price=_price("1.00", currency="AMD"),
            actual_price=_price("1.00", currency="AMD"),
        ),
    )
    trained_predictions = (_prediction(day=1, predicted="1.00", actual="1.00", currency="EUR"),)
    with pytest.raises(InvalidRequestError) as captured:
        _compare(persistence_cases, trained_predictions)
    assert captured.value.message == _CURRENCY_MISMATCH_MESSAGE
    assert "AMD" not in captured.value.message
    assert "EUR" not in captured.value.message


def test_duplicate_persistence_timestamps_fail_closed() -> None:
    persistence_cases = (
        _case(day=1, predicted="1.00", actual="1.00"),
        _case(day=1, predicted="2.00", actual="2.00"),
    )
    trained_predictions = (
        _prediction(day=1, predicted="1.00", actual="1.00"),
        _prediction(day=1, predicted="2.00", actual="2.00"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _compare(persistence_cases, trained_predictions)
    assert captured.value.message == _DUPLICATE_PERSISTENCE_TIMESTAMP_MESSAGE


def test_out_of_order_persistence_timestamps_fail_closed() -> None:
    persistence_cases = (
        _case(day=3, predicted="1.00", actual="1.00"),
        _case(day=1, predicted="2.00", actual="2.00"),
    )
    trained_predictions = (
        _prediction(day=3, predicted="1.00", actual="1.00"),
        _prediction(day=1, predicted="2.00", actual="2.00"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _compare(persistence_cases, trained_predictions)
    assert captured.value.message == _OUT_OF_ORDER_PERSISTENCE_MESSAGE


def test_duplicate_trained_timestamps_fail_closed() -> None:
    persistence_cases = (
        _case(day=1, predicted="1.00", actual="1.00"),
        _case(day=2, predicted="2.00", actual="2.00"),
    )
    trained_predictions = (
        _prediction(day=1, predicted="1.00", actual="1.00"),
        _prediction(day=1, predicted="2.00", actual="2.00"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _compare(persistence_cases, trained_predictions)
    assert captured.value.message == _DUPLICATE_TRAINED_TIMESTAMP_MESSAGE


def test_out_of_order_trained_timestamps_fail_closed() -> None:
    persistence_cases = (
        _case(day=1, predicted="1.00", actual="1.00"),
        _case(day=3, predicted="2.00", actual="2.00"),
    )
    trained_predictions = (
        _prediction(day=3, predicted="1.00", actual="1.00"),
        _prediction(day=1, predicted="2.00", actual="2.00"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _compare(persistence_cases, trained_predictions)
    assert captured.value.message == _OUT_OF_ORDER_TRAINED_MESSAGE


def test_same_timestamps_in_different_order_fail_rather_than_realign() -> None:
    # Both cohorts are individually strictly chronological, so chronology
    # validation passes and only positional identity can fail. The same
    # timestamp set shifted by one position must not be realigned.
    persistence_cases = (
        _case(day=2, predicted="1.00", actual="1.00"),
        _case(day=3, predicted="2.00", actual="2.00"),
    )
    trained_predictions = (
        _prediction(day=1, predicted="1.00", actual="1.00"),
        _prediction(day=2, predicted="2.00", actual="2.00"),
    )
    with pytest.raises(InvalidRequestError) as captured:
        _compare(persistence_cases, trained_predictions)
    assert captured.value.message == _TIMESTAMP_MISMATCH_MESSAGE


def test_pairwise_timestamp_mismatch_fails_closed() -> None:
    persistence_cases = (_case(day=1, predicted="1.00", actual="1.00"),)
    trained_predictions = (_prediction(day=5, predicted="1.00", actual="1.00"),)
    with pytest.raises(InvalidRequestError) as captured:
        _compare(persistence_cases, trained_predictions)
    assert captured.value.message == _TIMESTAMP_MISMATCH_MESSAGE


def test_pairwise_actual_price_amount_mismatch_fails_closed() -> None:
    persistence_cases = (_case(day=1, predicted="1.00", actual="5.00"),)
    trained_predictions = (_prediction(day=1, predicted="1.00", actual="6.00"),)
    with pytest.raises(InvalidRequestError) as captured:
        _compare(persistence_cases, trained_predictions)
    assert captured.value.message == _ACTUAL_MISMATCH_MESSAGE


def test_actual_price_mismatch_message_contains_no_numeric_actual() -> None:
    persistence_cases = (_case(day=1, predicted="1.00", actual="111.11"),)
    trained_predictions = (_prediction(day=1, predicted="1.00", actual="222.22"),)
    with pytest.raises(InvalidRequestError) as captured:
        _compare(persistence_cases, trained_predictions)
    message = captured.value.message
    assert "111.11" not in message
    assert "222.22" not in message


def test_exact_decimal_actual_equality_succeeds_without_conversion() -> None:
    persistence_cases = (_case(day=1, predicted="1.00", actual="0.10"),)
    trained_predictions = (_prediction(day=1, predicted="1.00", actual="0.1"),)
    result = _compare(persistence_cases, trained_predictions)
    assert result.case_count == 1
    assert isinstance(result.persistence_mae_amount_per_mwh, Decimal)
    assert not isinstance(result.persistence_mae_amount_per_mwh, float)


def test_different_predicted_values_are_explicitly_allowed() -> None:
    persistence_cases = (_case(day=1, predicted="1.00", actual="10.00"),)
    trained_predictions = (_prediction(day=1, predicted="9.00", actual="10.00"),)
    result = _compare(persistence_cases, trained_predictions)
    assert result.persistence_mae_amount_per_mwh == Decimal("9")
    assert result.trained_ols_mae_amount_per_mwh == Decimal("1")


def test_repeated_equivalent_calls_are_value_equivalent() -> None:
    persistence_cases = (
        _case(day=1, predicted="10.00", actual="12.00"),
        _case(day=2, predicted="20.00", actual="17.00"),
    )
    trained_predictions = (
        _prediction(day=1, predicted="11.00", actual="12.00"),
        _prediction(day=2, predicted="16.00", actual="17.00"),
    )
    assert _compare(persistence_cases, trained_predictions) == _compare(
        persistence_cases, trained_predictions
    )


def test_input_cohorts_and_objects_are_not_modified() -> None:
    case = _case(day=1, predicted="10.00", actual="12.00")
    prediction = _prediction(day=1, predicted="11.00", actual="12.00")
    persistence_cases = (case,)
    trained_predictions = (prediction,)
    _compare(persistence_cases, trained_predictions)
    assert persistence_cases == (case,)
    assert trained_predictions == (prediction,)
    assert case.predicted_price.amount_per_mwh == Decimal("10.00")
    assert case.actual_price.amount_per_mwh == Decimal("12.00")
    assert prediction.predicted_amount_per_mwh == Decimal("11.00")
    assert prediction.actual_amount_per_mwh == Decimal("12.00")
    assert prediction.market_id == "market-1"
    assert prediction.currency == "AMD"


def test_result_contract_is_frozen_slotted_and_exactly_four_fields() -> None:
    names = tuple(item.name for item in fields(DAMPricePersistenceVsTrainedOLSMAEComparison))
    assert names == FOUR_FIELDS
    assert DAMPricePersistenceVsTrainedOLSMAEComparison.__slots__ == names
    result = _compare(
        (_case(day=1, predicted="10.00", actual="12.00"),),
        (_prediction(day=1, predicted="11.00", actual="12.00"),),
    )
    with pytest.raises(FrozenInstanceError):
        result.case_count = 99  # type: ignore[misc]


def test_result_exposes_no_winner_champion_or_extra_metric_fields() -> None:
    names = {item.name for item in fields(DAMPricePersistenceVsTrainedOLSMAEComparison)}
    assert names == set(FOUR_FIELDS)
    forbidden = {
        "market_id",
        "winner",
        "champion",
        "preferred_model",
        "improvement",
        "absolute_improvement",
        "percentage_improvement",
        "ratio",
        "threshold",
        "status",
        "confidence",
        "mse",
        "rmse",
        "mape",
        "smape",
        "r2",
        "residual",
        "residuals",
        "model_name",
        "model_version",
        "provider",
        "metadata",
        "forecast_run_id",
        "generated_at",
    }
    assert forbidden.isdisjoint(names)
    assert len(names) == 4


def test_metric_values_are_decimal_not_float() -> None:
    result = _compare(
        (_case(day=1, predicted="100.10", actual="200.33"),),
        (_prediction(day=1, predicted="200.33", actual="200.33"),),
    )
    assert isinstance(result.persistence_mae_amount_per_mwh, Decimal)
    assert isinstance(result.trained_ols_mae_amount_per_mwh, Decimal)
    assert not isinstance(result.persistence_mae_amount_per_mwh, float)
    assert not isinstance(result.trained_ols_mae_amount_per_mwh, float)
    assert result.persistence_mae_amount_per_mwh == Decimal("100.23")
    assert result.trained_ols_mae_amount_per_mwh == Decimal("0")


def test_comparison_is_synchronous_and_keyword_only() -> None:
    assert not inspect.iscoroutinefunction(compare_dam_price_persistence_vs_trained_ols_mae)
    parameters = inspect.signature(compare_dam_price_persistence_vs_trained_ols_mae).parameters
    assert tuple(parameters) == ("persistence_cases", "trained_predictions")
    assert parameters["persistence_cases"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["trained_predictions"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["persistence_cases"].default is inspect.Parameter.empty
    assert parameters["trained_predictions"].default is inspect.Parameter.empty
