"""Exact route-level contracts for legacy targets and nutrient gaps."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import app
from app.middleware.api_tiers import TEST_KEY_PRO
from app.services import pro_nutrition_targets as service

_TARGETS_PATH = "/api/v1/premium/targets"
_STRICT_TARGETS_PATH = "/premium_targets"
_GAPS_PATH = "/api/v1/premium/gaps"
_PRO_TARGETS_PATH = "/api/v1/pro/nutrition/targets"
_AUTH_HEADER_VALUE = "targets-gaps-test-value"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("API_KEY", _AUTH_HEADER_VALUE)
    return TestClient(app)


def _headers(key: str = _AUTH_HEADER_VALUE) -> dict[str, str]:
    return {"X-API-Key": key}


def _profile(**overrides: object) -> dict[str, object]:
    profile: dict[str, object] = {
        "sex": "female",
        "age": 34,
        "height_cm": 168,
        "weight_kg": 62,
        "activity": "light",
        "goal": "maintain",
        "life_stage": "adult",
        "lang": "en",
    }
    profile.update(overrides)
    return profile


def _gaps_payload(**profile_overrides: object) -> dict[str, object]:
    return {
        "user_profile": _profile(**profile_overrides),
        "consumed_nutrients": {
            "protein_g": 10.0,
            "iron_mg": 1.0,
            "calcium_mg": 100.0,
        },
    }


@pytest.mark.parametrize(
    "profile",
    [
        _profile(goal="loss", deficit_pct=20.0),
        _profile(
            sex="male",
            age=45,
            height_cm=180,
            weight_kg=90,
            activity="very_active",
            goal="gain",
            surplus_pct=15.0,
            diet_flags=["VEGAN"],
        ),
        _profile(life_stage="pregnant", lang="ru"),
    ],
)
def test_premium_targets_real_profiles_return_exact_contract(
    client: TestClient,
    profile: dict[str, object],
) -> None:
    response = client.post(_TARGETS_PATH, headers=_headers(), json=profile)

    assert response.status_code == 200
    payload = response.json()
    assert 1200 <= payload["kcal_daily"] <= 5000
    assert payload["macros"]["protein_g"] > 0
    assert payload["priority_micros"]["iodine_ug"] > 0
    assert payload["next_best_action"]["recommended_tier"] == "PRO"


@pytest.mark.parametrize(
    "invalid_profile",
    [
        _profile(age=-5),
        _profile(activity="invalid_activity"),
        _profile(goal="loss", deficit_pct=50.0),
        {**_profile(), "unexpected": "field"},
    ],
)
def test_premium_targets_invalid_payloads_are_exact_422(
    client: TestClient,
    invalid_profile: dict[str, object],
) -> None:
    response = client.post(_TARGETS_PATH, headers=_headers(), json=invalid_profile)

    assert response.status_code == 422
    assert response.json()["detail"]


def test_pro_targets_rejects_infinite_height_before_core_builder(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core_calls: list[str] = []

    def _unexpected_builder(_profile: object) -> object:
        core_calls.append("builder")
        raise AssertionError("builder must not receive non-finite height")

    monkeypatch.setattr(
        service.nutrition_recommendations,
        "build_nutrition_targets",
        _unexpected_builder,
    )
    payload = _profile(height_cm=float("inf"))

    response = client.post(
        _PRO_TARGETS_PATH,
        headers={"X-API-Key": TEST_KEY_PRO, "Content-Type": "application/json"},
        content=json.dumps(payload, allow_nan=True),
    )

    assert response.status_code == 422
    assert any(error["loc"] == ["body", "height_cm"] for error in response.json()["detail"])
    assert core_calls == []


def test_pro_targets_rejects_huge_weight_before_core_builder(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core_calls: list[str] = []

    def _unexpected_builder(_profile: object) -> object:
        core_calls.append("builder")
        raise AssertionError("builder must not receive an overflowing weight")

    monkeypatch.setattr(
        service.nutrition_recommendations,
        "build_nutrition_targets",
        _unexpected_builder,
    )
    payload = _profile(weight_kg=10**4000)

    response = client.post(
        _PRO_TARGETS_PATH,
        headers={"X-API-Key": TEST_KEY_PRO, "Content-Type": "application/json"},
        content=json.dumps(payload),
    )

    assert response.status_code == 422
    assert any(error["loc"] == ["body", "weight_kg"] for error in response.json()["detail"])
    assert core_calls == []


def test_pro_targets_finite_measurements_still_work(client: TestClient) -> None:
    response = client.post(
        _PRO_TARGETS_PATH,
        headers={"X-API-Key": TEST_KEY_PRO},
        json=_profile(height_cm=168.0, weight_kg=62.0),
    )

    assert response.status_code == 200
    assert response.json()["kcal_daily"] > 0


def test_targets_missing_builder_preserves_alias_divergence(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service.nutrition_recommendations, "build_nutrition_targets", None)

    canonical_alias = client.post(_TARGETS_PATH, headers=_headers(), json=_profile())
    strict_legacy = client.post(_STRICT_TARGETS_PATH, headers=_headers(), json=_profile())

    assert canonical_alias.status_code == 200
    assert strict_legacy.status_code == 503
    assert strict_legacy.json() == {"detail": service.WHO_TARGETS_UNAVAILABLE_DETAIL}


@pytest.mark.parametrize(("lang", "prefix"), [("ru", "Для "), ("es", "Para ")])
def test_premium_gaps_real_profiles_use_localized_food_first_recommendations(
    client: TestClient,
    lang: str,
    prefix: str,
) -> None:
    response = client.post(
        _GAPS_PATH,
        headers=_headers(),
        json=_gaps_payload(lang=lang),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["gaps"]["iron_mg"]["priority"] == "high"
    assert payload["food_recommendations"]
    assert all(item.startswith(prefix) for item in payload["food_recommendations"])
    assert payload["adherence_score"] == 0.0


def test_premium_gaps_unavailable_analyzer_is_exact_503(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service.menu_engine, "analyze_nutrient_gaps", None)

    response = client.post(_GAPS_PATH, headers=_headers(), json=_gaps_payload())

    assert response.status_code == 503
    assert response.json() == {"detail": service.NUTRIENT_GAPS_UNAVAILABLE_DETAIL}


@pytest.mark.parametrize(
    "invalid_value",
    [
        pytest.param(-0.01, id="negative"),
        pytest.param(float("nan"), id="nan"),
        pytest.param(float("inf"), id="infinity"),
    ],
)
def test_premium_gaps_rejects_invalid_consumed_values_as_exact_400(
    client: TestClient,
    invalid_value: float,
) -> None:
    payload = _gaps_payload()
    payload["consumed_nutrients"] = {"iron_mg": invalid_value}

    response = client.post(
        _GAPS_PATH,
        headers={**_headers(), "Content-Type": "application/json"},
        content=json.dumps(payload, allow_nan=True),
    )

    assert response.status_code == 400
    assert response.json() == {"detail": service.INVALID_NUTRIENT_GAPS_INPUT_DETAIL}


def test_premium_gaps_invalid_profile_is_exact_422(client: TestClient) -> None:
    response = client.post(
        _GAPS_PATH,
        headers=_headers(),
        json=_gaps_payload(age=-10),
    )

    assert response.status_code == 422
    assert response.json()["detail"]


def test_premium_gaps_rejects_nested_infinite_weight_before_core_calls(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core_calls: list[str] = []

    def _unexpected_core_call(*_args: object) -> object:
        core_calls.append("called")
        raise AssertionError("core must not receive non-finite weight")

    monkeypatch.setattr(
        service.nutrition_recommendations,
        "build_nutrition_targets",
        _unexpected_core_call,
    )
    monkeypatch.setattr(
        service.menu_engine,
        "analyze_nutrient_gaps",
        _unexpected_core_call,
    )
    payload = _gaps_payload(weight_kg=float("inf"))

    response = client.post(
        _GAPS_PATH,
        headers={**_headers(), "Content-Type": "application/json"},
        content=json.dumps(payload, allow_nan=True),
    )

    assert response.status_code == 422
    assert any(
        error["loc"] == ["body", "user_profile", "weight_kg"] for error in response.json()["detail"]
    )
    assert core_calls == []


@pytest.mark.parametrize(
    "path",
    [_TARGETS_PATH, _STRICT_TARGETS_PATH, _GAPS_PATH],
)
@pytest.mark.parametrize("headers", [{}, _headers("wrong-key")])
def test_targets_and_gaps_api_key_guard_is_exact_403(
    client: TestClient,
    path: str,
    headers: dict[str, str],
) -> None:
    payload = _gaps_payload() if path == _GAPS_PATH else _profile()

    response = client.post(path, headers=headers, json=payload)

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("headers", "status_code", "detail", "authenticate"),
    [
        pytest.param(
            {},
            401,
            "API key required for PRO tier access",
            "ApiKey",
            id="missing",
        ),
        pytest.param(
            _headers("wrong-key"),
            403,
            "API key does not have PRO tier access",
            None,
            id="wrong",
        ),
    ],
)
def test_pro_targets_guard_rejects_before_core_builder(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    headers: dict[str, str],
    status_code: int,
    detail: str,
    authenticate: str | None,
) -> None:
    core_calls: list[str] = []

    def _unexpected_builder(_profile: object) -> object:
        core_calls.append("builder")
        raise AssertionError("builder must not run before PRO authorization")

    monkeypatch.setattr(
        service.nutrition_recommendations,
        "build_nutrition_targets",
        _unexpected_builder,
    )

    response = client.post(_PRO_TARGETS_PATH, headers=headers, json=_profile())

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert response.headers.get("www-authenticate") == authenticate
    assert core_calls == []
