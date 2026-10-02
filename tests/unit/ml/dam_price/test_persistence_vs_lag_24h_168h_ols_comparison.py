"""Aligned persistence-versus-two-feature OLS DAM Price MAE comparison."""

from __future__ import annotations

import inspect
from dataclasses import MISSING, FrozenInstanceError, fields
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
from energy_trading.ml.dam_price import persistence_vs_lag_24h_168h_ols_comparison
from energy_trading.ml.dam_price.lag_24h_168h_linear_regression_prediction import (
    DAMPriceLag24h168hLinearRegressionPrediction,
)
from energy_trading.ml.dam_price.persistence_vs_lag_24h_168h_ols_comparison import (
    DAMPricePersistenceVsLag24h168hOLSMAEComparison,
    compare_dam_price_persistence_vs_lag_24h_168h_ols_mae,
)
from energy_trading.ml.dam_price.previous_day_persistence_backtest import (
    PreviousDayPersistenceBacktestCase,
)

_EMPTY_BOTH_MESSAGE = (
    "DAM Price persistence-versus-two-feature OLS MAE comparison requires a non-empty aligned "
    "cohort."
)
_EMPTY_PERSISTENCE_MESSAGE = (
    "DAM Price persistence-versus-two-feature OLS MAE comparison requires a non-empty "
    "persistence cohort."
)
_EMPTY_LAG_24H_168H_MESSAGE = (
    "DAM Price persistence-versus-two-feature OLS MAE comparison requires a non-empty "
    "two-feature cohort."
)
_UNEQUAL_LENGTH_MESSAGE = (
    "DAM Price persistence-versus-two-feature OLS MAE comparison requires equal persistence and "
    "two-feature case counts."
)
_MIXED_PERSISTENCE_MARKET_MESSAGE = (
    "DAM Price persistence-versus-two-feature OLS MAE comparison requires persistence cases "
    "from exactly one market."
)
_MIXED_LAG_24H_168H_MARKET_MESSAGE = (
    "DAM Price persistence-versus-two-feature OLS MAE comparison requires two-feature "
    "predictions from exactly one market."
)
_MARKET_MISMATCH_MESSAGE = (
    "DAM Price persistence-versus-two-feature OLS MAE comparison requires persistence cases and "
    "two-feature predictions from the same market."
)
_PERSISTENCE_CURRENCY_COHERENCE_MESSAGE = (
    "DAM Price persistence-versus-two-feature OLS MAE comparison requires matching predicted "
    "and actual persistence currency."
)
_MIXED_PERSISTENCE_CURRENCY_MESSAGE = (
    "DAM Price persistence-versus-two-feature OLS MAE comparison requires persistence cases in "
    "exactly one currency."
)
_MIXED_LAG_24H_168H_CURRENCY_MESSAGE = (
    "DAM Price persistence-versus-two-feature OLS MAE comparison requires two-feature "
    "predictions in exactly one currency."
)
_CURRENCY_MISMATCH_MESSAGE = (
    "DAM Price persistence-versus-two-feature OLS MAE comparison requires persistence cases and "
    "two-feature predictions in the same currency."
)
_DUPLICATE_PERSISTENCE_TIMESTAMP_MESSAGE = (
    "DAM Price persistence-versus-two-feature OLS MAE comparison requires unique persistence "
    "target timestamps."
)
_DUPLICATE_LAG_24H_168H_TIMESTAMP_MESSAGE = (
    "DAM Price persistence-versus-two-feature OLS MAE comparison requires unique two-feature "
    "target timestamps."
)
_OUT_OF_ORDER_PERSISTENCE_MESSAGE = (
    "DAM Price persistence-versus-two-feature OLS MAE comparison requires strictly increasing "
    "persistence target timestamps."
)
_OUT_OF_ORDER_LAG_24H_168H_MESSAGE = (
    "DAM Price persistence-versus-two-feature OLS MAE comparison requires strictly increasing "
    "two-feature target timestamps."
)
_TIMESTAMP_MISMATCH_MESSAGE = (
    "DAM Price persistence-versus-two-feature OLS MAE comparison requires matching target "
    "timestamps at each aligned index."
)
_ACTUAL_MISMATCH_MESSAGE = (
    "DAM Price persistence-versus-two-feature OLS MAE comparison requires matching actual price "
    "amounts at each aligned index."
)

# Published evaluator message, used to prove evaluator failures propagate unchanged.
_LAG_24H_168H_EVALUATOR_NON_FINITE_MESSAGE = (
    "DAM Price 24h+168h linear regression MAE evaluation requires finite predicted and "
    "actual values."
)

FOUR_FIELDS = (
    "case_count",
    "currency",
    "persistence_mae_amount_per_mwh",
    "lag_24h_168h_mae_amount_per_mwh",
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


def _lag_24h_168h(
    *,
    day: int,
    predicted: str,
    actual: str,
    market_id: str = "market-1",
    currency: str = "AMD",
) -> DAMPriceLag24h168hLinearRegressionPrediction:
    return DAMPriceLag24h168hLinearRegressionPrediction(
        market_id=market_id,
        currency=currency,
        target_timestamp=_ts(day),
        predicted_amount_per_mwh=Decimal(predicted),
        actual_amount_per_mwh=Decimal(actual),
    )


def _compare(
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    lag_24h_168h_predictions: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
) -> DAMPricePersistenceVsLag24h168hOLSMAEComparison:
    return compare_dam_price_persistence_vs_lag_24h_168h_ols_mae(
        persistence_cases=persistence_cases,
        lag_24h_168h_predictions=lag_24h_168h_predictions,
    )


def _assert_fails(
    persistence_cases: tuple[PreviousDayPersistenceBacktestCase, ...],
    lag_24h_168h_predictions: tuple[DAMPriceLag24h168hLinearRegressionPrediction, ...],
    message: str,
) -> InvalidRequestError:
    with pytest.raises(InvalidRequestError) as captured:
        _compare(persistence_cases, lag_24h_168h_predictions)
    assert captured.value.message == message
    return captured.value


def test_valid_aligned_single_case() -> None:
    result = _compare(
        (_case(day=1, predicted="10.00", actual="12.00"),),
        (_lag_24h_168h(day=1, predicted="11.00", actual="12.00"),),
    )
    assert result.case_count == 1
    assert result.currency == "AMD"
    assert result.persistence_mae_amount_per_mwh == Decimal("2.00")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("1.00")


def test_valid_aligned_multiple_cases() -> None:
    persistence_cases = (
        _case(day=1, predicted="10.00", actual="12.00"),
        _case(day=2, predicted="17.00", actual="20.00"),
        _case(day=3, predicted="30.00", actual="30.00"),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h(day=1, predicted="11.00", actual="12.00"),
        _lag_24h_168h(day=2, predicted="19.00", actual="20.00"),
        _lag_24h_168h(day=3, predicted="31.00", actual="30.00"),
    )
    result = _compare(persistence_cases, lag_24h_168h_predictions)
    assert result.case_count == 3
    assert result.persistence_mae_amount_per_mwh == (Decimal("2") + Decimal("3") + Decimal("0")) / 3
    assert result.lag_24h_168h_mae_amount_per_mwh == (
        (Decimal("1") + Decimal("1") + Decimal("1")) / 3
    )


def test_exact_case_count_matches_supplied_cohort() -> None:
    persistence_cases = (
        _case(day=1, predicted="1.00", actual="2.00"),
        _case(day=2, predicted="3.00", actual="4.00"),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h(day=1, predicted="1.50", actual="2.00"),
        _lag_24h_168h(day=2, predicted="3.50", actual="4.00"),
    )
    assert _compare(persistence_cases, lag_24h_168h_predictions).case_count == 2


def test_canonical_shared_currency_is_returned() -> None:
    result = _compare(
        (_case(day=1, predicted="1.00", actual="2.00"),),
        (_lag_24h_168h(day=1, predicted="1.50", actual="2.00"),),
    )
    assert result.currency == "AMD"


def test_non_default_shared_currency_is_returned_exactly() -> None:
    persistence_cases = (
        _case(
            day=1,
            predicted="11.00",
            actual="13.00",
            market_id="market-7",
            predicted_currency="EUR",
            actual_currency="EUR",
        ),
        _case(
            day=2,
            predicted="21.00",
            actual="19.00",
            market_id="market-7",
            predicted_currency="EUR",
            actual_currency="EUR",
        ),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h(
            day=1, predicted="12.00", actual="13.00", market_id="market-7", currency="EUR"
        ),
        _lag_24h_168h(
            day=2, predicted="18.00", actual="19.00", market_id="market-7", currency="EUR"
        ),
    )
    result = _compare(persistence_cases, lag_24h_168h_predictions)
    assert result.currency == "EUR"
    assert result.persistence_mae_amount_per_mwh == Decimal("2")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("1")


def test_published_persistence_evaluator_mae_is_exposed() -> None:
    result = _compare(
        (_case(day=1, predicted="10.25", actual="13.75"),),
        (_lag_24h_168h(day=1, predicted="13.75", actual="13.75"),),
    )
    assert result.persistence_mae_amount_per_mwh == Decimal("3.50")


def test_published_two_feature_evaluator_mae_is_exposed() -> None:
    result = _compare(
        (_case(day=1, predicted="13.75", actual="13.75"),),
        (_lag_24h_168h(day=1, predicted="10.25", actual="13.75"),),
    )
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("3.50")


def test_lower_persistence_mae_produces_no_winner() -> None:
    result = _compare(
        (_case(day=1, predicted="13.00", actual="14.00"),),
        (_lag_24h_168h(day=1, predicted="10.00", actual="14.00"),),
    )
    assert result.persistence_mae_amount_per_mwh == Decimal("1")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("4")
    assert not hasattr(result, "winner")
    assert not hasattr(result, "preferred_model")
    assert {item.name for item in fields(result)} == set(FOUR_FIELDS)


def test_lower_two_feature_mae_produces_no_winner() -> None:
    result = _compare(
        (_case(day=1, predicted="10.00", actual="14.00"),),
        (_lag_24h_168h(day=1, predicted="13.00", actual="14.00"),),
    )
    assert result.persistence_mae_amount_per_mwh == Decimal("4")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("1")
    assert not hasattr(result, "winner")
    assert not hasattr(result, "champion")
    assert {item.name for item in fields(result)} == set(FOUR_FIELDS)


def test_equal_mae_values_produce_no_tie_policy() -> None:
    result = _compare(
        (_case(day=1, predicted="10.00", actual="14.00"),),
        (_lag_24h_168h(day=1, predicted="18.00", actual="14.00"),),
    )
    assert result.persistence_mae_amount_per_mwh == result.lag_24h_168h_mae_amount_per_mwh
    assert not hasattr(result, "tie")
    assert {item.name for item in fields(result)} == set(FOUR_FIELDS)


def test_negative_persistence_prediction_is_valid() -> None:
    result = _compare(
        (_case(day=1, predicted="-15.00", actual="5.00"),),
        (_lag_24h_168h(day=1, predicted="5.00", actual="5.00"),),
    )
    assert result.persistence_mae_amount_per_mwh == Decimal("20")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("0")


def test_negative_two_feature_prediction_is_valid() -> None:
    result = _compare(
        (_case(day=1, predicted="5.00", actual="5.00"),),
        (_lag_24h_168h(day=1, predicted="-15.00", actual="5.00"),),
    )
    assert result.persistence_mae_amount_per_mwh == Decimal("0")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("20")


def test_negative_actual_values_are_valid() -> None:
    result = _compare(
        (_case(day=1, predicted="10.00", actual="-12.00"),),
        (_lag_24h_168h(day=1, predicted="11.00", actual="-12.00"),),
    )
    assert result.persistence_mae_amount_per_mwh == Decimal("22")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("23")


def test_both_negative_predictions_and_actuals_are_valid() -> None:
    result = _compare(
        (_case(day=1, predicted="-20.00", actual="-15.00"),),
        (_lag_24h_168h(day=1, predicted="-18.00", actual="-15.00"),),
    )
    assert result.persistence_mae_amount_per_mwh == Decimal("5")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("3")


def test_zero_prices_are_valid() -> None:
    result = _compare(
        (_case(day=1, predicted="0.00", actual="0.00"),),
        (_lag_24h_168h(day=1, predicted="2.00", actual="0.00"),),
    )
    assert result.persistence_mae_amount_per_mwh == Decimal("0")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("2")


def test_different_predicted_values_are_explicitly_allowed() -> None:
    persistence_cases = (_case(day=1, predicted="1.00", actual="10.00"),)
    lag_24h_168h_predictions = (_lag_24h_168h(day=1, predicted="9.00", actual="10.00"),)
    assert (
        persistence_cases[0].predicted_price.amount_per_mwh
        != lag_24h_168h_predictions[0].predicted_amount_per_mwh
    )
    result = _compare(persistence_cases, lag_24h_168h_predictions)
    assert result.persistence_mae_amount_per_mwh == Decimal("9")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("1")


def test_empty_both_cohorts_fail_closed() -> None:
    _assert_fails((), (), _EMPTY_BOTH_MESSAGE)


def test_empty_persistence_cohort_fails_closed() -> None:
    _assert_fails(
        (),
        (_lag_24h_168h(day=1, predicted="1.00", actual="1.00"),),
        _EMPTY_PERSISTENCE_MESSAGE,
    )


def test_empty_two_feature_cohort_fails_closed() -> None:
    _assert_fails(
        (_case(day=1, predicted="1.00", actual="1.00"),),
        (),
        _EMPTY_LAG_24H_168H_MESSAGE,
    )


def test_unequal_cohort_lengths_fail_closed() -> None:
    _assert_fails(
        (
            _case(day=1, predicted="1.00", actual="1.00"),
            _case(day=2, predicted="2.00", actual="2.00"),
        ),
        (_lag_24h_168h(day=1, predicted="1.00", actual="1.00"),),
        _UNEQUAL_LENGTH_MESSAGE,
    )


def test_mixed_persistence_markets_fail_closed_without_leaking_ids() -> None:
    error = _assert_fails(
        (
            _case(day=1, predicted="1.00", actual="1.00", market_id="market-alpha"),
            _case(day=2, predicted="2.00", actual="2.00", market_id="market-beta"),
        ),
        (
            _lag_24h_168h(day=1, predicted="1.00", actual="1.00", market_id="market-alpha"),
            _lag_24h_168h(day=2, predicted="2.00", actual="2.00", market_id="market-beta"),
        ),
        _MIXED_PERSISTENCE_MARKET_MESSAGE,
    )
    assert "market-alpha" not in error.message
    assert "market-beta" not in error.message


def test_mixed_two_feature_markets_fail_closed() -> None:
    _assert_fails(
        (
            _case(day=1, predicted="1.00", actual="1.00"),
            _case(day=2, predicted="2.00", actual="2.00"),
        ),
        (
            _lag_24h_168h(day=1, predicted="1.00", actual="1.00", market_id="market-alpha"),
            _lag_24h_168h(day=2, predicted="2.00", actual="2.00", market_id="market-beta"),
        ),
        _MIXED_LAG_24H_168H_MARKET_MESSAGE,
    )


def test_cross_cohort_market_mismatch_fails_closed_without_leaking_ids() -> None:
    error = _assert_fails(
        (_case(day=1, predicted="1.00", actual="1.00", market_id="market-alpha"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="1.00", market_id="market-beta"),),
        _MARKET_MISMATCH_MESSAGE,
    )
    assert "market-alpha" not in error.message
    assert "market-beta" not in error.message


def test_persistence_predicted_actual_currency_incoherence_fails_closed() -> None:
    error = _assert_fails(
        (_case(day=1, predicted="1.00", actual="1.00", actual_currency="EUR"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="1.00"),),
        _PERSISTENCE_CURRENCY_COHERENCE_MESSAGE,
    )
    assert "AMD" not in error.message
    assert "EUR" not in error.message


def test_mixed_persistence_currencies_fail_closed() -> None:
    error = _assert_fails(
        (
            _case(day=1, predicted="1.00", actual="1.00"),
            _case(
                day=2,
                predicted="2.00",
                actual="2.00",
                predicted_currency="EUR",
                actual_currency="EUR",
            ),
        ),
        (
            _lag_24h_168h(day=1, predicted="1.00", actual="1.00"),
            _lag_24h_168h(day=2, predicted="2.00", actual="2.00"),
        ),
        _MIXED_PERSISTENCE_CURRENCY_MESSAGE,
    )
    assert "AMD" not in error.message
    assert "EUR" not in error.message


def test_mixed_two_feature_currencies_fail_closed() -> None:
    error = _assert_fails(
        (
            _case(day=1, predicted="1.00", actual="1.00"),
            _case(day=2, predicted="2.00", actual="2.00"),
        ),
        (
            _lag_24h_168h(day=1, predicted="1.00", actual="1.00", currency="AMD"),
            _lag_24h_168h(day=2, predicted="2.00", actual="2.00", currency="EUR"),
        ),
        _MIXED_LAG_24H_168H_CURRENCY_MESSAGE,
    )
    assert "AMD" not in error.message
    assert "EUR" not in error.message


def test_cross_cohort_currency_mismatch_fails_closed() -> None:
    error = _assert_fails(
        (_case(day=1, predicted="1.00", actual="1.00"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="1.00", currency="EUR"),),
        _CURRENCY_MISMATCH_MESSAGE,
    )
    assert "AMD" not in error.message
    assert "EUR" not in error.message


def test_duplicate_persistence_timestamps_fail_closed() -> None:
    _assert_fails(
        (
            _case(day=1, predicted="1.00", actual="1.00"),
            _case(day=1, predicted="2.00", actual="2.00"),
        ),
        (
            _lag_24h_168h(day=1, predicted="1.00", actual="1.00"),
            _lag_24h_168h(day=2, predicted="2.00", actual="2.00"),
        ),
        _DUPLICATE_PERSISTENCE_TIMESTAMP_MESSAGE,
    )


def test_out_of_order_persistence_timestamps_fail_closed() -> None:
    _assert_fails(
        (
            _case(day=3, predicted="1.00", actual="1.00"),
            _case(day=1, predicted="2.00", actual="2.00"),
        ),
        (
            _lag_24h_168h(day=1, predicted="1.00", actual="1.00"),
            _lag_24h_168h(day=3, predicted="2.00", actual="2.00"),
        ),
        _OUT_OF_ORDER_PERSISTENCE_MESSAGE,
    )


def test_duplicate_two_feature_timestamps_fail_closed() -> None:
    _assert_fails(
        (
            _case(day=1, predicted="1.00", actual="1.00"),
            _case(day=2, predicted="2.00", actual="2.00"),
        ),
        (
            _lag_24h_168h(day=1, predicted="1.00", actual="1.00"),
            _lag_24h_168h(day=1, predicted="2.00", actual="2.00"),
        ),
        _DUPLICATE_LAG_24H_168H_TIMESTAMP_MESSAGE,
    )


def test_out_of_order_two_feature_timestamps_fail_closed() -> None:
    _assert_fails(
        (
            _case(day=1, predicted="1.00", actual="1.00"),
            _case(day=3, predicted="2.00", actual="2.00"),
        ),
        (
            _lag_24h_168h(day=3, predicted="1.00", actual="1.00"),
            _lag_24h_168h(day=1, predicted="2.00", actual="2.00"),
        ),
        _OUT_OF_ORDER_LAG_24H_168H_MESSAGE,
    )


def test_same_timestamps_in_different_order_fail_rather_than_realign() -> None:
    # The same timestamp set in reversed order on one side must fail rather
    # than being sorted into alignment.
    _assert_fails(
        (
            _case(day=1, predicted="1.00", actual="1.00"),
            _case(day=2, predicted="2.00", actual="2.00"),
        ),
        (
            _lag_24h_168h(day=2, predicted="2.00", actual="2.00"),
            _lag_24h_168h(day=1, predicted="1.00", actual="1.00"),
        ),
        _OUT_OF_ORDER_LAG_24H_168H_MESSAGE,
    )


def test_shifted_timestamps_fail_rather_than_realign() -> None:
    # Both cohorts are individually strictly chronological, so only positional
    # identity can fail. Overlapping timestamps must not be intersected.
    _assert_fails(
        (
            _case(day=2, predicted="1.00", actual="1.00"),
            _case(day=3, predicted="2.00", actual="2.00"),
        ),
        (
            _lag_24h_168h(day=1, predicted="1.00", actual="1.00"),
            _lag_24h_168h(day=2, predicted="2.00", actual="2.00"),
        ),
        _TIMESTAMP_MISMATCH_MESSAGE,
    )


def test_pairwise_timestamp_mismatch_fails_closed() -> None:
    _assert_fails(
        (_case(day=1, predicted="1.00", actual="1.00"),),
        (_lag_24h_168h(day=5, predicted="1.00", actual="1.00"),),
        _TIMESTAMP_MISMATCH_MESSAGE,
    )


def test_pairwise_actual_price_amount_mismatch_fails_closed() -> None:
    _assert_fails(
        (_case(day=1, predicted="1.00", actual="5.00"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="6.00"),),
        _ACTUAL_MISMATCH_MESSAGE,
    )


def test_actual_price_mismatch_message_contains_no_amount() -> None:
    error = _assert_fails(
        (_case(day=1, predicted="1.00", actual="111.11"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="222.22"),),
        _ACTUAL_MISMATCH_MESSAGE,
    )
    assert "111.11" not in error.message
    assert "222.22" not in error.message


def test_exact_decimal_actual_equality_succeeds_without_conversion() -> None:
    result = _compare(
        (_case(day=1, predicted="1.00", actual="0.10"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="0.1"),),
    )
    assert result.case_count == 1


def test_near_equal_actual_amounts_are_not_tolerated() -> None:
    _assert_fails(
        (_case(day=1, predicted="1.00", actual="0.1000000000000000000001"),),
        (_lag_24h_168h(day=1, predicted="1.00", actual="0.1"),),
        _ACTUAL_MISMATCH_MESSAGE,
    )


def test_persistence_evaluator_failure_propagates_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Every published persistence-evaluator guard is already proven by
    # alignment, so a sentinel failure proves the comparison neither wraps nor
    # swallows evaluator exceptions.
    sentinel = InvalidRequestError("persistence evaluator sentinel failure")

    def _failing_evaluator(*, cases: object) -> object:
        raise sentinel

    monkeypatch.setattr(
        persistence_vs_lag_24h_168h_ols_comparison,
        "evaluate_previous_day_persistence_mae",
        _failing_evaluator,
    )
    with pytest.raises(InvalidRequestError) as captured:
        _compare(
            (_case(day=1, predicted="1.00", actual="1.00"),),
            (_lag_24h_168h(day=1, predicted="1.00", actual="1.00"),),
        )
    assert captured.value is sentinel


def test_two_feature_evaluator_failure_propagates_unchanged() -> None:
    # Alignment passes (actuals agree), so the published two-feature
    # evaluator's own non-finite guard is what fails closed.
    _assert_fails(
        (_case(day=1, predicted="1.00", actual="1.00"),),
        (_lag_24h_168h(day=1, predicted="Infinity", actual="1.00"),),
        _LAG_24H_168H_EVALUATOR_NON_FINITE_MESSAGE,
    )


def test_metric_values_are_decimal_not_float() -> None:
    result = _compare(
        (_case(day=1, predicted="100.10", actual="200.33"),),
        (_lag_24h_168h(day=1, predicted="200.33", actual="200.33"),),
    )
    assert isinstance(result.persistence_mae_amount_per_mwh, Decimal)
    assert isinstance(result.lag_24h_168h_mae_amount_per_mwh, Decimal)
    assert not isinstance(result.persistence_mae_amount_per_mwh, float)
    assert not isinstance(result.lag_24h_168h_mae_amount_per_mwh, float)
    assert result.persistence_mae_amount_per_mwh == Decimal("100.23")
    assert result.lag_24h_168h_mae_amount_per_mwh == Decimal("0")


def test_input_cohorts_and_objects_are_not_modified() -> None:
    case = _case(day=1, predicted="10.00", actual="12.00")
    prediction = _lag_24h_168h(day=1, predicted="11.00", actual="12.00")
    persistence_cases = (case,)
    lag_24h_168h_predictions = (prediction,)
    _compare(persistence_cases, lag_24h_168h_predictions)
    assert persistence_cases == (case,)
    assert lag_24h_168h_predictions == (prediction,)
    assert persistence_cases[0] is case
    assert lag_24h_168h_predictions[0] is prediction
    assert case.predicted_price.amount_per_mwh == Decimal("10.00")
    assert case.actual_price.amount_per_mwh == Decimal("12.00")
    assert prediction.predicted_amount_per_mwh == Decimal("11.00")
    assert prediction.actual_amount_per_mwh == Decimal("12.00")
    assert prediction.market_id == "market-1"
    assert prediction.currency == "AMD"


def test_repeated_equivalent_calls_are_value_equivalent() -> None:
    persistence_cases = (
        _case(day=1, predicted="10.00", actual="12.00"),
        _case(day=2, predicted="20.00", actual="17.00"),
    )
    lag_24h_168h_predictions = (
        _lag_24h_168h(day=1, predicted="11.00", actual="12.00"),
        _lag_24h_168h(day=2, predicted="16.00", actual="17.00"),
    )
    assert _compare(persistence_cases, lag_24h_168h_predictions) == _compare(
        persistence_cases, lag_24h_168h_predictions
    )


def test_result_contract_is_frozen_slotted_and_exactly_four_fields_without_defaults() -> None:
    contract_fields = fields(DAMPricePersistenceVsLag24h168hOLSMAEComparison)
    names = tuple(item.name for item in contract_fields)
    assert names == FOUR_FIELDS
    assert DAMPricePersistenceVsLag24h168hOLSMAEComparison.__slots__ == names
    for item in contract_fields:
        assert item.default is MISSING
        assert item.default_factory is MISSING
    result = _compare(
        (_case(day=1, predicted="10.00", actual="12.00"),),
        (_lag_24h_168h(day=1, predicted="11.00", actual="12.00"),),
    )
    with pytest.raises(FrozenInstanceError):
        result.case_count = 99  # type: ignore[misc]


def test_result_exposes_no_winner_champion_or_improvement_fields() -> None:
    names = {item.name for item in fields(DAMPricePersistenceVsLag24h168hOLSMAEComparison)}
    assert names == set(FOUR_FIELDS)
    forbidden = {
        "market_id",
        "winner",
        "champion",
        "preferred_model",
        "best_model",
        "tie",
        "delta",
        "improvement",
        "percentage_improvement",
        "ratio",
        "threshold",
        "rank",
        "score",
        "confidence",
        "significance",
        "mse",
        "rmse",
        "mape",
        "metadata",
    }
    assert forbidden.isdisjoint(names)


def test_comparison_is_synchronous_and_keyword_only() -> None:
    assert not inspect.iscoroutinefunction(compare_dam_price_persistence_vs_lag_24h_168h_ols_mae)
    parameters = inspect.signature(compare_dam_price_persistence_vs_lag_24h_168h_ols_mae).parameters
    assert tuple(parameters) == ("persistence_cases", "lag_24h_168h_predictions")
    for parameter in parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty
