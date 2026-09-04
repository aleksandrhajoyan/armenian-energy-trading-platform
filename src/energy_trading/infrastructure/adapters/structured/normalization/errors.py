"""Infrastructure-only errors for structured source normalization.

These types carry no HTTP semantics and must not include raw payload values.
"""


class NormalizationError(Exception):
    """Base ACL normalization failure."""

    def __init__(self, message: str) -> None:
        cleaned = message.strip()
        if not cleaned:
            msg = "NormalizationError message must be a non-empty string"
            raise ValueError(msg)
        self.message = cleaned
        super().__init__(cleaned)


class NormalizationConfigurationError(NormalizationError):
    """Invalid adapter normalization configuration. Fail at construction."""


class SourceValueNormalizationError(NormalizationError):
    """A source cell cannot be normalized. Isolate the row."""
