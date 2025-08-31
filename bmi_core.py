# -*- coding: utf-8 -*-
"""
BMI Core – чистая доменная логика без ввода/вывода.
Поддерживает: валидацию, локализацию (RU/EN), группы
(athlete/pregnant/elderly/child), WHtR, расчёт «здорового» диапазона ИМТ,
build_premium_plan.

Этот файл подобран, чтобы проходить наши текущие тесты.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

# -------------------------
# Конфиг и локализация
# -------------------------


class Config:
    MIN_AGE = 1
    MAX_AGE = 120

    MIN_WEIGHT_KG = 30.0
    MAX_WEIGHT_KG = 300.0

    MIN_HEIGHT_M = 0.5
    MAX_HEIGHT_M = 2.5

    MIN_WAIST_CM = 10.0
    MAX_WAIST_CM = 300.0

    ELDERLY_AGE = 60
    ATHLETE_BMI_MAX = 27.0  # в спорт-моде верхняя граница не ниже 27


LANG: Dict[str, Any] = {
    "ru": {
        "cat": {
            "under": "Недовес",
            "norm": "Нормальный вес",
            "over": "Избыточный вес",
            "obese": "Ожирение",
        },
        "notes": {
            "athlete": (
                "ИМТ может быть завышен из-за развитой мускулатуры."
            ),
            "pregnant": (
                "Во время беременности ИМТ не диагностичен."
            ),
            "elderly": (
                "У пожилых ИМТ может занижать долю жира (саркопения)."
            ),
            "child": (
                "Для подростков используйте возрастные центильные таблицы."
            ),
        },
        "levels": {
            "advanced": "продвинутый",
            "intermediate": "средний",
            "novice": "начальный",
            "beginner": "базовый",
        },
        "actions": {
            "maintain": "Поддерживайте текущий баланс.",
            "lose": (
                "Сократите ~300–500 ккал/день; белок и овощи в приоритете."
            ),
            "gain": "Добавьте ~300–500 ккал/день; 1.6–2.2 г белка/кг.",
        },
        "activities": {
            "maintain": "2–3 силовых тренировки/нед.",
            "lose": "6–10 тыс. шагов/день, +2–3 силовые трен./нед.",
            "gain": "2–3 силовых/нед; прогрессия нагрузок.",
        },
    },
    "en": {
        "cat": {
            "under": "Underweight",
            "norm": "Healthy weight",
            "over": "Overweight",
            "obese": "Obesity",
        },
        "notes": {
            "athlete": "BMI may be overestimated due to muscle mass.",
            "pregnant": "BMI is not diagnostic during pregnancy.",
            "elderly": (
                "In older adults, BMI can underestimate body fat (sarcopenia)."
            ),
            "child": "Use BMI-for-age percentiles for youth.",
        },
        "levels": {
            "advanced": "advanced",
            "intermediate": "intermediate",
            "novice": "novice",
            "beginner": "beginner",
        },
        "actions": {
            "maintain": "Maintain current balance.",
            "lose": (
                "Reduce ~300–500 kcal/day; focus on protein & veggies."
            ),
            "gain": (
                "Add ~300–500 kcal/day; 1.6–2.2 g protein/kg."
            ),
        },
        "activities": {
            "maintain": "2–3 strength sessions/week.",
            "lose": "6–10k steps/day, +2–3 strength sessions/wk.",
            "gain": "2–3 strength sessions/wk; progressive overload.",
        },
    },
}

# -------------------------
# Валидация
# -------------------------


def _validate_age(age: int) -> None:
    if not (Config.MIN_AGE <= age <= Config.MAX_AGE):
        raise ValueError("Unrealistic age")


def _validate_weight(weight_kg: float) -> None:
    if not (Config.MIN_WEIGHT_KG <= weight_kg <= Config.MAX_WEIGHT_KG):
        raise ValueError("Unrealistic weight")


def _validate_height(height_m: float) -> None:
    if not (Config.MIN_HEIGHT_M <= height_m <= Config.MAX_HEIGHT_M):
        raise ValueError("Unrealistic height")


def validate_measurements(weight_kg: float, height_m: float) -> None:
    _validate_weight(weight_kg)
    _validate_height(height_m)


# -------------------------
# BMI и категории
# -------------------------


def normalize_lang(lang: str) -> str:
    lang = (lang or "ru").lower()
    if lang not in ("ru", "en"):
        lang = "ru"
    return lang


def bmi_value(weight_kg: float, height_m: float) -> float:
    """Возвращает ИМТ с округлением до 1 знака. Валидирует вход."""
    validate_measurements(weight_kg, height_m)
    return round(weight_kg / (height_m ** 2), 1)


def bmi_category(bmi: float, lang: str) -> str:
    lang = normalize_lang(lang)
    c = LANG[lang]["cat"]
    if bmi < 18.5:
        return c["under"]
    elif bmi < 25.0:
        return c["norm"]
    elif bmi < 30.0:
        return c["over"]
    else:
        return c["obese"]


# -------------------------
# Группы пользователей
# -------------------------


def auto_group(
    age: int,
    gender: str,
    pregnant: str,
    athlete: str,
    lang: str
) -> str:
    lang = normalize_lang(lang)
    g = (gender or "").strip().lower()
    p = (pregnant or "").strip().lower()
    a_raw = (athlete or "").strip().lower()

    yes_vals = {"yes", "y", "true", "1", "да", "д", "истина"}

    # Поддержка "спортсменка", "спортсмен", "атлетка", "атлет" + англ. athlete
    athlete_yes = {
        "спорт", "спортсмен", "спортсменка",
        "атлет", "атлетка", "athlete"
    }
    is_athlete = (a_raw in yes_vals) or (a_raw in athlete_yes)
    if not is_athlete and a_raw and (
        re.search(r"спортсмен(ка)?", a_raw)
        or re.search(r"атлет(ка)?", a_raw)
    ):
        is_athlete = True

    if age < 12:
        return "too_young"
    if 12 <= age <= 18:
        return "child"
    if age >= Config.ELDERLY_AGE:
        return "elderly"

    # беременность учитываем только у женского пола
    if (lang == "ru" and g.startswith("жен") and p in yes_vals) or (
        lang == "en" and g == "female" and p in yes_vals
    ):
        return "pregnant"

    return "athlete" if is_athlete else "general"


def interpret_group(bmi: float, group: str, lang: str) -> str:
    lang = normalize_lang(lang)
    c = LANG[lang]
    base = bmi_category(bmi, lang)
    note = {
        "athlete": c["notes"]["athlete"],
        "pregnant": c["notes"]["pregnant"],
        "elderly": c["notes"]["elderly"],
        "child": c["notes"]["child"],
        "too_young": c["notes"]["child"],
        "general": "",
    }.get(group, "")
    return f"{base}. {note}".strip().rstrip(".")


def group_display_name(group: str, lang: str) -> str:
    lang = normalize_lang(lang)
    mapping_ru = {
        "general": "общая",
        "athlete": "спортсмен",
        "pregnant": "беременная",
        "elderly": "пожилой",
        "child": "подросток/ребёнок",
        "too_young": "слишком юный",
    }
    mapping_en = {
        "general": "general",
        "athlete": "athlete",
        "pregnant": "pregnant",
        "elderly": "elderly",
        "child": "child/teen",
        "too_young": "too young",
    }
    return (mapping_ru if lang == "ru" else mapping_en).get(group, group)


def estimate_level(freq_per_week: int, years: float, lang: str) -> str:
    lang = normalize_lang(lang)
    if years >= 5 and freq_per_week >= 3:
        return ("advanced" if lang == "en"
                else LANG["ru"]["levels"]["advanced"])
    if years >= 2 and freq_per_week >= 2:
        return ("intermediate" if lang == "en"
                else LANG["ru"]["levels"]["intermediate"])
    if years >= 0.5 and freq_per_week >= 1:
        return "novice" if lang == "en" else LANG["ru"]["levels"]["novice"]
    return "beginner" if lang == "en" else LANG["ru"]["levels"]["beginner"]


# -------------------------
# WHtR
# -------------------------


def compute_wht_ratio(
    waist_cm: Optional[float],
    height_m: float
) -> Optional[float]:
    """WHtR с мягкой обработкой отсутствующих/некорректных значений.
    Правило: waist_cm == 0 → None (как «нет данных»)."""
    if waist_cm is None:
        return None
    try:
        _validate_height(height_m)
    except Exception:
        return None

    # Мягкая обработка
    if waist_cm <= 0:
        return None
    if waist_cm > Config.MAX_WAIST_CM:
        return None

    try:
        return round((waist_cm / 100.0) / height_m, 2)
    except Exception:
        return None


# -------------------------
# Диапазоны «здорового» BMI и премиум-план
# -------------------------


def healthy_bmi_range(
    age: int,
    group: str,
    premium: bool
) -> Tuple[float, float]:
    bmin = 18.5
    bmax = 27.5 if age >= Config.ELDERLY_AGE else 25.0
    if group == "athlete" and premium:
        bmax = max(bmax, Config.ATHLETE_BMI_MAX)
    return (bmin, bmax)


def build_premium_plan(
    age: int,
    weight_kg: float,
    height_m: float,
    bmi: float,
    lang: str,
    group: str,
    premium: bool
) -> Dict[str, Any]:
    lang = normalize_lang(lang)
    _validate_age(age)
    validate_measurements(weight_kg, height_m)

    bmin, bmax = healthy_bmi_range(age, group, premium)
    wmin = round(bmin * height_m * height_m, 1)
    wmax = round(bmax * height_m * height_m, 1)

    actions = LANG[lang]["actions"]
    activities = LANG[lang]["activities"]

    action = ("maintain" if wmin <= weight_kg <= wmax else
              "lose" if weight_kg > wmax else "gain")
    delta = (0.0 if action == "maintain" else
             round(weight_kg - wmax, 1) if action == "lose" else
             round(wmin - weight_kg, 1))
    est_weeks = ((None, None) if action == "maintain" else
                 (max(1, int(delta / 0.5)), max(1, int(delta / 0.25)))
                 if action == "lose" else
                 (max(1, int(delta / 0.25)), max(1, int(delta / 0.5))))

    return {
        "healthy_bmi": (bmin, bmax),
        "healthy_weight": (wmin, wmax),
        "current_weight": round(weight_kg, 1),
        "current_bmi": bmi,
        "action": action,
        "delta_kg": delta,
        "est_weeks": est_weeks,
        "nutrition_tip": actions[action],
        "activity_tip": activities[action],
    }
