# -*- coding: utf-8 -*-
"""
RU: Пакет BMI: риск по талии и (дальше) orchestration BMI engine.
EN: BMI package: waist risk and (later) BMI engine orchestration.
"""

from core.bmi.risk import WaistRiskResult, calculate_waist_risk
from core.bmi.engine import get_bmi_visual_ranges

__all__ = ["WaistRiskResult", "calculate_waist_risk", "get_bmi_visual_ranges"]
