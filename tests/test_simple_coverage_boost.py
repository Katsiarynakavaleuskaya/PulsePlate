#!/usr/bin/env python3
"""
Simple coverage boost tests.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app from app.py file
import importlib.util

spec = importlib.util.spec_from_file_location("app_module", "legacy_app.py")
if spec is None or spec.loader is None:
    raise ImportError("Cannot load app.py")

app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app


class TestSimpleCoverageBoost:
    """Simple tests to boost coverage."""

    def test_health_endpoint(self):
        """Test health endpoint."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_root_endpoint(self):
        """Test root endpoint."""
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200

    def test_docs_endpoint(self):
        """Test docs endpoint."""
        client = TestClient(app)
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_endpoint(self):
        """Test OpenAPI endpoint."""
        client = TestClient(app)
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data

    def test_foods_search_endpoint(self):
        """Test foods search endpoint."""
        client = TestClient(app)
        response = client.get("/api/v1/foods/search?q=apple")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_recipes_endpoint(self):
        """Test recipes endpoint."""
        client = TestClient(app)
        response = client.get("/api/v1/recipes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_users_endpoint(self):
        """Test users endpoint."""
        client = TestClient(app)
        response = client.get("/api/v1/users")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_error_handling(self):
        """Test error handling."""
        client = TestClient(app)

        # Test invalid endpoint
        response = client.get("/invalid-endpoint")
        assert response.status_code == 404

    def test_lifespan_events(self):
        """Test lifespan events."""
        # This tests the lifespan context manager
        with TestClient(app) as client:
            # App startup and shutdown should be handled automatically
            pass

    def test_exception_handlers(self):
        """Test exception handlers."""
        client = TestClient(app)

        # Test with invalid JSON
        response = client.post(
            "/api/v1/bmi", content="invalid json", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
