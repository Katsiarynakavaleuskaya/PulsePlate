"""
Food Data Merge Logic

RU: Логика мерджа данных о продуктах.
EN: Food data merge logic.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from statistics import median
from typing import Dict, Iterable, List

from .food_sources.base import FoodRecord
from .off_nutrition import (
    NutritionInput,
    is_valid_nutrient_scalar,
    project_scalar_compat,
    resolve_nutrition,
)

# Micro nutrients list
MICROS = [
    "Fe_mg",
    "Ca_mg",
    "VitD_IU",
    "B12_ug",
    "Folate_ug",
    "Iodine_ug",
    "K_mg",
    "Mg_mg",
]
MERGED_NUTRIENT_KEYS = ["kcal", "protein_g", "fat_g", "carbs_g", "fiber_g", *MICROS]


def _merge_values(values: List[float], strategy: str = "median") -> float:
    """
    RU: Объединить значения по стратегии.
    EN: Merge values by strategy.

    Args:
        values: List of values to merge
        strategy: Merge strategy ("median" or "first")

    Returns:
        Merged value
    """
    vals = [v for v in values if v is not None and v >= 0]
    if not vals:
        return 0.0
    if strategy == "median":
        return float(median(vals))
    return float(vals[0])


def merge_records(streams: List[Iterable[FoodRecord]]) -> List[Dict]:
    """
    RU: Объединить записи из нескольких источников.
    EN: Merge records from multiple sources.

    Args:
        streams: List of iterables with FoodRecord objects

    Returns:
        List of merged food records as dictionaries
    """
    # Group records by canonical name
    bucket: Dict[str, List[FoodRecord]] = defaultdict(list)
    for stream in streams:
        for rec in stream:
            bucket[rec.name].append(rec)

    merged: List[Dict] = []
    today = date.today().isoformat()

    for name, rows in bucket.items():
        nutrition_inputs = [
            NutritionInput(
                source=r.source,
                record_id=r.name,
                version_ref=r.version_date,
                nutrients={
                    key: float(value)
                    for key, value in {
                        "kcal": r.kcal,
                        "protein_g": r.protein_g,
                        "fat_g": r.fat_g,
                        "carbs_g": r.carbs_g,
                        "fiber_g": r.fiber_g,
                        "Fe_mg": r.Fe_mg,
                        "Ca_mg": r.Ca_mg,
                        "VitD_IU": r.VitD_IU,
                        "B12_ug": r.B12_ug,
                        "Folate_ug": r.Folate_ug,
                        "Iodine_ug": r.Iodine_ug,
                        "K_mg": r.K_mg,
                        "Mg_mg": r.Mg_mg,
                    }.items()
                    if is_valid_nutrient_scalar(value)
                },
                raw_payload={},
            )
            for r in rows
        ]
        resolved = resolve_nutrition(inputs=nutrition_inputs, nutrient_keys=MERGED_NUTRIENT_KEYS)
        compat = project_scalar_compat(resolved, required_keys=MERGED_NUTRIENT_KEYS)
        has_usda_source = any(r.source == "USDA" for r in rows)

        # Preserve legacy median merge behavior for macronutrients until API clients
        # are upgraded to consume per-field provenance directly.
        compat["kcal"] = round(_merge_values([r.kcal for r in rows]), 1)
        compat["protein_g"] = round(_merge_values([r.protein_g for r in rows]), 2)
        compat["fat_g"] = round(_merge_values([r.fat_g for r in rows]), 2)
        compat["carbs_g"] = round(_merge_values([r.carbs_g for r in rows]), 2)
        compat["fiber_g"] = round(_merge_values([r.fiber_g for r in rows]), 2)
        if not has_usda_source:
            # Legacy median path: _merge_values already drops None and negative values
            # (same semantics as the retired micro_pick helper).
            for micro_key in MICROS:
                compat[micro_key] = _merge_values([getattr(r, micro_key) for r in rows])

        # Collect all flags
        all_flags = set()
        for r in rows:
            if r.flags:
                all_flags.update(r.flags)

        # Determine primary source for logging
        sources = sorted({r.source for r in rows})

        out = {
            "name": name,
            "group": "other",  # Will be determined by classification logic
            "per_g": 100.0,
            "kcal": compat["kcal"],
            "protein_g": compat["protein_g"],
            "fat_g": compat["fat_g"],
            "carbs_g": compat["carbs_g"],
            "fiber_g": compat["fiber_g"],
            **{k: round(compat[k], 3) for k in MICROS},
            "flags": list(sorted(all_flags)),
            "price": 0.0,  # Can be populated from OFF later
            "source": "MERGED(" + ",".join(sources) + ")",
            "version_date": today,
            "nutrition_inputs": [entry.to_dict() for entry in resolved.raw_inputs],
            "nutrition_provenance": dict(resolved.provenance),
            "nutrition_confidence": resolved.confidence,
        }
        merged.append(out)

    # Classify food groups based on macronutrient profile
    for record in merged:
        record["group"] = _classify_food_group(record)

    return merged


def _classify_food_group(record: Dict) -> str:
    """
    RU: Классифицировать продукт по группе на основе профиля макронутриентов.
    EN: Classify food by group based on macronutrient profile.

    Args:
        record: Food record dictionary

    Returns:
        Food group classification
    """
    protein_g = record.get("protein_g", 0)
    fat_g = record.get("fat_g", 0)
    carbs_g = record.get("carbs_g", 0)
    fiber_g = record.get("fiber_g", 0)
    kcal = record.get("kcal", 0)
    sugar_g = record.get("sugar_g", 0)
    flags = record.get("flags", [])
    name = record.get("name", "")

    protein_pct = (protein_g * 4 / max(1, kcal)) * 100 if kcal > 0 else 0
    fat_pct = (fat_g * 9 / max(1, kcal)) * 100 if kcal > 0 else 0
    carb_pct = (carbs_g * 4 / max(1, kcal)) * 100 if kcal > 0 else 0

    # High protein foods (>15% of calories from protein)
    if protein_pct > 15:
        if fat_g > 5:  # High fat protein (e.g., nuts, seeds)
            return "protein"
        else:  # Lean protein (e.g., chicken, fish)
            return "protein"

    # High fat foods (>30% of calories from fat)
    if fat_pct > 30:
        return "fat"

    # High carb foods (>50% of calories from carbs)
    if carb_pct > 50:
        if fiber_g > 3:  # High fiber carbs (e.g., whole grains, legumes)
            if "legume" in name or any(legume in name for legume in ["lentil", "bean", "chickpea"]):
                return "legume"
            return "grain"
        elif sugar_g > 10:  # High sugar carbs
            return "fruit"
        else:  # Starchy carbs
            return "grain"

    # Vegetables (moderate carbs, high fiber, low calories)
    if fiber_g > 2 and kcal < 100:
        return "veg"

    # Fruits (moderate carbs, natural sugars)
    if sugar_g > 5:
        return "fruit"

    # Dairy (if has dairy flags)
    if any("DAIRY" in flag for flag in flags):
        return "dairy"

    # Default classification
    return "other"
