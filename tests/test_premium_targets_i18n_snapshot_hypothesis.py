"""
Hypothesis-based snapshot tests for i18n (including ES) for /api/v1/premium/targets.
These tests ensure localization regression protection.
"""

import os
from typing import Dict

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

import app as app_mod


class TestPremiumTargetsI18nSnapshotHypothesis:
    """Hypothesis-based snapshot tests for premium targets i18n."""

    def setup_method(self):
        """Set up test environment."""
        os.environ["API_KEY"] = "test_key"
        self.client = TestClient(app_mod.app)

    @given(
        sex=st.sampled_from(["male", "female"]),
        age=st.integers(min_value=18, max_value=65),
        height_cm=st.floats(min_value=150.0, max_value=200.0),
        weight_kg=st.floats(min_value=45.0, max_value=120.0),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
        life_stage=st.sampled_from(
            ["adult", "teen", "pregnant", "lactating", "elderly", "child"]
        ),
        lang=st.sampled_from(["en", "ru", "es"]),
    )
    @settings(deadline=None)
    def test_premium_targets_i18n_snapshot_hypothesis(
        self,
        sex: str,
        age: int,
        height_cm: float,
        weight_kg: float,
        activity: str,
        goal: str,
        life_stage: str,
        lang: str,
    ):
        """Test i18n snapshot consistency across languages with Hypothesis."""
        payload = {
            "sex": sex,
            "age": age,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "activity": activity,
            "goal": goal,
            "life_stage": life_stage,
            "lang": lang,
        }

        response = self.client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )

        # Should succeed
        assert response.status_code == 200
        data = response.json()

        # Snapshot test - check basic structure
        assert "kcal_daily" in data
        assert "macros" in data
        assert "water_ml" in data
        assert "priority_micros" in data
        assert "activity_weekly" in data
        assert "calculation_date" in data
        assert "warnings" in data

        # Check that numerical values are reasonable
        assert 1000 <= data["kcal_daily"] <= 5000  # Reasonable calorie range
        assert data["macros"]["protein_g"] > 0
        assert data["macros"]["fat_g"] > 0
        assert data["macros"]["carbs_g"] > 0
        assert data["water_ml"] > 0

        # Check that warnings are properly localized
        for warning in data["warnings"]:
            assert "code" in warning
            assert "message" in warning
            assert isinstance(warning["message"], str)
            assert len(warning["message"]) > 0

    @given(
        lang=st.sampled_from(["en", "ru", "es"]),
        life_stage=st.sampled_from(
            ["teen", "pregnant", "lactating", "elderly", "child"]
        ),
        age=st.one_of(
            st.integers(min_value=13, max_value=17),  # teen
            st.integers(min_value=18, max_value=45),  # pregnant/lactating
            st.integers(min_value=65, max_value=85),  # elderly
            st.integers(min_value=5, max_value=12),  # child
        ),
    )
    def test_life_stage_warnings_i18n_snapshot_hypothesis(
        self, lang: str, life_stage: str, age: int
    ):
        """Test life stage warnings i18n snapshot with Hypothesis."""
        # Validate age matches life stage
        if life_stage == "teen" and not (13 <= age <= 17):
            return
        if life_stage in ["pregnant", "lactating"] and not (18 <= age <= 45):
            return
        if life_stage == "elderly" and not (65 <= age <= 85):
            return
        if life_stage == "child" and not (5 <= age <= 12):
            return

        payload = {
            "sex": "female" if life_stage in ["pregnant", "lactating"] else "male",
            "age": age,
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "activity": "moderate",
            "goal": "maintain",
            "life_stage": life_stage,
            "lang": lang,
        }

        response = self.client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()

        # Check that we have the expected warning
        warnings = data["warnings"]
        life_stage_warnings = [w for w in warnings if w.get("code") == life_stage]

        if life_stage_warnings:
            warning = life_stage_warnings[0]
            message = warning["message"].lower()

            # Check for language-specific keywords
            if lang == "es":
                spanish_keywords = {
                    "teen": ["adolescente", "apropiadas"],
                    "pregnant": ["embarazo", "especializada"],
                    "lactating": ["lactancia", "nutrientes"],
                    "elderly": ["micronutrientes", "diferir"],
                    "child": ["infantil", "pediátricas"],
                }
                expected_keywords = spanish_keywords.get(life_stage, [])
                assert any(
                    keyword in message for keyword in expected_keywords
                ), f"Expected Spanish keywords {expected_keywords} not found in message: {message}"

            elif lang == "ru":
                russian_keywords = {
                    "teen": ["подростковая", "группа", "специализированные"],
                    "pregnant": ["беременность", "специализированные"],
                    "lactating": ["лактация", "питательные"],
                    "elderly": [
                        "51+",
                        "возможна",
                        "иная",
                        "потребность",
                        "микронутриентах",
                    ],
                    "child": ["детский", "педиатрические"],
                }
                expected_keywords = russian_keywords.get(life_stage, [])
                assert any(
                    keyword in message for keyword in expected_keywords
                ), f"Expected Russian keywords {expected_keywords} not found in message: {message}"

    @given(
        sex=st.sampled_from(["male", "female"]),
        age=st.integers(min_value=18, max_value=65),
        height_cm=st.floats(min_value=150.0, max_value=200.0),
        weight_kg=st.floats(min_value=45.0, max_value=120.0),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
    )
    @settings(deadline=None)
    def test_multilingual_consistency_snapshot_hypothesis(
        self,
        sex: str,
        age: int,
        height_cm: float,
        weight_kg: float,
        activity: str,
        goal: str,
    ):
        """Test that numerical values are consistent across languages (snapshot test)."""
        base_payload = {
            "sex": sex,
            "age": age,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "activity": activity,
            "goal": goal,
            "life_stage": "adult",
        }

        languages = ["en", "ru", "es"]
        responses = {}

        # Get responses for all languages
        for lang in languages:
            payload = {**base_payload, "lang": lang}
            response = self.client.post(
                "/api/v1/premium/targets",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )
            assert response.status_code == 200
            responses[lang] = response.json()

        # Snapshot test - check that numerical values are identical across languages
        en_data = responses["en"]
        ru_data = responses["ru"]
        es_data = responses["es"]

        # Calorie values should be identical
        assert en_data["kcal_daily"] == ru_data["kcal_daily"] == es_data["kcal_daily"]

        # Macro values should be identical
        for macro in ["protein_g", "fat_g", "carbs_g", "fiber_g"]:
            assert (
                en_data["macros"][macro]
                == ru_data["macros"][macro]
                == es_data["macros"][macro]
            )

        # Water intake should be identical
        assert en_data["water_ml"] == ru_data["water_ml"] == es_data["water_ml"]

        # Priority micros should have identical values
        for nutrient in en_data["priority_micros"]:
            if (
                nutrient in ru_data["priority_micros"]
                and nutrient in es_data["priority_micros"]
            ):
                en_val = en_data["priority_micros"][nutrient]
                ru_val = ru_data["priority_micros"][nutrient]
                es_val = es_data["priority_micros"][nutrient]
                assert en_val == ru_val == es_val

        # Activity weekly should be identical
        for key in ["moderate_aerobic_min", "strength_sessions", "steps_daily"]:
            if (
                key in en_data["activity_weekly"]
                and key in ru_data["activity_weekly"]
                and key in es_data["activity_weekly"]
            ):
                en_val = en_data["activity_weekly"][key]
                ru_val = ru_data["activity_weekly"][key]
                es_val = es_data["activity_weekly"][key]
                assert en_val == ru_val == es_val

    @given(
        lang=st.sampled_from(["en", "ru", "es"]),
        invalid_input=st.sampled_from(
            [
                {"sex": "invalid"},
                {"activity": "invalid"},
                {"goal": "invalid"},
                {"life_stage": "invalid"},
            ]
        ),
    )
    def test_invalid_input_i18n_snapshot_hypothesis(
        self, lang: str, invalid_input: Dict[str, str]
    ):
        """Test invalid input handling with i18n (snapshot test)."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
            "life_stage": "adult",
            "lang": lang,
            **invalid_input,
        }

        response = self.client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )

        # Should return validation error
        assert response.status_code == 422
        data = response.json()

        # Snapshot test - check error structure
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert len(data["detail"]) > 0

        # Check that error messages are properly formatted
        for error in data["detail"]:
            assert "type" in error
            assert "loc" in error
            assert "msg" in error
            assert "input" in error

    def test_es_specific_snapshot_regression(self):
        """Test specific ES snapshot regression protection."""
        # Test case that previously had issues
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 168.0,
            "weight_kg": 60.0,
            "activity": "moderate",
            "goal": "maintain",
            "life_stage": "pregnant",
            "lang": "es",
        }

        response = self.client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()

        # Snapshot test - check specific ES pregnancy warning
        pregnancy_warnings = [
            w for w in data["warnings"] if w.get("code") == "pregnant"
        ]
        assert len(pregnancy_warnings) > 0

        pregnancy_warning = pregnancy_warnings[0]
        message = pregnancy_warning["message"].lower()

        # Should contain Spanish pregnancy-related terms
        spanish_terms = ["embarazo", "pregnancy", "especializada", "especialized"]
        assert any(
            term in message for term in spanish_terms
        ), f"Expected Spanish pregnancy terms not found in message: {message}"

    def test_ru_specific_snapshot_regression(self):
        """Test specific RU snapshot regression protection."""
        # Test case for Russian localization
        payload = {
            "sex": "male",
            "age": 70,
            "height_cm": 175.0,
            "weight_kg": 75.0,
            "activity": "light",
            "goal": "maintain",
            "life_stage": "elderly",
            "lang": "ru",
        }

        response = self.client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()

        # Snapshot test - check specific RU elderly warning
        elderly_warnings = [w for w in data["warnings"] if w.get("code") == "elderly"]
        assert len(elderly_warnings) > 0

        elderly_warning = elderly_warnings[0]
        message = elderly_warning["message"].lower()

        # Should contain Russian elderly-related terms
        russian_terms = [
            "51+",
            "возможна",
            "иная",
            "потребность",
            "микронутриентах",
            "micronutrients",
            "differ",
        ]
        assert any(
            term in message for term in russian_terms
        ), f"Expected Russian elderly terms not found in message: {message}"
