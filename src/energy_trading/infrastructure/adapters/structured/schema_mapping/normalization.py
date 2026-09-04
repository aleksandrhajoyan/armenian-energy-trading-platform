"""Deterministic Unicode field-name normalization.

This function is language-agnostic. It does not transliterate, translate, or
call external services. Armenian and other Unicode letters are preserved.
"""

from __future__ import annotations

import unicodedata

_LETTER_NUMBER_MARK_PREFIXES = ("L", "N", "M")


def normalize_field_name(value: str) -> str:
    """Normalize a raw external field/header for exact and fuzzy matching.

    Steps:

    1. Require a string at the public typed boundary.
    2. Unicode-normalize with NFKC.
    3. Strip surrounding whitespace.
    4. Apply Unicode-aware ``casefold()``.
    5. Treat non-letter/non-digit separators (``_``, ``-``, punctuation, runs
       of whitespace) as word separators.
    6. Collapse separator runs into a single ASCII space.
    7. Preserve Unicode letters and digits, including Armenian characters.
    """

    text = _require_str(value)
    normalized = unicodedata.normalize("NFKC", text).strip().casefold()
    pieces: list[str] = []
    for char in normalized:
        if unicodedata.category(char).startswith(_LETTER_NUMBER_MARK_PREFIXES):
            pieces.append(char)
        else:
            pieces.append(" ")
    return " ".join("".join(pieces).split())


def _require_str(value: object) -> str:
    if not isinstance(value, str):
        msg = "field name must be a string"
        raise TypeError(msg)
    return value
