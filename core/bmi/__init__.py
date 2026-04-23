# -*- coding: utf-8 -*-
"""
RU: Пакет BMI: риск по талии и (дальше) orchestration BMI engine.
EN: BMI package: waist risk and (later) BMI engine orchestration.
"""

from core.bmi.risk import WaistRiskResult, calculate_waist_risk
from core.bmi.engine import (
    build_premium_plan,
    estimate_level,
    get_bmi_visual_ranges,
    get_fitness_level_display,
    interpret_group,
    FITNESS_LEVEL_DISPLAY_NAMES,
    PremiumPlanResult,
)
from core.bmi.query import extract_bmi_inputs, render_bmi_query_answer

__all__ = [
    "WaistRiskResult",
    "calculate_waist_risk",
    "get_bmi_visual_ranges",
    "estimate_level",
    "get_fitness_level_display",
    "FITNESS_LEVEL_DISPLAY_NAMES",
    "interpret_group",
    "build_premium_plan",
    "PremiumPlanResult",
    "extract_bmi_inputs",
    "render_bmi_query_answer",
]
