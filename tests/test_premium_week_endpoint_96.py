"""
Tests for premium week endpoint to reach 96% coverage.
"""

import os
import sys
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

# Import the FastAPI app from app.py file
from app import app


def _make_canonical_week_payload() -> dict[str, object]:
    """Return a weekly-plan payload that matches the public endpoint contract.

    RU: Тестовые заглушки должны использовать каноническую форму weekly-plan,
    иначе fail-closed нормализация корректно возвращает 500.
    EN: Test doubles must match the canonical weekly-plan shape so fail-closed
    normalization only rejects truly malformed payloads.
    """
    return {
        "daily_menus": [
            {
                "meals": [
                    {
                        "title": "Protein bowl",
                        "title_translated": "Protein bowl",
                        "grams": {"serving_g": 420.0},
                        "kcal": 550.0,
                        "macros": {"protein_g": 42.0},
                        "micros": {"iron_mg": 4.2},
                        "price_est": 8.5,
                    }
                ],
                "kcal": 550.0,
                "macros": {"protein_g": 42.0},
                "micros": {"iron_mg": 4.2},
                "coverage": {"protein": 0.8},
                "tips": ["Stay hydrated"],
                "total_cost": 8.5,
            }
        ],
        "weekly_coverage": {"protein": 0.8},
        "shopping_list": {"apple": 5.0},
        "total_cost": 25.50,
        "adherence_score": 0.85,
    }


class TestPremiumWeekEndpoint96:
    """Tests for premium week endpoint coverage."""

    def test_generate_week_plan_with_targets(self):
        """Test generate_week_plan with provided targets - lines 93-117."""
        client = TestClient(app)

        with (
            patch.dict(os.environ, {"API_KEY": "test_api_key"}),
            patch("core.food_db_new.FoodDB") as mock_fooddb,
            patch("core.recipe_db_new.RecipeDB") as mock_recipedb,
            patch("app.routers.premium_week.build_week") as mock_build_week,
        ):
            # Mock database objects
            mock_fooddb.return_value = Mock()
            mock_recipedb.return_value = Mock()

            # Mock build_week response
            mock_build_week.return_value = _make_canonical_week_payload()

            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175,
                "weight_kg": 70,
                "activity": "moderate",
                "goal": "maintain",
                "diet_flags": ["VEG"],
                "lang": "en",
            }

            response = client.post(
                "/api/v1/premium/plan/week-flexible",
                json=payload,
                headers={"X-API-Key": "test_pro_key"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "daily_menus" in data
            assert "weekly_coverage" in data
            assert "shopping_list" in data
            assert "total_cost" in data
            assert "adherence_score" in data

    def test_generate_week_plan_with_targets_no_mock_db(self):
        """Test generate_week_plan with provided targets - lines 93-94 database instantiation."""
        client = TestClient(app)

        with (
            patch.dict(os.environ, {"API_KEY": "test_api_key"}),
            patch("app.routers.premium_week.build_week") as mock_build_week,
            patch("core.food_db_new.FoodDB") as mock_fooddb,
            patch("core.recipe_db_new.RecipeDB") as mock_recipedb,
        ):
            # Mock database objects
            mock_fooddb.return_value = Mock()
            mock_recipedb.return_value = Mock()

            # Mock build_week response but let database instantiation happen
            mock_build_week.return_value = _make_canonical_week_payload()

            payload = {
                "targets": {
                    "kcal": 2000,
                    "macros": {
                        "protein_g": 150,
                        "fat_g": 65,
                        "carbs_g": 250,
                        "fiber_g": 30,
                    },
                    "micro": {"iron_mg": 18, "calcium_mg": 1000},
                    "water_ml": 2000,
                    "activity_week": {"moderate_aerobic_min": 150},
                },
                "diet_flags": ["VEG"],
                "lang": "en",
            }

            response = client.post(
                "/api/v1/premium/plan/week-flexible",
                json=payload,
                headers={"X-API-Key": "test_pro_key"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "daily_menus" in data
            assert "weekly_coverage" in data
            assert "shopping_list" in data
            assert "total_cost" in data
            assert "adherence_score" in data

    def test_generate_week_plan_with_profile(self):
        """Test generate_week_plan with user profile - lines 93-117."""
        client = TestClient(app)

        with (
            patch.dict(os.environ, {"API_KEY": "test_api_key"}),
            patch("core.food_db_new.FoodDB") as mock_fooddb,
            patch("core.recipe_db_new.RecipeDB") as mock_recipedb,
            patch("app.routers.premium_week.estimate_targets_minimal") as mock_estimate,
            patch("app.routers.premium_week.build_week") as mock_build_week,
        ):
            # Mock database objects
            mock_fooddb.return_value = Mock()
            mock_recipedb.return_value = Mock()

            # Mock estimate_targets_minimal response
            mock_estimate.return_value = {
                "kcal": 2000,
                "macros": {"protein_g": 150, "fat_g": 65, "carbs_g": 250},
                "micro": {"iron_mg": 18, "calcium_mg": 1000},
                "water_ml": 2000,
                "activity_week": {"moderate_aerobic_min": 150},
            }

            # Mock build_week response
            mock_build_week.return_value = _make_canonical_week_payload()

            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175,
                "weight_kg": 70,
                "activity": "moderate",
                "goal": "maintain",
                "diet_flags": ["VEG"],
                "lang": "en",
            }

            response = client.post(
                "/api/v1/premium/plan/week-flexible",
                json=payload,
                headers={"X-API-Key": "test_pro_key"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "daily_menus" in data
            assert "weekly_coverage" in data
            assert "shopping_list" in data
            assert "total_cost" in data
            assert "adherence_score" in data

    def test_generate_week_plan_missing_profile_data(self):
        """Test generate_week_plan with missing profile data - lines 101-102."""
        client = TestClient(app)

        with (
            patch.dict(os.environ, {"API_KEY": "test_api_key"}),
            patch("core.food_db_new.FoodDB") as mock_fooddb,
            patch("core.recipe_db_new.RecipeDB") as mock_recipedb,
        ):
            # Mock database objects
            mock_fooddb.return_value = Mock()
            mock_recipedb.return_value = Mock()

            payload = {
                "sex": "male",
                "age": 30,
                # Missing height_cm and weight_kg
                "activity": "moderate",
                "goal": "maintain",
                "diet_flags": ["VEG"],
                "lang": "en",
            }

            response = client.post(
                "/api/v1/premium/plan/week-flexible",
                json=payload,
                headers={"X-API-Key": "test_pro_key"},
            )

            assert response.status_code == 400  # HTTPException for missing profile data
            # Check that the error is about missing required fields
            detail = response.json()["detail"]
            assert "Missing user profile data" in detail

    def test_generate_week_plan_unable_to_derive_targets(self):
        """Test generate_week_plan when unable to derive targets - lines 112-113."""
        client = TestClient(app)

        with (
            patch.dict(os.environ, {"API_KEY": "test_api_key"}),
            patch("core.food_db_new.FoodDB") as mock_fooddb,
            patch("core.recipe_db_new.RecipeDB") as mock_recipedb,
            patch("app.routers.premium_week.estimate_targets_minimal") as mock_estimate,
            patch("app.routers.premium_week.build_week") as mock_build_week,
        ):
            # Mock database objects
            mock_fooddb.return_value = Mock()
            mock_recipedb.return_value = Mock()

            # Mock estimate_targets_minimal to return None
            mock_estimate.return_value = None

            # Mock build_week to return a predictable result
            mock_build_week.return_value = _make_canonical_week_payload()

            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175,
                "weight_kg": 70,
                "activity": "moderate",
                "goal": "maintain",
                "diet_flags": ["VEG"],
                "lang": "en",
            }

            response = client.post(
                "/api/v1/premium/plan/week-flexible",
                json=payload,
                headers={"X-API-Key": "test_pro_key"},
            )

            assert response.status_code == 400
            data = response.json()
            assert "Unable to derive targets" in data["detail"]

    def test_generate_week_plan_with_different_languages(self):
        """Test generate_week_plan with different languages - lines 93-117."""
        client = TestClient(app)

        languages = ["en", "ru", "es"]

        for lang in languages:
            with (
                patch.dict(os.environ, {"API_KEY": "test_api_key"}),
                patch("core.food_db_new.FoodDB") as mock_fooddb,
                patch("core.recipe_db_new.RecipeDB") as mock_recipedb,
                patch("app.routers.premium_week.estimate_targets_minimal") as mock_estimate,
                patch("app.routers.premium_week.build_week") as mock_build_week,
            ):
                # Mock database objects
                mock_fooddb.return_value = Mock()
                mock_recipedb.return_value = Mock()

                # Mock estimate_targets_minimal response
                mock_estimate.return_value = {
                    "kcal": 2000,
                    "macros": {"protein_g": 150, "fat_g": 65, "carbs_g": 250},
                    "micro": {"iron_mg": 18, "calcium_mg": 1000},
                    "water_ml": 2000,
                    "activity_week": {"moderate_aerobic_min": 150},
                }

                # Mock build_week response
                mock_build_week.return_value = _make_canonical_week_payload()

                payload = {
                    "sex": "male",
                    "age": 30,
                    "height_cm": 175,
                    "weight_kg": 70,
                    "activity": "moderate",
                    "goal": "maintain",
                    "diet_flags": ["VEG"],
                    "lang": lang,
                }

                response = client.post(
                    "/api/v1/premium/plan/week-flexible",
                    json=payload,
                    headers={"X-API-Key": "test_pro_key"},
                )

                assert response.status_code == 200
                data = response.json()
                assert "daily_menus" in data

    def test_generate_week_plan_with_different_diet_flags(self):
        """Test generate_week_plan with different diet flags - lines 93-117."""
        client = TestClient(app)

        diet_flags_combinations = [
            ["VEG"],
            ["GF"],
            ["VEG", "DAIRY_FREE"],
            ["LOW_COST"],
            [],
        ]

        for diet_flags in diet_flags_combinations:
            with (
                patch.dict(os.environ, {"API_KEY": "test_api_key"}),
                patch("core.food_db_new.FoodDB") as mock_fooddb,
                patch("core.recipe_db_new.RecipeDB") as mock_recipedb,
                patch("app.routers.premium_week.estimate_targets_minimal") as mock_estimate,
                patch("app.routers.premium_week.build_week") as mock_build_week,
            ):
                # Mock database objects
                mock_fooddb.return_value = Mock()
                mock_recipedb.return_value = Mock()

                # Mock estimate_targets_minimal response
                mock_estimate.return_value = {
                    "kcal": 2000,
                    "macros": {"protein_g": 150, "fat_g": 65, "carbs_g": 250},
                    "micro": {"iron_mg": 18, "calcium_mg": 1000},
                    "water_ml": 2000,
                    "activity_week": {"moderate_aerobic_min": 150},
                }

                # Mock build_week response
                mock_build_week.return_value = _make_canonical_week_payload()

                payload = {
                    "sex": "male",
                    "age": 30,
                    "height_cm": 175,
                    "weight_kg": 70,
                    "activity": "moderate",
                    "goal": "maintain",
                    "diet_flags": diet_flags,
                    "lang": "en",
                }

                response = client.post(
                    "/api/v1/premium/plan/week-flexible",
                    json=payload,
                    headers={"X-API-Key": "test_pro_key"},
                )

                assert response.status_code == 200
                data = response.json()
                assert "daily_menus" in data
