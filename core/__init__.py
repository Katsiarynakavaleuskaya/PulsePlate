"""
Core nutrition and plate generation modules.

This package contains core business logic for nutrition calculations
and visual plate generation, now enhanced with WHO-based standards.
"""

from .menu_engine import analyze_nutrient_gaps, make_daily_menu, make_weekly_menu
from .plate import make_plate
from .recommendations import build_nutrition_targets
from .targets import NutritionTargets, UserProfile

__all__ = [
    "make_plate",
    "UserProfile",
    "NutritionTargets",
    "build_nutrition_targets",
    "make_daily_menu",
    "make_weekly_menu",
    "analyze_nutrient_gaps",
]
