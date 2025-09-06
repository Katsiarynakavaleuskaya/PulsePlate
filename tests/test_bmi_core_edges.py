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
    # Неизвестная локаль -> берём RU-словарь
    assert bmi_category(24.0, "de") == "Нормальный вес"


def test_interpret_group_general_ru_no_note():
    # Для general заметка пустая -> должен вернуться только base без точки
    assert interpret_group(22.0, "general", "ru") == "Нормальный вес"


def test_auto_group_regex_phrase_sportswoman():
    # Слово внутри фразы, не точное совпадение -> сработает regex
    assert auto_group(30, "жен", "нет", "я спортсменка, хожу в зал", "ru") == "athlete"


def test_auto_group_pregnant_en():
    # Беременность на EN-ветке
    assert auto_group(28, "female", "yes", "no", "en") == "pregnant"


def test_wht_ratio_too_large_waist_none():
    # Талия выше MAX -> считаем недействительным вводом (None)
    assert compute_wht_ratio(1000, 1.70) is None


def test_wht_ratio_bad_height_none():
    # Рост вне допустимого диапазона -> None
    assert compute_wht_ratio(80, 0.1) is None


def test_group_display_name_both_langs():
    assert group_display_name("elderly", "ru") == "пожилой"
    assert group_display_name("elderly", "en") == "elderly"


def test_estimate_level_beginner_en():
    assert estimate_level(0, 0.0, "en") == "beginner"


def test_healthy_bmi_range_athlete_premium_raise():
    bmin, bmax = healthy_bmi_range(30, "athlete", premium=True)
    assert bmin == 18.5
    assert bmax >= 27.0  # спорт-мод повышает верхнюю граница


def test_premium_plan_maintain_has_none_weeks():
    height = 1.75
    # Подберём вес в «здорового» диапазоне, чтобы action=maintain и
    # est_weeks=(None, None)
    bmin, bmax = healthy_bmi_range(30, "general", premium=False)
    wmin = round(bmin * height * height, 1)
    wmax = round(bmax * height * height, 1)
    weight = (wmin + wmax) / 2
    bmi = bmi_value(weight, height)
    plan = build_premium_plan(
        30,
        weight,
        height,
        bmi,
        "en",
        "general",
        False,
    )
    assert plan["action"] == "maintain"
    assert plan["est_weeks"] == (None, None)
