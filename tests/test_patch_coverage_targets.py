"""Test coverage for specific patch coverage targets.

Covers missing lines identified in patch coverage report:
- app/routers/test.py line 25: production environment check
- mcp_pulseplate_server.py line 36: invalid DEFAULT_MODEL validation
"""

import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


def test_test_router_production_block(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover line 25: HTTPException when APP_ENV=production.

    Test router should raise 404 when accessed in production environment.
    """
    # Set production environment
    monkeypatch.setenv("APP_ENV", "production")

    # Import router after setting env
    from app.routers import test as test_router

    # The dependency should raise HTTPException
    with pytest.raises(HTTPException) as exc_info:
        test_router._ensure_non_production()

    assert exc_info.value.status_code == 404
    assert "production" in exc_info.value.detail.lower()


def test_mcp_server_invalid_default_model() -> None:
    """Cover line 36: ValueError for invalid DEFAULT_MODEL.

    MCP server should raise ValueError if DEFAULT_MODEL is not in ALLOWED_MODELS.
    """
    from mcp_pulseplate_server import PulsePlateMCPServer

    # Temporarily modify class constants to trigger validation error
    original_default = PulsePlateMCPServer.DEFAULT_MODEL
    original_allowed = PulsePlateMCPServer.ALLOWED_MODELS

    try:
        # Set invalid DEFAULT_MODEL
        PulsePlateMCPServer.DEFAULT_MODEL = "invalid-model-xyz"
        PulsePlateMCPServer.ALLOWED_MODELS = {"gpt-4o", "gpt-4o-mini"}

        # Mock OPENAI_API_KEY to avoid env var requirement
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with pytest.raises(ValueError, match="DEFAULT_MODEL.*must be in ALLOWED_MODELS"):
                PulsePlateMCPServer()

    finally:
        # Restore original values
        PulsePlateMCPServer.DEFAULT_MODEL = original_default
        PulsePlateMCPServer.ALLOWED_MODELS = original_allowed


def test_test_router_health_endpoint() -> None:
    """Ensure test router health endpoint works in non-production."""
    import importlib
    from app import routers

    # Reload to ensure non-production state
    importlib.reload(routers.test)

    # Create test client
    from app.routers.test import router as test_router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(test_router)
    client = TestClient(app)

    # Test health endpoint
    response = client.get("/api/v1/test/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
