"""Application-owned Consumer Load Forecast model inference boundary.

A future ``energy_trading.ml`` adapter structurally implements this protocol
and returns already-canonical ``LoadForecastPoint`` values. This module is the
only application-facing seam a future Consumer Load Forecast Agent may use
to obtain numerical load forecasts.

Ownership:

* Application: owns ``ConsumerLoadForecastModelPort`` and
  ``ConsumerLoadForecastModelRequest``.
* Future ML adapter: structurally implements the protocol. Model files,
  LightGBM/XGBoost/sklearn classes, vendor arrays, training
  configuration, and feature engineering remain ML-layer concerns. There is
  no ML base class and no generic ``ModelPort``.
* Historical observations reuse canonical ``ConsumptionRecord`` (load in MW).
  Forecast points reuse canonical ``LoadForecastPoint`` (predicted load in MW).
  This port does not convert MW to MWh or invent a second history schema.
* Agent construction, LangGraph, persistence, and training remain deferred.

Returned tuples are already canonical. An empty tuple is a valid successful
result. Tuple order is the order returned by the future implementation.
Expected unavailable backends use existing application errors such as
``DependencyUnavailableError``. There is no Consumer-Load-Forecast-specific
error hierarchy.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from energy_trading.domain.models.forecasting import LoadForecastPoint
from energy_trading.domain.models.observations import ConsumptionRecord
from energy_trading.domain.value_objects.quantities import EntityId
from energy_trading.domain.value_objects.time import UtcDateTime, to_utc


@dataclass(frozen=True, slots=True)
class ConsumerLoadForecastModelRequest:
    """Immutable model-inference request: consumer, MW history, and targets.

    This is an application orchestration DTO, not a domain entity and not a
    workflow snapshot. It carries no model path, hyperparameters, provider,
    feature registry, weather series, or persistence handles.

    ``consumer_id`` identifies the consumer being forecast and is required even
    when ``history`` is empty. Identity is never inferred from observations.
    ``history`` reuses existing ``ConsumptionRecord`` values whose quantity is
    load/power in MW; when present, every record must belong to that same
    consumer. ``target_timestamps`` are explicit timezone-aware UTC instants;
    an integer horizon such as ``24`` is not a substitute.
    """

    consumer_id: EntityId
    history: tuple[ConsumptionRecord, ...]
    target_timestamps: tuple[UtcDateTime, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "consumer_id", _require_non_empty("consumer_id", self.consumer_id))
        history = _require_consumption_records(self.history)
        _require_history_matches_consumer(self.consumer_id, history)
        object.__setattr__(self, "history", history)
        object.__setattr__(
            self,
            "target_timestamps",
            _require_target_timestamps(self.target_timestamps),
        )


class ConsumerLoadForecastModelPort(Protocol):
    """Application-owned port for Consumer Load Forecast numerical inference.

    ML implementations satisfy this protocol structurally. The application
    depends on the protocol, never on a concrete model class, trainer, or
    vendor runtime.

    ``forecast`` accepts only ``ConsumerLoadForecastModelRequest``. It must not
    accept vendor arrays, model paths, hyperparameters, provider names,
    cache keys, or persistence handles.

    Conforming implementations:

    * return ``tuple[LoadForecastPoint, ...]``
    * treat an empty result tuple as a valid successful outcome
    * must not convert MW history into MWh or invent missing points
    * must not call an LLM to calculate the numeric forecast

    Unavailable or unusable model backends become sanitized
    ``DependencyUnavailableError``. Invalid request shapes fail closed during
    DTO construction. Retries and fallback belong to later orchestration.
    """

    async def forecast(
        self,
        *,
        request: ConsumerLoadForecastModelRequest,
    ) -> tuple[LoadForecastPoint, ...]:
        """Return canonical MW load forecast points for one request."""
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


def _require_consumption_records(value: object) -> tuple[ConsumptionRecord, ...]:
    if not isinstance(value, tuple):
        msg = "history must be an immutable tuple"
        raise TypeError(msg)
    if not all(isinstance(item, ConsumptionRecord) for item in value):
        msg = "history must contain ConsumptionRecord values"
        raise TypeError(msg)
    return value


def _require_history_matches_consumer(
    consumer_id: str,
    history: tuple[ConsumptionRecord, ...],
) -> None:
    if any(item.consumer_id != consumer_id for item in history):
        msg = "history consumer_id must match request consumer_id"
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
