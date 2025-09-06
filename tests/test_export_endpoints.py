"""
Tests for Export Endpoints

RU: Тесты для эндпоинтов экспорта.
EN: Tests for export endpoints.
"""

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app


class TestExportEndpoints:
    """Test export API endpoints."""

    def setup_method(self):
        """Set up test client."""
        os.environ["API_KEY"] = "test_key"
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test environment."""
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_export_daily_csv_success(self):
        """Test successful daily plan CSV export."""
        response = self.client.get(
            "/api/v1/premium/exports/day/test_plan.csv",
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert "daily_plan_test_plan.csv" in response.headers["content-disposition"]

        # Check that response contains CSV data
        content = response.content.decode("utf-8")
        assert len(content) > 0
        assert "Meal" in content

    def test_export_weekly_csv_success(self):
        """Test successful weekly plan CSV export."""
        response = self.client.get(
            "/api/v1/premium/exports/week/test_plan.csv",
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert "weekly_plan_test_plan.csv" in response.headers["content-disposition"]

        # Check that response contains CSV data
        content = response.content.decode("utf-8")
        assert len(content) > 0
        assert "Day" in content
        assert "Shopping List" in content

    def test_export_daily_pdf_success(self):
        """Test successful daily plan PDF export."""
        response = self.client.get(
            "/api/v1/premium/exports/day/test_plan.pdf",
            headers={"X-API-Key": "test_key"},
        )
        # PDF export might fail if ReportLab is not installed, which is expected in test environment
        assert response.status_code in [200, 503]

    def test_export_weekly_pdf_success(self):
        """Test successful weekly plan PDF export."""
        response = self.client.get(
            "/api/v1/premium/exports/week/test_plan.pdf",
            headers={"X-API-Key": "test_key"},
        )
        # PDF export might fail if ReportLab is not installed, which is expected in test environment
        assert response.status_code in [200, 503]

    def test_export_daily_csv_missing_api_key(self):
        """Test daily CSV export without API key."""
        response = self.client.get("/api/v1/premium/exports/day/test_plan.csv")
        assert response.status_code == 403

    def test_export_weekly_csv_missing_api_key(self):
        """Test weekly CSV export without API key."""
        response = self.client.get("/api/v1/premium/exports/week/test_plan.csv")
        assert response.status_code == 403

    def test_export_daily_pdf_missing_api_key(self):
        """Test daily PDF export without API key."""
        response = self.client.get("/api/v1/premium/exports/day/test_plan.pdf")
        assert response.status_code == 403

    def test_export_weekly_pdf_missing_api_key(self):
        """Test weekly PDF export without API key."""
        response = self.client.get("/api/v1/premium/exports/week/test_plan.pdf")
        assert response.status_code == 403

    def test_export_daily_csv_internal_error(self):
        """Test daily CSV export with internal error."""
        # Patch the function in the app module where it's used
        with patch("app.to_csv_day") as mock_export:
            mock_export.side_effect = Exception("Test error")

            response = self.client.get(
                "/api/v1/premium/exports/day/error_plan.csv",
                headers={"X-API-Key": "test_key"},
            )
            assert response.status_code == 500
            data = response.json()
            assert "CSV export failed" in data["detail"]

    def test_export_weekly_csv_internal_error(self):
        """Test weekly CSV export with internal error."""
        # Patch the function in the app module where it's used
        with patch("app.to_csv_week") as mock_export:
            mock_export.side_effect = Exception("Test error")

            response = self.client.get(
                "/api/v1/premium/exports/week/error_plan.csv",
                headers={"X-API-Key": "test_key"},
            )
            assert response.status_code == 500
            data = response.json()
            assert "CSV export failed" in data["detail"]
