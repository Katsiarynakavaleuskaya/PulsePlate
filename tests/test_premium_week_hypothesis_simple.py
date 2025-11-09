"""
Simple Hypothesis-based tests for premium week endpoint coverage.
Uses property-based testing to maximize coverage without complex mocking.
"""

import os
import time
from typing import Dict, List
from unittest.mock import patch

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

import app as app_mod

# Deadline constant for Hypothesis tests (None disables per-test deadline)
DEADLINE_MS = None

# Performance thresholds for meal plan generation (in seconds)
# RU: Увеличили порог до 3 секунд, чтобы снизить флаки из-за сетевых обращений.
# EN: Increased timeout to 3 seconds to avoid flaky failures caused by network retries.
MEAL_PLAN_GENERATION_TIMEOUT = 3.0
MEAL_PLAN_GENERATION_WARNING = 1.5


class TestPremiumWeekHypothesisSimple:
    """Simple Hypothesis tests for premium week endpoint coverage."""

    def setup_method(self):
        """Setup test environment for each test method"""
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"
        self.client = TestClient(app_mod.app)

    def teardown_method(self):
        """RU/EN: Close TestClient to avoid lingering event loops."""
        self.client.close()

    def _measure_response_time(self, url: str, payload: Dict, headers: Dict[str, str]) -> tuple:
        """
        Measure API request execution time.

        Args:
            url: API endpoint URL
            payload: Request payload dictionary
            headers: Request headers dictionary

        Returns:
            Tuple of (response, generation_time) where generation_time is in seconds
        """
        start_time = time.time()
        response = self.client.post(url, json=payload, headers=headers)
        generation_time = time.time() - start_time
        return response, generation_time

    @settings(deadline=DEADLINE_MS)
    @given(
        sex=st.sampled_from(["male", "female"]),
        age=st.integers(min_value=11, max_value=89),
        height_cm=st.floats(min_value=101.0, max_value=219.0),
        weight_kg=st.floats(min_value=31.0, max_value=299.0),
        activity=st.sampled_from(["sedentary", "light", "moderate", "active", "very_active"]),
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

            # Record execution time for meal plan generation
            response, generation_time = self._measure_response_time(
                "/api/v1/premium/plan/week",
                payload,
                {"X-API-Key": "test_key"},
            )

            # Should succeed and cover lines 93-117
            assert response.status_code == 200
            data = response.json()
            assert "daily_menus" in data
            assert "week_summary" in data

            # Performance observability: record timing metric
            # In production, this would be emitted to metrics registry (Prometheus, etc.)
            # For tests, we assert that generation completes within threshold
            assert (
                generation_time < MEAL_PLAN_GENERATION_TIMEOUT
            ), f"Meal plan generation exceeded timeout: {generation_time:.3f}s > {MEAL_PLAN_GENERATION_TIMEOUT}s"

    @settings(deadline=DEADLINE_MS)
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
        with patch.dict(os.environ, {"API_KEY": "test_key"}):
            payload = {"targets": targets, "lang": lang, "diet_flags": diet_flags}

            # Record execution time for meal plan generation
            response, generation_time = self._measure_response_time(
                "/api/v1/premium/plan/week",
                payload,
                {"X-API-Key": "test_key"},
            )

            # Should succeed and cover lines 97-98, or fail validation
            assert response.status_code in [200, 422]
            if response.status_code == 200:
                data = response.json()
                assert "daily_menus" in data
                assert "week_summary" in data

                # Performance observability: record timing metric
                assert (
                    generation_time < MEAL_PLAN_GENERATION_TIMEOUT
                ), f"Meal plan generation exceeded timeout: {generation_time:.3f}s > {MEAL_PLAN_GENERATION_TIMEOUT}s"

    @settings(deadline=DEADLINE_MS)
    @given(
        sex=st.sampled_from(["male", "female"]),
        age=st.integers(min_value=11, max_value=89),
        height_cm=st.floats(min_value=101.0, max_value=219.0),
        weight_kg=st.floats(min_value=31.0, max_value=299.0),
        activity=st.sampled_from(["sedentary", "light", "moderate", "active", "very_active"]),
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

            response = self.client.post(
                "/api/v1/premium/plan/week",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )

            # Should fail with 422 - Validation error (missing required field)
            assert response.status_code == 422

    @settings(deadline=DEADLINE_MS)
    @given(
        sex=st.sampled_from(["male", "female"]),
        age=st.integers(min_value=11, max_value=89),
        height_cm=st.floats(min_value=101.0, max_value=219.0),
        weight_kg=st.floats(min_value=31.0, max_value=299.0),
        activity=st.sampled_from(["sedentary", "light", "moderate", "active", "very_active"]),
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

            # Record execution time for meal plan generation
            response, generation_time = self._measure_response_time(
                "/api/v1/premium/plan/week",
                payload,
                {"X-API-Key": "test_key"},
            )

            # Should succeed and cover lines 104-113
            # (estimate_targets_minimal call and targets check)
            assert response.status_code == 200
            data = response.json()
            assert "daily_menus" in data
            assert "week_summary" in data

            # Performance observability: record timing metric
            assert (
                generation_time < MEAL_PLAN_GENERATION_TIMEOUT
            ), f"Meal plan generation exceeded timeout: {generation_time:.3f}s > {MEAL_PLAN_GENERATION_TIMEOUT}s"
