"""Helpers for lightweight BMI query handling inside canonical core/bmi surface."""

from __future__ import annotations

from typing import cast

from core.bmi.engine import _compute_bmi
from core.i18n import normalize_lang

_MIN_HUMAN_HEIGHT_M = 0.5
_MAX_HUMAN_HEIGHT_M = 3.0
# Bound free-form query parsing to keep matching linear-time and fail closed.
_MAX_BMI_QUERY_CHARS = 256
_MAX_INTEGER_DIGITS = 6
_MAX_FRACTION_DIGITS = 4

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

_WEIGHT_UNITS = ("kg", "кг")
_HEIGHT_CM_UNITS = ("cm", "см")
_HEIGHT_M_UNITS = ("m", "м")


def _is_unit_boundary(char: str) -> bool:
    """Return True when char cannot continue a unit token."""

    return not (char.isalnum() or char == "_")


def _is_ascii_digit(char: str) -> bool:
    """Return True for ASCII digits only (Unicode digits are rejected)."""

    return "0" <= char <= "9"


def _is_non_ascii_digit(char: str) -> bool:
    """Return True for Unicode digit-like chars that must fail closed."""

    return char.isdigit() and not _is_ascii_digit(char)


def _parse_bounded_number(text: str, start: int) -> tuple[float, int] | None:
    """Parse a bounded decimal number starting at ``start`` without regex."""

    index = start
    length = len(text)
    integer_digits = 0
    while index < length and _is_ascii_digit(text[index]):
        integer_digits += 1
        if integer_digits > _MAX_INTEGER_DIGITS:
            return None
        index += 1
    if integer_digits == 0:
        return None

    if index < length and text[index] == ".":
        index += 1
        fraction_digits = 0
        while index < length and _is_ascii_digit(text[index]):
            fraction_digits += 1
            if fraction_digits > _MAX_FRACTION_DIGITS:
                return None
            index += 1
        if fraction_digits == 0:
            return None

    # ASCII digit/dot tokens are always float()-safe; no Unicode digit path remains.
    return float(text[start:index]), index


def _next_valid_unit_match(
    lowered: str,
    units: tuple[str, ...],
    search_from: int,
) -> tuple[int, str] | None:
    """Return the earliest boundary-valid unit match at or after ``search_from``."""

    next_unit_at: int | None = None
    matched_unit = ""
    for unit in units:
        cursor = search_from
        while cursor < len(lowered):
            unit_at = lowered.find(unit, cursor)
            if unit_at < 0:
                break
            unit_end = unit_at + len(unit)
            if unit_end < len(lowered) and not _is_unit_boundary(lowered[unit_end]):
                cursor = unit_end
                continue
            if next_unit_at is None or unit_at < next_unit_at:
                next_unit_at = unit_at
                matched_unit = unit
            break
    if next_unit_at is None:
        return None
    return next_unit_at, matched_unit


def _find_number_before_unit(text: str, units: tuple[str, ...]) -> float | None:
    """Find the first bounded number immediately before one of ``units``."""

    lowered = text.lower()
    search_from = 0
    while search_from < len(lowered):
        unit_match = _next_valid_unit_match(lowered, units, search_from)
        if unit_match is None:
            return None
        next_unit_at, matched_unit = unit_match

        index = next_unit_at
        while index > 0 and text[index - 1].isspace():
            index -= 1
        end = index
        while index > 0 and (_is_ascii_digit(text[index - 1]) or text[index - 1] == "."):
            index -= 1
        # Reject mixed Unicode+ASCII numeric tokens (e.g. "¹70kg"): the ASCII
        # suffix must not be accepted when a non-ASCII digit immediately precedes.
        if index > 0 and _is_non_ascii_digit(text[index - 1]):
            search_from = next_unit_at + len(matched_unit)
            continue
        parsed = _parse_bounded_number(text, index)

        if parsed is not None and parsed[1] == end:
            return parsed[0]
        search_from = next_unit_at + len(matched_unit)
    return None


def extract_bmi_inputs(query: str) -> tuple[float, float] | None:
    """Extract weight and height from a free-form BMI query."""

    if len(query) > _MAX_BMI_QUERY_CHARS:
        return None

    normalized_query = query.replace(",", ".")
    weight_kg = _find_number_before_unit(normalized_query, _WEIGHT_UNITS)
    if weight_kg is None or weight_kg <= 0:
        return None

    height_cm = _find_number_before_unit(normalized_query, _HEIGHT_CM_UNITS)
    height_m: float | None = None
    if height_cm is not None:
        height_m = height_cm / 100.0
    else:
        height_m = _find_number_before_unit(normalized_query, _HEIGHT_M_UNITS)

    if height_m is None or not (_MIN_HUMAN_HEIGHT_M < height_m <= _MAX_HUMAN_HEIGHT_M):
        return None
    return weight_kg, height_m


def render_bmi_query_answer(query: str, *, lang: str | None) -> str:
    """Render a localized BMI answer from free-form query text."""

    lang_norm = cast(str, normalize_lang(lang))
    bmi_inputs = extract_bmi_inputs(query)
    if bmi_inputs is None:
        return _MISSING_INPUT_MESSAGES[lang_norm]

    weight_kg, height_m = bmi_inputs
    bmi = _compute_bmi(weight_kg, height_m)
    return _BMI_RESULT_MESSAGES[lang_norm].format(bmi=bmi)
