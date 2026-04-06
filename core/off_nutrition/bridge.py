"""
Bridge helpers: rebuild NutritionInput streams from unified wire payloads.

RU: Восстановление потоков NutritionInput из сериализованных unified-снимков.
EN: Rebuild NutritionInput streams from unified wire snapshots for OFF↔catalog merge.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import NutritionInput, NutritionResolved
from .resolver import is_valid_nutrient_scalar, resolve_nutrition


def nutrition_inputs_from_unified_wire(
    *,
    nutrition_inputs_wire: Sequence[Mapping[str, Any]],
    nutrients_per_100g: Mapping[str, float],
    fallback_source: str,
    record_id: str | None,
    version_ref: str | None = None,
) -> list[NutritionInput]:
    """
    RU: Строит NutritionInput из nutrition_inputs JSON + fallback на flat нутриенты.
    EN: Builds NutritionInput list from wire rows with flat nutrient fallback.
    """

    out: list[NutritionInput] = []
    for wire in nutrition_inputs_wire:
        if not isinstance(wire, Mapping):
            continue
        src = str(wire.get("source") or fallback_source)
        raw_nut = wire.get("nutrients")
        if not isinstance(raw_nut, Mapping):
            continue
        nutrients: dict[str, float] = {}
        for k, v in raw_nut.items():
            if is_valid_nutrient_scalar(v):
                nutrients[str(k)] = float(v)
        if not nutrients:
            continue
        rid_raw = wire.get("record_id")
        rid_str = None if rid_raw is None else str(rid_raw)
        vr_raw = wire.get("version_ref")
        vr_str = None if vr_raw is None else str(vr_raw)
        raw_pl = wire.get("raw_payload")
        raw_payload: dict[str, Any] = dict(raw_pl) if isinstance(raw_pl, Mapping) else {}
        out.append(
            NutritionInput(
                source=src,
                nutrients=nutrients,
                record_id=rid_str,
                version_ref=vr_str,
                raw_payload=raw_payload,
            )
        )
    if not out:
        nutrients_fb = {
            str(k): float(v) for k, v in nutrients_per_100g.items() if is_valid_nutrient_scalar(v)
        }
        out.append(
            NutritionInput(
                source=fallback_source,
                nutrients=nutrients_fb,
                record_id=record_id,
                version_ref=version_ref,
                raw_payload={},
            )
        )
    return out


def merge_wire_nutrition_sources(
    *,
    primary_inputs: Sequence[NutritionInput],
    secondary_inputs: Sequence[NutritionInput],
    nutrient_keys: Sequence[str] | None = None,
) -> NutritionResolved:
    """
    RU: Детерминированный merge двух потоков через resolve_nutrition.
    EN: Deterministic merge of two streams via resolve_nutrition.
    """

    combined = list(primary_inputs) + list(secondary_inputs)
    return resolve_nutrition(inputs=combined, nutrient_keys=nutrient_keys)
