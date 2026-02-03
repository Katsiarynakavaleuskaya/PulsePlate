import math

import pytest
from pydantic import ValidationError

import legacy_app
from app.schemas.nutrition_targets import TargetsIn as CanonicalTargetsIn


def test_legacy_targets_in_is_canonical_alias() -> None:
    """RU: Legacy TargetsIn должен быть alias на canonical (без drift).
    EN: Legacy TargetsIn must be an alias to canonical (no drift).
    """

    assert legacy_app.TargetsIn is CanonicalTargetsIn


@pytest.mark.parametrize(
    "payload",
    [
        {
            "kcal": 2000,
            "macros": {"protein_g": "150.0", "fat_g": "65.0", "carbs_g": "250.0"},
            "micro": {"vitamin_c_mg": "90.0"},
            "water_ml": 2000,
        },
        {
            "kcal": 2000,
            "macros": {"protein_g": 150.0},
            "micro": {"vitamin_c_mg": 90.0},
            "water_ml": 2000,
        },
    ],
)
def test_targets_in_accepts_numeric_strings(payload: dict[str, object]) -> None:
    """RU: Числовые строки (например, '150.0') валидны.
    EN: Numeric strings (e.g. '150.0') are valid.
    """

    out_canonical = CanonicalTargetsIn.model_validate(payload)
    out_legacy = legacy_app.TargetsIn.model_validate(payload)

    assert out_canonical.model_dump() == out_legacy.model_dump()
    assert out_canonical.kcal == 2000
    assert out_canonical.macros["protein_g"] == 150.0


@pytest.mark.parametrize(
    "payload",
    [
        # bool must be rejected explicitly (bool is subclass of int)
        {
            "kcal": 2000,
            "macros": {"protein_g": True},
            "micro": {"vitamin_c_mg": 90.0},
            "water_ml": 2000,
        },
        # NaN must be rejected
        {
            "kcal": 2000,
            "macros": {"protein_g": math.nan},
            "micro": {"vitamin_c_mg": 90.0},
            "water_ml": 2000,
        },
        # Infinity must be rejected
        {
            "kcal": 2000,
            "macros": {"protein_g": math.inf},
            "micro": {"vitamin_c_mg": 90.0},
            "water_ml": 2000,
        },
        # negative must be rejected
        {
            "kcal": 2000,
            "macros": {"protein_g": -1.0},
            "micro": {"vitamin_c_mg": 90.0},
            "water_ml": 2000,
        },
    ],
)
def test_targets_in_rejects_invalid_values(payload: dict[str, object]) -> None:
    """RU: Невалидные значения должны падать детерминированно.
    EN: Invalid values must fail deterministically.
    """

    with pytest.raises(ValidationError):
        CanonicalTargetsIn.model_validate(payload)

    with pytest.raises(ValidationError):
        legacy_app.TargetsIn.model_validate(payload)
