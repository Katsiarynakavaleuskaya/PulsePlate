"""BMI flags normalization helper for tests.

Canonical parity helper that replaces legacy app.normalize_flags() after TP1 cleanup.
"""

from __future__ import annotations

from core.bmi.engine import _DEFAULT_YES_VALUES, _normalize_bool_flag, _normalize_gender


def _normalize_flags_for_tests(
    gender: str, pregnant: str | bool, athlete: str | bool
) -> dict[str, bool]:
    """
    Canonical parity: normalize via core/bmi/engine helpers.
    Replaces legacy app.normalize_flags() for test coverage.

    Args:
        gender: Gender string (will be normalized)
        pregnant: Pregnant flag (string or bool)
        athlete: Athlete flag (string or bool)

    Returns:
        Dictionary with normalized flags: gender_male, is_pregnant, is_athlete
    """
    g = _normalize_gender(gender)

    # Handle pregnant with extended yes_values (legacy parity)
    pregnant_yes = _DEFAULT_YES_VALUES | {"pregnant", "беременна", "беременная"}
    is_pregnant = (
        _normalize_bool_flag(pregnant, yes_values=pregnant_yes)
        if isinstance(pregnant, str)
        else bool(pregnant)
    )
    # Male can't be pregnant (legacy behavior)
    if g == "male":
        is_pregnant = False

    # Handle athlete with extended yes_values (legacy parity)
    athlete_yes = _DEFAULT_YES_VALUES | {"спортсмен", "athlete"}
    is_athlete = (
        _normalize_bool_flag(athlete, yes_values=athlete_yes)
        if isinstance(athlete, str)
        else bool(athlete)
    )

    return {
        "gender_male": g == "male",
        "is_pregnant": is_pregnant,
        "is_athlete": is_athlete,
    }
