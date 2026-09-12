"""Application-owned DAM Price Forecast model inference boundary.

A future ``energy_trading.ml`` adapter structurally implements this protocol
and returns already-canonical ``PriceForecastPoint`` values. This module is the
only application-facing seam a future DAM Price Forecast Agent may use to
obtain numerical market-price forecasts.

Ownership:

* Application: owns ``DAMPriceForecastModelPort`` and
  ``DAMPriceForecastModelRequest``.
* Future ML adapter: structurally implements the protocol. Model files,
  LightGBM/XGBoost/sklearn classes, vendor arrays, training
  configuration, and feature engineering remain ML-layer concerns. There is
  no ML base class and no generic ``ModelPort``.
* Historical observations reuse canonical ``MarketPriceRecord``. Forecast
  points reuse canonical ``PriceForecastPoint``. Currency is explicit
  ``CurrencyCode`` on both sides. This port does not convert currencies or
  invent a second price schema.
* Agent construction, LangGraph, persistence, and training remain deferred.

Returned tuples are already canonical. An empty tuple is a valid successful
result. Tuple order is the order returned by the future implementation.
Expected unavailable backends use existing application errors such as
``DependencyUnavailableError``. There is no DAM-Price-Forecast-specific
error hierarchy.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from energy_trading.domain.models.forecasting import PriceForecastPoint
from energy_trading.domain.models.observations import MarketPriceRecord
from energy_trading.domain.value_objects.quantities import CurrencyCode, EntityId
from energy_trading.domain.value_objects.time import UtcDateTime, to_utc


@dataclass(frozen=True, slots=True)
class DAMPriceForecastModelRequest:
    """Immutable model-inference request: market, currency, history, targets.

    This is an application orchestration DTO, not a domain entity and not a
    workflow snapshot. It carries no model path, hyperparameters, provider,
    feature registry, load series, or persistence handles.

    ``market_id`` identifies the market being forecast and is required even
    when ``history`` is empty. ``currency`` is the explicit target
    ``CurrencyCode`` and is likewise required when history is empty. Neither
    identity is inferred from observations. ``history`` reuses existing
    ``MarketPriceRecord`` values; when present, every record must belong to
    that same market and carry that same currency. ``target_timestamps`` are
    explicit timezone-aware UTC instants; an integer horizon such as ``24``
    is not a substitute.
    """

    market_id: EntityId
    currency: CurrencyCode
    history: tuple[MarketPriceRecord, ...]
    target_timestamps: tuple[UtcDateTime, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "market_id", _require_non_empty("market_id", self.market_id))
        object.__setattr__(self, "currency", _require_currency_code(self.currency))
        history = _require_market_price_records(self.history)
        _require_history_matches_market(self.market_id, history)
        _require_history_matches_currency(self.currency, history)
        object.__setattr__(self, "history", history)
        object.__setattr__(
            self,
            "target_timestamps",
            _require_target_timestamps(self.target_timestamps),
        )


class DAMPriceForecastModelPort(Protocol):
    """Application-owned port for DAM Price Forecast numerical inference.

    ML implementations satisfy this protocol structurally. The application
    depends on the protocol, never on a concrete model class, trainer, or
    vendor runtime.

    ``forecast`` accepts only ``DAMPriceForecastModelRequest``. It must not
    accept vendor arrays, model paths, hyperparameters, provider names,
    cache keys, or persistence handles.

    Conforming implementations:

    * return ``tuple[PriceForecastPoint, ...]``
    * treat an empty result tuple as a valid successful outcome
    * must not convert currencies or invent missing points
    * must not call an LLM to calculate the numeric forecast

    Unavailable or unusable model backends become sanitized
    ``DependencyUnavailableError``. Invalid request shapes fail closed during
    DTO construction. Retries and fallback belong to later orchestration.
    """

    async def forecast(
        self,
        *,
        request: DAMPriceForecastModelRequest,
    ) -> tuple[PriceForecastPoint, ...]:
        """Return canonical market-price forecast points for one request."""
        ...


def _require_non_empty(field_name: str, value: object) -> str:
    if not isinstance(value, str):
        msg = f"{field_name} must be a string"
        raise TypeError(msg)
    cleaned = value.strip()
    if not cleaned:
        msg = f"{field_name} must be a non-empty string"
        raise ValueError(msg)
    return cleaned


def _require_currency_code(value: object) -> str:
    if not isinstance(value, str):
        msg = "currency must be a string"
        raise TypeError(msg)
    if len(value) != 3 or not value.isascii() or not value.isalpha() or not value.isupper():
        msg = "currency must be a three-letter uppercase currency code"
        raise ValueError(msg)
    return value


def _require_market_price_records(value: object) -> tuple[MarketPriceRecord, ...]:
    if not isinstance(value, tuple):
        msg = "history must be an immutable tuple"
        raise TypeError(msg)
    if not all(isinstance(item, MarketPriceRecord) for item in value):
        msg = "history must contain MarketPriceRecord values"
        raise TypeError(msg)
    return value


def _require_history_matches_market(
    market_id: str,
    history: tuple[MarketPriceRecord, ...],
) -> None:
    if any(item.market_id != market_id for item in history):
        msg = "history market_id must match request market_id"
        raise ValueError(msg)


def _require_history_matches_currency(
    currency: str,
    history: tuple[MarketPriceRecord, ...],
) -> None:
    if any(item.price.currency != currency for item in history):
        msg = "history currency must match request currency"
        raise ValueError(msg)


def _require_aware_utc(field_name: str, value: object) -> datetime:
    if not isinstance(value, datetime):
        msg = f"{field_name} must be a datetime"
        raise TypeError(msg)
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        msg = f"{field_name} must be timezone-aware"
        raise ValueError(msg)
    return to_utc(value)


def _require_target_timestamps(value: object) -> tuple[datetime, ...]:
    if not isinstance(value, tuple):
        msg = "target_timestamps must be an immutable tuple"
        raise TypeError(msg)
    if len(value) < 1:
        msg = "target_timestamps must contain at least one timestamp"
        raise ValueError(msg)
    return tuple(_require_aware_utc("target_timestamps", item) for item in value)
