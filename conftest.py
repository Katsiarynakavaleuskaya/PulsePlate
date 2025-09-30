"""
Global test configuration and fixtures for the project.
"""

import os
import sys
import pytest
import importlib.util
from fastapi.testclient import TestClient
from typing import cast
from starlette.types import ASGIApp


class AppLoadError(ImportError):
    """Raised when app.py cannot be loaded."""

    pass


@pytest.fixture(scope="session", autouse=True)
def init_test_database():
    """Initialize test database tables before running tests."""
    try:
        from core.db import init_db

        init_db()
    except Exception as e:
        # If DB initialization fails (e.g., DB not configured), tests should still run
        # but may fail if they require DB access
        print(f"Warning: Could not initialize test database: {e}")


@pytest.fixture(scope="session")
def dynamic_app():
    """Load FastAPI app dynamically from app.py"""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    spec = importlib.util.spec_from_file_location("app_module", "app.py")
    if spec is None or spec.loader is None:
        raise AppLoadError()

    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)

    # Apply API key override for this app instance
    def mock_get_api_key(api_key: str = ""):
        if not api_key or len(api_key.strip()) < 3:
            from fastapi import HTTPException

            raise HTTPException(status_code=403, detail="Invalid API Key")
        return api_key

    if hasattr(app_module.app, "dependency_overrides"):
        app_module.app.dependency_overrides[app_module.get_api_key] = mock_get_api_key

    return app_module.app


@pytest.fixture
def dynamic_client(dynamic_app):
    """TestClient using dynamically loaded app"""
    client = TestClient(cast(ASGIApp, dynamic_app))
    try:
        yield client
    finally:
        client.close()


@pytest.fixture(autouse=True)
def reset_environment():  # sourcery skip: use-contextlib-suppress
    """Automatically reset environment variables before and after each test."""
    # Save current environment
    old_env = dict(os.environ)

    # Save current sys.modules state
    old_modules = dict(sys.modules)

    # Set default environment for tests
    os.environ.setdefault("FEATURE_PREMIUM_NUTRITION", "true")
    # Don't set API_KEY to enable lenient mode in tests (accepts any non-trivial key)
    # os.environ.setdefault("API_KEY", "test_key")
    os.environ.setdefault("VIP_MODULE_ENABLED", "true")
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("ALLOW_DEV_API_KEY", "true")
    os.environ.setdefault("PYTHONPATH", ".:core:app:tests")

    # Override API key validation for all tests
    try:
        import app as app_module
        from app import app as fastapi_app

        # Simple pass-through that accepts any non-empty API key
        def mock_get_api_key(api_key: str = ""):
            if not api_key or len(api_key.strip()) < 3:
                from fastapi import HTTPException

                raise HTTPException(status_code=403, detail="Invalid API Key")
            return api_key

        # Override the dependency
        if hasattr(fastapi_app, "dependency_overrides"):
            from app import get_api_key

            fastapi_app.dependency_overrides[get_api_key] = mock_get_api_key
    except (ImportError, AttributeError):
        # App not yet loaded, that's fine
        pass

    yield

    # Restore environment
    os.environ.clear()
    os.environ.update(old_env)

    # Clear dependency overrides
    try:
        from app import app as fastapi_app

        if hasattr(fastapi_app, "dependency_overrides"):
            fastapi_app.dependency_overrides.clear()
    except (ImportError, AttributeError):
        pass

    # Restore sys.modules (be careful not to break everything)
    # Only restore modules that were added during the test
    current_modules = set(sys.modules.keys())
    original_modules = set(old_modules.keys())
    new_modules = current_modules - original_modules

    for module_name in new_modules:
        if module_name.startswith(("app.", "core.", "tests.")):
            try:
                del sys.modules[module_name]
            except KeyError:
                pass


@pytest.fixture(autouse=True)
def reset_sys_modules():
    """Reset sys.modules for VIP module tests."""
    # Store original VIP module if it exists
    original_vip_module = sys.modules.get("app.routers.vip")

    yield

    # Restore original VIP module
    if original_vip_module:
        sys.modules["app.routers.vip"] = original_vip_module
    elif "app.routers.vip" in sys.modules:
        del sys.modules["app.routers.vip"]


@pytest.fixture
def production_environment():  # sourcery skip: dict-assign-update-to-union
    """Fixture for production environment testing."""
    old_env = dict(os.environ)

    # Set production environment
    os.environ.update(
        {
            "APP_ENV": "production",
            "ALLOW_DEV_API_KEY": "false",
            "API_KEY": "production-secret-key",
            "FEATURE_PREMIUM_NUTRITION": "true",
            "VIP_MODULE_ENABLED": "true",
        }
    )

    yield

    # Restore environment
    os.environ.clear()
    os.environ.update(old_env)


@pytest.fixture
def test_environment():  # sourcery skip: dict-assign-update-to-union
    """Fixture for test environment testing."""
    old_env = dict(os.environ)

    # Set test environment
    os.environ.update(
        {
            "APP_ENV": "test",
            "ALLOW_DEV_API_KEY": "true",
            "API_KEY": "test_key",
            "FEATURE_PREMIUM_NUTRITION": "true",
            "VIP_MODULE_ENABLED": "true",
        }
    )

    yield

    # Restore environment
    os.environ.clear()
    os.environ.update(old_env)


@pytest.fixture
def premium_disabled_environment():  # sourcery skip: dict-assign-update-to-union
    """Fixture for testing with premium features disabled."""
    old_env = dict(os.environ)

    # Set environment with premium disabled
    os.environ.update(
        {
            "APP_ENV": "test",
            "ALLOW_DEV_API_KEY": "true",
            "API_KEY": "test_key",
            "FEATURE_PREMIUM_NUTRITION": "false",
            "VIP_MODULE_ENABLED": "false",
        }
    )

    yield

    # Restore environment
    os.environ.clear()
    os.environ.update(old_env)


@pytest.fixture
def test_client():
    """Fixture for creating and properly closing TestClient instances."""
    import app

    # Create TestClient
    client = TestClient(cast(ASGIApp, app.app))

    try:
        yield client
    finally:
        # Properly close the client to clean up resources
        client.close()


@pytest.fixture
def isolated_test_client():
    """Fixture for creating isolated TestClient instances with clean app state."""
    import importlib
    import app

    # Reload app module to get fresh state
    importlib.reload(app)

    # Create TestClient with fresh app
    client = TestClient(cast(ASGIApp, app.app))

    try:
        yield client
    finally:
        # Properly close the client to clean up resources
        client.close()

        # Reload app module again to reset state
        importlib.reload(app)


@pytest.fixture
def app_client(test_client):
    """Alias for test_client to maintain compatibility with existing tests."""
    return test_client
