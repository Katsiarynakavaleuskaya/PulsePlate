"""
Shared pytest fixtures for the PulsePlate test suite.
"""

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def app_module() -> ModuleType:
    """Dynamically load app.py and return the module."""
    repo_root = Path(__file__).parent.parent
    sys.path.insert(0, str(repo_root))

    app_path = repo_root / "app.py"
    spec = importlib.util.spec_from_file_location("app_module", str(app_path))
    if spec is None or spec.loader is None:
        pytest.skip("Cannot load app.py", allow_module_level=True)

    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    return app_module


@pytest.fixture
def app(app_module: ModuleType) -> FastAPI:
    """Return the FastAPI app instance with API key mock."""

    # Apply lenient API key mode
    def mock_get_api_key(api_key: str = ""):
        if not api_key or len(api_key.strip()) < 3:
            from fastapi import HTTPException

            raise HTTPException(status_code=403, detail="Invalid API Key")
        return api_key

    if hasattr(app_module.app, "dependency_overrides") and hasattr(app_module, "get_api_key"):
        app_module.app.dependency_overrides[app_module.get_api_key] = mock_get_api_key

    return app_module.app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Return a TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def api_key():
    """Set up and tear down API key for testing."""
    os.environ["API_KEY"] = "test_key"
    yield "test_key"
    if "API_KEY" in os.environ:
        del os.environ["API_KEY"]
