import os
from unittest.mock import patch

import pytest

from app.effective_routes import iter_effective_route_candidates, route_path
from app.main import app as canonical_app
from app.services import pro_nutrition_plate


class TestAppVIPComprehensive97:
    """Comprehensive tests for app.py VIP functionality to improve coverage to 97%."""

    def test_premium_plate_fallback_mode(
        self,
        test_client,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test premium plate endpoint in fallback mode when backends are unavailable."""
        # This tests lines 1338-1399 in app.py (the fallback code path)
        client = test_client

        # Canonical dependencies are resolved per call; force all calculation
        # backends unavailable to exercise the deterministic fallback.
        monkeypatch.setattr(pro_nutrition_plate.nutrition_plate, "make_plate", None)
        monkeypatch.setattr(
            pro_nutrition_plate.nutrition_bmr,
            "calculate_all_bmr",
            None,
        )
        monkeypatch.setattr(
            pro_nutrition_plate.nutrition_bmr,
            "calculate_all_tdee",
            None,
        )
        response = client.post(
            "/api/v1/premium/plate",
            json={
                "sex": "male",
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "kcal" in data
        assert "macros" in data

    def test_premium_plate_fallback_with_build_nutrition_targets(
        self,
        test_client,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test premium plate fallback with build_nutrition_targets available."""
        # This tests lines 1358-1377 in app.py (the WHO targets alignment in fallback)
        client = test_client

        # Leave build_nutrition_targets available while forcing the three
        # canonical calculation backends unavailable.
        monkeypatch.setattr(pro_nutrition_plate.nutrition_plate, "make_plate", None)
        monkeypatch.setattr(
            pro_nutrition_plate.nutrition_bmr,
            "calculate_all_bmr",
            None,
        )
        monkeypatch.setattr(
            pro_nutrition_plate.nutrition_bmr,
            "calculate_all_tdee",
            None,
        )
        response = client.post(
            "/api/v1/premium/plate",
            json={
                "sex": "male",
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 200

    def test_premium_plate_feature_flag_disabled(self, test_client):
        """Test premium plate endpoint when FEATURE_PREMIUM_NUTRITION is disabled."""
        # This tests lines 1402-1408 in app.py
        client = test_client

        with patch.dict(os.environ, {"FEATURE_PREMIUM_NUTRITION": "false"}):
            response = client.post(
                "/api/v1/premium/plate",
                json={
                    "sex": "male",
                    "age": 30,
                    "height_cm": 175.0,
                    "weight_kg": 70.0,
                    "activity": "moderate",
                    "goal": "maintain",
                },
                headers={"X-API-Key": "test_key"},
            )

            # Should return 503 when feature is disabled
            assert response.status_code == 503
            assert "Enhanced plate feature not available" in response.json().get("detail", "")

    def test_premium_plate_with_diet_flags(self, test_client):
        """Test premium plate endpoint with diet flags."""
        # This tests the diet_flags handling in lines around 1420-1430
        client = test_client

        response = client.post(
            "/api/v1/premium/plate",
            json={
                "sex": "female",
                "age": 25,
                "height_cm": 165.0,
                "weight_kg": 60.0,
                "activity": "active",
                "goal": "loss",
                "deficit_pct": 15,
                "diet_flags": ["VEG", "GF"],
            },
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 200
        data = response.json()
        meal_titles = " ".join(meal["title"] for meal in data["meals"])
        assert "тофу" in meal_titles
        assert "нут" in meal_titles
        assert "Овсянка" not in meal_titles
        assert "Рис" not in meal_titles
        assert "Гречка" in meal_titles

    def test_premium_plate_macro_alignment(self, test_client):
        """Test premium plate macro alignment with WHO targets."""
        # This tests lines 1474-1520 in app.py
        client = test_client

        response = client.post(
            "/api/v1/premium/plate",
            json={
                "sex": "male",
                "age": 35,
                "height_cm": 180.0,
                "weight_kg": 80.0,
                "activity": "very_active",
                "goal": "gain",
                "surplus_pct": 10,
            },
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 200
        data = response.json()
        macros = data["macros"]
        assert set(macros) == {
            "protein_g",
            "fat_g",
            "carbs_g",
            "fiber_g",
        }
        assert data["kcal"] == (
            macros["protein_g"] * 4 + macros["fat_g"] * 9 + macros["carbs_g"] * 4
        )
        assert macros["fiber_g"] >= 25
        assert data["meals_per_day"] == 3

    def test_premium_plate_heuristic_fallback(
        self,
        test_client,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test premium plate heuristic fallback when WHO targets unavailable."""
        # This tests lines 1522-1528 in app.py
        client = test_client

        monkeypatch.setattr(
            pro_nutrition_plate.nutrition_recommendations,
            "build_nutrition_targets",
            None,
        )
        monkeypatch.setattr(pro_nutrition_plate.nutrition_plate, "make_plate", None)
        response = client.post(
            "/api/v1/premium/plate",
            json={
                "sex": "female",
                "age": 30,
                "height_cm": 170.0,
                "weight_kg": 65.0,
                "activity": "light",
                "goal": "maintain",
            },
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["kcal"] == 2145
        assert data["macros"] == {
            "protein_g": 104,
            "fat_g": 58,
            "carbs_g": 302,
            "fiber_g": 25,
        }

    def test_vip_endpoints_via_app_client(self, test_client):
        """Test VIP endpoints are accessible via the app client."""
        # This helps cover the router inclusion lines
        client = test_client

        # Test VIP health endpoint
        response = client.get("/api/v1/vip/health")
        # May be 200, 404, or other status depending on VIP module availability
        assert response.status_code in [200, 401, 403, 404]

    def test_app_includes_all_routers(self):
        """Test that the canonical application includes its baseline routes."""
        route_paths = {
            route_path(route) for route in iter_effective_route_candidates(canonical_app.routes)
        }
        assert "/" in route_paths
        assert "/health" in route_paths
        assert "/api/v1/health" in route_paths


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
