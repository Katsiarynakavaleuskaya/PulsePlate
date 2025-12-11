"""Shared pytest fixtures for the PulsePlate test suite.

Includes tenant-based sharding configuration for memory-efficient parallel testing.
"""

import importlib
import importlib.util
import logging
import os
import sys
import warnings
from pathlib import Path
from types import ModuleType
from typing import Any, Generator, cast
import tempfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

from core import db as db_module

# Ensure key feature flags are enabled during test collection
os.environ.setdefault("FEATURE_BMI_PRO_ENABLED", "true")
os.environ.setdefault("BUSINESS_MODULE_ENABLED", "true")

# Configure logger for test cleanup operations
logger = logging.getLogger(__name__)


# ============================================================================
# TENANT-BASED SHARDING CONFIGURATION
# ============================================================================
# Imported from pytest_sharding.py to enable memory-efficient parallel testing
# Usage: pytest --shard-id=1 tests/
# ============================================================================

_sharding_module_path = Path(__file__).parent.parent / "pytest_sharding.py"
if _sharding_module_path.exists():
    _spec = importlib.util.spec_from_file_location("pytest_sharding", _sharding_module_path)
    if _spec and _spec.loader:
        try:
            _sharding = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_sharding)
            # Register sharding hooks globally
            pytest_addoption = _sharding.pytest_addoption
            pytest_collection_modifyitems = _sharding.pytest_collection_modifyitems
        except Exception as e:
            warnings.warn(f"Failed to load pytest_sharding.py: {e}. Sharding disabled.")


@pytest.fixture(scope="session", autouse=True)
def configure_sqlite_database(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Configure and initialize a per-worker SQLite database for the test session."""
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("ENVIRONMENT", "test")

    worker_info = getattr(request.config, "workerinput", {}) or {}
    worker_id = worker_info.get("workerid", "master")

    cache_root = Path.cwd() / "cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=f"test_db_{worker_id}_", dir=cache_root))
    base_path = temp_dir / "test_app.sqlite"

    base_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path = base_path.resolve()

    os.environ["TEST_DB_PATH"] = str(resolved_path)
    os.environ["DATABASE_URL"] = f"sqlite:///{resolved_path}"

    # Reload db module to pick up new DATABASE_URL
    db_module_reloaded = importlib.reload(importlib.import_module("core.db"))

    models_module = importlib.import_module("core.models")
    importlib.reload(models_module)

    # Remove existing database file if it exists to ensure clean state
    if resolved_path.exists():
        try:
            resolved_path.unlink()
            logger.debug(
                f"Removed existing test database file for worker {worker_id}: {resolved_path}"
            )
        except Exception as e:
            logger.debug(f"Could not remove existing database file: {e}")

    db_module_reloaded.init_db()

    # Ensure SQLite file is writable for tests
    try:
        resolved_path.chmod(0o666)
    except Exception as e:
        logger.debug(f"Could not set permissions on test database: {e}")

    yield

    # Teardown: Clean up database connections and files
    try:
        # Close database connections if available
        # First, close the raw engine if it exists
        if hasattr(db_module_reloaded, "_RAW_ENGINE") and db_module_reloaded._RAW_ENGINE:
            try:
                db_module_reloaded._RAW_ENGINE.dispose()
                logger.debug(f"Disposed raw database engine for worker {worker_id}")
            except Exception as e:
                logger.warning(f"Error disposing raw database engine: {e}")

        if hasattr(db_module_reloaded, "engine") and db_module_reloaded.engine:
            try:
                db_module_reloaded.engine.dispose()
                logger.debug(f"Disposed database engine for worker {worker_id}")
            except Exception as e:
                logger.warning(f"Error disposing database engine: {e}")

        # Close any active sessions - SessionLocal is a sessionmaker, not a session
        # The sessionmaker doesn't have sessions to close, but we can clear the engine binding
        if hasattr(db_module_reloaded, "SessionLocal"):
            try:
                # Clear the bind to prevent any new sessions from being created
                db_module_reloaded.SessionLocal.configure(bind=None)
                logger.debug(f"Cleared SessionLocal binding for worker {worker_id}")
            except Exception as e:
                logger.debug(f"Error clearing SessionLocal binding: {e}")

        # Remove the SQLite database file
        db_path = Path(os.environ.get("TEST_DB_PATH", ""))
        if db_path and db_path.exists():
            try:
                db_path.unlink()
                logger.info(f"Removed test database file: {db_path}")
            except FileNotFoundError:
                # File already removed, ignore
                pass
            except PermissionError:
                # File might still be in use by another process/worker
                logger.debug(f"Could not remove database file (may be in use): {db_path}")
            except Exception as e:
                logger.error(f"Unexpected error removing database file {db_path}: {e}")

            # Try to remove parent directory if empty
            try:
                parent_dir = db_path.parent
                if parent_dir.exists() and parent_dir.is_dir():
                    # Check if directory is empty (ignoring hidden files)
                    visible_files = [f for f in parent_dir.iterdir() if not f.name.startswith(".")]
                    if not visible_files:
                        parent_dir.rmdir()
                        logger.info(f"Removed empty cache directory: {parent_dir}")
            except OSError:
                # Directory not empty or cannot be removed
                pass
            except Exception as e:
                logger.debug(f"Could not remove parent directory: {e}")

    except Exception as e:
        logger.error(f"Error during database cleanup: {e}")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables before any tests run.

    This fixture runs automatically for the entire session to ensure
    API_KEY is configured before the app module is loaded.
    """
    # Set API key for the entire test session
    os.environ["API_KEY"] = "test_key"
    yield
    # Clean up after all tests
    if "API_KEY" in os.environ:
        del os.environ["API_KEY"]


_CACHED_APP_MODULE: ModuleType | None = None


@pytest.fixture(scope="session")
def app_module() -> ModuleType:
    """Dynamically load app.py and return a stable module instance.

    This fixture depends on setup_test_environment to ensure
    API_KEY is set before loading the app.
    """
    global _CACHED_APP_MODULE

    repo_root = Path(__file__).parent.parent
    sys.path.insert(0, str(repo_root))

    # Reuse cached module if we already loaded it (protects against
    # sys.modules["app"] being removed by other tests).
    if _CACHED_APP_MODULE is not None:
        if "app" not in sys.modules:
            sys.modules["app"] = _CACHED_APP_MODULE
        return _CACHED_APP_MODULE

    # Import app directly (app.py can import from app/ package)
    import app as app_mod

    _CACHED_APP_MODULE = app_mod
    return app_mod


@pytest.fixture(autouse=True)
def _ensure_app_module(app_module: ModuleType) -> None:
    """Ensure sys.modules always contains the cached app module."""
    sys.modules["app"] = app_module


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

    return cast(FastAPI, app_module.app)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Return a TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def api_key():
    """Return the test API key value.

    The actual environment setup is done by setup_test_environment fixture.
    This fixture just provides the key value for tests to use in headers.
    """
    return "test_key"


@pytest.fixture
def export_client(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Client configured for export endpoints with API key env."""
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("API_KEY_REQUIRED", "true")
    return client


@pytest.fixture(autouse=True)
def test_environment(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Set up deterministic test environment variables."""
    # Set consistent environment for deterministic testing
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "true")
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("FEATURE_BMI_PRO_ENABLED", "true")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("API_KEY_REQUIRED", "false")
    monkeypatch.setenv("METRICS_ENABLED", "true")
    yield
    # Cleanup is automatic with monkeypatch


@pytest.fixture(autouse=True)
def _cleanup_users(configure_sqlite_database: Any) -> Generator[None, None, None]:
    """Best-effort users table cleanup before/after each test.

    Attempts to truncate the users table before and after each test. If the
    database is not accessible (e.g., locked SQLite), logs a warning and
    continues to avoid flakiness.
    """
    # Use the reloaded db module from configure_sqlite_database fixture
    # to ensure consistency with the configured database
    db_module = configure_sqlite_database

    def _truncate() -> None:
        with db_module.session_scope() as session:
            session.execute(text("DELETE FROM users"))

    try:
        _truncate()
    except (OperationalError, ProgrammingError) as e:
        # Database not accessible or table doesn't exist - proceed without failing the suite
        logger.warning(f"Database not accessible or users table missing during test setup: {e}")
        try:
            db_module.init_db()
            try:
                _truncate()
            except Exception as retry_err:  # pragma: no cover - defensive
                logger.warning(f"Retrying users cleanup after init_db failed: {retry_err}")
        except Exception as init_err:
            logger.error(f"init_db during cleanup setup failed: {init_err}")
            # Don't return - must yield to ensure fixture lifecycle completes
    except Exception as e:
        # Handle any other unexpected exceptions
        logger.error(f"Unexpected error during test setup cleanup: {e}", exc_info=True)

    yield

    # Cleanup after test - log errors to reduce flakiness when SQLite is locked
    try:
        _truncate()
    except (OperationalError, ProgrammingError) as e:
        # Avoid hard failures on teardown to reduce flakiness in CI when SQLite is locked
        # or when the table doesn't exist
        logger.warning(
            f"Test cleanup skipped - database not accessible or users table missing: {e}"
        )
    except Exception as e:
        # Handle any other unexpected exceptions during teardown
        logger.warning(f"Unexpected error during test teardown cleanup: {e}")
