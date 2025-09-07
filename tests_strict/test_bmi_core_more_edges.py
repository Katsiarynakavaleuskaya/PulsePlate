# -*- coding: utf-8 -*-
"""Маленькие edge-тесты, которые добивают покрытие до ~99–100% при нашей версии ядра."""

from bmi_core import (
    bmi_value,
    build_premium_plan,
    estimate_level,
    healthy_bmi_range,
)


def test_estimate_level_beginner_en():
    assert estimate_level(0, 0.0, "en") == "beginner"


def test_healthy_bmi_range_athlete_premium_raise():
    bmin, bmax = healthy_bmi_range(30, "athlete", premium=True)
    assert bmin == 18.5
    assert bmax >= 27.0


def test_premium_plan_maintain_has_none_weeks():
    height = 1.75
    bmin, bmax = healthy_bmi_range(30, "general", premium=False)
    wmin = round(bmin * height * height, 1)
    wmax = round(bmax * height * height, 1)
    weight = (wmin + wmax) / 2
    bmi = bmi_value(weight, height)
    plan = build_premium_plan(30, weight, height, bmi, "en", "general", False)
    assert plan["action"] == "maintain"
    assert plan["est_weeks"] == (None, None)
