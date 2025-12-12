"""
Dietary Constraints - Diet Flag Processing and Recipe Compatibility

RU: Модуль обработки диетических ограничений и совместимости рецептов.
EN: Module for processing dietary restrictions and recipe compatibility.

This module handles dietary flags (VEGAN, KETO, PALEO, etc.) and ensures
recipes and meal plans comply with user's dietary preferences and restrictions.
"""

from __future__ import annotations

from typing import Dict, Optional, Set

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
    {"KETO", "HIGH_CARB"},
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


def normalize_diet_flags(diet_flags: Set[str]) -> Set[str]:
    """
    RU: Нормализует диетические флаги, разрешая конфликты и добавляя импликации.
    EN: Normalizes diet flags by resolving conflicts and adding implications.

    Args:
        diet_flags: Raw set of diet flags from user

    Returns:
        Normalized set of diet flags

    Examples:
        >>> normalize_diet_flags({"VEGAN"})
        {'VEGAN', 'VEG', 'DAIRY_FREE'}
        >>> normalize_diet_flags({"KETO", "VEGAN"})
        {'VEGAN', 'VEG', 'DAIRY_FREE', 'LOW_CARB', 'HIGH_PROTEIN'}
    """
    if not diet_flags:
        return set()

    normalized = set(diet_flags)

    # Resolve incompatible combinations
    for incompatible_pair in INCOMPATIBLE_COMBINATIONS:
        if incompatible_pair.issubset(normalized):
            # Prefer more specific/restrictive diet
            # KETO > VEGAN > VEG, etc.
            priority_order = ["KETO", "VEGAN", "PALEO", "VEG", "MEDITERRANEAN"]
            for diet in priority_order:
                if diet in incompatible_pair and diet in normalized:
                    # Keep this one, remove others
                    normalized -= incompatible_pair
                    normalized.add(diet)
                    break

    # Add implications
    for base_diet, implied_flags in DIET_IMPLICATIONS.items():
        if base_diet in normalized:
            normalized.update(implied_flags)

    return normalized


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
        non_vegan_indicators = {
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
        if recipe_name:
            name_lower = recipe_name.lower()
            if any(indicator in name_lower for indicator in non_vegan_indicators):
                return False

    elif "VEG" in normalized_diet:
        # Recipe must be VEG or VEGAN
        if not recipe_flags.intersection({"VEG", "VEGAN"}):
            # Check name for meat/fish
            non_veg_indicators = {
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
            if recipe_name:
                name_lower = recipe_name.lower()
                if any(indicator in name_lower for indicator in non_veg_indicators):
                    return False

    # Gluten-free checks
    if "GF" in normalized_diet:
        gluten_indicators = {"глютен", "gluten", "пшеница", "wheat", "овсянка", "oats"}
        if recipe_flags.intersection(gluten_indicators):
            return False
        if recipe_name:
            name_lower = recipe_name.lower()
            if any(indicator in name_lower for indicator in gluten_indicators):
                return False

    # Dairy-free checks
    if "DAIRY_FREE" in normalized_diet:
        dairy_indicators = {"молоко", "milk", "сыр", "cheese", "йогурт", "yogurt", "творог"}
        if recipe_flags.intersection(dairy_indicators):
            return False

    # Nut-free checks
    if "NUT_FREE" in normalized_diet:
        nut_indicators = {"орех", "nut", "миндаль", "almond", "арахис", "peanut"}
        if recipe_flags.intersection(nut_indicators):
            return False
        if recipe_name:
            name_lower = recipe_name.lower()
            if any(indicator in name_lower for indicator in nut_indicators):
                return False

    return True


def adjust_macros_for_diet(
    macros: Dict[str, int],
    diet_flags: Set[str],
    weight_kg: float,
    kcal: int,
) -> Dict[str, int]:
    """
    RU: Адаптирует макронутриенты под диетические флаги.
    EN: Adjusts macronutrients for dietary flags.

    Args:
        macros: Base macros {"protein_g", "fat_g", "carbs_g", "fiber_g"}
        diet_flags: User's dietary flags (normalized)
        weight_kg: User's body weight in kg
        kcal: Target daily calories

    Returns:
        Adjusted macros dictionary

    Examples:
        >>> macros = {"protein_g": 100, "fat_g": 50, "carbs_g": 200, "fiber_g": 25}
        >>> adjust_macros_for_diet(macros, {"HIGH_PROTEIN"}, 70, 2000)
        {"protein_g": 140, "fat_g": 50, "carbs_g": 165, "fiber_g": 25}
    """
    normalized = normalize_diet_flags(diet_flags)

    protein = float(macros["protein_g"])
    fat = float(macros["fat_g"])
    carbs = float(macros["carbs_g"])
    fiber = float(macros["fiber_g"])

    changed = False

    # HIGH_PROTEIN: 2.0 g/kg minimum
    if "HIGH_PROTEIN" in normalized:
        target_protein = max(protein, weight_kg * 2.0)
        if target_protein > protein:
            protein = target_protein
            changed = True

    # LOW_CARB: max 25% calories from carbs, minimum 40g
    carb_ceiling: Optional[float] = None
    if "LOW_CARB" in normalized:
        low_carb_cap = max(40.0, (kcal * 0.25) / 4)
        if carbs > low_carb_cap:
            carbs = low_carb_cap
            changed = True
        carb_ceiling = low_carb_cap

    # KETO: max 10% calories from carbs (very strict)
    if "KETO" in normalized:
        keto_carb_cap = max(30.0, (kcal * 0.10) / 4)
        if carbs > keto_carb_cap:
            carbs = keto_carb_cap
            changed = True
        carb_ceiling = keto_carb_cap
        # Increase fat to compensate
        protein_kcal = protein * 4
        carbs_kcal = carbs * 4
        remaining_kcal = kcal - protein_kcal - carbs_kcal
        if remaining_kcal > 0:
            fat = max(fat, remaining_kcal / 9)
            changed = True

    # MEDITERRANEAN: higher healthy fats (35-40% kcal), more fiber
    if "MEDITERRANEAN" in normalized:
        # Fat should be at least 35% of calories
        desired_fat = max(fat, (kcal * 0.35) / 9)
        # Also ensure fat >= 1.2 * protein (healthy ratio)
        desired_fat = max(desired_fat, protein * 1.2)
        if desired_fat > fat:
            fat = desired_fat
            changed = True
        # Increase fiber target
        fiber = max(fiber, 30.0)

    # LOW_FAT: max 25% calories from fat
    if "LOW_FAT" in normalized:
        low_fat_cap = (kcal * 0.25) / 9
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
            min_fat = max(0.6 * weight_kg, 30.0)  # Minimum healthy fat
            if fat > min_fat:
                reduction = min((-remaining_kcal) / 9, fat - min_fat)
                fat -= reduction
                fat_kcal = fat * 9
                remaining_kcal = kcal - protein_kcal - fat_kcal

        # If still negative, reduce protein slightly
        if remaining_kcal < 0:
            min_protein = max(1.6 * weight_kg, 50.0)
            if "HIGH_PROTEIN" in normalized:
                min_protein = max(min_protein, 2.0 * weight_kg)
            if protein > min_protein:
                reduction = min((-remaining_kcal) / 4, protein - min_protein)
                protein -= reduction
                protein_kcal = protein * 4
                remaining_kcal = kcal - protein_kcal - fat_kcal

    # Calculate final carbs
    carb_floor = 40.0 if "LOW_CARB" in normalized else 50.0
    if "KETO" in normalized:
        carb_floor = 30.0

    computed_carbs = max(carb_floor, remaining_kcal / 4 if remaining_kcal > 0 else carb_floor)

    if carb_ceiling is not None:
        carbs = min(carb_ceiling, computed_carbs)
    else:
        carbs = computed_carbs

    return {
        "protein_g": int(round(protein)),
        "fat_g": int(round(fat)),
        "carbs_g": int(round(carbs)),
        "fiber_g": int(round(fiber)),
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
