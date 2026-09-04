"""Generic regulatory constraint contract. Official PSRC structures are not encoded."""

from datetime import date
from typing import Self

from pydantic import model_validator

from energy_trading.domain.models.base import CanonicalModel
from energy_trading.domain.value_objects.quantities import (
    CurrencyCode,
    EntityId,
    FiniteNumber,
    NonEmptyString,
)


class RegulatoryConstraint(CanonicalModel):
    """Structured constraint derived from regulation or licenses.

    Numeric limits and effective dates are carried as data. No Armenian DAM
    tariffs, network costs, or PSRC identifiers are hardcoded.
    """

    constraint_id: EntityId
    constraint_type: NonEmptyString
    description: NonEmptyString
    effective_from: date
    effective_to: date | None = None
    minimum_value: FiniteNumber | None = None
    maximum_value: FiniteNumber | None = None
    unit: NonEmptyString | None = None
    currency: CurrencyCode | None = None
    source_document_id: EntityId | None = None

    @model_validator(mode="after")
    def validate_windows_and_bounds(self) -> Self:
        if self.effective_to is not None and self.effective_to < self.effective_from:
            msg = "effective_to must be greater than or equal to effective_from"
            raise ValueError(msg)
        if (
            self.minimum_value is not None
            and self.maximum_value is not None
            and self.minimum_value > self.maximum_value
        ):
            msg = "minimum_value must be less than or equal to maximum_value"
            raise ValueError(msg)
        return self
