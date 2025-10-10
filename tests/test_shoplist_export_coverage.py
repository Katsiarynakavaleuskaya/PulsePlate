"""Tests for shoplist_export.py to improve coverage."""

from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
import pytest

from app import app


class TestShoplistExportCoverage:
    """Test coverage for shoplist export functionality."""

    def test_export_shoplist_csv_basic(self):
        """Test basic CSV shoplist export."""
        client = TestClient(app)

        with (
            patch("app.routers.shoplist_export.get_unified_food_db") as mock_food_db,
            patch("app.routers.shoplist_export.require_api_key") as mock_api_key,
        ):
            mock_food_db.return_value = Mock()
            mock_api_key.return_value = "test_key"

            response = client.get(
                "/api/v1/export/shoplist/csv",
                params={
                    "sex": "male",
                    "age": 30,
                    "height_cm": 180,
                    "weight_kg": 75,
                    "activity": "moderate",
                    "goal": "maintain",
                },
                headers={"X-API-Key": "test_key"},
            )

            assert response.status_code == 200
            assert "text/csv" in response.headers["content-type"]

    def test_export_shoplist_pdf_basic(self):
        """Test basic PDF shoplist export."""
        client = TestClient(app)

        with (
            patch("app.routers.shoplist_export.get_unified_food_db") as mock_food_db,
            patch("app.routers.shoplist_export.require_api_key") as mock_api_key,
        ):
            mock_food_db.return_value = Mock()
            mock_api_key.return_value = "test_key"

            response = client.get(
                "/api/v1/export/shoplist/pdf",
                params={
                    "sex": "female",
                    "age": 25,
                    "height_cm": 165,
                    "weight_kg": 60,
                    "activity": "active",
                    "goal": "loss",
                },
                headers={"X-API-Key": "test_key"},
            )

            assert response.status_code == 200
            assert "application/pdf" in response.headers["content-type"]

    def test_export_shoplist_with_targets(self):
        """Test shoplist export with custom targets."""
        client = TestClient(app)

        with (
            patch("app.routers.shoplist_export.get_unified_food_db") as mock_food_db,
            patch("app.routers.shoplist_export.require_api_key") as mock_api_key,
        ):
            mock_food_db.return_value = Mock()
            mock_api_key.return_value = "test_key"

            response = client.get(
                "/api/v1/export/shoplist/csv",
                params={"kcal_daily": 2000, "protein_g": 150, "carbs_g": 250, "fat_g": 80},
                headers={"X-API-Key": "test_key"},
            )

            assert response.status_code == 200

    def test_export_shoplist_error_handling(self):
        """Test error handling in shoplist export."""
        client = TestClient(app)

        with (
            patch("app.routers.shoplist_export.get_unified_food_db") as mock_food_db,
            patch("app.routers.shoplist_export.require_api_key") as mock_api_key,
        ):
            mock_food_db.side_effect = Exception("Database error")
            mock_api_key.return_value = "test_key"

            response = client.get(
                "/api/v1/export/shoplist/csv",
                params={
                    "sex": "male",
                    "age": 30,
                    "height_cm": 180,
                    "weight_kg": 75,
                    "activity": "moderate",
                    "goal": "maintain",
                },
                headers={"X-API-Key": "test_key"},
            )

            assert response.status_code in [500, 422]

    def test_export_shoplist_missing_params(self):
        """Test shoplist export with missing parameters."""
        client = TestClient(app)

        with patch("app.routers.shoplist_export.require_api_key") as mock_api_key:
            mock_api_key.return_value = "test_key"

            response = client.get(
                "/api/v1/export/shoplist/csv", params={}, headers={"X-API-Key": "test_key"}
            )

            assert response.status_code == 422

    def test_export_shoplist_invalid_params(self):
        """Test shoplist export with invalid parameters."""
        client = TestClient(app)

        with patch("app.routers.shoplist_export.require_api_key") as mock_api_key:
            mock_api_key.return_value = "test_key"

            response = client.get(
                "/api/v1/export/shoplist/csv",
                params={
                    "sex": "invalid",
                    "age": -5,
                    "height_cm": 0,
                    "weight_kg": -10,
                    "activity": "invalid",
                    "goal": "invalid",
                },
                headers={"X-API-Key": "test_key"},
            )

            assert response.status_code == 422

    def test_export_shoplist_different_formats(self):
        """Test different shoplist export formats."""
        client = TestClient(app)

        with (
            patch("app.routers.shoplist_export.get_unified_food_db") as mock_food_db,
            patch("app.routers.shoplist_export.require_api_key") as mock_api_key,
        ):
            mock_food_db.return_value = Mock()
            mock_api_key.return_value = "test_key"

            base_params = {
                "sex": "male",
                "age": 30,
                "height_cm": 180,
                "weight_kg": 75,
                "activity": "moderate",
                "goal": "maintain",
            }

            # Test CSV format
            csv_response = client.get(
                "/api/v1/export/shoplist/csv", params=base_params, headers={"X-API-Key": "test_key"}
            )
            assert csv_response.status_code == 200

            # Test PDF format
            pdf_response = client.get(
                "/api/v1/export/shoplist/pdf", params=base_params, headers={"X-API-Key": "test_key"}
            )
            assert pdf_response.status_code == 200

    def test_export_shoplist_different_goals(self):
        """Test shoplist export with different fitness goals."""
        client = TestClient(app)

        with (
            patch("app.routers.shoplist_export.get_unified_food_db") as mock_food_db,
            patch("app.routers.shoplist_export.require_api_key") as mock_api_key,
        ):
            mock_food_db.return_value = Mock()
            mock_api_key.return_value = "test_key"

            base_params = {
                "sex": "female",
                "age": 25,
                "height_cm": 165,
                "weight_kg": 60,
                "activity": "active",
            }

            goals = ["loss", "maintain", "gain"]

            for goal in goals:
                response = client.get(
                    "/api/v1/export/shoplist/csv",
                    params={**base_params, "goal": goal},
                    headers={"X-API-Key": "test_key"},
                )
                assert response.status_code == 200

    def test_export_shoplist_different_activities(self):
        """Test shoplist export with different activity levels."""
        client = TestClient(app)

        with (
            patch("app.routers.shoplist_export.get_unified_food_db") as mock_food_db,
            patch("app.routers.shoplist_export.require_api_key") as mock_api_key,
        ):
            mock_food_db.return_value = Mock()
            mock_api_key.return_value = "test_key"

            base_params = {
                "sex": "male",
                "age": 30,
                "height_cm": 180,
                "weight_kg": 75,
                "goal": "maintain",
            }

            activities = ["sedentary", "light", "moderate", "active", "very_active"]

            for activity in activities:
                response = client.get(
                    "/api/v1/export/shoplist/csv",
                    params={**base_params, "activity": activity},
                    headers={"X-API-Key": "test_key"},
                )
                assert response.status_code == 200

    def test_export_shoplist_diet_flags(self):
        """Test shoplist export with different diet flags."""
        client = TestClient(app)

        with (
            patch("app.routers.shoplist_export.get_unified_food_db") as mock_food_db,
            patch("app.routers.shoplist_export.require_api_key") as mock_api_key,
        ):
            mock_food_db.return_value = Mock()
            mock_api_key.return_value = "test_key"

            base_params = {
                "sex": "female",
                "age": 25,
                "height_cm": 165,
                "weight_kg": 60,
                "activity": "moderate",
                "goal": "maintain",
            }

            diet_flags = ["VEG", "GF", "VEGAN", "KETO"]

            for flag in diet_flags:
                response = client.get(
                    "/api/v1/export/shoplist/csv",
                    params={**base_params, "diet_flags": flag},
                    headers={"X-API-Key": "test_key"},
                )
                assert response.status_code == 200

    def test_export_shoplist_currency_options(self):
        """Test shoplist export with different currency options."""
        client = TestClient(app)

        with (
            patch("app.routers.shoplist_export.get_unified_food_db") as mock_food_db,
            patch("app.routers.shoplist_export.require_api_key") as mock_api_key,
        ):
            mock_food_db.return_value = Mock()
            mock_api_key.return_value = "test_key"

            base_params = {
                "sex": "male",
                "age": 30,
                "height_cm": 180,
                "weight_kg": 75,
                "activity": "moderate",
                "goal": "maintain",
            }

            currencies = ["USD", "EUR", "RUB", "BYN"]

            for currency in currencies:
                response = client.get(
                    "/api/v1/export/shoplist/csv",
                    params={**base_params, "currency": currency},
                    headers={"X-API-Key": "test_key"},
                )
                assert response.status_code == 200
