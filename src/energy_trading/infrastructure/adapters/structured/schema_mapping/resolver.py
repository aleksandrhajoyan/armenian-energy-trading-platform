"""Deterministic schema field resolver (infrastructure ACL).

Resolution pipeline for this chunk:

    raw header
    → Unicode normalization
    → exact canonical-name / alias matching
    → deterministic fuzzy matching
    → confidence / ambiguity / unresolved decision

A later optional infrastructure-local semantic/LLM resolver may run after this
path. It is not implemented here. The deterministic path must keep working
when no semantic resolver exists.

This module performs schema interpretation only. It does not read files,
construct canonical domain records, convert units, emit DLQ records, or
cross the application ingestion boundary.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from energy_trading.infrastructure.adapters.structured.schema_mapping.models import (
    CanonicalFieldCollision,
    CanonicalFieldSpec,
    FieldCandidate,
    FieldResolution,
    FieldResolutionMethod,
    FieldResolutionStatus,
    ResolverConfigurationError,
    SchemaResolution,
)
from energy_trading.infrastructure.adapters.structured.schema_mapping.normalization import (
    normalize_field_name,
)

_DEFAULT_FUZZY_THRESHOLD = 0.85
_DEFAULT_AMBIGUITY_MARGIN = 0.05


@dataclass(frozen=True, slots=True)
class _IndexedField:
    spec: CanonicalFieldSpec
    match_targets: tuple[tuple[str, str], ...]


class DeterministicFieldResolver:
    """Synchronous, provider-independent field/schema resolver.

    Mapping configuration is supplied by the caller. There is no global
    vendor alias catalog and no unit conversion.
    """

    def __init__(
        self,
        field_specs: Sequence[CanonicalFieldSpec],
        *,
        fuzzy_threshold: float = _DEFAULT_FUZZY_THRESHOLD,
        ambiguity_margin: float = _DEFAULT_AMBIGUITY_MARGIN,
    ) -> None:
        self._fuzzy_threshold = _require_unit_interval("fuzzy_threshold", fuzzy_threshold)
        self._ambiguity_margin = _require_unit_interval("ambiguity_margin", ambiguity_margin)
        self._specs = _freeze_specs(field_specs)
        self._fields, self._exact_lookup = _build_mapping_index(self._specs)

    @property
    def fuzzy_threshold(self) -> float:
        return self._fuzzy_threshold

    @property
    def ambiguity_margin(self) -> float:
        return self._ambiguity_margin

    def resolve_field(self, source_field: str) -> FieldResolution:
        """Resolve one raw source header to a canonical field, or fail closed."""

        source_field = _require_source_field(source_field)
        normalized = normalize_field_name(source_field)
        if not normalized:
            return _unresolved(source_field, normalized, confidence=0.0, candidates=())

        exact = self._exact_lookup.get(normalized)
        if exact is not None:
            canonical_name, matched_representation = exact
            candidate = FieldCandidate(
                canonical_field=canonical_name,
                confidence=1.0,
                matched_representation=matched_representation,
            )
            return FieldResolution(
                source_field=source_field,
                normalized_source_field=normalized,
                status=FieldResolutionStatus.RESOLVED,
                canonical_field=canonical_name,
                method=FieldResolutionMethod.EXACT,
                confidence=1.0,
                candidates=(candidate,),
            )

        ranked = self._rank_fuzzy_candidates(normalized)
        if not ranked:
            return _unresolved(source_field, normalized, confidence=0.0, candidates=())

        best = ranked[0]
        if best.confidence < self._fuzzy_threshold:
            return _unresolved(
                source_field,
                normalized,
                confidence=best.confidence,
                candidates=(best,),
            )

        credible = tuple(
            candidate for candidate in ranked if candidate.confidence >= self._fuzzy_threshold
        )
        if _is_ambiguous(credible, self._ambiguity_margin):
            relevant = _relevant_ambiguous_candidates(credible, self._ambiguity_margin)
            return FieldResolution(
                source_field=source_field,
                normalized_source_field=normalized,
                status=FieldResolutionStatus.AMBIGUOUS,
                canonical_field=None,
                method=None,
                confidence=best.confidence,
                candidates=relevant,
            )

        return FieldResolution(
            source_field=source_field,
            normalized_source_field=normalized,
            status=FieldResolutionStatus.RESOLVED,
            canonical_field=best.canonical_field,
            method=FieldResolutionMethod.FUZZY,
            confidence=best.confidence,
            candidates=(best,),
        )

    def resolve_schema(self, source_fields: Sequence[str]) -> SchemaResolution:
        """Resolve an ordered sequence of source headers.

        Reports missing required canonical fields and destination collisions.
        Does not choose a winning column when two headers map to one field.
        """

        if isinstance(source_fields, str):
            msg = "source_fields must be a sequence of header strings, not a single string"
            raise TypeError(msg)

        resolutions = tuple(self.resolve_field(name) for name in source_fields)
        resolved_sources: dict[str, list[str]] = {}
        for resolution in resolutions:
            if (
                resolution.status is FieldResolutionStatus.RESOLVED
                and resolution.canonical_field is not None
            ):
                resolved_sources.setdefault(resolution.canonical_field, []).append(
                    resolution.source_field
                )

        collisions = tuple(
            CanonicalFieldCollision(
                canonical_field=canonical_field,
                source_fields=tuple(source_names),
            )
            for canonical_field, source_names in sorted(resolved_sources.items())
            if len(source_names) > 1
        )
        resolved_canonicals = frozenset(resolved_sources)
        missing_required_fields = tuple(
            spec.canonical_name
            for spec in self._specs
            if spec.required and spec.canonical_name not in resolved_canonicals
        )
        return SchemaResolution(
            field_resolutions=resolutions,
            missing_required_fields=missing_required_fields,
            collisions=collisions,
        )

    def _rank_fuzzy_candidates(self, normalized_source: str) -> tuple[FieldCandidate, ...]:
        scored: list[FieldCandidate] = []
        for indexed in self._fields:
            best_score = -1.0
            best_representation = indexed.spec.canonical_name
            for normalized_target, original_representation in indexed.match_targets:
                score = SequenceMatcher(
                    a=normalized_source,
                    b=normalized_target,
                    autojunk=False,
                ).ratio()
                if score > best_score:
                    best_score = score
                    best_representation = original_representation
            scored.append(
                FieldCandidate(
                    canonical_field=indexed.spec.canonical_name,
                    confidence=best_score,
                    matched_representation=best_representation,
                )
            )
        scored.sort(key=lambda candidate: (-candidate.confidence, candidate.canonical_field))
        return tuple(scored)


def _freeze_specs(field_specs: object) -> tuple[CanonicalFieldSpec, ...]:
    if isinstance(field_specs, str) or not isinstance(field_specs, Sequence):
        msg = "field_specs must be a sequence of CanonicalFieldSpec values"
        raise TypeError(msg)
    specs = tuple(field_specs)
    if not all(isinstance(spec, CanonicalFieldSpec) for spec in specs):
        msg = "field_specs must contain CanonicalFieldSpec values"
        raise TypeError(msg)
    return specs


def _build_mapping_index(
    specs: tuple[CanonicalFieldSpec, ...],
) -> tuple[tuple[_IndexedField, ...], dict[str, tuple[str, str]]]:
    exact_lookup: dict[str, tuple[str, str]] = {}
    indexed_fields: list[_IndexedField] = []
    seen_canonical: dict[str, str] = {}

    for spec in specs:
        normalized_canonical = normalize_field_name(spec.canonical_name)
        if not normalized_canonical:
            msg = "canonical field name is empty after normalization"
            raise ResolverConfigurationError(msg)
        previous = seen_canonical.get(normalized_canonical)
        if previous is not None:
            msg = (
                "duplicate canonical field definition: "
                f"{spec.canonical_name!r} collides with {previous!r}"
            )
            raise ResolverConfigurationError(msg)
        seen_canonical[normalized_canonical] = spec.canonical_name
        _register_exact(
            exact_lookup,
            token=normalized_canonical,
            canonical_name=spec.canonical_name,
            matched_representation=spec.canonical_name,
        )

    for spec in specs:
        match_targets: list[tuple[str, str]] = [
            (normalize_field_name(spec.canonical_name), spec.canonical_name)
        ]
        seen_tokens = {match_targets[0][0]}
        for alias in spec.aliases:
            normalized_alias = normalize_field_name(alias)
            if not normalized_alias:
                msg = (
                    f"alias {alias!r} for canonical field {spec.canonical_name!r} "
                    "is empty after normalization"
                )
                raise ResolverConfigurationError(msg)
            _register_exact(
                exact_lookup,
                token=normalized_alias,
                canonical_name=spec.canonical_name,
                matched_representation=alias,
            )
            if normalized_alias not in seen_tokens:
                match_targets.append((normalized_alias, alias))
                seen_tokens.add(normalized_alias)
        indexed_fields.append(_IndexedField(spec=spec, match_targets=tuple(match_targets)))

    return tuple(indexed_fields), exact_lookup


def _register_exact(
    exact_lookup: dict[str, tuple[str, str]],
    *,
    token: str,
    canonical_name: str,
    matched_representation: str,
) -> None:
    existing = exact_lookup.get(token)
    if existing is None:
        exact_lookup[token] = (canonical_name, matched_representation)
        return
    existing_canonical, _existing_repr = existing
    if existing_canonical != canonical_name:
        msg = (
            f"normalized alias {token!r} is assigned to both "
            f"{existing_canonical!r} and {canonical_name!r}"
        )
        raise ResolverConfigurationError(msg)


def _require_unit_interval(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        msg = f"{name} must be a finite number in [0, 1]"
        raise ResolverConfigurationError(msg)
    number = float(value)
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        msg = f"{name} must be a finite number in [0, 1]"
        raise ResolverConfigurationError(msg)
    return number


def _is_ambiguous(credible: tuple[FieldCandidate, ...], ambiguity_margin: float) -> bool:
    if len(credible) < 2:
        return False
    return (credible[0].confidence - credible[1].confidence) < ambiguity_margin


def _relevant_ambiguous_candidates(
    credible: tuple[FieldCandidate, ...],
    ambiguity_margin: float,
) -> tuple[FieldCandidate, ...]:
    best_score = credible[0].confidence
    return tuple(
        candidate
        for candidate in credible
        if (best_score - candidate.confidence) < ambiguity_margin
    )


def _require_source_field(value: object) -> str:
    if not isinstance(value, str):
        msg = "source_field must be a string"
        raise TypeError(msg)
    return value


def _unresolved(
    source_field: str,
    normalized: str,
    *,
    confidence: float,
    candidates: tuple[FieldCandidate, ...],
) -> FieldResolution:
    return FieldResolution(
        source_field=source_field,
        normalized_source_field=normalized,
        status=FieldResolutionStatus.UNRESOLVED,
        canonical_field=None,
        method=None,
        confidence=confidence,
        candidates=candidates,
    )
