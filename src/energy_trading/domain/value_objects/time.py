"""Canonical timezone-aware UTC timestamps."""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, PlainSerializer


def to_utc(value: datetime) -> datetime:
    """Normalize an aware datetime to UTC. Naive values never reach this helper."""

    return value.astimezone(UTC)


def utc_isoformat(value: datetime) -> str:
    """Serialize UTC datetimes with an explicit +00:00 offset."""

    return to_utc(value).isoformat()


UtcDateTime = Annotated[
    AwareDatetime,
    AfterValidator(to_utc),
    PlainSerializer(utc_isoformat, return_type=str, when_used="json"),
]
