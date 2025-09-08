# -*- coding: utf-8 -*-
"""
--sql

;
"""

"""Complex tests for bmi_core with edge case coverage."""
import pytest

from bmi_core import (
    auto_group,
    bmi_category,
    bmi_value,
    build_premium_plan,
    compute_wht_ratio,
    estimate_level,
    healthy_bmi_range,
    interpret_group,
)

# ---------- Базовые расчёты BMI ----------


def test_bmi_value_rounding():
    # 70 / 1.7^2 ≈ 24.22 → 24.2
    assert bmi_value(70.0, 1.7) == 24.2


def test_bmi_value_invalid_inputs():
    with pytest.raises(ValueError):
        bmi_value(0, 1.7)
    with pytest.raises(ValueError):
        bmi_value(70, 0)
    with pytest.raises(ValueError):
        bmi_value(-10, 1.7)
    with pytest.raises(ValueError):
        bmi_value(70, -1.8)


# ---------- Категории BMI (RU/EN) ----------


def test_bmi_category_edges_ru():
    assert bmi_category(18.49, "ru") == "Недостаточная масса"
    assert bmi_category(18.5, "ru") == "Норма"
    assert bmi_category(24.99, "ru") == "Норма"
    assert bmi_category(25.0, "ru") == "Избыточная масса"
    assert bmi_category(29.99, "ru") == "Избыточная масса"
    # Obesity in RU now has classes
    assert bmi_category(30.0, "ru") == "Ожирение I степени"


def test_bmi_category_edges_en():
    assert bmi_category(18.49, "en") == "Underweight"
    assert bmi_category(18.5, "en") == "Normal weight"
    assert bmi_category(24.99, "en") == "Normal weight"
    assert bmi_category(25.0, "en") == "Overweight"
    assert bmi_category(29.99, "en") == "Overweight"
    assert bmi_category(30.0, "en") == "Obese Class I"


# ---------- Группы пользователей ----------


def test_auto_group_variants():
    assert auto_group(10, "муж", "нет", "нет", "ru") == "too_young"
    assert auto_group(12, "муж", "нет", "нет", "ru") == "child"  # Pre-teen
    assert auto_group(16, "муж", "нет", "нет", "ru") == "teen"  # Teenager
    assert auto_group(61, "муж", "нет", "нет", "ru") == "elderly"
    assert auto_group(30, "жен", "да", "нет", "ru") == "pregnant"
    assert auto_group(30, "жен", "нет", "спортсменка", "ru") == "athlete"
    assert auto_group(30, "female", "no", "y", "en") == "athlete"


def test_interpret_group_notes_en():
    txt = interpret_group(26.0, "athlete", "en")
    # Updated i18n phrasing focuses on body fat wording
    assert "body fat" in txt.lower() or "overestimate" in txt.lower()


# ---------- Уровень подготовки ----------


def test_estimate_level_rules():
    assert estimate_level(3, 5, "en") == "advanced"
    assert estimate_level(2, 2, "en") == "intermediate"
    assert estimate_level(1, 0.6, "ru") == "начальный"
    assert estimate_level(0, 0.0, "ru") == "базовый"


# ---------- WHtR ----------


def test_compute_wht_ratio_values():
    assert compute_wht_ratio(None, 1.7) is None
    assert compute_wht_ratio(80, 1.7) == 0.47  # 0.8 / 1.7 ≈ 0.4706 → 0.47
    assert compute_wht_ratio(0, 1.7) is None
    assert compute_wht_ratio(200, 0) is None


# ---------- Диапазоны «здорового» BMI ----------


def test_healthy_bmi_ranges_adult_elderly_sport():
    # взрослый (<60): 18.5–25.0
    assert healthy_bmi_range(30, "general", premium=False) == (18.5, 25.0)
    # пожилой (>=60): верх 27.5
    assert healthy_bmi_range(65, "general", premium=False) == (18.5, 27.5)
    # спортсмен + premium: верх не ниже 27.0
    bmin, bmax = healthy_bmi_range(30, "athlete", premium=True)
    assert bmin == 18.5
    assert bmax >= 27.0


# ---------- Премиум-план (maintain / lose / gain) ----------


def test_build_premium_plan_maintain():
    # Подберём вес в «здоровом» диапазоне, чтобы действие было maintain
    height = 1.75
    bmin, bmax = healthy_bmi_range(30, "general", premium=False)  # (18.5, 25.0)
    wmin = round(bmin * height * height, 1)  # ~56.6
    wmax = round(bmax * height * height, 1)  # ~76.6
    weight = (wmin + wmax) / 2
    bmi = bmi_value(weight, height)
    plan = build_premium_plan(30, weight, height, bmi, "en", "general", False)
    assert plan["action"] == "maintain"
    assert plan["healthy_weight"] == (wmin, wmax)


def test_build_premium_plan_lose():
    height = 1.70
    bmin, bmax = healthy_bmi_range(35, "general", premium=False)  # (18.5, 25.0)
    wmax = round(bmax * height * height, 1)
    weight = wmax + 5.0  # выше «здорового» → нужно снижать
    bmi = bmi_value(weight, height)
    plan = build_premium_plan(35, weight, height, bmi, "ru", "general", False)
    assert plan["action"] == "lose"
    assert plan["delta_kg"] == round(weight - wmax, 1)
    assert isinstance(plan["est_weeks"], tuple) and len(plan["est_weeks"]) == 2


def test_build_premium_plan_gain():
    height = 1.60
    bmin, bmax = healthy_bmi_range(25, "general", premium=False)  # (18.5, 25.0)
    wmin = round(bmin * height * height, 1)
    weight = wmin - 3.0  # ниже «здорового» → нужно набирать
    bmi = bmi_value(weight, height)
    plan = build_premium_plan(25, weight, height, bmi, "en", "general", False)
    assert plan["action"] == "gain"
    assert plan["delta_kg"] == round(wmin - weight, 1)
    assert isinstance(plan["est_weeks"], tuple) and len(plan["est_weeks"]) == 2


# ---------- Интеграционный тест ----------


def test_integration_normal_case():
    # Рост 1.75, вес ~63.5 → BMI ≈ 20.7 (норма), план: maintain
    height = 1.75
    weight = 63.5
    bmi = bmi_value(weight, height)
    assert pytest.approx(bmi, 0.1) == 20.7
    plan = build_premium_plan(30, weight, height, bmi, "en", "general", False)
    assert plan["action"] == "maintain"
