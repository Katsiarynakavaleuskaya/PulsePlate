"""
Simple Hypothesis-based tests for premium week endpoint coverage.
Uses property-based testing to maximize coverage without complex mocking.
"""

import os
from typing import Dict, List
from unittest.mock import patch

from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st

import app as app_mod


class TestPremiumWeekHypothesisSimple:
    """Simple Hypothesis tests for premium week endpoint coverage."""

    @given(
        sex=st.sampled_from(["male", "female"]),
        age=st.integers(min_value=11, max_value=89),
        height_cm=st.floats(min_value=101.0, max_value=219.0),
        weight_kg=st.floats(min_value=31.0, max_value=299.0),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
        lang=st.sampled_from(["en", "ru", "es"]),
        diet_flags=st.lists(
            st.sampled_from(["VEG", "GF", "DAIRY_FREE", "LOW_COST"]),
            min_size=0,
            max_size=3,
            unique=True,
        ),
    )
    def test_generate_week_plan_simple_hypothesis(
        self,
        sex: str,
        age: int,
        height_cm: float,
        weight_kg: float,
        activity: str,
        goal: str,
        lang: str,
        diet_flags: List[str],
    ):
        """Test generate_week_plan with Hypothesis to cover lines 93-117."""
        client = TestClient(app_mod.app)

        with patch.dict(os.environ, {"API_KEY": "test_key"}):
            payload = {
                "sex": sex,
                "age": age,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "activity": activity,
                "goal": goal,
                "lang": lang,
                "diet_flags": diet_flags,
            }

            response = client.post(
                "/api/v1/premium/plan/week",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )

            # Should succeed and cover lines 93-117
            assert response.status_code == 200
            data = response.json()
            assert "daily_menus" in data
            assert "week_summary" in data

    @given(
        targets=st.dictionaries(
            keys=st.sampled_from(
                [
                    "kcal",
                    "protein",
                    "carbs",
                    "fat",
                    "fiber",
                    "sugar",
                    "sodium",
                    "calcium",
                    "iron",
                    "magnesium",
                    "potassium",
                    "zinc",
                    "vitamin_c",
                    "vitamin_d",
                    "vitamin_e",
                    "vitamin_k",
                    "folate",
                    "vitamin_b12",
                    "omega3",
                    "omega6",
                ]
            ),
            values=st.floats(min_value=0.1, max_value=10000.0),
            min_size=5,
            max_size=20,
        ),
        lang=st.sampled_from(["en", "ru", "es"]),
        diet_flags=st.lists(
            st.sampled_from(["VEG", "GF", "DAIRY_FREE", "LOW_COST"]),
            min_size=0,
            max_size=3,
            unique=True,
        ),
    )
    def test_generate_week_plan_with_targets_simple_hypothesis(
        self, targets: Dict[str, float], lang: str, diet_flags: List[str]
    ):
        """Test generate_week_plan with provided targets - lines 97-98."""
        client = TestClient(app_mod.app)

        with patch.dict(os.environ, {"API_KEY": "test_key"}):
            payload = {"targets": targets, "lang": lang, "diet_flags": diet_flags}

            response = client.post(
                "/api/v1/premium/plan/week",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )

            # Should succeed and cover lines 97-98, or fail validation
            assert response.status_code in [200, 422]
            if response.status_code == 200:
                data = response.json()
                assert "daily_menus" in data
                assert "week_summary" in data

    @given(
        sex=st.sampled_from(["male", "female"]),
        age=st.integers(min_value=11, max_value=89),
        height_cm=st.floats(min_value=101.0, max_value=219.0),
        weight_kg=st.floats(min_value=31.0, max_value=299.0),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
        lang=st.sampled_from(["en", "ru", "es"]),
        diet_flags=st.lists(
            st.sampled_from(["VEG", "GF", "DAIRY_FREE", "LOW_COST"]),
            min_size=0,
            max_size=3,
            unique=True,
        ),
    )
    def test_generate_week_plan_missing_profile_data_simple_hypothesis(
        self,
        sex: str,
        age: int,
        height_cm: float,
        weight_kg: float,
        activity: str,
        goal: str,
        lang: str,
        diet_flags: List[str],
    ):
        """Test generate_week_plan with missing profile data - lines 101-102."""
        client = TestClient(app_mod.app)

        with patch.dict(os.environ, {"API_KEY": "test_key"}):
            # Test with missing sex
            payload = {
                "age": age,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "activity": activity,
                "goal": goal,
                "lang": lang,
                "diet_flags": diet_flags,
            }

            response = client.post(
                "/api/v1/premium/plan/week",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )

            # Should fail with 422 - Validation error (missing required field)
            assert response.status_code == 422

    @given(
        sex=st.sampled_from(["male", "female"]),
        age=st.integers(min_value=11, max_value=89),
        height_cm=st.floats(min_value=101.0, max_value=219.0),
        weight_kg=st.floats(min_value=31.0, max_value=299.0),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
        lang=st.sampled_from(["en", "ru", "es"]),
        diet_flags=st.lists(
            st.sampled_from(["VEG", "GF", "DAIRY_FREE", "LOW_COST"]),
            min_size=0,
            max_size=3,
            unique=True,
        ),
    )
    def test_generate_week_plan_unable_to_derive_targets_simple_hypothesis(
        self,
        sex: str,
        age: int,
        height_cm: float,
        weight_kg: float,
        activity: str,
        goal: str,
        lang: str,
        diet_flags: List[str],
    ):
        """Test generate_week_plan with valid profile data - covers lines 104-113."""
        client = TestClient(app_mod.app)

        with patch.dict(os.environ, {"API_KEY": "test_key"}):
            payload = {
                "sex": sex,
                "age": age,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "activity": activity,
                "goal": goal,
                "lang": lang,
                "diet_flags": diet_flags,
            }

            response = client.post(
                "/api/v1/premium/plan/week",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )

            # Should succeed and cover lines 104-113
            # (estimate_targets_minimal call and targets check)
            assert response.status_code == 200
            data = response.json()
            assert "daily_menus" in data
            assert "week_summary" in data
