# -*- coding: utf-8 -*-
"""Edge-тесты для доведения покрытия до ~100%."""

from bmi_core import (
    auto_group,
    bmi_category,
    bmi_value,
    build_premium_plan,
    compute_wht_ratio,
    estimate_level,
    group_display_name,
    healthy_bmi_range,
    interpret_group,
)

def test_bmi_category_lang_fallback_to_ru():
    assert bmi_category(24.0, "de") == "Нормальный вес"

def test_interpret_group_general_ru_no_note():
    assert interpret_group(22.0, "general", "ru") == "Нормальный вес"

def test_auto_group_regex_phrase_sportswoman():
    assert auto_group(30, "жен", "нет", "я спортсменка, хожу в зал", "ru") == "athlete"
