"""
Global test configuration and fixtures for the project.
"""

import faulthandler
import os
import signal
import sys
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from typing import cast, Iterator
from starlette.types import ASGIApp

# Enable faulthandler for debugging hangs/deadlocks (CI only to avoid noise)
# In CI: dumps thread stacks after N seconds, repeating every N seconds.
# Manual trigger (UNIX): kill -USR1 <pytest_pid> to dump stacks on demand.
#
# NOTE:
# Do NOT enable this for all local pytest runs (PYTEST_CURRENT_TEST is set for every test),
# otherwise longer suites will emit misleading "Timeout" dumps even when nothing is hung.
if os.getenv("CI"):
    faulthandler.enable()

    # SIGUSR1 is UNIX-only; skip on Windows safely
    sigusr1 = getattr(signal, "SIGUSR1", None)
    if sigusr1 is not None:
        faulthandler.register(sigusr1)  # Manual trigger

    timeout_s = int(os.getenv("PYTEST_FAULTHANDLER_TIMEOUT_S", "600"))
    faulthandler.dump_traceback_later(timeout=timeout_s, repeat=True)


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest environment before test collection.

    This hook runs BEFORE pytest starts collecting tests, ensuring
    environment variables are set before any modules are imported.
    This prevents import errors and shell environment instability.

    IMPORTANT: Only runs during actual pytest sessions, not when IDE
    language servers import this file.
    """
    # Guard: Skip if not running in an actual pytest session
    # This prevents IDE language servers from triggering DB initialization
    if not hasattr(config, "option"):
        return

    import contextlib

    # Set test environment variables BEFORE any imports
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("TESTING", "true")  # Enable export endpoints
    os.environ.setdefault("FEATURE_PREMIUM_NUTRITION", "true")
    os.environ.setdefault("VIP_MODULE_ENABLED", "true")
    os.environ.setdefault("ALLOW_DEV_API_KEY", "true")
    os.environ.setdefault("PYTHONPATH", ".:core:app:tests")
    os.environ.setdefault("CLIENT_FINGERPRINT_SALT", "test-salt-for-ci-only-not-for-production")

    # Configure test database path BEFORE core.db is imported
    # This ensures DATABASE_URL is set before any SQLAlchemy initialization
    db_path_env = os.environ.get("TEST_DB_PATH", "cache/test_app.sqlite")
    # Handle empty or invalid paths (Sourcery feedback)
    if not db_path_env or db_path_env == ".":
        db_path_env = "cache/test_app.sqlite"
    db_path = Path(db_path_env)

    # Handle pytest-xdist worker isolation
    # Prefer config.workerinput API over environment variable (Sourcery feedback)
    worker_info = getattr(config, "workerinput", {}) or {}
    worker_id = worker_info.get("workerid", "") or os.environ.get("PYTEST_XDIST_WORKER", "")
    if worker_id:
        import re

        # Use or for fallback (Sourcery suggestion)
        safe_worker = re.sub(r"[^A-Za-z0-9_-]", "", worker_id) or "worker"
        db_path = db_path.with_name(f"{db_path.stem}_{safe_worker}{db_path.suffix}")

    # Use pytest's root path instead of cwd for stability (Sourcery feedback)
    if not db_path.is_absolute():
        db_path = config.rootpath / db_path

    db_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["TEST_DB_PATH"] = str(db_path)

    # Remove stale DB file if it exists (prevent conflicts)
    with contextlib.suppress(OSError):
        db_path.unlink(missing_ok=True)

    # NOTE: DB initialization moved to session autouse fixture (_init_db_for_api_suite)
    # This prevents dual-Base issues from module reloads and ensures stable Base identity


class AppLoadError(ImportError):
    """Raised when app.py cannot be loaded."""

    pass


# NOTE: Database initialization is handled by _init_db_for_api_suite fixture in tests/conftest.py
# No separate verification fixture needed - _init_db_for_api_suite ensures DB is initialized


@pytest.fixture(scope="session", autouse=True)
def cleanup_async_resources() -> Iterator[None]:
    """Clean up async resources after test session to prevent ResourceWarnings."""
    yield

    # Clean up database connections FIRST before garbage collection
    try:
        import core.db

        if hasattr(core.db, "_RAW_ENGINE") and core.db._RAW_ENGINE:
            core.db._RAW_ENGINE.dispose()
        if hasattr(core.db, "engine") and core.db.engine:
            core.db.engine.dispose()
    except Exception:  # nosec B110
        pass  # Best-effort cleanup

    # Force garbage collection to close any remaining unclosed connections
    import gc

    gc.collect()


@pytest.fixture(scope="session")
def dynamic_app():
    """Load FastAPI app from legacy_app.py via standard import."""
    import legacy_app as app_module

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
def reset_environment() -> Iterator[None]:  # sourcery skip: use-contextlib-suppress
    """Automatically reset environment variables before and after each test."""
    # Save current environment
    old_env = dict(os.environ)

    # NOTE: We no longer track sys.modules state or delete modules.
    # Module cleanup should be done explicitly via module_purge.purge_modules() with protect lists.

    # Set default environment for tests
    os.environ.setdefault("FEATURE_PREMIUM_NUTRITION", "true")
    # Don't set API_KEY to enable lenient mode in tests (accepts any non-trivial key)
    # os.environ.setdefault("API_KEY", "test_key")
    os.environ.setdefault("VIP_MODULE_ENABLED", "true")
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("ALLOW_DEV_API_KEY", "true")
    os.environ.setdefault("PYTHONPATH", ".:core:app:tests")

    # Override API key validation for all tests
    # CRITICAL: Use sys.modules.get() instead of fresh import to prevent model re-registration.
    # Importing app in teardown triggers SQLAlchemy declarative mapping re-registration,
    # which causes "Table already defined" cascade failures in subsequent tests.
    # See: tests/conftest.py for metadata.clear() strategy for xdist workers.
    fastapi_app = sys.modules.get("app")
    if fastapi_app is not None and hasattr(fastapi_app, "app"):
        # Simple pass-through that accepts any non-empty API key
        def mock_get_api_key(api_key: str = "") -> str:
            if not api_key or len(api_key.strip()) < 3:
                from fastapi import HTTPException

                raise HTTPException(status_code=403, detail="Invalid API Key")
            return api_key

        # Override the dependency
        if hasattr(fastapi_app.app, "dependency_overrides"):
            get_api_key = getattr(fastapi_app, "get_api_key", None)
            if get_api_key is not None:
                fastapi_app.app.dependency_overrides[get_api_key] = mock_get_api_key

    yield

    # Restore environment
    os.environ.clear()
    os.environ.update(old_env)

    # Clear dependency overrides (use sys.modules.get to avoid re-import)
    fastapi_app = sys.modules.get("app")
    if (
        fastapi_app is not None
        and hasattr(fastapi_app, "app")
        and hasattr(fastapi_app.app, "dependency_overrides")
    ):
        fastapi_app.app.dependency_overrides.clear()

    # CRITICAL: Do NOT delete modules from sys.modules
    # This causes dual-Base issues, module identity chaos, and unpredictable test failures.
    # Module cleanup should be done explicitly via module_purge.purge_modules() with protect lists,
    # NOT via autouse fixtures that affect all tests.
    #
    # Why this is dangerous:
    # - Deleting app.* modules can cause re-imports that create new Base instances
    # - Deleting tests.* modules can break test isolation in unexpected ways
    # - Even with core.* protection, deleting app.* can trigger model re-registration
    # - This makes tests flaky and unpredictable, especially under pytest-xdist
    #
    # If module isolation is needed, use module_purge.purge_modules() explicitly in specific tests
    # with appropriate protect lists (e.g., protect core.db, core.models).


@pytest.fixture(autouse=True)
def reset_sys_modules() -> Iterator[None]:
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
            "PRO_API_KEYS": "test_pro_key",  # nosec B105: deterministic non-production test key (remove-by: 2026-09-30, ref: PR-1052)  # pragma: allowlist secret
            "VIP_API_KEYS": "test_vip_key",  # nosec B105: deterministic non-production test key (remove-by: 2026-09-30, ref: PR-1052)  # pragma: allowlist secret
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
    from tests._client import get_client

    client = get_client()

    try:
        yield client
    finally:
        # Properly close the client to clean up resources
        client.close()


@pytest.fixture
def isolated_test_client():
    """Fixture for creating isolated TestClient instances with clean app state.

    NOTE: Removed importlib.reload() to prevent dual-Base issues.
    Instead, create a fresh TestClient and clear dependency_overrides in teardown.
    """
    from app.main import app as main_app

    # Create TestClient with current app state (no reload to avoid dual-Base)
    client = TestClient(cast(ASGIApp, main_app))

    try:
        yield client
    finally:
        # Properly close the client to clean up resources
        client.close()
        # Clear dependency overrides to reset state
        if hasattr(main_app, "dependency_overrides"):
            main_app.dependency_overrides.clear()


@pytest.fixture
def app_client(test_client):
    """Alias for test_client to maintain compatibility with existing tests."""
    return test_client
