"""
Tests for the premium week plan API endpoint.
"""

import importlib.abc
import importlib.util
import os

import pytest
from fastapi.testclient import TestClient

# Import the app correctly from app.py
spec = importlib.util.spec_from_file_location("app", "app.py")
if spec is None:
    raise ImportError("Could not load app.py spec")
if spec.loader is None:
    raise ImportError("Spec loader is None")
app_module = importlib.util.module_from_spec(spec)
loader = spec.loader
if not isinstance(loader, importlib.abc.Loader):
    raise ImportError("Spec loader is not a valid Loader")
loader.exec_module(app_module)
client = TestClient(app_module.app)


class TestPremiumWeekAPI:
    """Test the premium week plan API endpoint."""

    def setup_method(self):
        os.environ["API_KEY"] = "test_key"

    def teardown_method(self):
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_premium_week_endpoint_multilingual(self):
        test_data = {
            "sex": "male",
            "age": 30,
            "height_cm": 180,
            "weight_kg": 75,
            "activity": "moderate",
            "goal": "maintain",
            "diet_flags": [],
            "lang": "en",
        }
        # sourcery skip: no-loop-in-tests
        for lang in ["en", "ru", "es"]:
            test_data["lang"] = lang
            response = client.post(
                "/api/v1/premium/plan/week",
                json=test_data,
                headers={"X-API-Key": "test_key"},
            )
            assert response.status_code == 200, f"Failed for language {lang}"
            result = response.json()
            self._check_week_response_structure(result)

    def test_premium_week_endpoint_with_targets(self):
        test_data = {
            "targets": {
                "kcal": 2000,
                "macros": {
                    "protein_g": 100,
                    "fat_g": 70,
                    "carbs_g": 250,
                    "fiber_g": 30,
                },
                "micro": {
                    "Fe_mg": 18.0,
                    "Ca_mg": 1000.0,
                    "VitD_IU": 600.0,
                    "B12_ug": 2.4,
                    "Folate_ug": 400.0,
                    "Iodine_ug": 150.0,
                    "K_mg": 3500.0,
                    "Mg_mg": 400.0,
                },
            },
            "diet_flags": [],
            "lang": "es",
        }
        response = client.post(
            "/api/v1/premium/plan/week",
            json=test_data,
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 422
        result = response.json()
        assert "detail" in result

    def _check_week_response_structure(self, result):
        assert "daily_menus" in result
        assert "weekly_coverage" in result
        assert "shopping_list" in result
        assert "total_cost" in result
        assert "adherence_score" in result
        assert len(result["daily_menus"]) == 7
        for day in result["daily_menus"]:
            self._check_day_structure(day)
        self._check_shopping_list_structure(result["shopping_list"])

    def _check_day_structure(self, day):
        assert "meals" in day
        assert "total_kcal" in day
        assert "daily_cost" in day
        for meal in day["meals"]:
            assert "title" in meal

    def _check_shopping_list_structure(self, shopping_list):
        assert isinstance(shopping_list, dict)
        for item_name, quantity in shopping_list.items():
            assert isinstance(item_name, str)
            assert isinstance(quantity, (int, float))


if __name__ == "__main__":
    pytest.main([__file__])
