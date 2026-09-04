"""Shared Pydantic configuration for canonical domain models."""

from pydantic import BaseModel, ConfigDict


class CanonicalModel(BaseModel):
    """Immutable canonical contract with explicit validation.

    Unknown fields are rejected. String whitespace is stripped. Numeric
    finiteness is enforced on constrained field types, not via business rules.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )
