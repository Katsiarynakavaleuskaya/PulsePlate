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
import warnings
from typing import Any

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

# Meal-level detection threshold (kcal)
# Values ≤ this threshold are considered single meals rather than daily totals
# Set to 450 kcal to capture most smaller meals (~400–450 kcal)
# Larger meals (~500–600 kcal) require meal-context keywords to be classified as meals,
# avoiding false positives for daily totals
MEAL_KCAL_THRESHOLD = 450

# BMI Safety Thresholds
# Based on WHO classification and medical supervision requirements
BMI_DANGEROUS_LOW = 16.0  # Below this requires immediate medical attention
BMI_OBESITY_THRESHOLD = 30.0  # Above this indicates obesity (class I+)
# Deprecated alias for backward compatibility - will emit a warning when accessed
_BMI_DANGEROUS_HIGH_VALUE = BMI_OBESITY_THRESHOLD


# BMI_DANGEROUS_HIGH is intentionally not defined as a module-level constant.
# Accessing it (e.g. via import * or attribute lookup) is routed through the
# __getattr__ handler below, which emits a DeprecationWarning and returns
# BMI_OBESITY_THRESHOLD. This behavior must be preserved for existing callers;
# new code should use BMI_OBESITY_THRESHOLD directly.


def _compute_deprecation_stacklevel() -> int:  # pragma: no cover
    """Compute the correct stacklevel for deprecation warnings.

    Walks the call stack upward to find the first frame that is not part of:
    - This module (nutrition_constants.py)
    - Python's import machinery (importlib)

    Returns:
        The stacklevel to pass to warnings.warn() so it points to the real caller.
    """
    import inspect
    import os

    current_file = os.path.abspath(__file__)
    stack = inspect.stack()

    # Start from frame 1 (caller of this function)
    # Frame 0 is this function itself
    for i, frame_info in enumerate(stack[1:], start=1):
        frame_file = os.path.abspath(frame_info.filename)

        # Skip frames from this module
        if frame_file == current_file:
            continue

        # Skip frames from importlib (Python's import machinery)
        if "importlib" in frame_file:
            continue

        # Found the first external caller
        return i

    # Fallback: if we can't determine the correct level, use 2
    # (which points to the direct caller of warnings.warn)
    return 2


class _DeprecatedBMIAlias:
    """Accessor for deprecated BMI_DANGEROUS_HIGH alias that emits a warning when accessed."""

    def __getattr__(self, name: str) -> Any:
        if name == "BMI_DANGEROUS_HIGH":
            stacklevel = _compute_deprecation_stacklevel()
            warnings.warn(
                "BMI_DANGEROUS_HIGH is deprecated and will be removed in a future release. "
                "Use BMI_OBESITY_THRESHOLD instead.",
                DeprecationWarning,
                stacklevel=stacklevel,
            )
            return _BMI_DANGEROUS_HIGH_VALUE
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Create an instance to handle deprecated attribute access
_deprecated_alias_handler = _DeprecatedBMIAlias()


# Override __getattr__ at module level to intercept deprecated alias access
def __getattr__(name: str) -> Any:
    return getattr(_deprecated_alias_handler, name)


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
    - Very small portions (≤ MEAL_KCAL_THRESHOLD kcal) → meal
    - Otherwise → daily total (conservative: flag potential issues)

    Raises:
        TypeError: If kcal is not a number (int or float)
        ValueError: If kcal is NaN, Infinity, or negative
    """
    # Input validation: fail fast on invalid inputs
    # Explicitly reject boolean values since bool is a subclass of int
    if isinstance(kcal, bool):
        raise TypeError(f"kcal must be a number (int or float), got boolean value {kcal}")
    if not isinstance(kcal, (int, float)):
        raise TypeError(f"kcal must be a number (int or float), got {type(kcal).__name__}")

    if not math.isfinite(kcal):
        raise ValueError(f"kcal must be a finite number, got {kcal} (NaN or Infinity)")

    if kcal < 0:
        raise ValueError(f"kcal must be non-negative, got {kcal}")

    context_lower = (context or "").lower()
    meal_keywords = ["meal", "breakfast", "lunch", "dinner", "snack", "portion"]
    daily_keywords = ["daily", "total", "day", "tdee", "intake"]

    # Strong daily signal - definitely not a meal
    if any(keyword in context_lower for keyword in daily_keywords):
        return False

    # Strong meal signal
    if any(keyword in context_lower for keyword in meal_keywords):
        return True

    # Only tiny portions default to meal without context
    if kcal <= MEAL_KCAL_THRESHOLD:
        return True

    # Ambiguous - assume daily to avoid missing real issues
    return False


__all__ = [
    "KCAL_MIN_SUPERVISED",
    "KCAL_MIN_SAFE",
    "KCAL_MIN_TYPICAL",
    "KCAL_MAX_TYPICAL",
    "KCAL_MAX_SAFE",
    "MEAL_KCAL_THRESHOLD",
    "BMI_DANGEROUS_LOW",
    "BMI_OBESITY_THRESHOLD",
    # BMI_DANGEROUS_HIGH is deprecated and accessed via __getattr__, not exported in __all__
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
