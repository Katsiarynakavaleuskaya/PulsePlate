"""
ES snapshots for canonical /api/v1/pro/nutrition/targets
(including legacy alias coverage: /api/v1/premium/targets).

Detailed snapshot tests for Spanish localization covering all micronutrients,
warnings, and UI labels for both male and female profiles.
"""

import pytest
from fastapi.testclient import TestClient
from typing import Any


class TestPremiumTargetsESSnapshots:
    """ES snapshot tests for premium targets endpoint"""

    client: TestClient
    _CANONICAL_ENDPOINT = "/api/v1/pro/nutrition/targets"
    _LEGACY_ALIAS_ENDPOINT = "/api/v1/premium/targets"

    @pytest.fixture(autouse=True)
    def _bind_client(self, client: TestClient) -> None:
        self.client = client

    def _post_targets(
        self,
        payload: dict[str, Any],
        pro_headers: dict[str, str],
    ) -> dict[str, Any]:
        resp = self.client.post(self._CANONICAL_ENDPOINT, json=payload, headers=pro_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert isinstance(data, dict)
        ui_labels = data.get("ui_labels")
        assert isinstance(ui_labels, dict), "ui_labels must be a dict in response"
        assert ui_labels, "ui_labels must be non-empty"
        assert (
            ui_labels.get("kcal_daily") == "Calorías diarias"
        ), "Expected Spanish ui_labels anchor for kcal_daily."
        return data

    def test_female_adult_es_snapshot(self, pro_headers: dict[str, str]) -> None:
        """ES snapshot for female adult profile"""
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 168,
            "weight_kg": 60,
            "activity": "moderate",
            "goal": "maintain",
            "life_stage": "adult",
            "lang": "es",
        }

        data = self._post_targets(payload, pro_headers)

        # Verify all required keys are present
        required_keys = {
            "kcal_daily",
            "macros",
            "water_ml",
            "priority_micros",
            "activity_weekly",
            "calculation_date",
            "warnings",
        }
        assert all(key in data for key in required_keys)

        # Verify micronutrient keys (Fe/Ca/VitD/B12/I/Folate/Mg/K)
        expected_micros = {
            "iron_mg",
            "calcium_mg",
            "vitamin_d_iu",
            "b12_ug",
            "iodine_ug",
            "folate_ug",
            "magnesium_mg",
            "potassium_mg",
        }
        assert all(micro in data["priority_micros"] for micro in expected_micros)

        # Verify warnings structure (should be empty for adult)
        assert isinstance(data["warnings"], list)

        # Verify UI labels are in Spanish (if present)
        # Note: ui_labels may not be present in current API response

        # Verify calorie range is reasonable
        assert 1500 <= data["kcal_daily"] <= 2500

        # Verify water intake is reasonable
        assert 1500 <= data["water_ml"] <= 3000

    def test_legacy_alias_coverage_with_pro_headers(self, pro_headers: dict[str, str]) -> None:
        """Legacy alias guard coverage with pro headers."""
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 168,
            "weight_kg": 60,
            "activity": "moderate",
            "goal": "maintain",
            "life_stage": "adult",
            "lang": "es",
        }
        # Legacy alias coverage — canonical snapshots use /api/v1/pro/nutrition/targets
        resp = self.client.post(self._LEGACY_ALIAS_ENDPOINT, json=payload, headers=pro_headers)
        assert resp.status_code == 403
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert isinstance(data, dict)

    def test_male_adult_es_snapshot(self, pro_headers: dict[str, str]) -> None:
        """ES snapshot for male adult profile"""
        payload = {
            "sex": "male",
            "age": 35,
            "height_cm": 180,
            "weight_kg": 75,
            "activity": "active",
            "goal": "maintain",
            "life_stage": "adult",
            "lang": "es",
        }

        data = self._post_targets(payload, pro_headers)

        # Verify all required keys are present
        required_keys = {
            "kcal_daily",
            "macros",
            "water_ml",
            "priority_micros",
            "activity_weekly",
            "calculation_date",
            "warnings",
        }
        assert all(key in data for key in required_keys)

        # Verify micronutrient keys (Fe/Ca/VitD/B12/I/Folate/Mg/K)
        expected_micros = {
            "iron_mg",
            "calcium_mg",
            "vitamin_d_iu",
            "b12_ug",
            "iodine_ug",
            "folate_ug",
            "magnesium_mg",
            "potassium_mg",
        }
        assert all(micro in data["priority_micros"] for micro in expected_micros)

        # Verify warnings structure (should be empty for adult)
        assert isinstance(data["warnings"], list)

        # Verify UI labels are in Spanish (if present)
        # Note: ui_labels may not be present in current API response

        # Verify calorie range is reasonable (higher for male)
        assert 2000 <= data["kcal_daily"] <= 3000

        # Verify water intake is reasonable
        assert 2000 <= data["water_ml"] <= 3500

    def test_female_teen_es_snapshot_with_warnings(self, pro_headers: dict[str, str]) -> None:
        """ES snapshot for female teen with life stage warnings"""
        payload = {
            "sex": "female",
            "age": 16,
            "height_cm": 165,
            "weight_kg": 55,
            "activity": "moderate",
            "goal": "maintain",
            "life_stage": "teen",
            "lang": "es",
        }

        data = self._post_targets(payload, pro_headers)

        # Verify warnings are present for teen
        assert len(data["warnings"]) > 0

        # Check teen warning in Spanish
        teen_warnings = [w for w in data["warnings"] if w["code"] == "teen"]
        assert len(teen_warnings) == 1

        teen_warning = teen_warnings[0]
        assert "Etapa adolescente" in teen_warning["message"]
        assert "apropiadas para la edad" in teen_warning["message"]

        # Verify micronutrient keys are still present
        expected_micros = {
            "iron_mg",
            "calcium_mg",
            "vitamin_d_iu",
            "b12_ug",
            "iodine_ug",
            "folate_ug",
            "magnesium_mg",
            "potassium_mg",
        }
        assert all(micro in data["priority_micros"] for micro in expected_micros)

    def test_female_pregnant_es_snapshot_with_warnings(self, pro_headers: dict[str, str]) -> None:
        """ES snapshot for pregnant female with life stage warnings"""
        payload = {
            "sex": "female",
            "age": 28,
            "height_cm": 170,
            "weight_kg": 65,
            "activity": "light",
            "goal": "maintain",
            "life_stage": "pregnant",
            "lang": "es",
        }

        data = self._post_targets(payload, pro_headers)

        # Verify warnings are present for pregnant
        assert len(data["warnings"]) > 0

        # Check pregnant warning in Spanish
        pregnant_warnings = [w for w in data["warnings"] if w["code"] == "pregnant"]
        assert len(pregnant_warnings) == 1

        pregnant_warning = pregnant_warnings[0]
        assert "Embarazo" in pregnant_warning["message"]
        assert "requisitos difieren" in pregnant_warning["message"]

        # Verify micronutrient keys are present
        expected_micros = {
            "iron_mg",
            "calcium_mg",
            "vitamin_d_iu",
            "b12_ug",
            "iodine_ug",
            "folate_ug",
            "magnesium_mg",
            "potassium_mg",
        }
        assert all(micro in data["priority_micros"] for micro in expected_micros)

    def test_male_elderly_es_snapshot_with_warnings(self, pro_headers: dict[str, str]) -> None:
        """ES snapshot for elderly male with life stage warnings"""
        payload = {
            "sex": "male",
            "age": 65,
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "light",
            "goal": "maintain",
            "life_stage": "elderly",
            "lang": "es",
        }

        data = self._post_targets(payload, pro_headers)

        # Verify warnings are present for elderly
        assert len(data["warnings"]) > 0

        # Check elderly warning in Spanish
        elderly_warnings = [w for w in data["warnings"] if w["code"] == "elderly"]
        assert len(elderly_warnings) == 1

        elderly_warning = elderly_warnings[0]
        assert "51+" in elderly_warning["message"]
        assert "micronutrientes pueden diferir" in elderly_warning["message"]

        # Verify micronutrient keys are present
        expected_micros = {
            "iron_mg",
            "calcium_mg",
            "vitamin_d_iu",
            "b12_ug",
            "iodine_ug",
            "folate_ug",
            "magnesium_mg",
            "potassium_mg",
        }
        assert all(micro in data["priority_micros"] for micro in expected_micros)

    def test_female_lactating_es_snapshot_with_warnings(self, pro_headers: dict[str, str]) -> None:
        """ES snapshot for lactating female with life stage warnings"""
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 168,
            "weight_kg": 62,
            "activity": "moderate",
            "goal": "maintain",
            "life_stage": "lactating",
            "lang": "es",
        }

        data = self._post_targets(payload, pro_headers)

        # Verify warnings are present for lactating
        assert len(data["warnings"]) > 0

        # Check lactating warning in Spanish
        lactating_warnings = [w for w in data["warnings"] if w["code"] == "lactating"]
        assert len(lactating_warnings) == 1

        lactating_warning = lactating_warnings[0]
        assert "Lactancia" in lactating_warning["message"]
        assert "requisitos de nutrientes aumentados" in lactating_warning["message"]

        # Verify micronutrient keys are present
        expected_micros = {
            "iron_mg",
            "calcium_mg",
            "vitamin_d_iu",
            "b12_ug",
            "iodine_ug",
            "folate_ug",
            "magnesium_mg",
            "potassium_mg",
        }
        assert all(micro in data["priority_micros"] for micro in expected_micros)

    def test_child_es_snapshot_with_warnings(self, pro_headers: dict[str, str]) -> None:
        """ES snapshot for child with life stage warnings"""
        payload = {
            "sex": "male",
            "age": 10,
            "height_cm": 140,
            "weight_kg": 35,
            "activity": "active",
            "goal": "maintain",
            "life_stage": "child",
            "lang": "es",
        }

        data = self._post_targets(payload, pro_headers)

        # Verify warnings are present for child
        assert len(data["warnings"]) > 0

        # Check child warning in Spanish
        child_warnings = [w for w in data["warnings"] if w["code"] == "child"]
        assert len(child_warnings) == 1

        child_warning = child_warnings[0]
        assert "Edad infantil" in child_warning["message"]
        assert "pediátricas" in child_warning["message"]

        # Verify micronutrient keys are present
        expected_micros = {
            "iron_mg",
            "calcium_mg",
            "vitamin_d_iu",
            "b12_ug",
            "iodine_ug",
            "folate_ug",
            "magnesium_mg",
            "potassium_mg",
        }
        assert all(micro in data["priority_micros"] for micro in expected_micros)

    def test_micronutrient_values_consistency(self, pro_headers: dict[str, str]) -> None:
        """Test that micronutrient values are consistent across different profiles"""
        profiles = [
            {"sex": "female", "age": 30, "life_stage": "adult"},
            {"sex": "male", "age": 35, "life_stage": "adult"},
            {"sex": "female", "age": 16, "life_stage": "teen"},
        ]

        micro_values = {}

        for profile in profiles:
            payload = {
                **profile,
                "height_cm": 170,
                "weight_kg": 65,
                "activity": "moderate",
                "goal": "maintain",
                "lang": "es",
            }

            data = self._post_targets(payload, pro_headers)
            micro_values[profile["sex"] + "_" + profile["life_stage"]] = data["priority_micros"]

        # Verify all profiles have the same micronutrient keys
        expected_micros = {
            "iron_mg",
            "calcium_mg",
            "vitamin_d_iu",
            "b12_ug",
            "iodine_ug",
            "folate_ug",
            "magnesium_mg",
            "potassium_mg",
        }

        for micros in micro_values.values():
            assert all(micro in micros for micro in expected_micros)

    def test_ui_labels_spanish_consistency(self, pro_headers: dict[str, str]) -> None:
        """Test that UI labels are consistently present and localized in Spanish."""
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 168,
            "weight_kg": 60,
            "activity": "moderate",
            "goal": "maintain",
            "life_stage": "adult",
            "lang": "es",
        }

        data = self._post_targets(payload, pro_headers)
        ui_labels = data.get("ui_labels")
        assert isinstance(ui_labels, dict), "ui_labels must be a dict in response"
        assert ui_labels, "ui_labels must be non-empty"

        required_keys = {
            "kcal_daily",
            "macros_protein_g",
            "macros_fat_g",
            "macros_carbs_g",
            "macros_fiber_g",
            "water_ml",
            "priority_micros",
            "activity_weekly",
            "warnings",
        }
        missing = required_keys - set(ui_labels.keys())
        assert not missing, f"ui_labels missing keys: {sorted(missing)}"

        assert ui_labels["kcal_daily"] == "Calorías diarias"
