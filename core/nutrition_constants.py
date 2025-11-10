"""Centralized nutrition safety constants and thresholds.

RU: Централизованные константы безопасности питания и пороговые значения.
EN: Centralized nutrition safety constants and thresholds.

Based on:
- USDA Dietary Guidelines 2020-2025
- WHO Healthy Diet Guidance
- EFSA Scientific Opinions on Dietary Reference Values
- Medical supervision thresholds for extreme diets

All values represent daily totals unless otherwise specified.
"""

from __future__ import annotations

import math

# Calorie Safety Thresholds (kcal/day)
# Based on WHO/USDA guidelines and medical supervision requirements

# Absolute minimum - requires medical supervision
KCAL_MIN_SUPERVISED = 800  # Very low calorie diets (VLCD) require medical monitoring

# Safe minimum for adults (WHO recommendation)
KCAL_MIN_SAFE = 1200  # Below this risks nutritional deficiencies

# Typical healthy range
KCAL_MIN_TYPICAL = 1500  # Lower bound for sustainable diets
KCAL_MAX_TYPICAL = 3000  # Upper bound for most adults

# Absolute maximum - above this is unusual/unsafe
KCAL_MAX_SAFE = 6000  # Elite athletes/special populations only

# Danger thresholds for red flags
KCAL_DANGEROUS_LOW = 1200  # Daily total - triggers safety warnings
KCAL_DANGEROUS_HIGH = 6000  # Daily total - triggers safety warnings

# Macronutrient Percentage Ranges (% of total calories)
# Based on USDA Dietary Guidelines 2020-2025 and WHO recommendations

# Protein (10-35% per USDA DG 2020-2025)
PROTEIN_MIN_PERCENT = 10.0
PROTEIN_MAX_PERCENT = 35.0

# Fat (20-35% per USDA DG 2020-2025)
FAT_MIN_PERCENT = 20.0
FAT_MAX_PERCENT = 35.0

# Carbohydrates (45-65% per USDA DG 2020-2025)
CARBS_MIN_PERCENT = 45.0
CARBS_MAX_PERCENT = 65.0

# Fiber (g/day, WHO recommendation)
FIBER_MIN_G = 25.0  # WHO minimum for adults
FIBER_MAX_G = 50.0  # Upper safe limit

# Macro absolute limits (g/day) for data validation
PROTEIN_G_MIN = 0
PROTEIN_G_MAX = 500  # Extreme upper bound
FAT_G_MIN = 0
FAT_G_MAX = 400  # Extreme upper bound
CARBS_G_MIN = 0
CARBS_G_MAX = 1000  # Extreme upper bound


def is_meal_level_value(kcal: float, context: str = "") -> bool:
    """Determine if a kcal value represents a single meal vs daily total.

    RU: Определить, представляет ли значение ккал одно блюдо или дневной итог.
    EN: Determine if a kcal value represents a single meal vs daily total.

    Args:
        kcal: Calorie value to check
        context: Optional context string (variable name, test name, code snippet)

    Returns:
        True if value appears to be meal-level, False if daily total

    Heuristics (require explicit cues, default to daily):
    - Explicit daily keywords → daily total
    - Explicit meal keywords → meal
    - Very small portions (≤ 300 kcal) → meal
    - Otherwise → daily total (conservative: flag potential issues)

    Raises:
        TypeError: If kcal is not a number (int or float)
        ValueError: If kcal is NaN, Infinity, or negative
    """
    # Input validation: fail fast on invalid inputs
    if not isinstance(kcal, (int, float)):
        raise TypeError(f"kcal must be a number (int or float), got {type(kcal).__name__}")

    if not math.isfinite(kcal):
        raise ValueError(f"kcal must be a finite number, got {kcal} (NaN or Infinity)")

    if kcal < 0:
        raise ValueError(f"kcal must be non-negative, got {kcal}")

    context_lower = context.lower()
    meal_keywords = ["meal", "breakfast", "lunch", "dinner", "snack", "portion"]
    daily_keywords = ["daily", "total", "day", "tdee", "intake"]

    # Strong daily signal - definitely not a meal
    if any(keyword in context_lower for keyword in daily_keywords):
        return False

    # Strong meal signal
    if any(keyword in context_lower for keyword in meal_keywords):
        return True

    # Only tiny portions default to meal without context
    if kcal <= 300:
        return True

    # Ambiguous - assume daily to avoid missing real issues
    return False


__all__ = [
    "KCAL_MIN_SUPERVISED",
    "KCAL_MIN_SAFE",
    "KCAL_MIN_TYPICAL",
    "KCAL_MAX_TYPICAL",
    "KCAL_MAX_SAFE",
    "KCAL_DANGEROUS_LOW",
    "KCAL_DANGEROUS_HIGH",
    "PROTEIN_MIN_PERCENT",
    "PROTEIN_MAX_PERCENT",
    "FAT_MIN_PERCENT",
    "FAT_MAX_PERCENT",
    "CARBS_MIN_PERCENT",
    "CARBS_MAX_PERCENT",
    "FIBER_MIN_G",
    "FIBER_MAX_G",
    "PROTEIN_G_MIN",
    "PROTEIN_G_MAX",
    "FAT_G_MIN",
    "FAT_G_MAX",
    "CARBS_G_MIN",
    "CARBS_G_MAX",
    "is_meal_level_value",
]
