"""
Hypothesis tests for life_stage error and warning branches.

Tests all life_stage warning codes (teen/pregnant/51+) and invalid sex/activity/goal/lang inputs
using property-based testing for maximum coverage optimization.
"""

import os

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

import app as app_mod


class TestLifeStageErrorBranchesHypothesis:
    """Hypothesis tests for life_stage error and warning branches."""

    def setup_method(self):
        """Setup test environment."""
        os.environ["API_KEY"] = "test_key"

    @given(
        age=st.integers(min_value=12, max_value=18),
        life_stage=st.sampled_from(["teen"]),
        lang=st.sampled_from(["en", "ru", "es"]),
        sex=st.sampled_from(["male", "female"]),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
    )
    def test_teen_life_stage_warning_hypothesis(
        self, age: int, life_stage: str, lang: str, sex: str, activity: str, goal: str
    ):
        """Test teen life_stage warning generation with Hypothesis."""
        client = TestClient(app_mod.app)

        payload = {
            "sex": sex,
            "age": age,
            "height_cm": 170.0,
            "weight_kg": 60.0,
            "activity": activity,
            "goal": goal,
            "life_stage": life_stage,
            "lang": lang,
        }

        response = client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )

        # Should succeed and include teen warning
        assert response.status_code == 200
        data = response.json()
        assert "warnings" in data
        assert len(data["warnings"]) >= 1

        # Check for teen warning
        teen_warnings = [w for w in data["warnings"] if w["code"] == "teen"]
        assert len(teen_warnings) == 1
        message = teen_warnings[0]["message"].lower()
        assert "teen" in message or "подростк" in message or "adolescent" in message

    @given(
        age=st.integers(min_value=18, max_value=45),
        life_stage=st.sampled_from(["pregnant"]),
        lang=st.sampled_from(["en", "ru", "es"]),
        sex=st.sampled_from(["female"]),  # Only females can be pregnant
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
    )
    def test_pregnant_life_stage_warning_hypothesis(
        self, age: int, life_stage: str, lang: str, sex: str, activity: str, goal: str
    ):
        """Test pregnant life_stage warning generation with Hypothesis."""
        client = TestClient(app_mod.app)

        payload = {
            "sex": sex,
            "age": age,
            "height_cm": 165.0,
            "weight_kg": 55.0,
            "activity": activity,
            "goal": goal,
            "life_stage": life_stage,
            "lang": lang,
        }

        response = client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )

        # Should succeed and include pregnant warning
        assert response.status_code == 200
        data = response.json()
        assert "warnings" in data
        assert len(data["warnings"]) >= 1

        # Check for pregnant warning
        pregnant_warnings = [w for w in data["warnings"] if w["code"] == "pregnant"]
        assert len(pregnant_warnings) == 1
        message = pregnant_warnings[0]["message"].lower()
        assert "pregnancy" in message or "беремен" in message or "embaraz" in message

    @given(
        age=st.integers(min_value=51, max_value=80),
        life_stage=st.sampled_from(["elderly"]),
        lang=st.sampled_from(["en", "ru", "es"]),
        sex=st.sampled_from(["male", "female"]),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
    )
    def test_elderly_life_stage_warning_hypothesis(
        self, age: int, life_stage: str, lang: str, sex: str, activity: str, goal: str
    ):
        """Test elderly (51+) life_stage warning generation with Hypothesis."""
        client = TestClient(app_mod.app)

        payload = {
            "sex": sex,
            "age": age,
            "height_cm": 160.0,
            "weight_kg": 65.0,
            "activity": activity,
            "goal": goal,
            "life_stage": life_stage,
            "lang": lang,
        }

        response = client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )

        # Should succeed and include elderly warning
        assert response.status_code == 200
        data = response.json()
        assert "warnings" in data
        assert len(data["warnings"]) >= 1

        # Check for elderly warning
        elderly_warnings = [w for w in data["warnings"] if w["code"] == "elderly"]
        assert len(elderly_warnings) == 1
        message = elderly_warnings[0]["message"]
        message_lower = message.lower()
        assert (
            "51+" in message or "elderly" in message_lower or "пожил" in message_lower
        )

    @given(
        age=st.integers(min_value=1, max_value=11),
        life_stage=st.sampled_from(["child"]),
        lang=st.sampled_from(["en", "ru", "es"]),
        sex=st.sampled_from(["male", "female"]),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
    )
    def test_child_life_stage_warning_hypothesis(
        self, age: int, life_stage: str, lang: str, sex: str, activity: str, goal: str
    ):
        """Test child life_stage warning generation with Hypothesis."""
        client = TestClient(app_mod.app)

        payload = {
            "sex": sex,
            "age": age,
            "height_cm": 120.0,
            "weight_kg": 25.0,
            "activity": activity,
            "goal": goal,
            "life_stage": life_stage,
            "lang": lang,
        }

        response = client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )

        # Should succeed and include child warning
        assert response.status_code == 200
        data = response.json()
        assert "warnings" in data
        assert len(data["warnings"]) >= 1

        # Check for child warning
        child_warnings = [w for w in data["warnings"] if w["code"] == "child"]
        assert len(child_warnings) == 1
        message = child_warnings[0]["message"].lower()
        assert "child" in message or "детск" in message or "infantil" in message

    @given(
        age=st.integers(min_value=18, max_value=45),
        life_stage=st.sampled_from(["lactating"]),
        lang=st.sampled_from(["en", "ru", "es"]),
        sex=st.sampled_from(["female"]),  # Only females can be lactating
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
    )
    def test_lactating_life_stage_warning_hypothesis(
        self, age: int, life_stage: str, lang: str, sex: str, activity: str, goal: str
    ):
        """Test lactating life_stage warning generation with Hypothesis."""
        client = TestClient(app_mod.app)

        payload = {
            "sex": sex,
            "age": age,
            "height_cm": 165.0,
            "weight_kg": 55.0,
            "activity": activity,
            "goal": goal,
            "life_stage": life_stage,
            "lang": lang,
        }

        response = client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )

        # Should succeed and include lactating warning
        assert response.status_code == 200
        data = response.json()
        assert "warnings" in data
        assert len(data["warnings"]) >= 1

        # Check for lactating warning
        lactating_warnings = [w for w in data["warnings"] if w["code"] == "lactating"]
        assert len(lactating_warnings) == 1
        message = lactating_warnings[0]["message"].lower()
        assert "lactat" in message or "лактац" in message or "lactancia" in message

    @given(
        age=st.integers(min_value=18, max_value=50),
        life_stage=st.sampled_from(["adult"]),
        lang=st.sampled_from(["en", "ru", "es"]),
        sex=st.sampled_from(["male", "female"]),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
    )
    @settings(deadline=None)
    def test_adult_no_warnings_hypothesis(
        self, age: int, life_stage: str, lang: str, sex: str, activity: str, goal: str
    ):
        """Test adult life_stage with no warnings using Hypothesis."""
        client = TestClient(app_mod.app)

        payload = {
            "sex": sex,
            "age": age,
            "height_cm": 170.0,
            "weight_kg": 65.0,
            "activity": activity,
            "goal": goal,
            "life_stage": life_stage,
            "lang": lang,
        }

        response = client.post(
            "/api/v1/premium/targets", json=payload, headers={"X-API-Key": "test_key"}
        )

        # Should succeed with no life_stage warnings
        assert response.status_code == 200
        data = response.json()
        assert "warnings" in data

        # Check that no life_stage warnings are present
        life_stage_warning_codes = ["teen", "pregnant", "lactating", "elderly", "child"]
        life_stage_warnings = [
            w for w in data["warnings"] if w["code"] in life_stage_warning_codes
        ]
        assert len(life_stage_warnings) == 0

    @given(
        age=st.integers(min_value=18, max_value=50),
        life_stage=st.sampled_from(["adult"]),
        lang=st.sampled_from(["en", "ru", "es"]),
        sex=st.sampled_from(["male", "female"]),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
    )
    @settings(deadline=None)
    def test_invalid_sex_validation_hypothesis(
        self, age: int, life_stage: str, lang: str, sex: str, activity: str, goal: str
    ):
        """Test invalid sex validation with Hypothesis."""
        client = TestClient(app_mod.app)

        # Test with invalid sex values
        invalid_sex_values = ["invalid", "other", "unknown", "x", "y"]

        for invalid_sex in invalid_sex_values:
            payload = {
                "sex": invalid_sex,
                "age": age,
                "height_cm": 170.0,
                "weight_kg": 65.0,
                "activity": activity,
                "goal": goal,
                "life_stage": life_stage,
                "lang": lang,
            }

            response = client.post(
                "/api/v1/premium/targets",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )

            # Should fail with validation error
            assert response.status_code == 422

    @given(
        age=st.integers(min_value=18, max_value=50),
        life_stage=st.sampled_from(["adult"]),
        lang=st.sampled_from(["en", "ru", "es"]),
        sex=st.sampled_from(["male", "female"]),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
    )
    @settings(deadline=None)
    def test_invalid_activity_validation_hypothesis(
        self, age: int, life_stage: str, lang: str, sex: str, activity: str, goal: str
    ):
        """Test invalid activity validation with Hypothesis."""
        client = TestClient(app_mod.app)

        # Test with invalid activity values
        invalid_activity_values = ["invalid", "extreme", "none", "low", "high"]

        for invalid_activity in invalid_activity_values:
            payload = {
                "sex": sex,
                "age": age,
                "height_cm": 170.0,
                "weight_kg": 65.0,
                "activity": invalid_activity,
                "goal": goal,
                "life_stage": life_stage,
                "lang": lang,
            }

            response = client.post(
                "/api/v1/premium/targets",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )

            # Should fail with validation error
            assert response.status_code == 422

    @given(
        age=st.integers(min_value=18, max_value=50),
        life_stage=st.sampled_from(["adult"]),
        lang=st.sampled_from(["en", "ru", "es"]),
        sex=st.sampled_from(["male", "female"]),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
    )
    @settings(deadline=None)
    def test_invalid_goal_validation_hypothesis(
        self, age: int, life_stage: str, lang: str, sex: str, activity: str, goal: str
    ):
        """Test invalid goal validation with Hypothesis."""
        client = TestClient(app_mod.app)

        # Test with invalid goal values
        invalid_goal_values = [
            "invalid",
            "weight_loss",
            "weight_gain",
            "maintenance",
            "bulk",
            "cut",
        ]

        for invalid_goal in invalid_goal_values:
            payload = {
                "sex": sex,
                "age": age,
                "height_cm": 170.0,
                "weight_kg": 65.0,
                "activity": activity,
                "goal": invalid_goal,
                "life_stage": life_stage,
                "lang": lang,
            }

            response = client.post(
                "/api/v1/premium/targets",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )

            # Should fail with validation error
            assert response.status_code == 422

    @given(
        age=st.integers(min_value=18, max_value=50),
        life_stage=st.sampled_from(["adult"]),
        lang=st.sampled_from(["en", "ru", "es"]),
        sex=st.sampled_from(["male", "female"]),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
    )
    @settings(deadline=None)
    def test_invalid_life_stage_validation_hypothesis(
        self, age: int, life_stage: str, lang: str, sex: str, activity: str, goal: str
    ):
        """Test invalid life_stage validation with Hypothesis."""
        client = TestClient(app_mod.app)

        # Test with invalid life_stage values
        invalid_life_stage_values = [
            "invalid",
            "senior",
            "youth",
            "middle_aged",
            "infant",
        ]

        for invalid_life_stage in invalid_life_stage_values:
            payload = {
                "sex": sex,
                "age": age,
                "height_cm": 170.0,
                "weight_kg": 65.0,
                "activity": activity,
                "goal": goal,
                "life_stage": invalid_life_stage,
                "lang": lang,
            }

            response = client.post(
                "/api/v1/premium/targets",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )

            # Should fail with validation error
            assert response.status_code == 422

    @given(
        age=st.integers(min_value=18, max_value=50),
        life_stage=st.sampled_from(["adult"]),
        lang=st.sampled_from(["en", "ru", "es"]),
        sex=st.sampled_from(["male", "female"]),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
    )
    @settings(deadline=None)
    def test_invalid_lang_validation_hypothesis(
        self, age: int, life_stage: str, lang: str, sex: str, activity: str, goal: str
    ):
        """Test invalid lang validation with Hypothesis."""
        client = TestClient(app_mod.app)

        # Test with invalid lang values (should still work as lang is just a string)
        invalid_lang_values = ["invalid", "fr", "de", "it", "pt", "zh", "ja"]

        for invalid_lang in invalid_lang_values:
            payload = {
                "sex": sex,
                "age": age,
                "height_cm": 170.0,
                "weight_kg": 65.0,
                "activity": activity,
                "goal": goal,
                "life_stage": life_stage,
                "lang": invalid_lang,
            }

            response = client.post(
                "/api/v1/premium/targets",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )

            # Should succeed (lang is just a string, not validated)
            assert response.status_code == 200
            data = response.json()
            assert "warnings" in data
