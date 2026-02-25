"""Tests for Nutrition Recommendations API endpoints (PR-1 + PR-2).

Covers:
- FREE: GET /api/v1/nutrition/recommendations
- PRO:  POST /api/v1/pro/nutrition/coverage
- PRO:  POST /api/v1/pro/nutrition/deficiency-recommendations  (PR-2)
- PRO:  POST /api/v1/pro/nutrition/micronutrient-targets        (PR-2)
- PRO:  POST /api/v1/pro/nutrition/safety-check                 (PR-2)

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

    def test_missing_height_422(self, client: TestClient) -> None:
        params = {k: v for k, v in _VALID_PARAMS.items() if k != "height_cm"}
        resp = client.get(_FREE_URL, params=params)
        assert resp.status_code == 422

    def test_missing_activity_level_422(self, client: TestClient) -> None:
        params = {k: v for k, v in _VALID_PARAMS.items() if k != "activity_level"}
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


# ---------------------------------------------------------------------------
# PR-2 endpoints
# ---------------------------------------------------------------------------

_PRO_DEFICIENCY_URL = "/api/v1/pro/nutrition/deficiency-recommendations"
_PRO_MICRO_TARGETS_URL = "/api/v1/pro/nutrition/micronutrient-targets"
_PRO_SAFETY_CHECK_URL = "/api/v1/pro/nutrition/safety-check"

_VALID_PROFILE: dict = {
    "age": 35,
    "gender": "male",
    "weight_kg": 75.0,
    "height_cm": 178.0,
    "activity_level": "moderate",
}

_VALID_DEFICIENCY_BODY: dict = {
    "profile": _VALID_PROFILE,
    "consumed": {
        "protein_g": 80.0,
        "fat_g": 60.0,
        "carbs_g": 250.0,
        "fiber_g": 25.0,
        "iron_mg": 5.0,
        "calcium_mg": 400.0,
        "vitamin_c_mg": 10.0,
    },
    "lang": "en",
}

_VALID_MICRO_BODY: dict = {"profile": _VALID_PROFILE}
_VALID_SAFETY_BODY: dict = {"profile": _VALID_PROFILE}


# ---------------------------------------------------------------------------
# Deficiency Recommendations
# ---------------------------------------------------------------------------


class TestDeficiencyRecsTierGuards:
    """Tier guard tests: deficiency-recommendations requires PRO key."""

    def test_no_auth_401_or_403(self, client: TestClient) -> None:
        resp = client.post(_PRO_DEFICIENCY_URL, json=_VALID_DEFICIENCY_BODY)
        assert resp.status_code in (401, 403)

    def test_pro_key_200(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        resp = client.post(_PRO_DEFICIENCY_URL, json=_VALID_DEFICIENCY_BODY, headers=pro_headers)
        assert resp.status_code == 200

    def test_vip_key_200(self, client: TestClient, vip_headers: dict[str, str]) -> None:
        resp = client.post(_PRO_DEFICIENCY_URL, json=_VALID_DEFICIENCY_BODY, headers=vip_headers)
        assert resp.status_code == 200


class TestDeficiencyRecsContract:
    """Contract tests for deficiency-recommendations endpoint."""

    def test_response_structure(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        resp = client.post(_PRO_DEFICIENCY_URL, json=_VALID_DEFICIENCY_BODY, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        data = resp.json()
        assert "recommendations" in data
        assert "deficient_count" in data
        assert "profile_summary" in data
        assert isinstance(data["recommendations"], list)
        assert isinstance(data["deficient_count"], int)
        assert data["deficient_count"] >= 0

    def test_lang_ru(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        body = {**_VALID_DEFICIENCY_BODY, "lang": "ru"}
        resp = client.post(_PRO_DEFICIENCY_URL, json=body, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        data = resp.json()
        assert isinstance(data["recommendations"], list)

    def test_lang_es(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        body = {**_VALID_DEFICIENCY_BODY, "lang": "es"}
        resp = client.post(_PRO_DEFICIENCY_URL, json=body, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        data = resp.json()
        assert isinstance(data["recommendations"], list)

    def test_lang_invalid_rejected(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        body = {**_VALID_DEFICIENCY_BODY, "lang": "de"}
        resp = client.post(_PRO_DEFICIENCY_URL, json=body, headers=pro_headers)
        assert resp.status_code == 422
        _assert_json_content_type(resp)

    def test_veg_flag_accepted(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        body = {
            "profile": {**_VALID_PROFILE, "diet_flags": ["VEG"]},
            "consumed": _VALID_DEFICIENCY_BODY["consumed"],
            "lang": "en",
        }
        resp = client.post(_PRO_DEFICIENCY_URL, json=body, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)

    def test_profile_summary_format(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        resp = client.post(_PRO_DEFICIENCY_URL, json=_VALID_DEFICIENCY_BODY, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        summary = resp.json()["profile_summary"]
        assert "male" in summary
        assert "35y" in summary
        assert "75.0kg" in summary


class TestDeficiencyRecsValidation:
    """422 validation tests for deficiency-recommendations."""

    def test_empty_consumed_422(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        body = {"profile": _VALID_PROFILE, "consumed": {}, "lang": "en"}
        resp = client.post(_PRO_DEFICIENCY_URL, json=body, headers=pro_headers)
        assert resp.status_code == 422

    def test_negative_consumed_422(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        body = {"profile": _VALID_PROFILE, "consumed": {"iron_mg": -5.0}, "lang": "en"}
        resp = client.post(_PRO_DEFICIENCY_URL, json=body, headers=pro_headers)
        assert resp.status_code == 422

    def test_invalid_profile_422(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        body = {
            "profile": {**_VALID_PROFILE, "age": 200},
            "consumed": {"iron_mg": 5.0},
            "lang": "en",
        }
        resp = client.post(_PRO_DEFICIENCY_URL, json=body, headers=pro_headers)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Micronutrient Targets
# ---------------------------------------------------------------------------


class TestMicroTargetsTierGuards:
    """Tier guard tests: micronutrient-targets requires PRO key."""

    def test_no_auth_401_or_403(self, client: TestClient) -> None:
        resp = client.post(_PRO_MICRO_TARGETS_URL, json=_VALID_MICRO_BODY)
        assert resp.status_code in (401, 403)

    def test_pro_key_200(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        resp = client.post(_PRO_MICRO_TARGETS_URL, json=_VALID_MICRO_BODY, headers=pro_headers)
        assert resp.status_code == 200

    def test_vip_key_200(self, client: TestClient, vip_headers: dict[str, str]) -> None:
        resp = client.post(_PRO_MICRO_TARGETS_URL, json=_VALID_MICRO_BODY, headers=vip_headers)
        assert resp.status_code == 200


class TestMicroTargetsContract:
    """Contract tests for micronutrient-targets endpoint."""

    def test_response_structure(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        resp = client.post(_PRO_MICRO_TARGETS_URL, json=_VALID_MICRO_BODY, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        data = resp.json()
        assert "nutrients" in data
        assert "deficiency_threshold" in data
        assert 0.0 < data["deficiency_threshold"] <= 1.0

    def test_all_12_nutrients_present(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        resp = client.post(_PRO_MICRO_TARGETS_URL, json=_VALID_MICRO_BODY, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        nutrients = resp.json()["nutrients"]
        expected = {
            "iron_mg",
            "calcium_mg",
            "magnesium_mg",
            "zinc_mg",
            "potassium_mg",
            "iodine_ug",
            "selenium_ug",
            "folate_ug",
            "b12_ug",
            "vitamin_d_iu",
            "vitamin_a_ug",
            "vitamin_c_mg",
        }
        assert set(nutrients.keys()) == expected

        expected_units = {
            "iron_mg": "mg",
            "calcium_mg": "mg",
            "magnesium_mg": "mg",
            "zinc_mg": "mg",
            "potassium_mg": "mg",
            "iodine_ug": "mcg",
            "selenium_ug": "mcg",
            "folate_ug": "mcg",
            "b12_ug": "mcg",
            "vitamin_d_iu": "IU",
            "vitamin_a_ug": "mcg",
            "vitamin_c_mg": "mg",
        }
        for name, detail in nutrients.items():
            assert (
                isinstance(detail.get("unit"), str) and detail["unit"]
            ), f"{name} has missing/empty unit"
            assert (
                detail["unit"] == expected_units[name]
            ), f"{name} unit mismatch: expected {expected_units[name]!r}, got {detail['unit']!r}"

    def test_ranges_min_le_target_le_max(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        resp = client.post(_PRO_MICRO_TARGETS_URL, json=_VALID_MICRO_BODY, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        for name, detail in resp.json()["nutrients"].items():
            assert (
                detail["min"] <= detail["target"] <= detail["max"]
            ), f"{name}: min={detail['min']} target={detail['target']} max={detail['max']}"

    def test_priority_field_present(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        resp = client.post(_PRO_MICRO_TARGETS_URL, json=_VALID_MICRO_BODY, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        nutrients = resp.json()["nutrients"]
        # iron_mg should have priority=5 (highest priority mineral)
        assert nutrients["iron_mg"]["priority"] == 5


class TestMicroTargetsValidation:
    """422 validation tests for micronutrient-targets."""

    def test_invalid_profile_422(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        body = {"profile": {**_VALID_PROFILE, "gender": "other"}}
        resp = client.post(_PRO_MICRO_TARGETS_URL, json=body, headers=pro_headers)
        assert resp.status_code == 422

    def test_missing_profile_422(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        resp = client.post(_PRO_MICRO_TARGETS_URL, json={}, headers=pro_headers)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Safety Check
# ---------------------------------------------------------------------------


class TestSafetyCheckTierGuards:
    """Tier guard tests: safety-check requires PRO key."""

    def test_no_auth_401_or_403(self, client: TestClient) -> None:
        resp = client.post(_PRO_SAFETY_CHECK_URL, json=_VALID_SAFETY_BODY)
        assert resp.status_code in (401, 403)

    def test_pro_key_200(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        resp = client.post(_PRO_SAFETY_CHECK_URL, json=_VALID_SAFETY_BODY, headers=pro_headers)
        assert resp.status_code == 200

    def test_vip_key_200(self, client: TestClient, vip_headers: dict[str, str]) -> None:
        resp = client.post(_PRO_SAFETY_CHECK_URL, json=_VALID_SAFETY_BODY, headers=vip_headers)
        assert resp.status_code == 200


class TestSafetyCheckContract:
    """Contract tests for safety-check endpoint."""

    def test_response_structure(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        resp = client.post(_PRO_SAFETY_CHECK_URL, json=_VALID_SAFETY_BODY, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        data = resp.json()
        assert "is_safe" in data
        assert "warnings" in data
        assert "targets_summary" in data
        assert isinstance(data["is_safe"], bool)
        assert isinstance(data["warnings"], list)

    def test_normal_profile_is_safe(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        """A healthy normal profile should pass safety checks."""
        resp = client.post(_PRO_SAFETY_CHECK_URL, json=_VALID_SAFETY_BODY, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        data = resp.json()
        assert data["is_safe"] is True
        assert data["warnings"] == []

    def test_targets_summary_fields(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        resp = client.post(_PRO_SAFETY_CHECK_URL, json=_VALID_SAFETY_BODY, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        ts = resp.json()["targets_summary"]
        assert "kcal_daily" in ts
        assert "protein_pct" in ts
        assert "water_ml_daily" in ts
        assert ts["kcal_daily"] > 0
        assert 0.0 <= ts["protein_pct"] <= 100.0
        assert ts["water_ml_daily"] > 0

    def test_is_safe_matches_warnings(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        """is_safe must be True iff warnings list is empty."""
        resp = client.post(_PRO_SAFETY_CHECK_URL, json=_VALID_SAFETY_BODY, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        data = resp.json()
        assert data["is_safe"] == (len(data["warnings"]) == 0)

    def test_zero_kcal_guard_sets_protein_pct_zero(
        self,
        client: TestClient,
        pro_headers: dict[str, str],
        monkeypatch,
    ) -> None:
        from dataclasses import replace

        import core.recommendations as core_recommendations

        original_build = core_recommendations.build_nutrition_targets

        def _build_zero_kcal(profile):
            return replace(original_build(profile), kcal_daily=0)

        monkeypatch.setattr(core_recommendations, "build_nutrition_targets", _build_zero_kcal)

        resp = client.post(_PRO_SAFETY_CHECK_URL, json=_VALID_SAFETY_BODY, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)
        data = resp.json()
        assert data["targets_summary"]["protein_pct"] == 0.0
        assert any("Invalid kcal_daily value" in item for item in data["warnings"])


class TestSafetyCheckValidation:
    """422 validation tests for safety-check."""

    def test_invalid_profile_422(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        body = {"profile": {**_VALID_PROFILE, "age": 0}}
        resp = client.post(_PRO_SAFETY_CHECK_URL, json=body, headers=pro_headers)
        assert resp.status_code == 422

    def test_missing_profile_422(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        resp = client.post(_PRO_SAFETY_CHECK_URL, json={}, headers=pro_headers)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Extended ProfileInput (cross-endpoint)
# ---------------------------------------------------------------------------


class TestProfileInputExtended:
    """Tests for extended ProfileInput optional fields across endpoints."""

    def test_defaults_backward_compatible(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        """Omitting optional fields should still work (defaults to maintain/adult/[])."""
        body = {"profile": _VALID_PROFILE}
        resp = client.post(_PRO_MICRO_TARGETS_URL, json=body, headers=pro_headers)
        assert resp.status_code == 200

    def test_goal_loss_accepted(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        body = {"profile": {**_VALID_PROFILE, "goal": "loss"}}
        resp = client.post(_PRO_SAFETY_CHECK_URL, json=body, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)

    def test_diet_flags_and_life_stage(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        body = {
            "profile": {
                **_VALID_PROFILE,
                "goal": "gain",
                "diet_flags": ["VEG", "GF"],
                "life_stage": "elderly",
                "age": 65,
            }
        }
        resp = client.post(_PRO_MICRO_TARGETS_URL, json=body, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)

    def test_deficit_pct_accepted(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        """deficit_pct should be passed to core for loss goal."""
        body = {"profile": {**_VALID_PROFILE, "goal": "loss", "deficit_pct": 20}}
        resp = client.post(_PRO_SAFETY_CHECK_URL, json=body, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)

    def test_surplus_pct_accepted(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        """surplus_pct should be passed to core for gain goal."""
        body = {"profile": {**_VALID_PROFILE, "goal": "gain", "surplus_pct": 15}}
        resp = client.post(_PRO_SAFETY_CHECK_URL, json=body, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)

    def test_bodyfat_accepted(self, client: TestClient, pro_headers: dict[str, str]) -> None:
        """bodyfat should enable Katch-McArdle BMR formula."""
        body = {"profile": {**_VALID_PROFILE, "bodyfat": 18.5}}
        resp = client.post(_PRO_MICRO_TARGETS_URL, json=body, headers=pro_headers)
        assert resp.status_code == 200
        _assert_json_content_type(resp)

    def test_deficit_pct_out_of_range_422(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        """deficit_pct outside 5-25 range should be rejected."""
        body = {"profile": {**_VALID_PROFILE, "goal": "loss", "deficit_pct": 30}}
        resp = client.post(_PRO_SAFETY_CHECK_URL, json=body, headers=pro_headers)
        assert resp.status_code == 422

    def test_surplus_pct_out_of_range_422(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        """surplus_pct outside 5-20 range should be rejected."""
        body = {"profile": {**_VALID_PROFILE, "goal": "gain", "surplus_pct": 25}}
        resp = client.post(_PRO_SAFETY_CHECK_URL, json=body, headers=pro_headers)
        assert resp.status_code == 422

    def test_bodyfat_out_of_range_422(
        self, client: TestClient, pro_headers: dict[str, str]
    ) -> None:
        """bodyfat outside 3-60 range should be rejected."""
        body = {"profile": {**_VALID_PROFILE, "bodyfat": 70}}
        resp = client.post(_PRO_MICRO_TARGETS_URL, json=body, headers=pro_headers)
        assert resp.status_code == 422
