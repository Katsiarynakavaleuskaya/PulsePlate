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

# Micro nutrients list
MICROS = ["Fe_mg", "Ca_mg", "VitD_IU", "B12_ug", "Folate_ug", "Iodine_ug", "K_mg", "Mg_mg"]


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
        # Merge macronutrients using median
        kcal = _merge_values([r.kcal for r in rows])
        protein = _merge_values([r.protein_g for r in rows])
        fat = _merge_values([r.fat_g for r in rows])
        carbs = _merge_values([r.carbs_g for r in rows])
        fiber = _merge_values([r.fiber_g for r in rows])

        # Priority for micronutrients: if USDA present, take from USDA, otherwise median
        def micro_pick(key: str) -> float:
            # Get values from USDA source first
            usda_vals = [getattr(r, key) for r in rows if r.source == "USDA"]
            usda_vals = [v for v in usda_vals if v is not None and v >= 0]

            if usda_vals:
                # If we have USDA values, use median of USDA values
                return _merge_values(usda_vals, "median")

            # Otherwise, use median of all values
            all_vals = [getattr(r, key) for r in rows]
            all_vals = [v for v in all_vals if v is not None and v >= 0]
            return _merge_values(all_vals, "median")

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
            "kcal": round(kcal, 1),
            "protein_g": round(protein, 2),
            "fat_g": round(fat, 2),
            "carbs_g": round(carbs, 2),
            "fiber_g": round(fiber, 2),
            **{k: round(micro_pick(k), 3) for k in MICROS},
            "flags": list(sorted(all_flags)),
            "price": 0.0,  # Can be populated from OFF later
            "source": "MERGED(" + ",".join(sources) + ")",
            "version_date": today,
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
    protein_pct = (record["protein_g"] * 4 / max(1, record["kcal"])) * 100 if record["kcal"] > 0 else 0
    fat_pct = (record["fat_g"] * 9 / max(1, record["kcal"])) * 100 if record["kcal"] > 0 else 0
    carb_pct = (record["carbs_g"] * 4 / max(1, record["kcal"])) * 100 if record["kcal"] > 0 else 0

    # High protein foods (>15% of calories from protein)
    if protein_pct > 15:
        if record["fat_g"] > 5:  # High fat protein (e.g., nuts, seeds)
            return "protein"
        else:  # Lean protein (e.g., chicken, fish)
            return "protein"

    # High fat foods (>30% of calories from fat)
    if fat_pct > 30:
        return "fat"

    # High carb foods (>50% of calories from carbs)
    if carb_pct > 50:
        if record["fiber_g"] > 3:  # High fiber carbs (e.g., whole grains, legumes)
            if "legume" in record["name"] or any(legume in record["name"] for legume in ["lentil", "bean", "chickpea"]):
                return "legume"
            return "grain"
        elif record["sugar_g"] > 10 if "sugar_g" in record else False:  # High sugar carbs
            return "fruit"
        else:  # Starchy carbs
            return "grain"

    # Vegetables (moderate carbs, high fiber, low calories)
    if record["fiber_g"] > 2 and record["kcal"] < 100:
        return "veg"

    # Fruits (moderate carbs, natural sugars)
    if record["sugar_g"] > 5 if "sugar_g" in record else False:
        return "fruit"

    # Dairy (if has dairy flags)
    if any("DAIRY" in flag for flag in record["flags"]):
        return "dairy"

    # Default classification
    return "other"
