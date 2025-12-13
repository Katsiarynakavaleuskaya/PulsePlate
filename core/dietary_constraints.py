"""
Dietary Constraints - Diet Flag Processing and Recipe Compatibility

RU: Модуль обработки диетических ограничений и совместимости рецептов.
EN: Module for processing dietary restrictions and recipe compatibility.

This module handles dietary flags (VEGAN, KETO, PALEO, etc.) and ensures
recipes and meal plans comply with user's dietary preferences and restrictions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Set

from core.targets import (
    DEFAULT_CARB_FLOOR_G,
    HIGH_PROTEIN_MIN_G_PER_KG,
    KETO_CARB_FLOOR_G,
    KETO_MAX_CARB_PERCENT,
    LOW_CARB_CARB_FLOOR_G,
    LOW_CARB_MAX_PERCENT,
    LOW_FAT_MAX_PERCENT,
    MEDITERRANEAN_FAT_MIN_PERCENT,
    MEDITERRANEAN_FIBER_MIN_G,
    MIN_HEALTHY_FAT_ABSOLUTE_G,
    MIN_HEALTHY_FAT_G_PER_KG,
    MIN_PROTEIN_ABSOLUTE_G,
    MIN_PROTEIN_G_PER_KG,
)

# Diet flag constants
DIET_FLAGS = {
    # Dietary patterns
    "VEGAN": "Fully plant-based, no animal products",
    "VEG": "Vegetarian, includes dairy and eggs",
    "KETO": "Ketogenic, very low carb (<50g), high fat",
    "PALEO": "Paleo, no grains/legumes/dairy",
    "MEDITERRANEAN": "Mediterranean diet, high healthy fats",
    # Restrictions
    "GF": "Gluten-free",
    "DAIRY_FREE": "No dairy products",
    "NUT_FREE": "No tree nuts or peanuts",
    "SOY_FREE": "No soy products",
    # Preferences
    "LOW_CARB": "Reduced carbohydrate intake",
    "HIGH_PROTEIN": "Increased protein intake",
    "LOW_FAT": "Reduced fat intake",
    "LOW_COST": "Budget-friendly options",
}

# Incompatible diet flag combinations
INCOMPATIBLE_COMBINATIONS = [
    {"LOW_FAT", "KETO"},
    {"LOW_FAT", "MEDITERRANEAN"},
    {"VEGAN", "PALEO"},  # Paleo restricts legumes which are vegan protein source
]

# Diet implications (flags that imply other flags)
DIET_IMPLICATIONS = {
    "VEGAN": {"VEG", "DAIRY_FREE"},
    "KETO": {"LOW_CARB", "HIGH_PROTEIN"},
    "PALEO": {"HIGH_PROTEIN", "GF", "DAIRY_FREE"},
}

# Non-vegan food indicators (for recipe compatibility checks)
NON_VEGAN_INDICATORS = {
    "курица",
    "chicken",
    "лосось",
    "salmon",
    "рыба",
    "fish",
    "мясо",
    "meat",
    "молоко",
    "milk",
    "яйцо",
    "egg",
    "сыр",
    "cheese",
}

# Non-vegetarian food indicators (for recipe compatibility checks)
NON_VEG_INDICATORS = {
    "курица",
    "chicken",
    "лосось",
    "salmon",
    "рыба",
    "fish",
    "мясо",
    "meat",
    "beef",
    "pork",
}

# Gluten indicators for GF compatibility checks
GLUTEN_INDICATORS = {"глютен", "gluten", "пшеница", "wheat", "овсянка", "oats"}

# Dairy indicators for DAIRY_FREE compatibility checks
DAIRY_INDICATORS = {"молоко", "milk", "сыр", "cheese", "йогурт", "yogurt", "творог"}

# Nut indicators for NUT_FREE compatibility checks
NUT_INDICATORS = {"орех", "nut", "миндаль", "almond", "арахис", "peanut"}

# Soy indicators for SOY_FREE compatibility checks
SOY_INDICATORS = {"соя", "soy", "тофу", "tofu", "эдамаме", "edamame"}


@dataclass
class NormalizedDietFlags:
    """
    RU: Результат нормализации диетических флагов.
    EN: Result of diet flags normalization.

    Attributes:
        flags: Normalized set of diet flags
        overridden_flags: Flags that were removed due to conflicts
        conflicts_resolved: List of conflict resolutions (winner, losers)
    """

    flags: Set[str]
    overridden_flags: Set[str]
    conflicts_resolved: list[tuple[str, Set[str]]]  # (chosen_diet, removed_flags)


def normalize_diet_flags(diet_flags: Set[str]) -> Set[str]:
    """
    RU: Нормализует диетические флаги, разрешая конфликты и добавляя импликации.
    EN: Normalizes diet flags by resolving conflicts and adding implications.

    Args:
        diet_flags: Raw set of diet flags from user

    Returns:
        Normalized set of diet flags (for backward compatibility)

    Note:
        Use normalize_diet_flags_detailed() to get information about overridden flags.

    Examples:
        >>> normalize_diet_flags({"VEGAN"})
        {'VEGAN', 'VEG', 'DAIRY_FREE'}
        >>> normalize_diet_flags({"KETO", "LOW_FAT"})
        {'KETO', 'LOW_CARB', 'HIGH_PROTEIN'}
    """
    result = normalize_diet_flags_detailed(diet_flags)
    return result.flags


def normalize_diet_flags_detailed(diet_flags: Set[str]) -> NormalizedDietFlags:
    """
    RU: Нормализует диетические флаги с детальной информацией о конфликтах.
    EN: Normalizes diet flags with detailed conflict information.

    Args:
        diet_flags: Raw set of diet flags from user

    Returns:
        NormalizedDietFlags with flags, overridden_flags, and conflicts_resolved

    Examples:
        >>> result = normalize_diet_flags_detailed({"VEGAN"})
        >>> result.flags
        {'VEGAN', 'VEG', 'DAIRY_FREE'}
        >>> result.overridden_flags
        set()
        >>> result = normalize_diet_flags_detailed({"LOW_FAT", "KETO"})
        >>> result.flags
        {'KETO', 'LOW_CARB', 'HIGH_PROTEIN'}
        >>> result.overridden_flags
        {'LOW_FAT'}
        >>> result.conflicts_resolved
        [('KETO', {'LOW_FAT'})]
    """
    if not diet_flags:
        return NormalizedDietFlags(flags=set(), overridden_flags=set(), conflicts_resolved=[])

    normalized = set(diet_flags)
    overridden_flags: Set[str] = set()
    conflicts_resolved: list[tuple[str, Set[str]]] = []

    # Resolve incompatible combinations
    for incompatible_pair in INCOMPATIBLE_COMBINATIONS:
        if incompatible_pair.issubset(normalized):
            # Prefer more specific/restrictive diet
            # KETO > VEGAN > PALEO > VEG > MEDITERRANEAN
            priority_order = ["KETO", "VEGAN", "PALEO", "VEG", "MEDITERRANEAN"]
            resolved = False
            for diet in priority_order:
                if diet in incompatible_pair and diet in normalized:
                    # Keep this one (chosen_diet), remove ONLY the other conflicting flags
                    removed_flags = incompatible_pair - {diet}
                    normalized -= removed_flags
                    overridden_flags.update(removed_flags)
                    conflicts_resolved.append((diet, removed_flags))
                    resolved = True
                    break

            # Fallback: if no priority diet found, remove one arbitrarily
            # This handles future incompatible combinations not in priority_order
            if not resolved:
                # Remove all but the first diet alphabetically (deterministic)
                sorted_diets = sorted(incompatible_pair)
                kept_diet = sorted_diets[0]
                removed_flags = incompatible_pair - {kept_diet}
                normalized -= removed_flags
                overridden_flags.update(removed_flags)
                conflicts_resolved.append((kept_diet, removed_flags))

    # Add implications
    for base_diet, implied_flags in DIET_IMPLICATIONS.items():
        if base_diet in normalized:
            normalized.update(implied_flags)

    return NormalizedDietFlags(
        flags=normalized,
        overridden_flags=overridden_flags,
        conflicts_resolved=conflicts_resolved,
    )


def is_recipe_compatible(
    recipe_flags: Set[str],
    diet_flags: Set[str],
    recipe_name: Optional[str] = None,
) -> bool:
    """
    RU: Проверяет совместимость рецепта с диетическими ограничениями.
    EN: Checks recipe compatibility with dietary restrictions.

    Args:
        recipe_flags: Flags/tags on the recipe (ingredients, categories)
        diet_flags: User's dietary restrictions (normalized)
        recipe_name: Optional recipe name for additional checks

    Returns:
        True if recipe is compatible, False otherwise

    Examples:
        >>> is_recipe_compatible({"VEG"}, {"VEGAN"})
        False
        >>> is_recipe_compatible({"VEGAN", "GF"}, {"VEGAN"})
        True
    """
    # Normalize user's diet flags
    normalized_diet = normalize_diet_flags(diet_flags)

    # Vegetarian checks
    if "VEGAN" in normalized_diet:
        # Recipe must be explicitly VEGAN
        if "VEGAN" not in recipe_flags:
            return False
        # Check for animal products in name/flags
        if recipe_name:
            name_lower = recipe_name.lower()
            if any(indicator in name_lower for indicator in NON_VEGAN_INDICATORS):
                return False

    elif "VEG" in normalized_diet:
        # Recipe must be VEG or VEGAN
        if not recipe_flags.intersection({"VEG", "VEGAN"}):
            # Check name for meat/fish
            if recipe_name:
                name_lower = recipe_name.lower()
                if any(indicator in name_lower for indicator in NON_VEG_INDICATORS):
                    return False

    # Gluten-free checks
    if "GF" in normalized_diet:
        if recipe_flags.intersection(GLUTEN_INDICATORS):
            return False
        if recipe_name:
            name_lower = recipe_name.lower()
            if any(indicator in name_lower for indicator in GLUTEN_INDICATORS):
                return False

    # Dairy-free checks
    if "DAIRY_FREE" in normalized_diet:
        if recipe_flags.intersection(DAIRY_INDICATORS):
            return False

    # Nut-free checks
    if "NUT_FREE" in normalized_diet:
        if recipe_flags.intersection(NUT_INDICATORS):
            return False
        if recipe_name:
            name_lower = recipe_name.lower()
            if any(indicator in name_lower for indicator in NUT_INDICATORS):
                return False

    # Soy-free checks
    if "SOY_FREE" in normalized_diet:
        if recipe_flags.intersection(SOY_INDICATORS):
            return False
        if recipe_name:
            name_lower = recipe_name.lower()
            if any(indicator in name_lower for indicator in SOY_INDICATORS):
                return False

    return True


def adjust_macros_for_diet(
    macros: Dict[str, float],
    diet_flags: Set[str],
    weight_kg: float,
    kcal: int,
) -> Dict[str, float]:
    """
    RU: Адаптирует макронутриенты под диетические флаги.
    EN: Adjusts macronutrients for dietary flags.

    Args:
        macros: Base macros {"protein_g", "fat_g", "carbs_g", "fiber_g"} as floats
        diet_flags: User's dietary flags (normalized)
        weight_kg: User's body weight in kg
        kcal: Target daily calories (must be > 0)

    Returns:
        Adjusted macros dictionary with float values (preserves precision)

    Note:
        Returns float values to preserve calculation precision. Callers should
        round to int at the point of display/storage if needed.

    Examples:
        >>> macros = {"protein_g": 100.0, "fat_g": 50.0, "carbs_g": 200.0, "fiber_g": 25.0}
        >>> result = adjust_macros_for_diet(macros, {"HIGH_PROTEIN"}, 70, 2000)
        >>> result["protein_g"]
        140.0
    """
    # Guard against invalid input
    if kcal <= 0:
        return macros

    normalized = normalize_diet_flags(diet_flags)

    protein = float(macros["protein_g"])
    fat = float(macros["fat_g"])
    carbs = float(macros["carbs_g"])
    fiber = float(macros["fiber_g"])

    changed = False

    # HIGH_PROTEIN: minimum protein based on body weight
    if "HIGH_PROTEIN" in normalized:
        target_protein = max(protein, weight_kg * HIGH_PROTEIN_MIN_G_PER_KG)
        if target_protein > protein:
            protein = target_protein
            changed = True

    # LOW_CARB: max percentage calories from carbs, with minimum floor
    carb_ceiling: Optional[float] = None
    if "LOW_CARB" in normalized:
        low_carb_cap = max(LOW_CARB_CARB_FLOOR_G, (kcal * LOW_CARB_MAX_PERCENT) / 4)
        if carbs > low_carb_cap:
            carbs = low_carb_cap
            changed = True
        carb_ceiling = low_carb_cap

    # KETO: max percentage calories from carbs (very strict)
    # Note: KETO implies LOW_CARB, so this intentionally overwrites the LOW_CARB ceiling
    if "KETO" in normalized:
        keto_carb_cap = max(KETO_CARB_FLOOR_G, (kcal * KETO_MAX_CARB_PERCENT) / 4)
        if carbs > keto_carb_cap:
            carbs = keto_carb_cap
            changed = True
        carb_ceiling = keto_carb_cap  # Overwrite LOW_CARB ceiling with stricter KETO limit
        # Increase fat to compensate
        protein_kcal = protein * 4
        carbs_kcal = carbs * 4
        remaining_kcal = kcal - protein_kcal - carbs_kcal
        if remaining_kcal > 0:
            fat = max(fat, remaining_kcal / 9)
            changed = True

    # MEDITERRANEAN: higher healthy fats, more fiber
    if "MEDITERRANEAN" in normalized:
        # Fat should be at least specified percentage of calories
        desired_fat = max(fat, (kcal * MEDITERRANEAN_FAT_MIN_PERCENT) / 9)
        # Also ensure fat >= 1.2 * protein (healthy ratio)
        desired_fat = max(desired_fat, protein * 1.2)
        if desired_fat > fat:
            fat = desired_fat
            changed = True
        # Increase fiber target
        fiber = max(fiber, MEDITERRANEAN_FIBER_MIN_G)

    # LOW_FAT: max percentage calories from fat
    if "LOW_FAT" in normalized:
        low_fat_cap = (kcal * LOW_FAT_MAX_PERCENT) / 9
        if fat > low_fat_cap:
            fat = low_fat_cap
            changed = True

    if not changed:
        return macros

    # Rebalance carbs to fit within calorie budget
    protein_kcal = protein * 4
    fat_kcal = fat * 9
    remaining_kcal = kcal - protein_kcal - fat_kcal

    if remaining_kcal < 0:
        # Reduce fat first (if not MEDITERRANEAN or KETO)
        if "MEDITERRANEAN" not in normalized and "KETO" not in normalized:
            min_fat = max(MIN_HEALTHY_FAT_G_PER_KG * weight_kg, MIN_HEALTHY_FAT_ABSOLUTE_G)
            if fat > min_fat:
                reduction = min((-remaining_kcal) / 9, fat - min_fat)
                fat -= reduction
                fat_kcal = fat * 9
                remaining_kcal = kcal - protein_kcal - fat_kcal

        # If still negative, reduce protein slightly
        if remaining_kcal < 0:
            min_protein = max(MIN_PROTEIN_G_PER_KG * weight_kg, MIN_PROTEIN_ABSOLUTE_G)
            if "HIGH_PROTEIN" in normalized:
                min_protein = max(min_protein, HIGH_PROTEIN_MIN_G_PER_KG * weight_kg)
            if protein > min_protein:
                reduction = min((-remaining_kcal) / 4, protein - min_protein)
                protein -= reduction
                protein_kcal = protein * 4
                remaining_kcal = kcal - protein_kcal - fat_kcal

    # Calculate final carbs
    carb_floor = LOW_CARB_CARB_FLOOR_G if "LOW_CARB" in normalized else DEFAULT_CARB_FLOOR_G
    if "KETO" in normalized:
        carb_floor = KETO_CARB_FLOOR_G

    computed_carbs = max(carb_floor, remaining_kcal / 4 if remaining_kcal > 0 else carb_floor)

    if carb_ceiling is not None:
        carbs = min(carb_ceiling, computed_carbs)
    else:
        carbs = computed_carbs

    return {
        "protein_g": protein,
        "fat_g": fat,
        "carbs_g": carbs,
        "fiber_g": fiber,
    }


def get_diet_description(diet_flags: Set[str]) -> str:
    """
    RU: Получает человекочитаемое описание диеты.
    EN: Gets human-readable diet description.

    Args:
        diet_flags: Set of diet flags

    Returns:
        Comma-separated description string

    Examples:
        >>> get_diet_description({"VEGAN", "GF"})
        "Fully plant-based, no animal products, Gluten-free"
    """
    if not diet_flags:
        return "No dietary restrictions"

    descriptions = []
    for flag in sorted(diet_flags):
        if flag in DIET_FLAGS:
            descriptions.append(DIET_FLAGS[flag])

    return ", ".join(descriptions) if descriptions else "Custom diet"
