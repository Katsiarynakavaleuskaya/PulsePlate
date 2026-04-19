"""
Nutrition resolver.

RU: Детерминированный resolver для provenance/confidence питания.
EN: Deterministic nutrition resolver for provenance and confidence.
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence

from .contracts import NutritionInput, NutritionResolved

DEFAULT_SOURCE_PRIORITY: tuple[str, ...] = ("label", "producer", "usda", "estimate")
SOURCE_CONFIDENCE_WEIGHTS: Mapping[str, float] = {
    "label": 1.0,
    "producer": 0.9,
    "usda": 0.7,
    "estimate": 0.4,
}
DEFAULT_SOURCE_CONFIDENCE = 0.3


def _normalize_source_name(source: str) -> str:
    normalized = source.strip().lower()
    if normalized in {"open food facts", "off"}:
        # Legacy OFF rows do not yet expose the new upstream nutrition_inputs source
        # taxonomy, so treat them conservatively until upstream provenance is present.
        return "estimate"
    if normalized.startswith("merged("):
        return "estimate"
    return normalized


def _is_valid_numeric(value: object) -> bool:
    # bool is a subclass of int; reject it so True/False cannot masquerade as nutrients.
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    as_float = float(value)
    return math.isfinite(as_float) and as_float >= 0.0


def is_valid_nutrient_scalar(value: object) -> bool:
    """Return True when *value* is a finite, non-negative numeric nutrient scalar."""
    return _is_valid_numeric(value)


def _iter_priority_order(
    inputs: Sequence[NutritionInput],
    source_priority: Sequence[str],
) -> list[NutritionInput]:
    priority_index = {name: idx for idx, name in enumerate(source_priority)}
    return sorted(
        inputs,
        key=lambda item: (
            priority_index.get(_normalize_source_name(item.source), len(priority_index)),
            _normalize_source_name(item.source),
            item.record_id or "",
        ),
    )


def resolve_nutrition(
    inputs: Sequence[NutritionInput],
    nutrient_keys: Sequence[str] | None = None,
    source_priority: Sequence[str] | None = None,
) -> NutritionResolved:
    """
    Resolve nutrients from prioritized source inputs.

    RU: Разрешает нутриенты по приоритету источников.
    EN: Resolves nutrients using explicit source priority.
    """

    ordered_inputs = _iter_priority_order(inputs, source_priority or DEFAULT_SOURCE_PRIORITY)
    keys: list[str]
    if nutrient_keys is None:
        discovered = {key for entry in ordered_inputs for key in entry.nutrients}
        keys = sorted(discovered)
    else:
        keys = list(dict.fromkeys(nutrient_keys))

    resolved: dict[str, float] = {}
    provenance: dict[str, str] = {}
    nutrient_confidence: dict[str, float] = {}

    for nutrient in keys:
        for entry in ordered_inputs:
            if nutrient not in entry.nutrients:
                continue
            value = entry.nutrients[nutrient]
            if not _is_valid_numeric(value):
                continue
            source_name = _normalize_source_name(entry.source)
            resolved[nutrient] = float(value)
            provenance[nutrient] = source_name
            nutrient_confidence[nutrient] = SOURCE_CONFIDENCE_WEIGHTS.get(
                source_name,
                DEFAULT_SOURCE_CONFIDENCE,
            )
            break

    confidence = 0.0
    if nutrient_confidence:
        confidence = round(sum(nutrient_confidence.values()) / len(nutrient_confidence), 4)

    return NutritionResolved(
        nutrients=resolved,
        provenance=provenance,
        nutrient_confidence=nutrient_confidence,
        confidence=confidence,
        raw_inputs=tuple(ordered_inputs),
    )


def project_scalar_compat(
    resolved: NutritionResolved,
    required_keys: Sequence[str] | None = None,
) -> dict[str, float]:
    """
    Produce additive-compatible scalar nutrient payload.

    RU: Строит совместимый flat payload для старых scalar consumers.
    EN: Produces a flat compatibility payload for legacy scalar consumers.
    """

    result = {key: float(value) for key, value in resolved.nutrients.items()}
    for nutrient in required_keys or ():
        result.setdefault(nutrient, 0.0)
    return result
