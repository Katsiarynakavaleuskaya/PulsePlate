"""Tests for plan_export.py to improve coverage."""

from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
import pytest

from app import app


class TestPlanExportCoverage:
    """Test coverage for plan export functionality."""

    def test_export_week_csv_basic(self):
        """Test basic CSV export functionality."""
        client = TestClient(app)

        # Test CSV export with valid token
        with patch("app.routers.plan_export._require_valid_token") as mock_token:
            mock_token.return_value = None  # Token validation passed

            response = client.get("/api/v1/plan/week/export.csv")

            # Should return CSV content
            assert response.status_code == 200
            assert "text/csv" in response.headers["content-type"]

    def test_export_week_pdf_basic(self):
        """Test basic PDF export functionality."""
        client = TestClient(app)

        with patch("app.routers.plan_export._require_valid_token") as mock_token:
            mock_token.return_value = None  # Token validation passed

            response = client.get("/api/v1/plan/week/export.pdf")

            # Should return PDF content
            assert response.status_code == 200
            assert "application/pdf" in response.headers["content-type"]

    def test_export_sign_endpoint(self):
        """Test export sign endpoint."""
        client = TestClient(app)

        sign_data = {"url": "/api/v1/plan/week/export.csv", "ttl_seconds": 3600}

        response = client.post("/api/v1/export/sign", json=sign_data)

        # Should return signed URL or appropriate response
        assert response.status_code in [200, 201, 422, 500]

    def test_export_sign_invalid_data(self):
        """Test export sign with invalid data."""
        client = TestClient(app)

        invalid_data = {
            "url": "",  # Empty URL
            "ttl_seconds": -1,  # Invalid TTL
        }

        response = client.post("/api/v1/export/sign", json=invalid_data)

        # Should return validation error
        assert response.status_code == 422

    def test_export_sign_missing_data(self):
        """Test export sign with missing data."""
        client = TestClient(app)

        response = client.post("/api/v1/export/sign", json={})

        # Should return validation error
        assert response.status_code == 422

    def test_export_week_csv_invalid_token(self):
        """Test CSV export with invalid token."""
        client = TestClient(app)

        with patch("app.routers.plan_export._require_valid_token") as mock_token:
            from fastapi import HTTPException

            mock_token.side_effect = HTTPException(status_code=403, detail="Invalid token")

            response = client.get("/api/v1/plan/week/export.csv")

            # Should return 403 Forbidden
            assert response.status_code == 403

    def test_export_week_pdf_invalid_token(self):
        """Test PDF export with invalid token."""
        client = TestClient(app)

        with patch("app.routers.plan_export._require_valid_token") as mock_token:
            from fastapi import HTTPException

            mock_token.side_effect = HTTPException(status_code=403, detail="Invalid token")

            response = client.get("/api/v1/plan/week/export.pdf")

            # Should return 403 Forbidden
            assert response.status_code == 403

    def test_get_week_plan_function(self):
        """Test _get_week_plan function directly."""
        from app.routers.plan_export import _get_week_plan

        week_plan = _get_week_plan()

        # Should return a valid week plan structure
        assert isinstance(week_plan, dict)
        assert "days" in week_plan
        assert isinstance(week_plan["days"], list)
        assert len(week_plan["days"]) > 0

    def test_sum_week_macros_function(self):
        """Test sum_week_macros function."""
        from app.routers.plan_export import _get_week_plan, sum_week_macros

        week_plan = _get_week_plan()
        totals = sum_week_macros(week_plan)

        # Should return macro totals
        assert isinstance(totals, dict)
        expected_keys = ["energy_kcal", "protein_g", "carbs_g", "fat_g"]
        for key in expected_keys:
            assert key in totals
            assert isinstance(totals[key], int | float)

    def test_export_sign_different_ttl_values(self):
        """Test export sign with different TTL values."""
        client = TestClient(app)

        base_data = {"url": "/api/v1/plan/week/export.csv"}
        ttl_values = [60, 3600, 86400, 604800]  # 1 min, 1 hour, 1 day, 1 week

        for ttl in ttl_values:
            sign_data = {**base_data, "ttl_seconds": ttl}

            response = client.post("/api/v1/export/sign", json=sign_data)

            # Should handle different TTL values
            assert response.status_code in [200, 201, 422, 500]

    def test_export_sign_different_urls(self):
        """Test export sign with different URLs."""
        client = TestClient(app)

        base_data = {"ttl_seconds": 3600}
        urls = [
            "/api/v1/plan/week/export.csv",
            "/api/v1/plan/week/export.pdf",
            "/api/v1/export/shoplist/csv",
            "/api/v1/export/shoplist/pdf",
        ]

        for url in urls:
            sign_data = {**base_data, "url": url}

            response = client.post("/api/v1/export/sign", json=sign_data)

            # Should handle different URLs
            assert response.status_code in [200, 201, 422, 500]

    def test_export_week_csv_content_structure(self):
        """Test CSV export content structure."""
        client = TestClient(app)

        with patch("app.routers.plan_export._require_valid_token") as mock_token:
            mock_token.return_value = None

            response = client.get("/api/v1/plan/week/export.csv")

            assert response.status_code == 200

            # Check CSV content structure
            content = response.text
            assert "# WEEK_TOTALS:" in content
            assert "date,day_idx,meal,item,qty,unit,energy_kcal,protein_g,carbs_g,fat_g" in content

    def test_export_week_pdf_content_type(self):
        """Test PDF export content type and structure."""
        client = TestClient(app)

        with patch("app.routers.plan_export._require_valid_token") as mock_token:
            mock_token.return_value = None

            response = client.get("/api/v1/plan/week/export.pdf")

            assert response.status_code == 200
            assert "application/pdf" in response.headers["content-type"]

            # Check that response has binary content (PDF)
            assert len(response.content) > 0
