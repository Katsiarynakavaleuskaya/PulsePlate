# -*- coding: utf-8 -*-
"""
RU: Контрактные тесты для поля visualization в BMICalculateResponse.
EN: Contract tests for BMICalculateResponse.visualization.

Важно:
- Не тестируем "математику" BMI (это покрыто engine/визуализацией).
- Тестируем структуру и инварианты контракта ответа для клиентов (iOS/Web).

Contract invariants tested:
1. Structure: visualization field exists, has correct shape when not null
2. Ranges: exactly 4, sorted, contiguous, cover [min, max]
3. Group awareness: athlete vs adult ranges differ
4. Null cases: visualization is null for category=None groups
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


def _valid_payload(**overrides: Any) -> dict[str, Any]:
    """
    RU: Валидный payload для BMICalculateRequest (совместим с существующими тестами).
    EN: Valid payload for BMICalculateRequest (compatible with existing tests).
    """
    base: dict[str, Any] = {
        "weight_kg": 70.0,
        "height_cm": 170.0,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "lang": "en",
    }
    base.update(overrides)
    return base


def _post_bmi(client: TestClient, payload: dict[str, Any]) -> dict[str, Any]:
    """
    RU: POST helper для BMI calculate endpoint.
    EN: POST helper for BMI calculate endpoint.
    """
    r = client.post("/api/v1/bmi/calculate", json=payload)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    return r.json()


def _assert_ranges_invariants(spec: dict[str, Any]) -> None:
    """
    RU: Проверка инвариантов диапазонов шкалы.
    EN: Validate scale range invariants.

    Contract:
    - Exactly 4 ranges
    - Sorted by 'from' (ascending)
    - Contiguous (no gaps)
    - Covers [min, max] completely
    """
    assert spec["min"] < spec["max"], "min must be less than max"
    ranges = spec["ranges"]
    assert isinstance(ranges, list), "ranges must be a list"
    assert len(ranges) == 4, f"Expected exactly 4 ranges, got {len(ranges)}"

    # Sorted + contiguous + covers [min, max]
    # Use pytest.approx for float comparisons (handles precision artifacts)
    assert ranges[0]["from"] == pytest.approx(spec["min"]), "First range must start at min"
    assert ranges[-1]["to"] == pytest.approx(spec["max"]), "Last range must end at max"

    prev_to = None
    for i, rr in enumerate(ranges):
        assert (
            rr["from"] < rr["to"]
        ), f"Range {i}: from ({rr['from']}) must be less than to ({rr['to']})"
        assert isinstance(rr["key"], str) and rr["key"], f"Range {i}: key must be non-empty string"
        if i == 0:
            prev_to = rr["to"]
            continue
        # Use pytest.approx for float comparison (handles precision artifacts)
        assert rr["from"] == pytest.approx(
            prev_to
        ), f"Range {i}: from ({rr['from']}) must equal previous to ({prev_to})"
        prev_to = rr["to"]

    # Marker consistency
    assert "marker" in spec, "marker field must exist"
    assert isinstance(spec["marker"], dict), "marker must be a dict"
    assert "value" in spec["marker"], "marker must have 'value' field"
    # Use pytest.approx for float comparison (handles precision)
    assert (
        pytest.approx(spec["bmi"], rel=0, abs=1e-6) == spec["marker"]["value"]
    ), f"marker.value ({spec['marker']['value']}) must equal bmi ({spec['bmi']})"


def _find_range_to(spec: dict[str, Any], key: str) -> float:
    """
    RU: Найти верхнюю границу диапазона по i18n ключу.
    EN: Find range upper bound by i18n key.
    """
    for rr in spec["ranges"]:
        if rr["key"] == key:
            return float(rr["to"])
    raise AssertionError(f"Range key not found: {key}")


def test_visualization_contract_adult_has_spec(client: TestClient) -> None:
    """
    RU: Контракт: adult group возвращает visualization spec с корректной структурой.
    EN: Contract: adult group returns visualization spec with correct structure.
    """
    payload = _valid_payload(
        weight_kg=70.0,
        height_cm=175.0,
        age=30,  # adult
        gender="male",
        athlete="no",
    )

    data = _post_bmi(client, payload)
    spec = data.get("visualization")

    # Contract: visualization exists and is not null for adult
    assert spec is not None, "visualization must not be null for adult group"
    assert spec["kind"] == "bmi_scale_v1", "kind must be 'bmi_scale_v1'"
    assert isinstance(spec["bmi"], (int, float)), "bmi must be a number"
    assert isinstance(spec["min"], (int, float)), "min must be a number"
    assert isinstance(spec["max"], (int, float)), "max must be a number"

    # Contract: ranges structure
    _assert_ranges_invariants(spec)


def test_visualization_contract_child_is_null(client: TestClient) -> None:
    """
    RU: Контракт: child group (age 12) возвращает visualization null.
    EN: Contract: child group (age 12) returns visualization null.
    """
    payload = _valid_payload(
        weight_kg=40.0,
        height_cm=140.0,
        age=12,  # child (age == 12 maps to "child" age_band)
        gender="male",
    )

    data = _post_bmi(client, payload)

    # Contract: visualization is null for child (category=None group)
    assert "visualization" in data, "visualization field must exist in response"
    assert data["visualization"] is None, "visualization must be null for child group"
    # Verify category is None (for documentation)
    assert data.get("category") is None, "category must be None for child group"


def test_visualization_contract_teen_is_null(client: TestClient) -> None:
    """
    RU: Контракт: teen group (age 13-19) возвращает visualization null.
    EN: Contract: teen group (age 13-19) returns visualization null.
    """
    payload = _valid_payload(
        weight_kg=50.0,
        height_cm=160.0,
        age=16,  # teen (13 <= age <= 19)
        gender="female",
    )

    data = _post_bmi(client, payload)

    # Contract: visualization is null for teen (category=None group)
    assert "visualization" in data, "visualization field must exist in response"
    assert data["visualization"] is None, "visualization must be null for teen group"
    assert data.get("category") is None, "category must be None for teen group"


def test_visualization_contract_pregnant_is_null(client: TestClient) -> None:
    """
    RU: Контракт: pregnant group возвращает visualization null.
    EN: Contract: pregnant group returns visualization null.
    """
    payload = _valid_payload(
        weight_kg=65.0,
        height_cm=165.0,
        age=25,
        gender="female",
        pregnant="yes",  # pregnant group
    )

    data = _post_bmi(client, payload)

    # Contract: visualization is null for pregnant (category=None group)
    assert "visualization" in data, "visualization field must exist in response"
    assert data["visualization"] is None, "visualization must be null for pregnant group"
    assert data.get("category") is None, "category must be None for pregnant group"


def test_visualization_ranges_are_group_aware_athlete_vs_adult(client: TestClient) -> None:
    """
    RU: Контракт: athlete group имеет другие ranges чем adult (normal upper bound отличается).
    EN: Contract: athlete group has different ranges than adult (normal upper bound differs).

    We only assert "different normal upper" (not the exact number),
    to keep this contract test stable and non-math.
    """
    base = {
        "weight_kg": 85.0,
        "height_cm": 180.0,
        "age": 30,  # adult
        "gender": "male",
        "lang": "en",
    }

    adult_data = _post_bmi(client, {**base, "athlete": "no"})
    athlete_data = _post_bmi(client, {**base, "athlete": "yes"})

    adult_spec = adult_data.get("visualization")
    athlete_spec = athlete_data.get("visualization")

    # Contract: both groups return visualization (not null)
    assert adult_spec is not None, "adult group must have visualization"
    assert athlete_spec is not None, "athlete group must have visualization"

    # Contract: athlete normal range upper bound differs from adult
    adult_normal_to = _find_range_to(adult_spec, "bmi.normal")
    athlete_normal_to = _find_range_to(athlete_spec, "bmi.normal")

    assert (
        athlete_normal_to != adult_normal_to
    ), f"Athlete normal upper ({athlete_normal_to}) must differ from adult ({adult_normal_to})"
    # Expected: athlete_normal_to == 27.0, adult_normal_to == 25.0
    assert (
        athlete_normal_to > adult_normal_to
    ), f"Athlete normal upper ({athlete_normal_to}) should be higher than adult ({adult_normal_to})"


def test_visualization_ranges_are_group_aware_elderly_vs_adult(client: TestClient) -> None:
    """
    RU: Контракт: elderly group имеет другие ranges чем adult (underweight и normal thresholds отличаются).
    EN: Contract: elderly group has different ranges than adult (underweight and normal thresholds differ).
    """
    base = {
        "weight_kg": 60.0,
        "height_cm": 180.0,
        "gender": "male",
        "lang": "en",
    }

    adult_data = _post_bmi(client, {**base, "age": 30})  # adult
    elderly_data = _post_bmi(client, {**base, "age": 75})  # elderly (age >= 60)

    adult_spec = adult_data.get("visualization")
    elderly_spec = elderly_data.get("visualization")

    # Contract: both groups return visualization (not null)
    assert adult_spec is not None, "adult group must have visualization"
    assert elderly_spec is not None, "elderly group must have visualization"

    # Contract: elderly underweight threshold differs from adult
    adult_underweight_to = _find_range_to(adult_spec, "bmi.underweight")
    elderly_underweight_to = _find_range_to(elderly_spec, "bmi.underweight")

    assert (
        elderly_underweight_to != adult_underweight_to
    ), f"Elderly underweight upper ({elderly_underweight_to}) must differ from adult ({adult_underweight_to})"
    # Expected: elderly_underweight_to == 17.5, adult_underweight_to == 18.5
    assert (
        elderly_underweight_to < adult_underweight_to
    ), f"Elderly underweight upper ({elderly_underweight_to}) should be lower than adult ({adult_underweight_to})"

    # Contract: elderly normal upper bound differs from adult
    adult_normal_to = _find_range_to(adult_spec, "bmi.normal")
    elderly_normal_to = _find_range_to(elderly_spec, "bmi.normal")

    assert (
        elderly_normal_to != adult_normal_to
    ), f"Elderly normal upper ({elderly_normal_to}) must differ from adult ({adult_normal_to})"
    # Expected: elderly_normal_to == 26.0, adult_normal_to == 25.0
    assert (
        elderly_normal_to > adult_normal_to
    ), f"Elderly normal upper ({elderly_normal_to}) should be higher than adult ({adult_normal_to})"


def test_visualization_contract_graceful_fallback_on_builder_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Контракт: endpoint возвращает 200 с visualization null если builder падает.
    EN: Contract: endpoint returns 200 with visualization null if builder fails.
    """
    import app.routers.bmi as bmi_router

    def _boom(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Builder failure (test)")

    monkeypatch.setattr(bmi_router, "build_bmi_scale_v1", _boom)

    payload = _valid_payload()

    data = _post_bmi(client, payload)

    # Contract: endpoint still returns 200
    # Contract: visualization is null on builder failure
    assert "visualization" in data, "visualization field must exist in response"
    assert data["visualization"] is None, "visualization must be null on builder failure"
    # Contract: other fields still present
    assert "bmi" in data, "bmi field must still be present"
    assert data["bmi"] > 0, "bmi must be positive"
