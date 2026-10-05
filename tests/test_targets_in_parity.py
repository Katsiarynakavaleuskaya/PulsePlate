import math
from collections import UserDict
from collections.abc import Callable, Mapping
from types import MappingProxyType
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import legacy_app
import app.routers.legacy_premium_weekly_plan as weekly_plan_router
import app.routers.premium_week as premium_week_router
import app.routers.pro as pro_router
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
        # micro invalid (negative)
        {
            "kcal": 2000,
            "macros": {"protein_g": 150.0},
            "micro": {"vitamin_c_mg": -1.0},
            "water_ml": 2000,
        },
        # water_ml invalid (negative)
        {
            "kcal": 2000,
            "macros": {"protein_g": 150.0},
            "micro": {"vitamin_c_mg": 90.0},
            "water_ml": -1,
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


@pytest.mark.parametrize("field", ("macros", "micro"))
@pytest.mark.parametrize(
    "bad_value",
    ([], None, "private-structured-target-marker", True, 42, {"amount": 10**400}),
    ids=("list", "null", "string", "boolean", "number", "overflow"),
)
def test_targets_in_rejects_malformed_mapping_or_overflow(field: str, bad_value: object) -> None:
    payload: dict[str, object] = {
        "kcal": 2000,
        "macros": {"protein_g": 150.0},
        "micro": {"vitamin_c_mg": 90.0},
    }
    payload[field] = bad_value

    with pytest.raises(ValidationError):
        CanonicalTargetsIn.model_validate(payload)
    with pytest.raises(ValidationError):
        legacy_app.TargetsIn.model_validate(payload)


@pytest.mark.parametrize("mapping_factory", (MappingProxyType, UserDict))
def test_targets_in_preserves_supported_mappings_and_zero(
    mapping_factory: Callable[[dict[str, object]], Mapping[str, object]],
) -> None:
    mapping = mapping_factory({"protein_g": "150.0", "optional_g": 0})
    targets = CanonicalTargetsIn.model_validate(
        {"kcal": 2000, "macros": mapping, "micro": {}, "water_ml": 0}
    )

    assert targets.macros == {"protein_g": 150.0, "optional_g": 0.0}
    assert targets.micro == {}
    assert targets.water_ml == 0


@pytest.mark.parametrize("field", ("macros", "micro"))
@pytest.mark.parametrize(
    "bad_value",
    ([], None, "private-structured-target-marker", True, 42, {"amount": 10**400}),
    ids=("list", "null", "string", "boolean", "number", "overflow"),
)
@pytest.mark.parametrize(
    ("route", "module", "getter_name"),
    (
        ("/api/v1/pro/meal/weekly", pro_router, "get_food_db"),
        ("/api/v1/premium/plan/week-flexible", premium_week_router, "_get_food_db"),
    ),
    ids=("pro", "flexible"),
)
def test_weekly_routes_reject_invalid_targets_before_work(
    client: TestClient,
    pro_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    route: str,
    module: object,
    getter_name: str,
    field: str,
    bad_value: object,
) -> None:
    getter = Mock()
    monkeypatch.setattr(module, getter_name, getter)
    targets: dict[str, object] = {
        "kcal": 2000,
        "macros": {"protein_g": 150.0},
        "micro": {"vitamin_c_mg": 90.0},
    }
    targets[field] = bad_value

    response = client.post(route, json={"targets": targets}, headers=pro_headers)

    assert response.status_code == 422, response.text
    assert response.headers.get("Content-Type", "").startswith("application/json")
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert len(detail) == 1
    assert detail[0]["loc"] == ["body", "targets", field]
    getter.assert_not_called()


def test_legacy_week_endpoint_accepts_numeric_string_targets(
    client: TestClient, vip_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """RU: Legacy endpoint не должен ломаться при targets с числовыми строками.
    EN: Legacy endpoint must not break when targets contains numeric strings.
    """

    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    # Legacy API-key guard compares against env API_KEY; align it to the VIP test key.
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    monkeypatch.setattr(
        weekly_plan_router,
        "get_weekly_menu_builder",
        lambda: _weekly_menu_stub,
    )

    payload = {
        "sex": "male",
        "age": 30,
        "height_cm": 175,
        "weight_kg": 70,
        "activity": "moderate",
        "goal": "maintain",
        "targets": {
            "kcal": 2000,
            "macros": {"protein_g": "150.0"},
            "micro": {"vitamin_c_mg": "90.0"},
            "water_ml": 2000,
        },
    }
    r = client.post("/api/v1/premium/plan/week", json=payload, headers=vip_headers)
    assert r.status_code == 200, r.text

    data = r.json()
    assert isinstance(data, dict)
    for key in ("weekly_coverage", "shopping_list", "total_cost"):
        assert key in data
    assert isinstance(data["weekly_coverage"], dict)
    assert isinstance(data["shopping_list"], dict)
    assert isinstance(data["total_cost"], (int, float))


@pytest.mark.parametrize(
    "bad_targets",
    [
        {"macros": {"protein_g": True}},
        {"micro": {"vitamin_c_mg": -1.0}},
        {"water_ml": -1},
    ],
)
def test_legacy_week_endpoint_rejects_invalid_targets_values(
    client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    bad_targets: dict[str, object],
) -> None:
    """RU: Legacy endpoint отклоняет невалидные значения в structured targets (contract no-break).
    EN: Legacy endpoint rejects invalid values in structured targets (contract no-break).
    """

    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", vip_headers["X-API-Key"])
    monkeypatch.setattr(
        weekly_plan_router,
        "get_weekly_menu_builder",
        lambda: _weekly_menu_stub,
    )

    targets: dict[str, object] = {
        "kcal": 2000,
        "macros": {"protein_g": 150.0},
        "micro": {"vitamin_c_mg": 90.0},
        "water_ml": 2000,
    }
    targets.update(bad_targets)

    payload: dict[str, object] = {
        "sex": "male",
        "age": 30,
        "height_cm": 175,
        "weight_kg": 70,
        "activity": "moderate",
        "goal": "maintain",
        "targets": targets,
    }
    r = client.post("/api/v1/premium/plan/week", json=payload, headers=vip_headers)
    assert r.status_code == 422, r.text
