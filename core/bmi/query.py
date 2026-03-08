"""Helpers for lightweight BMI query handling inside canonical core/bmi surface."""

from __future__ import annotations

import re

from core.bmi.engine import _compute_bmi
from core.i18n import normalize_lang

_MIN_HUMAN_HEIGHT_M = 0.5
_MAX_HUMAN_HEIGHT_M = 3.0

_MISSING_INPUT_MESSAGES = {
    "en": "To calculate BMI, send both weight and height, for example: 70kg and 175cm.",
    "ru": "Чтобы рассчитать BMI, отправьте и вес, и рост, например: 70 кг и 175 см.",
    "es": "Para calcular el BMI, envía tanto el peso como la altura, por ejemplo: 70kg y 175cm.",
}

_BMI_RESULT_MESSAGES = {
    "en": "Your estimated BMI is {bmi}. For interpretation, compare it with standard BMI ranges.",
    "ru": "Ваш примерный BMI — {bmi}. Для интерпретации сравните результат со стандартными диапазонами BMI.",
    "es": "Tu BMI estimado es {bmi}. Para interpretarlo, compáralo con los rangos estándar de BMI.",
}


def extract_bmi_inputs(query: str) -> tuple[float, float] | None:
    """Extract weight and height from a free-form BMI query."""

    weight_match = re.search(r"(\d+\.?\d*)\s*kg\b", query, re.IGNORECASE)
    height_cm_match = re.search(r"(\d+\.?\d*)\s*cm\b", query, re.IGNORECASE)
    height_m_match = re.search(r"(\d+\.?\d*)\s*m\b", query, re.IGNORECASE)
    if weight_match is None:
        return None
    weight_kg = float(weight_match.group(1))
    height_m: float | None = None
    if height_cm_match is not None:
        height_m = float(height_cm_match.group(1)) / 100.0
    elif height_m_match is not None:
        height_m = float(height_m_match.group(1))
    if height_m is None or not (_MIN_HUMAN_HEIGHT_M < height_m <= _MAX_HUMAN_HEIGHT_M):
        return None
    return weight_kg, height_m


def render_bmi_query_answer(query: str, *, lang: str | None) -> str:
    """Render a localized BMI answer from free-form query text."""

    lang_norm = normalize_lang(lang)
    bmi_inputs = extract_bmi_inputs(query)
    if bmi_inputs is None:
        return _MISSING_INPUT_MESSAGES[lang_norm]

    weight_kg, height_m = bmi_inputs
    bmi = _compute_bmi(weight_kg, height_m)
    return _BMI_RESULT_MESSAGES[lang_norm].format(bmi=bmi)
