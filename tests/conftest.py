"""Shared pytest fixtures for the PulsePlate test suite.

Includes tenant-based sharding configuration for memory-efficient parallel testing.
"""

import importlib
import importlib.util
import logging
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Generator, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from core import db as db_module

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
        _sharding = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_sharding)
        # Register sharding hooks globally
        pytest_addoption = _sharding.pytest_addoption  # type: ignore[misc]
        pytest_collection_modifyitems = _sharding.pytest_collection_modifyitems  # type: ignore[misc]


@pytest.fixture(scope="session", autouse=True)
def configure_sqlite_database(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Configure and initialize a per-worker SQLite database for the test session."""
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("ENVIRONMENT", "test")

    worker_info = getattr(request.config, "workerinput", {}) or {}
    worker_id = worker_info.get("workerid", "master")

    base_path = Path(os.environ.get("TEST_DB_PATH", "cache/test_app.sqlite"))
    if worker_id != "master":
        base_path = base_path.with_name(f"{base_path.stem}_{worker_id}{base_path.suffix}")

    if not base_path.is_absolute():
        base_path = Path.cwd() / base_path

    base_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path = base_path.resolve()

    os.environ["TEST_DB_PATH"] = str(resolved_path)
    os.environ["DATABASE_URL"] = f"sqlite:///{resolved_path}"

    # Reload db module to pick up new DATABASE_URL
    db_module_reloaded = importlib.import_module("core.db")
    db_module_reloaded = importlib.reload(db_module_reloaded)

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

    if "app" in sys.modules:
        importlib.reload(sys.modules["app"])

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


@pytest.fixture(scope="session")
def app_module() -> ModuleType:
    """Dynamically load app.py and return the module.

    This fixture depends on setup_test_environment to ensure
    API_KEY is set before loading the app.
    """
    repo_root = Path(__file__).parent.parent
    sys.path.insert(0, str(repo_root))

    app_path = repo_root / "app.py"
    spec = importlib.util.spec_from_file_location("app_module", str(app_path))
    if spec is None or spec.loader is None:
        pytest.skip("Cannot load app.py", allow_module_level=True)

    # At this point we know spec and spec.loader are not None due to the check above
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


@pytest.fixture
def test_environment(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Set up deterministic test environment variables."""
    # Set consistent environment for deterministic testing
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "true")
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("API_KEY_REQUIRED", "true")
    monkeypatch.setenv("METRICS_ENABLED", "true")
    yield
    # Cleanup is automatic with monkeypatch


@pytest.fixture(autouse=True)
def _cleanup_users() -> Generator[None, None, None]:
    """RU: Очищает таблицу пользователей между тестами.

    EN: Ensure users table is cleared between tests.
    """

    def _truncate() -> None:
        with db_module.session_scope() as session:
            session.execute(text("DELETE FROM users"))

    try:
        _truncate()
    except OperationalError as e:
        # Database not accessible - yield and skip cleanup to avoid test pollution
        logger.warning(f"Database not accessible during test setup: {e}")
        yield
        return

    yield

    # Cleanup after test - re-raise on errors to surface cleanup failures
    try:
        with db_module.session_scope() as session:
            session.execute(text("DELETE FROM users"))
    except OperationalError as e:
        # Re-raise to fail the test on cleanup errors
        # This prevents test pollution and flakiness
        logger.error(f"Test cleanup failed - database not accessible: {e}")
        raise
