# -*- coding: utf-8 -*-
"""Маленькие edge-тесты, которые добивают покрытие до ~99–100% при нашей версии ядра."""
from bmi_core import (
    bmi_value,
    build_premium_plan,
    estimate_level,
    healthy_bmi_range,
    interpret_group,
)


def test_interpret_group_general_en_no_extra_dot():
    # Для group='general' строка не должна заканчиваться лишней точкой
    txt = interpret_group(22.0, 'general', 'en')
    assert txt == 'Healthy weight'

def test_estimate_level_beginner_ru():
    # Добиваем RU-ветку 'beginner'
    assert estimate_level(0, 0.0, 'ru') == 'базовый'

def test_build_premium_plan_gain_ru_tips():
    # Добиваем RU-ветку 'gain' + наличие подсказок
    height = 1.60
    bmin, bmax = healthy_bmi_range(25, 'general', premium=False)
    wmin = round(bmin * height * height, 1)
    weight = wmin - 2.0  # ниже «здорового» -> gain
    bmi = bmi_value(weight, height)
    plan = build_premium_plan(25, weight, height, bmi, 'ru', 'general', False)
    assert plan['action'] == 'gain'
    assert isinstance(plan['nutrition_tip'], str) and len(plan['nutrition_tip']) > 0
    assert isinstance(plan['activity_tip'], str) and len(plan['activity_tip']) > 0
