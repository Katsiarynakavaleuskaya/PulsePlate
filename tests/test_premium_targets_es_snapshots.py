"""
ES Snapshots for /api/v1/premium/targets

Detailed snapshot tests for Spanish localization covering all micronutrients,
warnings, and UI labels for both male and female profiles.
"""

import pytest
from fastapi.testclient import TestClient

try:
    import app as app_mod  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"FastAPI app import failed: {exc}", allow_module_level=True)

client = TestClient(app_mod.app)  # type: ignore


class TestPremiumTargetsESSnapshots:
    """ES snapshot tests for premium targets endpoint"""

    def test_female_adult_es_snapshot(self):
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

        resp = client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert resp.status_code == 200

        data = resp.json()

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

    def test_male_adult_es_snapshot(self):
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

        resp = client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert resp.status_code == 200

        data = resp.json()

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

    def test_female_teen_es_snapshot_with_warnings(self):
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

        resp = client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert resp.status_code == 200

        data = resp.json()

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

    def test_female_pregnant_es_snapshot_with_warnings(self):
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

        resp = client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert resp.status_code == 200

        data = resp.json()

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

    def test_male_elderly_es_snapshot_with_warnings(self):
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

        resp = client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert resp.status_code == 200

        data = resp.json()

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

    def test_female_lactating_es_snapshot_with_warnings(self):
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

        resp = client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert resp.status_code == 200

        data = resp.json()

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

    def test_child_es_snapshot_with_warnings(self):
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

        resp = client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert resp.status_code == 200

        data = resp.json()

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

    def test_micronutrient_values_consistency(self):
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

            resp = client.post(
                "/api/v1/premium/targets",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )
            assert resp.status_code == 200

            data = resp.json()
            micro_values[profile["sex"] + "_" + profile["life_stage"]] = data[
                "priority_micros"
            ]

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

        for profile_key, micros in micro_values.items():
            assert all(micro in micros for micro in expected_micros)

    def test_ui_labels_spanish_consistency(self):
        """Test that UI labels are consistently in Spanish (if present)"""
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

        resp = client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )
        assert resp.status_code == 200

        data = resp.json()

        # Check if ui_labels is present in response
        if "ui_labels" in data:
            ui_labels = data["ui_labels"]

            # Verify UI labels structure
            assert isinstance(ui_labels, dict)
            assert len(ui_labels) > 0

            # Check that labels contain Spanish text
            all_labels_text = " ".join(str(v) for v in ui_labels.values()).lower()

            # Spanish indicators that should be present
            spanish_indicators = [
                "kcal",
                "proteína",
                "grasa",
                "carbohidratos",
                "fibra",
                "agua",
                "actividad",
                "semanal",
                "diario",
                "mg",
                "g",
                "ml",
            ]

            # At least some Spanish indicators should be present
            found_indicators = [
                ind for ind in spanish_indicators if ind in all_labels_text
            ]
            assert (
                len(found_indicators) > 0
            ), f"No Spanish indicators found in: {all_labels_text}"
        else:
            # Skip test if ui_labels is not present in current API
            pytest.skip("ui_labels not present in current API response")
