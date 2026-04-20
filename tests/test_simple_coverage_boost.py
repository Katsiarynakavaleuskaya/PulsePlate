#!/usr/bin/env python3
"""
Simple coverage boost tests.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import app
from app.services import food_store
from tests._helpers.api_headers import API_KEY_HEADERS


class TestSimpleCoverageBoost:
    """Simple tests to boost coverage."""

    def test_health_endpoint(self) -> None:
        """Test health endpoint."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_root_endpoint(self) -> None:
        """Test root endpoint."""
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200

    def test_docs_endpoint(self) -> None:
        """Test docs endpoint."""
        client = TestClient(app)
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_endpoint(self) -> None:
        """Test OpenAPI endpoint."""
        client = TestClient(app)
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data

    def test_foods_search_endpoint(self) -> None:
        """Test foods search endpoint."""
        client = TestClient(app)
        response = client.get("/api/v1/foods/search?q=apple")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_foods_search_endpoint_legacy_schema_returns_safe_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Legacy SQLite search path must stay 200 and expose additive default confidence."""
        db_path = tmp_path / "legacy_foods.sqlite"
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE foods (
                    id TEXT PRIMARY KEY,
                    canonical_name TEXT NOT NULL,
                    kcal REAL,
                    protein_g REAL,
                    fat_g REAL,
                    carbs_g REAL
                )
                """)
            conn.execute(
                "INSERT INTO foods (id, canonical_name, kcal, protein_g, fat_g, carbs_g) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("fid1", "Apple", 52.0, 0.3, 0.2, 14.0),
            )
            conn.commit()

        monkeypatch.setattr(food_store, "DB_PATH", db_path)
        food_store.reset_foods_nutrition_confidence_column_cache()

        client = TestClient(app)
        response = client.get("/api/v1/foods/search?q=apple")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data
        assert data[0]["name"] == "Apple"
        assert data[0]["nutrition_confidence"] == 0.0

    def test_recipes_endpoint(self) -> None:
        """Test recipes endpoint."""
        client = TestClient(app)
        response = client.get("/api/v1/recipes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_users_endpoint(self) -> None:
        """Test users endpoint."""
        client = TestClient(app)
        response = client.get("/api/v1/users", headers=API_KEY_HEADERS)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert isinstance(data, list)

    def test_error_handling(self) -> None:
        """Test error handling."""
        client = TestClient(app)

        # Test invalid endpoint
        response = client.get("/invalid-endpoint")
        assert response.status_code == 404

    def test_lifespan_events(self) -> None:
        """Test lifespan events."""
        # This tests the lifespan context manager
        with TestClient(app) as client:
            # App startup and shutdown should be handled automatically
            pass

    def test_exception_handlers(self) -> None:
        """Test exception handlers."""
        client = TestClient(app)

        # Test with invalid JSON
        response = client.post(
            "/api/v1/bmi", content="invalid json", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
