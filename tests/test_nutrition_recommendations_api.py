"""Tests for Nutrition Recommendations API endpoints (PR-1).

Covers:
- FREE: GET /api/v1/nutrition/recommendations
- PRO:  POST /api/v1/pro/nutrition/coverage

RU: Тесты для API эндпоинтов рекомендаций по питанию.
EN: Tests for nutrition recommendation API endpoints.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _assert_json_content_type(resp: object) -> None:
    """Assert response Content-Type is application/json before calling .json()."""
    ct = getattr(resp, "headers", {}).get("content-type", "")
    assert ct.startswith("application/json"), f"Expected application/json, got {ct!r}"


# ---------------------------------------------------------------------------
# FREE endpoint: GET /api/v1/nutrition/recommendations
# ---------------------------------------------------------------------------

_FREE_URL = "/api/v1/nutrition/recommendations"
_VALID_PARAMS: dict[str, str | int | float] = {
    "age": 35,
    "gender": "male",
    "weight_kg": 75.0,
    "height_cm": 178.0,
    "activity_level": "moderate",
}


class TestFreeRecommendationsSuccess:
    """Happy-path tests for the FREE recommendations endpoint."""

    def test_recommendations_success(self, client: TestClient) -> None:
        resp = client.get(_FREE_URL, params=_VALID_PARAMS)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        data = resp.json()
        assert data["kcal_daily"] > 0
        assert data["macros"]["protein_g"] > 0
        assert data["macros"]["fat_g"] > 0
        assert data["macros"]["carbs_g"] > 0
        assert data["macros"]["fiber_g"] > 0
        assert data["water_ml_daily"] > 0
        assert isinstance(data["micros"], dict)
        assert len(data["micros"]) > 0
        assert isinstance(data["activity"], dict)

    def test_recommendations_female(self, client: TestClient) -> None:
        params = {**_VALID_PARAMS, "gender": "female"}
        resp = client.get(_FREE_URL, params=params)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        data = resp.json()
        assert data["kcal_daily"] > 0

    def test_recommendations_female_vs_male(self, client: TestClient) -> None:
        male_resp = client.get(_FREE_URL, params=_VALID_PARAMS)
        female_params = {**_VALID_PARAMS, "gender": "female"}
        female_resp = client.get(_FREE_URL, params=female_params)
        assert male_resp.status_code == 200
        assert female_resp.status_code == 200
        _assert_json_content_type(male_resp)
        _assert_json_content_type(female_resp)
        # Male and female targets should differ for same age/weight/height
        assert male_resp.json()["kcal_daily"] != female_resp.json()["kcal_daily"]

    def test_recommendations_all_activity_levels(self, client: TestClient) -> None:
        for level in ("low", "light", "moderate", "high", "very_high"):
            params = {**_VALID_PARAMS, "activity_level": level}
            resp = client.get(_FREE_URL, params=params)
            assert resp.status_code == 200, f"Failed for activity_level={level}"

    def test_recommendations_boundary_age_min(self, client: TestClient) -> None:
        params = {**_VALID_PARAMS, "age": 18}
        resp = client.get(_FREE_URL, params=params)
        assert resp.status_code == 200

    def test_recommendations_boundary_age_max(self, client: TestClient) -> None:
        params = {**_VALID_PARAMS, "age": 120}
        resp = client.get(_FREE_URL, params=params)
        assert resp.status_code == 200

    def test_recommendations_boundary_weight_min(self, client: TestClient) -> None:
        params = {**_VALID_PARAMS, "weight_kg": 30.0}
        resp = client.get(_FREE_URL, params=params)
        assert resp.status_code == 200

    def test_recommendations_boundary_height_min(self, client: TestClient) -> None:
        params = {**_VALID_PARAMS, "height_cm": 100.0}
        resp = client.get(_FREE_URL, params=params)
        assert resp.status_code == 200


class TestFreeRecommendationsValidation:
    """422 validation error tests for the FREE endpoint."""

    def test_invalid_age_too_high_422(self, client: TestClient) -> None:
        params = {**_VALID_PARAMS, "age": 150}
        resp = client.get(_FREE_URL, params=params)
        assert resp.status_code == 422

    def test_invalid_age_too_low_422(self, client: TestClient) -> None:
        params = {**_VALID_PARAMS, "age": 0}
        resp = client.get(_FREE_URL, params=params)
        assert resp.status_code == 422

    def test_invalid_age_pediatric_rejected_422(self, client: TestClient) -> None:
        """Age < 18 is rejected — API is adults-only."""
        params = {**_VALID_PARAMS, "age": 10}
        resp = client.get(_FREE_URL, params=params)
        assert resp.status_code == 422

    def test_invalid_gender_422(self, client: TestClient) -> None:
        params = {**_VALID_PARAMS, "gender": "other"}
        resp = client.get(_FREE_URL, params=params)
        assert resp.status_code == 422

    def test_invalid_weight_too_low_422(self, client: TestClient) -> None:
        params = {**_VALID_PARAMS, "weight_kg": 5.0}
        resp = client.get(_FREE_URL, params=params)
        assert resp.status_code == 422

    def test_invalid_weight_too_high_422(self, client: TestClient) -> None:
        params = {**_VALID_PARAMS, "weight_kg": 500.0}
        resp = client.get(_FREE_URL, params=params)
        assert resp.status_code == 422

    def test_invalid_height_too_low_422(self, client: TestClient) -> None:
        params = {**_VALID_PARAMS, "height_cm": 50.0}
        resp = client.get(_FREE_URL, params=params)
        assert resp.status_code == 422

    def test_invalid_activity_level_422(self, client: TestClient) -> None:
        params = {**_VALID_PARAMS, "activity_level": "extreme"}
        resp = client.get(_FREE_URL, params=params)
        assert resp.status_code == 422

    def test_missing_age_422(self, client: TestClient) -> None:
        params = {k: v for k, v in _VALID_PARAMS.items() if k != "age"}
        resp = client.get(_FREE_URL, params=params)
        assert resp.status_code == 422

    def test_missing_gender_422(self, client: TestClient) -> None:
        params = {k: v for k, v in _VALID_PARAMS.items() if k != "gender"}
        resp = client.get(_FREE_URL, params=params)
        assert resp.status_code == 422

    def test_missing_weight_422(self, client: TestClient) -> None:
        params = {k: v for k, v in _VALID_PARAMS.items() if k != "weight_kg"}
        resp = client.get(_FREE_URL, params=params)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PRO endpoint: POST /api/v1/pro/nutrition/coverage
# ---------------------------------------------------------------------------

_PRO_COVERAGE_URL = "/api/v1/pro/nutrition/coverage"

_VALID_COVERAGE_BODY: dict = {
    "profile": {
        "age": 35,
        "gender": "male",
        "weight_kg": 75.0,
        "height_cm": 178.0,
        "activity_level": "moderate",
    },
    "consumed": {
        "protein_g": 80.0,
        "fat_g": 60.0,
        "carbs_g": 250.0,
        "fiber_g": 25.0,
        "iron_mg": 14.0,
        "calcium_mg": 900.0,
        "vitamin_c_mg": 80.0,
    },
}


class TestProCoverageTierGuards:
    """Tier guard tests: coverage endpoint requires PRO key."""

    def test_coverage_no_auth_401_or_403(self, client: TestClient) -> None:
        resp = client.post(_PRO_COVERAGE_URL, json=_VALID_COVERAGE_BODY)
        assert resp.status_code in (401, 403)

    def test_coverage_empty_headers_403(self, client: TestClient) -> None:
        resp = client.post(_PRO_COVERAGE_URL, json=_VALID_COVERAGE_BODY, headers={})
        assert resp.status_code in (401, 403)

    def test_coverage_pro_key_200(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        resp = client.post(_PRO_COVERAGE_URL, json=_VALID_COVERAGE_BODY, headers=pro_headers)
        assert resp.status_code == 200

    def test_coverage_vip_key_200(self, client: TestClient, vip_headers: dict[str, str]) -> None:
        resp = client.post(_PRO_COVERAGE_URL, json=_VALID_COVERAGE_BODY, headers=vip_headers)
        assert resp.status_code == 200


class TestProCoverageContract:
    """Contract tests for the PRO coverage endpoint."""

    def test_coverage_response_structure(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        resp = client.post(_PRO_COVERAGE_URL, json=_VALID_COVERAGE_BODY, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        data = resp.json()
        assert "coverage" in data
        assert "summary" in data
        summary = data["summary"]
        assert "total_nutrients" in summary
        assert "adequate_count" in summary
        assert "deficient_count" in summary
        assert "excess_count" in summary
        assert "overall_score" in summary
        assert 0.0 <= summary["overall_score"] <= 100.0

    def test_coverage_item_fields(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        resp = client.post(_PRO_COVERAGE_URL, json=_VALID_COVERAGE_BODY, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        coverage = resp.json()["coverage"]
        assert len(coverage) > 0
        # Check one item has all required fields
        first_item = next(iter(coverage.values()))
        assert "consumed" in first_item
        assert "target" in first_item
        assert "coverage_percent" in first_item
        assert "status" in first_item
        assert "unit" in first_item
        assert first_item["status"] in ("deficient", "adequate", "excess")

    def test_coverage_adequate_nutrients(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        """When consumed meets targets, status should be adequate."""
        # Use high values to ensure adequate coverage
        body = {
            "profile": _VALID_COVERAGE_BODY["profile"],
            "consumed": {
                "protein_g": 200.0,
                "fat_g": 100.0,
                "carbs_g": 400.0,
                "fiber_g": 40.0,
                "iron_mg": 20.0,
                "calcium_mg": 1200.0,
                "magnesium_mg": 500.0,
                "zinc_mg": 15.0,
                "potassium_mg": 5000.0,
                "iodine_ug": 200.0,
                "selenium_ug": 70.0,
                "folate_ug": 500.0,
                "b12_ug": 5.0,
                "vitamin_d_iu": 1000.0,
                "vitamin_a_ug": 1000.0,
                "vitamin_c_mg": 120.0,
            },
        }
        resp = client.post(_PRO_COVERAGE_URL, json=body, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        summary = resp.json()["summary"]
        assert summary["deficient_count"] == 0

    def test_coverage_deficient_nutrient(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        """When consumed is very low, status should be deficient."""
        body = {
            "profile": _VALID_COVERAGE_BODY["profile"],
            "consumed": {
                "vitamin_c_mg": 5.0,  # very low
            },
        }
        resp = client.post(_PRO_COVERAGE_URL, json=body, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        coverage = resp.json()["coverage"]
        vc = coverage["vitamin_c_mg"]
        assert vc["status"] == "deficient"
        assert vc["coverage_percent"] < 67.0

    def test_coverage_excess_nutrient(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        """When consumed is very high, status should be excess."""
        body = {
            "profile": _VALID_COVERAGE_BODY["profile"],
            "consumed": {
                "iron_mg": 100.0,  # way above target
            },
        }
        resp = client.post(_PRO_COVERAGE_URL, json=body, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        coverage = resp.json()["coverage"]
        iron = coverage["iron_mg"]
        assert iron["status"] == "excess"
        assert iron["coverage_percent"] > 150.0

    def test_coverage_summary_counts_add_up(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        resp = client.post(_PRO_COVERAGE_URL, json=_VALID_COVERAGE_BODY, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        summary = resp.json()["summary"]
        total = summary["adequate_count"] + summary["deficient_count"] + summary["excess_count"]
        assert total == summary["total_nutrients"]

    def test_coverage_overall_score_range(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        resp = client.post(_PRO_COVERAGE_URL, json=_VALID_COVERAGE_BODY, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        score = resp.json()["summary"]["overall_score"]
        assert 0.0 <= score <= 100.0


class TestProCoverageValidation:
    """422 validation tests for the PRO coverage endpoint."""

    def test_coverage_empty_consumed_422(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        body = {
            "profile": _VALID_COVERAGE_BODY["profile"],
            "consumed": {},
        }
        resp = client.post(_PRO_COVERAGE_URL, json=body, headers=pro_headers)
        assert resp.status_code == 422

    def test_coverage_negative_consumed_422(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        """Negative consumed values must be rejected at 422."""
        body = {
            "profile": _VALID_COVERAGE_BODY["profile"],
            "consumed": {"protein_g": -10.0},
        }
        resp = client.post(_PRO_COVERAGE_URL, json=body, headers=pro_headers)
        assert resp.status_code == 422

    def test_coverage_invalid_profile_age_422(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        body = {
            "profile": {**_VALID_COVERAGE_BODY["profile"], "age": 200},
            "consumed": {"protein_g": 80.0},
        }
        resp = client.post(_PRO_COVERAGE_URL, json=body, headers=pro_headers)
        assert resp.status_code == 422

    def test_coverage_invalid_profile_gender_422(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        body = {
            "profile": {**_VALID_COVERAGE_BODY["profile"], "gender": "other"},
            "consumed": {"protein_g": 80.0},
        }
        resp = client.post(_PRO_COVERAGE_URL, json=body, headers=pro_headers)
        assert resp.status_code == 422

    def test_coverage_missing_profile_422(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        body = {"consumed": {"protein_g": 80.0}}
        resp = client.post(_PRO_COVERAGE_URL, json=body, headers=pro_headers)
        assert resp.status_code == 422
