"""
BMI Engine Orchestrator

RU: Единый engine для расчета BMI (canonical source of truth).
EN: Unified engine for BMI calculation (canonical source of truth).

Canonical implementation: all BMI calculations must use this module.
No other calculation paths are allowed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Final, Literal, NamedTuple, TypeAlias

from core.i18n import Language, normalize_lang

if TYPE_CHECKING:
    from core.bmi.risk import WaistRiskResult

AgeBand: TypeAlias = Literal["too_young", "child", "teen", "adult", "elderly"]
BMIGroup: TypeAlias = Literal[
    "too_young",
    "child",
    "teen",
    "general",
    "athlete",
    "elderly",
    "pregnant",
]
BMICategory: TypeAlias = Literal[
    "underweight",
    "normal",
    "overweight",
    "obesity_1",
    "obesity_2",
    "obesity_3",
]

# RU: Константы доменной валидации для WHtR (parity с legacy).
# EN: Domain validation constants for WHtR (legacy parity).
_MIN_HEIGHT_M = 0.5
_MAX_HEIGHT_M = 3.0
_MAX_WAIST_CM = 300.0

# RU: "Здоровый" диапазон BMI для общего населения (WHO guidelines).
# EN: "Healthy" BMI range for general population (WHO guidelines).
# Used in legacy /plan response shape.


class HealthyBMIRange(NamedTuple):
    """Immutable BMI range with named fields (kg/m²)."""

    min: float
    max: float


HEALTHY_BMI_RANGE: Final[HealthyBMIRange] = HealthyBMIRange(18.5, 24.9)

_DEFAULT_YES_VALUES: set[str] = {
    "yes",
    "y",
    "true",
    "1",
    "да",
    "д",
    "истина",
    "si",
    "sí",
}


def _normalize_gender(gender: str | None) -> str:
    """
    RU: Нормализует gender к 'male'/'female' с parity по legacy.
    EN: Normalize gender to 'male'/'female' with legacy parity.

    Legacy nuance: uses startswith("жен") / startswith("mujer").

    IMPORTANT: Must match schema's _MALE_EXACT/_FEMALE_EXACT tokens to prevent
    contract mismatch (schema allows "woman" + pregnant, but engine treats "woman" as male).
    """
    g = (gender or "").strip().lower()
    if not g:
        # Fallback: legacy-compatible default
        return "male"

    # Female exact tokens (must match schema's _FEMALE_EXACT)
    # Check BEFORE male to avoid conflict: "f" is female, not male
    female_exact = {"female", "f", "woman", "w", "ж"}
    if g in female_exact:
        return "female"

    # Female prefixes (RU/ES startswith parity)
    if g.startswith("жен") or g.startswith("mujer"):
        return "female"

    # Male exact tokens (must match schema's _MALE_EXACT)
    male_exact = {"male", "m", "man", "м"}
    if g in male_exact:
        return "male"

    # Male prefixes (RU/ES startswith parity)
    if g.startswith("муж") or g.startswith("hombre"):
        return "male"

    # Fallback: legacy-compatible default
    return "male"


def _normalize_bool_flag(value: str | bool, yes_values: set[str] | None = None) -> bool:
    """
    RU: Нормализует флаг yes/no (pregnant/athlete и т.п.) в bool.
    EN: Normalize yes/no-ish flag to bool.

    IMPORTANT:
    - Commit 1: без regex для athlete (оставляем на Commit 2 в _auto_group()).
      Это уменьшает дублирование и риск расхождений.
    """
    if isinstance(value, bool):
        return value

    if not isinstance(value, str):
        return False

    s = value.strip().lower()
    if not s:
        return False

    allowed = yes_values if yes_values is not None else _DEFAULT_YES_VALUES
    return s in allowed


def _normalize_lang(lang: str | None) -> Language:
    """
    RU: Используем canonical normalize_lang из core.i18n (не дублируем).
    EN: Use canonical core.i18n.normalize_lang() (no duplication).

    Wrapper must not be more restrictive than delegate (core.i18n.normalize_lang accepts Optional[str]).
    """
    return normalize_lang(lang)


def _age_band(age: int) -> AgeBand:
    """
    RU: Возрастные диапазоны — канон из TODO/Qoder.
    EN: Age bands — canonical from TODO/Qoder.

    NOTE: age 19 inclusive is 'teen'; adult starts at 20.
    """
    if age < 12:
        return "too_young"
    if age == 12:
        return "child"
    if 13 <= age <= 19:
        return "teen"
    if 19 < age < 60:
        return "adult"
    return "elderly"


def _compute_bmi(weight_kg: float, height_m: float) -> float:
    """
    RU: BMI = weight_kg / (height_m ** 2), округление до 1 знака (legacy parity).
    EN: BMI = weight_kg / (height_m ** 2), rounded to 1 decimal (legacy parity).

    Domain bounds validation (10..100) делаем в orchestrator (Commit 3), не здесь.
    """
    if weight_kg <= 0:
        raise ValueError("weight_kg must be positive")
    if height_m <= 0:
        raise ValueError("height_m must be positive")

    bmi = weight_kg / (height_m**2)
    return round(bmi, 1)


def _safe_ratio_decimal(*, numer: Decimal, denom: Decimal) -> Decimal | None:
    """
    RU: Безопасное деление Decimal для controlled overflow тестирования.
    EN: Safe Decimal division for controlled overflow testing.

    Helper для тестов: принимает Decimal напрямую, ловит overflow/invalid.
    Returns None on overflow, non-finite, or zero division.
    """
    import decimal

    try:
        if denom == 0:
            return None
        value = numer / denom
        if not value.is_finite():
            return None
        return value
    except (decimal.Overflow, decimal.InvalidOperation, ZeroDivisionError):
        return None


def _compute_wht_ratio(waist_cm: float | None, height_m: float) -> float | None:
    """
    RU: WHtR = (waist_cm / 100.0) / height_m, округление до 2 знаков.
    EN: WHtR = (waist_cm / 100.0) / height_m, rounded to 2 decimals.

    Fail-soft parity:
    - invalid height or waist -> None
    - try/except for safety
    """
    if waist_cm is None:
        return None

    # Height validation (legacy parity)
    if height_m <= _MIN_HEIGHT_M or height_m > _MAX_HEIGHT_M:
        return None

    # Waist validation (legacy parity)
    if waist_cm <= 0 or waist_cm > _MAX_WAIST_CM:
        return None

    try:
        ratio = (waist_cm / 100.0) / height_m
        # Check for non-finite values (inf, nan) before rounding
        if not (ratio > 0 and ratio < float("inf")):
            return None
        return round(ratio, 2)
    except (OverflowError, ZeroDivisionError):
        # ZeroDivisionError should not occur due to height_m > 0.5 guard,
        # but handle it for robustness
        return None


def _compute_whr(waist_cm: float | None, hip_cm: float | None) -> float | None:
    """
    RU: WHR = waist_cm / hip_cm, округление до 2 знаков.
    EN: WHR = waist_cm / hip_cm, rounded to 2 decimals.

    Returns None if either waist_cm or hip_cm is None or <= 0.
    """
    if waist_cm is None or hip_cm is None:
        return None
    if waist_cm <= 0 or hip_cm <= 0:
        return None
    try:
        ratio = waist_cm / hip_cm
        return round(ratio, 2)
    except (ZeroDivisionError, OverflowError):
        return None


# --- Commit 2: Group/Category/Interpretation helpers ---

# RU/EN/ES display names — Commit 2 uses table (Commit 5 moves to i18n keys).
# EN: Display names table (Commit 5: migrate to i18n).
GROUP_DISPLAY_NAMES: dict[str, dict[Language, str]] = {
    "too_young": {"ru": "Слишком малый возраст", "en": "Too young", "es": "Demasiado joven"},
    "child": {"ru": "Ребёнок", "en": "Child", "es": "Niño/a"},
    "teen": {"ru": "Подросток", "en": "Teen", "es": "Adolescente"},
    "general": {"ru": "Общий", "en": "General", "es": "General"},
    "athlete": {"ru": "Спортсмен", "en": "Athlete", "es": "Atleta"},
    "elderly": {"ru": "Пожилой возраст", "en": "Elderly", "es": "Mayor"},
    "pregnant": {"ru": "Беременность", "en": "Pregnancy", "es": "Embarazo"},
}

# Athlete string detection (legacy parity) — strict, NOT including "спорт".
_ATHLETE_REGEX = re.compile(r"(спортсмен(ка)?|атлет(ка)?)", flags=re.IGNORECASE)

# BMI category breakpoints by (age_band, group)
# Format: list of (upper_bound_exclusive, category) tuples
# Used by both _bmi_category() and get_bmi_visual_ranges()
# Key: (age_band, group) -> list[tuple[float, BMICategory]]
# Note: elderly age_band normalizes group to "general" (elderly wins)
_BMI_BREAKPOINTS: dict[tuple[AgeBand, BMIGroup], list[tuple[float, BMICategory]]] = {
    # Elderly (age_band wins, group normalized to "general")
    ("elderly", "general"): [
        (17.5, "underweight"),
        (26.0, "normal"),
        (30.0, "overweight"),
        (35.0, "obesity_1"),
        (40.0, "obesity_2"),
        (float("inf"), "obesity_3"),
    ],
    # Athlete (adult age_band)
    ("adult", "athlete"): [
        (18.5, "underweight"),
        (27.0, "normal"),  # Key difference: 27.0 vs 25.0
        (30.0, "overweight"),
        (35.0, "obesity_1"),
        (40.0, "obesity_2"),
        (float("inf"), "obesity_3"),
    ],
    # General adult (default)
    ("adult", "general"): [
        (18.5, "underweight"),
        (25.0, "normal"),
        (30.0, "overweight"),
        (35.0, "obesity_1"),
        (40.0, "obesity_2"),
        (float("inf"), "obesity_3"),
    ],
}


def _get_bmi_breakpoints(age_band: AgeBand, group: BMIGroup) -> list[tuple[float, BMICategory]]:
    """
    RU: Возвращает breakpoints BMI для комбинации age_band и group.
    EN: Return BMI breakpoints for age_band and group combination.

    Returns list of (upper_bound_exclusive, category) tuples.

    Fallback strategy (cascading):
    1. Try (age_band, group)
    2. Try (age_band, "general")
    3. Fallback to ("adult", "general")

    Elderly normalization: if age_band == "elderly", group is normalized to "general"
    to enforce "elderly wins over group" invariant.
    """
    # Normalize: elderly age_band wins over group
    if age_band == "elderly":
        normalized_group: BMIGroup = "general"
    else:
        normalized_group = group

    # Cascading fallback
    key = (age_band, normalized_group)
    if key in _BMI_BREAKPOINTS:
        return _BMI_BREAKPOINTS[key]

    # Fallback to age_band-specific general
    general_group: BMIGroup = "general"
    key_fallback = (age_band, general_group)
    if key_fallback in _BMI_BREAKPOINTS:
        return _BMI_BREAKPOINTS[key_fallback]

    # Final fallback: adult general
    return _BMI_BREAKPOINTS[("adult", "general")]


def _auto_group(
    *,
    age: int,
    gender: str,
    pregnant: bool,
    athlete: bool,
    athlete_text: str | None = None,
) -> BMIGroup:
    """
    RU: Вычисляет группу для интерпретации BMI (Commit 2).
    EN: Compute BMI interpretation group (Commit 2).

    Canonical priorities (decisions):
    age-based bands > pregnant > athlete > general.
    - pregnant does NOT override elderly (age priority).
    - pregnant applies only to female.
    - athlete detection: boolean OR text regex/athlete keyword.
    """
    band = _age_band(age)
    if band == "too_young":
        return "too_young"
    if band == "child":
        return "child"
    if band == "teen":
        return "teen"
    if band == "elderly":
        return "elderly"

    # Adult path (20..59)
    g = _normalize_gender(gender)

    if pregnant and g == "female":
        return "pregnant"

    if athlete:
        return "athlete"

    if isinstance(athlete_text, str):
        s = athlete_text.strip().lower()
        if s == "athlete":
            return "athlete"
        if _ATHLETE_REGEX.search(s):
            return "athlete"

    return "general"


def _bmi_category(
    *,
    bmi: float,
    age: int,
    group: BMIGroup,
) -> BMICategory | None:
    """
    RU: Возвращает категорию BMI по каноническим порогам (decisions/Qoder).
    EN: Return BMI category by canonical thresholds (decisions/Qoder).

    Canon:
    - category=None only for: too_young, child, teen, pregnant
    - elderly thresholds are selected by age_band (elderly wins over athlete)
    """
    if group in {"too_young", "child", "teen", "pregnant"}:
        return None

    band = _age_band(age)
    breakpoints = _get_bmi_breakpoints(band, group)

    # Find category using breakpoints
    for upper_bound, category in breakpoints:
        if bmi < upper_bound:
            return category

    # Should never reach here (last breakpoint is inf), but safety fallback
    return "obesity_3"


def _upper_for(
    breakpoints: list[tuple[float, BMICategory]],
    target: BMICategory,
) -> float:
    """
    RU: Извлекает верхнюю границу для указанной категории из breakpoints.
    EN: Extract upper bound for specified category from breakpoints.

    Args:
        breakpoints: List of (upper_bound, category) tuples
        target: Target category to find

    Returns:
        Upper bound (exclusive) for the target category

    Raises:
        ValueError: If target category not found in breakpoints
    """
    for upper, cat in breakpoints:
        if cat == target:
            return upper
    raise ValueError(f"Missing breakpoint for {target!r}")


def get_bmi_visual_ranges(
    group: BMIGroup,
    age_band: AgeBand,
    scale_min: float = 0.0,
    scale_max: float = 60.0,
) -> list[tuple[float, float, str]] | None:
    """
    RU: Возвращает диапазоны BMI для визуализации на основе порогов группы.
    EN: Return BMI ranges for visualization based on group thresholds.

    Args:
        group: BMI group (general, athlete, elderly, etc.)
        age_band: Age band (adult, elderly, etc.)
        scale_min: Minimum BMI for visualization scale (default 0.0)
        scale_max: Maximum BMI for visualization scale (default 60.0)

    Returns:
        List of (start, end, i18n_key) tuples for visualization ranges, or None
        if group should not have visualization (category=None groups).

        Returns exactly 4 ranges:
        - (scale_min, underweight_max, "bmi.underweight")
        - (underweight_max, normal_max, "bmi.normal")
        - (normal_max, overweight_max, "bmi.overweight")
        - (overweight_max, scale_max, "bmi.obesity")

        Note: obesity_1/2/3 are aggregated into single "bmi.obesity" range.
        Obesity tiers (35.0, 40.0) are NOT used in visualization ranges.

    Returns None for groups where category=None (checked by group, not category):
    - too_young, child, teen, pregnant
    """
    # Groups without category should not have visualization (check by group, not category)
    if group in {"too_young", "child", "teen", "pregnant"}:
        return None

    breakpoints = _get_bmi_breakpoints(age_band, group)

    # Extract visualization breakpoints by category name (not index) for robustness
    underweight_max = _upper_for(breakpoints, "underweight")
    normal_max = _upper_for(breakpoints, "normal")
    overweight_max = _upper_for(breakpoints, "overweight")

    return [
        (scale_min, underweight_max, "bmi.underweight"),
        (underweight_max, normal_max, "bmi.normal"),
        (normal_max, overweight_max, "bmi.overweight"),
        (overweight_max, scale_max, "bmi.obesity"),
    ]


def _group_display_name(group: BMIGroup, lang: Language) -> str:
    """
    RU: Отображаемое имя группы (Commit 2: table; Commit 5: i18n).
    EN: Human-readable group name (Commit 2: table; Commit 5: i18n).
    """
    table = GROUP_DISPLAY_NAMES.get(group)
    if table is None:
        # Defensive fallback: shouldn't happen
        return group
    return table.get(lang, table["en"])


def _interpretation(
    *,
    category: BMICategory | None,
    note: str | None,
) -> str:
    """
    RU: Возвращает интерпретацию: "{category}. {note}" или только note если category=None.
    EN: Interpretation: "{category}. {note}" or note only if category=None.
    """
    n = (note or "").strip()
    if category is None:
        return n

    if not n:
        return str(category)

    return f"{category}. {n}"


@dataclass(frozen=True)
class BMICalculateResult:
    """Stub result dataclass for BMI calculation."""

    bmi: float
    category: str | None
    group: BMIGroup  # Matches _auto_group() return type
    group_display: str
    interpretation: str
    wht_ratio: float | None
    whr: float | None
    waist_risk: WaistRiskResult | None
    notes: tuple[str, ...]
    age_band: AgeBand


def calculate_bmi_result(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    pregnant: bool,
    athlete: bool,
    waist_cm: float | None,
    hip_cm: float | None,
    lang: str | None,
) -> BMICalculateResult:
    """
    RU: Canonical orchestrator: validation → normalization → compute → assemble.
    EN: Canonical orchestrator: validation → normalization → compute → assemble.

    Commit 3: integrates waist risk (fail-soft), notes only from waist_risk.notes.

    Args:
        weight_kg: Weight in kilograms
        height_cm: Height in centimeters
        age: Age in years
        gender: Gender ("male"/"female", will be normalized)
        pregnant: Pregnant flag (bool, normalized by router)
        athlete: Athlete flag (bool, normalized by router)
        waist_cm: Waist circumference in cm (optional)
        hip_cm: Hip circumference in cm (optional)
        lang: Language code ("ru"/"en"/"es", can be None)

    Returns:
        BMICalculateResult: BMI calculation result with all fields populated

    Raises:
        ValueError: If input validation fails (weight/height/age/BMI bounds)
    """
    # Step 1: Input validation (fail-loud)
    if weight_kg <= 0:
        raise ValueError("weight_kg must be positive")
    if height_cm <= 0:
        raise ValueError("height_cm must be positive")
    if age < 1 or age > 120:
        raise ValueError("age must be between 1 and 120")

    # Step 2: Normalization
    lang_norm = _normalize_lang(lang)
    gender_norm = _normalize_gender(gender)

    height_m = height_cm / 100.0

    # Step 3: BMI calculation
    bmi = _compute_bmi(weight_kg, height_m)

    # Step 4: BMI bounds validation (fail-loud)
    if bmi < 10.0 or bmi > 100.0:
        raise ValueError("BMI out of valid range (10-100)")

    # Step 5: Age band
    age_band = _age_band(age)

    # Step 6: Group determination (Commit 3: no athlete_text)
    group = _auto_group(
        age=age,
        gender=gender_norm,
        pregnant=pregnant,
        athlete=athlete,
        athlete_text=None,
    )

    # Step 7: Category determination
    category = _bmi_category(bmi=bmi, age=age, group=group)

    # Step 8: Group display name
    group_display = _group_display_name(group, lang_norm)

    # Step 9: WHtR calculation (fail-soft)
    wht_ratio = _compute_wht_ratio(waist_cm, height_m)

    # Step 9.5: WHR calculation (fail-soft)
    whr = _compute_whr(waist_cm, hip_cm)

    # Step 10: Waist risk calculation (fail-soft)
    waist_risk = None
    if waist_cm is not None:
        try:
            from core.bmi.risk import calculate_waist_risk  # local import by design

            # Be robust to signature drift: prefer keyword args.
            waist_risk = calculate_waist_risk(
                waist_cm=waist_cm,
                height_m=height_m,
                gender=gender_norm,
                lang=lang_norm,
            )
        except TypeError:
            # Fallback path for legacy signature variants (positional, etc.)
            try:
                from core.bmi.risk import calculate_waist_risk

                waist_risk = calculate_waist_risk(waist_cm, height_m, gender_norm, lang_norm)
            except Exception:
                waist_risk = None
        except Exception:
            waist_risk = None

    # Step 11: Notes aggregation (only from waist_risk)
    notes_list: list[str] = []
    if waist_risk is not None:
        wr_notes = getattr(waist_risk, "notes", None)
        if isinstance(wr_notes, (list, tuple)):
            # Filter only strings, keep deterministic order
            notes_list.extend([n for n in wr_notes if isinstance(n, str) and n.strip()])

    # Step 12: Interpretation formatting
    note_str = ". ".join(notes_list) if notes_list else None
    interpretation = _interpretation(category=category, note=note_str)

    # Step 13: Category string conversion
    category_str = str(category) if category is not None else None

    # Step 14: Return result
    return BMICalculateResult(
        bmi=bmi,
        category=category_str,
        group=group,
        group_display=group_display,
        interpretation=interpretation,
        wht_ratio=wht_ratio,
        whr=whr,
        waist_risk=waist_risk,
        notes=tuple(notes_list),
        age_band=age_band,
    )
