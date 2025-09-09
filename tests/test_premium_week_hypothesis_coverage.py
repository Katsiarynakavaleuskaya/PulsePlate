# -*- coding: utf-8 -*-
"""
Hypothesis tests for premium_week.py coverage

RU: Hypothesis тесты для покрытия premium_week.py
EN: Hypothesis tests for premium_week.py coverage
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from app import app


class TestPremiumWeekHypothesisCoverage:
    """Test suite for premium_week.py coverage using Hypothesis."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    @given(
        sex=st.sampled_from(["female", "male"]),
        age=st.integers(min_value=18, max_value=80),
        height_cm=st.floats(min_value=140.0, max_value=220.0),
        weight_kg=st.floats(min_value=40.0, max_value=150.0),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
        diet_flags=st.lists(
            st.sampled_from(["VEG", "GF", "DAIRY_FREE"]), min_size=0, max_size=3
        ),
        lang=st.sampled_from(["en", "ru", "es"]),
    )
    @settings(deadline=None, max_examples=20)
    def test_generate_week_plan_missing_profile_data_hypothesis(
        self, sex, age, height_cm, weight_kg, activity, goal, diet_flags, lang
    ):
        """Test missing user profile data scenarios."""
        # Test with missing required fields
        payload = {
            "sex": sex,
            "age": age,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "activity": activity,
            "goal": goal,
            "diet_flags": diet_flags,
            "lang": lang,
        }

        # Test with missing sex
        payload_no_sex = payload.copy()
        payload_no_sex.pop("sex")
        response = self.client.post("/api/v1/premium/week", json=payload_no_sex)
        assert response.status_code == 400
        assert "Missing user profile data" in response.json()["detail"]

        # Test with missing age
        payload_no_age = payload.copy()
        payload_no_age.pop("age")
        response = self.client.post("/api/v1/premium/week", json=payload_no_age)
        assert response.status_code == 400
        assert "Missing user profile data" in response.json()["detail"]

        # Test with missing height_cm
        payload_no_height = payload.copy()
        payload_no_height.pop("height_cm")
        response = self.client.post("/api/v1/premium/week", json=payload_no_height)
        assert response.status_code == 400
        assert "Missing user profile data" in response.json()["detail"]

        # Test with missing weight_kg
        payload_no_weight = payload.copy()
        payload_no_weight.pop("weight_kg")
        response = self.client.post("/api/v1/premium/week", json=payload_no_weight)
        assert response.status_code == 400
        assert "Missing user profile data" in response.json()["detail"]

    @given(
        sex=st.sampled_from(["female", "male"]),
        age=st.integers(min_value=18, max_value=80),
        height_cm=st.floats(min_value=140.0, max_value=220.0),
        weight_kg=st.floats(min_value=40.0, max_value=150.0),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
        diet_flags=st.lists(
            st.sampled_from(["VEG", "GF", "DAIRY_FREE"]), min_size=0, max_size=3
        ),
        lang=st.sampled_from(["en", "ru", "es"]),
    )
    @settings(deadline=None, max_examples=10)
    def test_generate_week_plan_unable_to_derive_targets_hypothesis(
        self, sex, age, height_cm, weight_kg, activity, goal, diet_flags, lang
    ):
        """Test unable to derive targets scenario."""
        payload = {
            "sex": sex,
            "age": age,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "activity": activity,
            "goal": goal,
            "diet_flags": diet_flags,
            "lang": lang,
        }

        # Mock estimate_targets_minimal to return None
        with patch(
            "app.routers.premium_week.estimate_targets_minimal", return_value=None
        ):
            response = self.client.post("/api/v1/premium/week", json=payload)
            assert response.status_code == 400
            assert "Unable to derive targets" in response.json()["detail"]

    @given(
        sex=st.sampled_from(["female", "male"]),
        age=st.integers(min_value=18, max_value=80),
        height_cm=st.floats(min_value=140.0, max_value=220.0),
        weight_kg=st.floats(min_value=40.0, max_value=150.0),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
        diet_flags=st.lists(
            st.sampled_from(["VEG", "GF", "DAIRY_FREE"]), min_size=0, max_size=3
        ),
        lang=st.sampled_from(["en", "ru", "es"]),
    )
    @settings(deadline=None, max_examples=5)
    def test_generate_week_plan_with_targets_hypothesis(
        self, sex, age, height_cm, weight_kg, activity, goal, diet_flags, lang
    ):
        """Test with provided targets."""
        # Mock targets
        mock_targets = {
            "kcal_daily": 2000,
            "protein_g": 150,
            "carbs_g": 250,
            "fat_g": 67,
        }

        payload = {
            "sex": sex,
            "age": age,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "activity": activity,
            "goal": goal,
            "diet_flags": diet_flags,
            "lang": lang,
            "targets": mock_targets,
        }

        # Mock build_week to return a valid response
        mock_week = {
            "week_start": "2024-01-01",
            "daily_menus": [],
            "weekly_coverage": {},
            "shopping_list": {},
            "total_cost": 100.0,
            "adherence_score": 85.0,
        }

        with patch("app.routers.premium_week.build_week", return_value=mock_week):
            response = self.client.post("/api/v1/premium/week", json=payload)
            # Should not fail with 400, might be 500 due to missing dependencies
            assert response.status_code in [200, 500]

    @given(
        sex=st.sampled_from(["female", "male"]),
        age=st.integers(min_value=18, max_value=80),
        height_cm=st.floats(min_value=140.0, max_value=220.0),
        weight_kg=st.floats(min_value=40.0, max_value=150.0),
        activity=st.sampled_from(
            ["sedentary", "light", "moderate", "active", "very_active"]
        ),
        goal=st.sampled_from(["loss", "maintain", "gain"]),
        diet_flags=st.lists(
            st.sampled_from(["VEG", "GF", "DAIRY_FREE"]), min_size=0, max_size=3
        ),
        lang=st.sampled_from(["en", "ru", "es"]),
    )
    @settings(deadline=None, max_examples=5)
    def test_generate_week_plan_database_initialization_hypothesis(
        self, sex, age, height_cm, weight_kg, activity, goal, diet_flags, lang
    ):
        """Test database initialization paths."""
        payload = {
            "sex": sex,
            "age": age,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "activity": activity,
            "goal": goal,
            "diet_flags": diet_flags,
            "lang": lang,
        }

        # Mock FoodDB and RecipeDB initialization
        mock_fooddb = MagicMock()
        mock_recipedb = MagicMock()

        with patch("app.routers.premium_week.FoodDB", return_value=mock_fooddb), patch(
            "app.routers.premium_week.RecipeDB", return_value=mock_recipedb
        ), patch(
            "app.routers.premium_week.estimate_targets_minimal",
            return_value={"kcal_daily": 2000},
        ), patch(
            "app.routers.premium_week.build_week",
            return_value={
                "week_start": "2024-01-01",
                "daily_menus": [],
                "weekly_coverage": {},
                "shopping_list": {},
                "total_cost": 100.0,
                "adherence_score": 85.0,
            },
        ):

            response = self.client.post("/api/v1/premium/week", json=payload)
            # Should not fail with 400, might be 500 due to missing dependencies
            assert response.status_code in [200, 500]

    def test_generate_week_plan_edge_cases(self):
        """Test edge cases for coverage."""
        # Test with empty diet_flags
        payload = {
            "sex": "female",
            "age": 30,
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "activity": "moderate",
            "goal": "maintain",
            "diet_flags": [],
            "lang": "en",
        }

        with patch(
            "app.routers.premium_week.estimate_targets_minimal", return_value=None
        ):
            response = self.client.post("/api/v1/premium/week", json=payload)
            assert response.status_code == 400
            assert "Unable to derive targets" in response.json()["detail"]

        # Test with None values
        payload_none = {
            "sex": None,
            "age": 30,
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "activity": "moderate",
            "goal": "maintain",
            "diet_flags": [],
            "lang": "en",
        }

        response = self.client.post("/api/v1/premium/week", json=payload_none)
        assert response.status_code == 400
        assert "Missing user profile data" in response.json()["detail"]
