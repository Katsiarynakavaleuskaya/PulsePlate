"""
Tests for Premium Week Router

RU: Тесты для роутера Premium Week.
EN: Tests for Premium Week router.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("app.routers.premium_week")
from app.routers.premium_week import TargetsIn, WeekPlanRequest, WeekPlanResponse, router


class TestPremiumWeekRouter:
    """Test Premium Week router functionality."""

    def setup_method(self):
        """Set up test client."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    @patch("app.routers.premium_week.FoodDB")
    @patch("app.routers.premium_week.RecipeDB")
    @patch("app.routers.premium_week.build_week")
    def test_generate_week_plan_with_targets(self, mock_build_week, mock_recipe_db, mock_food_db):
        """Test week plan generation with provided targets."""
        # Mock the databases
        mock_food_db_instance = MagicMock()
        mock_food_db.return_value = mock_food_db_instance

        mock_recipe_db_instance = MagicMock()
        mock_recipe_db.return_value = mock_recipe_db_instance

        # Mock the build_week function
        mock_build_week.return_value = {
            "daily_menus": [{"day": "Monday", "meals": []}],
            "weekly_coverage": {"protein": 0.95},
            "shopping_list": {"chicken": 1.0},
            "total_cost": 25.50,
            "adherence_score": 0.95,
        }

        response = self.client.post(
            "/api/v1/premium/plan/week-flexible",
            json={
                "targets": {
                    "kcal": 2000,
                    "macros": {"protein_g": 150.0, "fat_g": 65.0, "carbs_g": 250.0},
                    "micro": {"vitamin_c_mg": 90.0, "iron_mg": 18.0},
                    "water_ml": 2000,
                },
                "diet_flags": ["vegetarian"],
                "lang": "en",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "daily_menus" in data
        assert "weekly_coverage" in data
        assert "shopping_list" in data
        assert "total_cost" in data
        assert "adherence_score" in data

    @patch("app.routers.premium_week.FoodDB")
    @patch("app.routers.premium_week.RecipeDB")
    @patch("app.routers.premium_week.build_week")
    @patch("app.routers.premium_week.estimate_targets_minimal")
    def test_generate_week_plan_with_profile(
        self, mock_estimate_targets, mock_build_week, mock_recipe_db, mock_food_db
    ):
        """Test week plan generation with user profile."""
        # Mock the databases
        mock_food_db_instance = MagicMock()
        mock_food_db.return_value = mock_food_db_instance

        mock_recipe_db_instance = MagicMock()
        mock_recipe_db.return_value = mock_recipe_db_instance

        # Mock the estimate_targets_minimal function
        mock_estimate_targets.return_value = {
            "kcal": 2000,
            "macros": {"protein_g": 150.0, "fat_g": 65.0, "carbs_g": 250.0},
            "micro": {"vitamin_c_mg": 90.0},
            "water_ml": 2000,
        }

        # Mock the build_week function
        mock_build_week.return_value = {
            "daily_menus": [{"day": "Monday", "meals": []}],
            "weekly_coverage": {"protein": 0.95},
            "shopping_list": {"chicken": 1.0},
            "total_cost": 25.50,
            "adherence_score": 0.95,
        }

        response = self.client.post(
            "/api/v1/premium/plan/week-flexible",
            json={
                "sex": "male",
                "age": 30,
                "height_cm": 175,
                "weight_kg": 70,
                "activity": "moderate",
                "goal": "maintain",
                "diet_flags": [],
                "lang": "en",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "daily_menus" in data
        assert "weekly_coverage" in data
        assert "shopping_list" in data
        assert "total_cost" in data
        assert "adherence_score" in data

    def test_generate_week_plan_missing_profile_data(self):
        """Test week plan generation with missing profile data."""
        response = self.client.post(
            "/api/v1/premium/plan/week-flexible",
            json={
                "sex": "male",
                "age": 30,
                # Missing height_cm and weight_kg
                "activity": "moderate",
                "goal": "maintain",
            },
        )

        assert response.status_code == 400
        assert "Missing user profile data" in response.json()["detail"]

    @patch("app.routers.premium_week.FoodDB")
    @patch("app.routers.premium_week.RecipeDB")
    @patch("app.routers.premium_week.estimate_targets_minimal")
    def test_generate_week_plan_unable_to_derive_targets(
        self, mock_estimate_targets, mock_recipe_db, mock_food_db
    ):
        """Test week plan generation when unable to derive targets."""
        # Mock the databases
        mock_food_db_instance = MagicMock()
        mock_food_db.return_value = mock_food_db_instance

        mock_recipe_db_instance = MagicMock()
        mock_recipe_db.return_value = mock_recipe_db_instance

        # Mock the estimate_targets_minimal function to return None
        mock_estimate_targets.return_value = None

        response = self.client.post(
            "/api/v1/premium/plan/week-flexible",
            json={
                "sex": "male",
                "age": 30,
                "height_cm": 175,
                "weight_kg": 70,
                "activity": "moderate",
                "goal": "maintain",
            },
        )

        assert response.status_code == 400
        assert "Unable to derive targets" in response.json()["detail"]

    def test_targets_in_model_validation(self):
        """Test TargetsIn model validation."""
        # Valid targets
        targets = TargetsIn(
            kcal=2000,
            macros={"protein_g": 150.0, "fat_g": 65.0, "carbs_g": 250.0},
            micro={"vitamin_c_mg": 90.0, "iron_mg": 18.0},
            water_ml=2000,
        )
        assert targets.kcal == 2000
        assert targets.macros["protein_g"] == 150.0
        assert targets.micro["vitamin_c_mg"] == 90.0
        assert targets.water_ml == 2000

    def test_targets_in_validation_errors(self):
        """Test TargetsIn model validation errors."""
        # Test kcal too low
        with pytest.raises(ValueError):
            TargetsIn(
                kcal=400,
                macros={"protein_g": 150.0},
                micro={"vitamin_c_mg": 90.0},  # Too low
            )

        # Test kcal too high
        with pytest.raises(ValueError):
            TargetsIn(
                kcal=7000,
                macros={"protein_g": 150.0},
                micro={"vitamin_c_mg": 90.0},  # Too high
            )

        # Test negative macro value
        with pytest.raises(ValueError):
            TargetsIn(
                kcal=2000,
                macros={"protein_g": -150.0},
                micro={"vitamin_c_mg": 90.0},  # Negative
            )

    def test_week_plan_request_model(self):
        """Test WeekPlanRequest model."""
        request = WeekPlanRequest(
            sex="female",
            age=25,
            height_cm=165,
            weight_kg=60,
            activity="active",
            goal="loss",
            diet_flags=["vegetarian", "gluten_free"],
            lang="ru",
        )
        assert request.sex == "female"
        assert request.age == 25
        assert request.height_cm == 165
        assert request.weight_kg == 60
        assert request.activity == "active"
        assert request.goal == "loss"
        assert request.diet_flags == ["vegetarian", "gluten_free"]
        assert request.lang == "ru"
        assert request.targets is None

    def test_week_plan_response_model(self):
        """Test WeekPlanResponse model."""
        response = WeekPlanResponse(
            daily_menus=[{"day": "Monday", "meals": []}],
            weekly_coverage={"protein": 0.95, "carbs": 0.90},
            shopping_list={"chicken": 1.0},
            total_cost=25.50,
            adherence_score=0.95,
        )
        assert len(response.daily_menus) == 1
        assert response.weekly_coverage["protein"] == 0.95
        assert len(response.shopping_list) == 1
        assert response.total_cost == 25.50
        assert response.adherence_score == 0.95
