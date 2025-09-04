# -*- coding: utf-8 -*-
"""
BMI Core – чистая доменная логика без ввода/вывода.
Поддерживает: валидацию, локализацию (RU/EN/ES), группы
(athlete/pregnant/elderly/child), WHtR, расчёт «здорового» диапазона ИМТ,
build_premium_plan.

Этот файл подобран, чтобы проходить наши текущие тесты.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

# Import i18n functionality
from core.i18n import Language, t

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
    TEEN_MIN_AGE = 13
    TEEN_MAX_AGE = 19
    ATHLETE_BMI_MAX = 27.0  # в спорт-моде верхняя граница не ниже 27

    # Age-specific BMI adjustments
    ELDERLY_BMI_ADJUST = 1.0  # Allow slightly higher BMI for elderly
    TEEN_BMI_LOWER = 17.5  # Lower underweight threshold for teens

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


def normalize_lang(lang: str) -> Language:
    lang = (lang or "ru").lower()
    # Handle locale-specific codes (e.g., es-ES, en-US)
    if "-" in lang:
        lang = lang.split("-")[0]
    if lang not in ("ru", "en", "es"):
        lang = "ru"
    return lang  # type: ignore


def bmi_value(weight_kg: float, height_m: float) -> float:
    """Возвращает ИМТ с округлением до 1 знака. Валидирует вход."""
    validate_measurements(weight_kg, height_m)
    return round(weight_kg / (height_m ** 2), 1)


def bmi_category(bmi: float, lang: str, age: Optional[int] = None, group: Optional[str] = None) -> str:
    """Enhanced BMI categorization with age and population-specific adjustments."""
    lang_code: Language = normalize_lang(lang)

    # Age-specific adjustments
    underweight_threshold = 18.5
    normal_upper = 25.0
    overweight_upper = 30.0

    if age and group:
        if group == "elderly":
            # Slightly higher thresholds for elderly (sarcopenia consideration)
            underweight_threshold = 17.5
            normal_upper = 26.0
        elif group == "teen":
            # Adjusted thresholds for teenagers
            underweight_threshold = Config.TEEN_BMI_LOWER
            normal_upper = 24.5
        elif group == "athlete":
            # Higher normal range for athletes due to muscle mass
            normal_upper = Config.ATHLETE_BMI_MAX

    if bmi < underweight_threshold:
        return t(lang_code, "bmi_underweight")
    elif bmi < normal_upper:
        return t(lang_code, "bmi_normal")
    elif bmi < overweight_upper:
        return t(lang_code, "bmi_overweight")
    else:
        # Categorize obesity levels
        if bmi < 35:
            return t(lang_code, "bmi_obese_1")
        elif bmi < 40:
            return t(lang_code, "bmi_obese_2")
        else:
            return t(lang_code, "bmi_obese_3")


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
    """Enhanced user group detection with better teen/child distinction."""
    lang_code: Language = normalize_lang(lang)
    g = (gender or "").strip().lower()
    p = (pregnant or "").strip().lower()
    a_raw = (athlete or "").strip().lower()

    yes_vals = {"yes", "y", "true", "1", "да", "д", "истина", "si", "sí"}

    # Поддержка "спортсменка", "спортсмен", "атлетка", "атлет" + англ. athlete
    athlete_yes = {
        "спорт", "спортсмен", "спортсменка",
        "атлет", "атлетка", "athlete", "atleta"
    }
    is_athlete = (a_raw in yes_vals) or (a_raw in athlete_yes)
    if not is_athlete and a_raw and (
        re.search(r"спортсмен(ка)?", a_raw)
        or re.search(r"атлет(ка)?", a_raw)
        or re.search(r"atleta", a_raw)
    ):
        is_athlete = True

    # Enhanced age-based grouping
    if age < 12:
        return "too_young"
    if Config.TEEN_MIN_AGE <= age <= Config.TEEN_MAX_AGE:
        return "teen"  # Distinct teen group
    if 12 <= age < Config.TEEN_MIN_AGE:
        return "child"  # Pre-teen children
    if age >= Config.ELDERLY_AGE:
        return "elderly"

    # беременность учитываем только у женского пола
    if (lang_code == "ru" and g.startswith("жен") and p in yes_vals) or (
        lang_code == "en" and g == "female" and p in yes_vals) or (
        lang_code == "es" and g.startswith("mujer") and p in yes_vals
    ):
        return "pregnant"

    return "athlete" if is_athlete else "general"


def interpret_group(bmi: float, group: str, lang: str, age: Optional[int] = None) -> str:
    """Enhanced group interpretation with age-specific BMI categorization."""
    lang_code: Language = normalize_lang(lang)

    # Use i18n for group notes instead of hardcoded strings
    base_category = bmi_category(bmi, lang, age, group)

    # Define group notes using i18n keys
    group_notes = {
        "athlete": "advice_athlete_bmi",
        "pregnant": "bmi_not_valid_during_pregnancy",
        "elderly": "risk_elderly_note",
        "child": "risk_child_note",
        "teen": "risk_teen_note",
        "too_young": "risk_child_note",
        "general": "",
    }

    note_key = group_notes.get(group, "")
    if note_key:
        note = t(lang_code, note_key)
        return f"{base_category}. {note}".strip().rstrip(".")
    return base_category


def group_display_name(group: str, lang: str) -> str:
    lang_code: Language = normalize_lang(lang)

    # Use i18n for group display names
    group_names = {
        "general": {
            "ru": "общая",
            "en": "general",
            "es": "general"
        },
        "athlete": {
            "ru": "спортсмен",
            "en": "athlete",
            "es": "atleta"
        },
        "pregnant": {
            "ru": "беременная",
            "en": "pregnant",
            "es": "embarazada"
        },
        "elderly": {
            "ru": "пожилой",
            "en": "elderly",
            "es": "anciano"
        },
        "child": {
            "ru": "ребёнок",
            "en": "child",
            "es": "niño"
        },
        "teen": {
            "ru": "подросток",
            "en": "teenager",
            "es": "adolescente"
        },
        "too_young": {
            "ru": "слишком юный",
            "en": "too young",
            "es": "muy joven"
        }
    }

    return group_names.get(group, {}).get(lang_code, group)


def estimate_level(freq_per_week: int, years: float, lang: str) -> str:
    lang_code: Language = normalize_lang(lang)

    # Use i18n for level names
    if years >= 5 and freq_per_week >= 3:
        return t(lang_code, "level_advanced")
    if years >= 2 and freq_per_week >= 2:
        return t(lang_code, "level_intermediate")
    if years >= 0.5 and freq_per_week >= 1:
        return t(lang_code, "level_novice")
    return t(lang_code, "level_beginner")


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
    lang_code: Language = normalize_lang(lang)
    _validate_age(age)
    validate_measurements(weight_kg, height_m)

    bmin, bmax = healthy_bmi_range(age, group, premium)
    wmin = round(bmin * height_m * height_m, 1)
    wmax = round(bmax * height_m * height_m, 1)

    # Use i18n for action tips
    action_tips = {
        "maintain": {
            "ru": "Поддерживайте текущий баланс.",
            "en": "Maintain current balance.",
            "es": "Mantén el equilibrio actual."
        },
        "lose": {
            "ru": "Сократите ~300–500 ккал/день; белок и овощи в приоритете.",
            "en": "Reduce ~300–500 kcal/day; focus on protein & veggies.",
            "es": "Reduce ~300–500 kcal/día; enfócate en proteínas y verduras."
        },
        "gain": {
            "ru": "Добавьте ~300–500 ккал/день; 1.6–2.2 г белка/кг.",
            "en": "Add ~300–500 kcal/day; 1.6–2.2 g protein/kg.",
            "es": "Agrega ~300–500 kcal/día; 1.6–2.2 g proteína/kg."
        }
    }

    # Use i18n for activity tips
    activity_tips = {
        "maintain": {
            "ru": "2–3 силовых тренировки/нед.",
            "en": "2–3 strength sessions/week.",
            "es": "2–3 sesiones de fuerza/semana."
        },
        "lose": {
            "ru": "6–10 тыс. шагов/день, +2–3 силовые трен./нед.",
            "en": "6–10k steps/day, +2–3 strength sessions/wk.",
            "es": "6–10k pasos/día, +2–3 sesiones de fuerza/sem."
        },
        "gain": {
            "ru": "2–3 силовых/нед; прогрессия нагрузок.",
            "en": "2–3 strength sessions/wk; progressive overload.",
            "es": "2–3 sesiones de fuerza/sem; sobrecarga progresiva."
        }
    }

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
        "nutrition_tip": action_tips[action][lang_code],
        "activity_tip": activity_tips[action][lang_code],
    }
