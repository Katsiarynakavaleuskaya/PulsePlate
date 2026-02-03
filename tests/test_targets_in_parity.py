import math

import pytest
from pydantic import ValidationError

import legacy_app
from app.schemas.nutrition_targets import TargetsIn as CanonicalTargetsIn


def _weekly_menu_stub(*args: object, **kwargs: object) -> object:
    """RU: Заглушка weekly menu для e2e-ish legacy endpoint tests.
    EN: Weekly menu stub for e2e-ish legacy endpoint tests.
    """

    class _WeekMenu:
        weekly_coverage = {"protein": 0.9}
        shopping_list = {"chicken": 1.0}
        total_cost = 10.0
        adherence_score = 0.5
        daily_menus: list[object] = []

    return _WeekMenu()


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


def test_legacy_week_endpoint_accepts_numeric_string_targets(
    client, api_key: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RU: Legacy endpoint не должен ломаться при targets с числовыми строками.
    EN: Legacy endpoint must not break when targets contains numeric strings.
    """

    import app as app_module

    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setattr(app_module, "make_weekly_menu", _weekly_menu_stub)

    payload = {
        "sex": "male",
        "age": 30,
        "height_cm": 175,
        "weight_kg": 70,
        "activity": "moderate",
        "targets": {
            "kcal": 2000,
            "macros": {"protein_g": "150.0"},
            "micro": {"vitamin_c_mg": "90.0"},
            "water_ml": 2000,
        },
    }
    r = client.post("/api/v1/premium/plan/week", json=payload, headers={"X-API-Key": api_key})
    assert r.status_code == 200, r.text


@pytest.mark.parametrize(
    "bad_macros",
    [
        {"protein_g": True},
        # JSON payload cannot carry NaN/Inf floats; send strings to hit the same validator branch.
        {"protein_g": "nan"},
        {"protein_g": "inf"},
        {"protein_g": -1.0},
    ],
)
def test_legacy_week_endpoint_rejects_invalid_targets_values(
    client,
    api_key: str,
    monkeypatch: pytest.MonkeyPatch,
    bad_macros: dict[str, object],
) -> None:
    """RU: Legacy endpoint отклоняет невалидные значения в structured targets (contract no-break).
    EN: Legacy endpoint rejects invalid values in structured targets (contract no-break).
    """

    import app as app_module

    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setattr(app_module, "make_weekly_menu", _weekly_menu_stub)

    payload = {
        "sex": "male",
        "age": 30,
        "height_cm": 175,
        "weight_kg": 70,
        "activity": "moderate",
        "targets": {
            "kcal": 2000,
            "macros": bad_macros,
            "micro": {"vitamin_c_mg": 90.0},
            "water_ml": 2000,
        },
    }
    r = client.post("/api/v1/premium/plan/week", json=payload, headers={"X-API-Key": api_key})
    assert r.status_code == 422, r.text
