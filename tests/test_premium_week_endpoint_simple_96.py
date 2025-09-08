"""
Simple tests for premium week endpoint to reach 96% coverage.
"""

import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from app import app


class TestPremiumWeekEndpointSimple96:
    """Simple tests for premium week endpoint coverage."""

    def test_generate_week_plan_with_targets(self):
        """Test generate_week_plan with provided targets - lines 93-117."""
        client = TestClient(app)
        
        with patch('app.get_api_key') as mock_get_api_key, \
             patch('app.routers.premium_week.FoodDB') as mock_fooddb, \
             patch('app.routers.premium_week.RecipeDB') as mock_recipedb, \
             patch('app.routers.premium_week.build_week') as mock_build_week:
            
            # Mock authentication
            mock_get_api_key.return_value = "test_api_key"
            
            # Mock database objects
            mock_fooddb.return_value = Mock()
            mock_recipedb.return_value = Mock()
            
            # Mock build_week response
            mock_build_week.return_value = {
                "daily_menus": [{"breakfast": "test"}],
                "weekly_coverage": {"protein": 0.8},
                "shopping_list": {"apple": 5.0},
                "total_cost": 25.50,
                "adherence_score": 0.85
            }
            
            payload = {
                "targets": {
                    "kcal": 2000,
                    "macros": {"protein_g": 150, "fat_g": 65, "carbs_g": 250},
                    "micro": {"iron_mg": 18, "calcium_mg": 1000},
                    "water_ml": 2000
                },
                "diet_flags": ["vegetarian"],
                "lang": "en"
            }
            
            response = client.post("/api/v1/premium/plan/week", json=payload, headers={"X-API-Key": "test_api_key"})
            
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
        
        with patch('app.get_api_key') as mock_get_api_key, \
             patch('app.routers.premium_week.FoodDB') as mock_fooddb, \
             patch('app.routers.premium_week.RecipeDB') as mock_recipedb, \
             patch('app.routers.premium_week.estimate_targets_minimal') as mock_estimate, \
             patch('app.routers.premium_week.build_week') as mock_build_week:
            
            # Mock authentication
            mock_get_api_key.return_value = "test_api_key"
            
            # Mock database objects
            mock_fooddb.return_value = Mock()
            mock_recipedb.return_value = Mock()
            
            # Mock estimate_targets_minimal response
            mock_estimate.return_value = {
                "kcal": 2000,
                "macros": {"protein_g": 150, "fat_g": 65, "carbs_g": 250},
                "micro": {"iron_mg": 18, "calcium_mg": 1000},
                "water_ml": 2000,
                "activity_week": {"moderate_aerobic_min": 150}
            }
            
            # Mock build_week response
            mock_build_week.return_value = {
                "daily_menus": [{"breakfast": "test"}],
                "weekly_coverage": {"protein": 0.8},
                "shopping_list": {"apple": 5.0},
                "total_cost": 25.50,
                "adherence_score": 0.85
            }
            
            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175,
                "weight_kg": 70,
                "activity": "moderate",
                "goal": "maintain",
                "diet_flags": ["vegetarian"],
                "lang": "en"
            }
            
            response = client.post("/api/v1/premium/plan/week", json=payload, headers={"X-API-Key": "test_api_key"})
            
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
        
        with patch('app.get_api_key') as mock_get_api_key, \
             patch('app.routers.premium_week.FoodDB') as mock_fooddb, \
             patch('app.routers.premium_week.RecipeDB') as mock_recipedb:
            
            # Mock authentication
            mock_get_api_key.return_value = "test_api_key"
            
            # Mock database objects
            mock_fooddb.return_value = Mock()
            mock_recipedb.return_value = Mock()
            
            payload = {
                "sex": "male",
                "age": 30,
                # Missing height_cm and weight_kg
                "activity": "moderate",
                "goal": "maintain",
                "diet_flags": ["vegetarian"],
                "lang": "en"
            }
            
            response = client.post("/api/v1/premium/plan/week", json=payload, headers={"X-API-Key": "test_api_key"})
            
            assert response.status_code == 400
            assert "Missing user profile data" in response.json()["detail"]

    def test_generate_week_plan_unable_to_derive_targets(self):
        """Test generate_week_plan when unable to derive targets - lines 112-113."""
        client = TestClient(app)
        
        with patch('app.get_api_key') as mock_get_api_key, \
             patch('app.routers.premium_week.FoodDB') as mock_fooddb, \
             patch('app.routers.premium_week.RecipeDB') as mock_recipedb, \
             patch('app.routers.premium_week.estimate_targets_minimal') as mock_estimate:
            
            # Mock authentication
            mock_get_api_key.return_value = "test_api_key"
            
            # Mock database objects
            mock_fooddb.return_value = Mock()
            mock_recipedb.return_value = Mock()
            
            # Mock estimate_targets_minimal to return None
            mock_estimate.return_value = None
            
            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175,
                "weight_kg": 70,
                "activity": "moderate",
                "goal": "maintain",
                "diet_flags": ["vegetarian"],
                "lang": "en"
            }
            
            response = client.post("/api/v1/premium/plan/week", json=payload, headers={"X-API-Key": "test_api_key"})
            
            assert response.status_code == 400
            assert "Unable to derive targets" in response.json()["detail"]
