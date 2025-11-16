"""
Shared pytest fixtures for the PulsePlate test suite.
"""

import importlib
import importlib.util
import logging
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Generator, Iterator, cast
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Configure logger for test cleanup operations
logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def configure_sqlite_database(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Configure and initialize a per-worker SQLite database for the test session."""
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("ENVIRONMENT", "test")
    # Enable premium features by default in tests (individual tests can override)
    os.environ.setdefault("FEATURE_PREMIUM_NUTRITION", "true")

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

    db_module = importlib.import_module("core.db")
    db_module = importlib.reload(db_module)

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

    db_module.init_db()

    if "app" in sys.modules:
        importlib.reload(sys.modules["app"])

    yield

    # Teardown: Clean up database connections and files
    try:
        # Close database connections if available
        # First, close the raw engine if it exists
        if hasattr(db_module, "_RAW_ENGINE") and db_module._RAW_ENGINE:
            try:
                db_module._RAW_ENGINE.dispose()
                logger.debug(f"Disposed raw database engine for worker {worker_id}")
            except Exception as e:
                logger.warning(f"Error disposing raw database engine: {e}")

        if hasattr(db_module, "engine") and db_module.engine:
            try:
                db_module.engine.dispose()
                logger.debug(f"Disposed database engine for worker {worker_id}")
            except Exception as e:
                logger.warning(f"Error disposing database engine: {e}")

        # Close any active sessions - SessionLocal is a sessionmaker, not a session
        # The sessionmaker doesn't have sessions to close, but we can clear the engine binding
        if hasattr(db_module, "SessionLocal"):
            try:
                # Clear the bind to prevent any new sessions from being created
                db_module.SessionLocal.configure(bind=None)
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
def setup_test_environment() -> Generator[None, None, None]:
    """
    Set up test environment variables before any tests run.

    This fixture runs automatically for the entire session to ensure
    API_KEY is configured before the app module is loaded.
    """
    os.environ["API_KEY"] = "test_key"
    try:
        yield
    finally:
        os.environ.pop("API_KEY", None)


@pytest.fixture(scope="session")
def app_module() -> ModuleType:
    """
    Dynamically load app.py and return the module.

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
    def mock_get_api_key(api_key: str = "") -> str:
        """
        Validates the provided API key for test requests.

        This function checks if the API key is present and meets a minimum length requirement.
        If the key is invalid, it raises an HTTPException with a 403 status code.

        Args:
            api_key: The API key string to validate.

        Returns:
            The validated API key string.

        Raises:
            HTTPException: If the API key is missing or too short.
        """
        if not api_key or len(api_key.strip()) < 3:
            from fastapi import HTTPException

            raise HTTPException(status_code=403, detail="Invalid API Key")
        return api_key

    app_instance = getattr(app_module, "app", None)
    if not isinstance(app_instance, FastAPI):
        raise RuntimeError("app_module.app is not initialised")
    app_instance = cast(FastAPI, app_instance)
    if hasattr(app_module, "get_api_key"):
        app_instance.dependency_overrides[app_module.get_api_key] = mock_get_api_key

    return app_instance


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Return a TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def inject_client_into_test_class(request: pytest.FixtureRequest, client: TestClient) -> None:
    """Autouse fixture that injects TestClient into test class instances.

    This fixture only runs when request.instance exists (i.e., for test class methods),
    and sets self.client on the test class instance. This eliminates the need for
    duplicate _setup_client fixtures in individual test classes.
    """
    # Only inject into test class instances, not standalone test functions
    if hasattr(request, "instance") and request.instance is not None:
        try:
            setattr(request.instance, "client", client)
        except AttributeError:
            # Some legacy classes expose client as a read-only @property; skip injection for them.
            pass


@pytest.fixture
def api_key() -> str:
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


def _apply_test_environment(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    env_overrides = {
        "TESTING": "true",
        "APP_ENV": "test",
        "ALLOW_DEV_API_KEY": "true",
        "FEATURE_INSIGHT": "true",
        "FEATURE_PREMIUM_NUTRITION": "true",
        "VIP_MODULE_ENABLED": "true",
        "DEBUG": "true",
        "API_KEY": "test_key",
        "API_KEY_REQUIRED": "true",
        "METRICS_ENABLED": "true",
    }
    for key, value in env_overrides.items():
        monkeypatch.setenv(key, value)
    return env_overrides


@pytest.fixture
def test_environment(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> Generator[None, None, None]:
    """Set up deterministic test environment variables."""
    _apply_test_environment(monkeypatch)
    yield None
    # Cleanup handled by monkeypatch


@pytest.fixture
def _test_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[dict[str, str], None, None]:
    """Backward-compatible alias that exposes the env overrides dictionary."""
    env_overrides = _apply_test_environment(monkeypatch)
    yield env_overrides
    # Cleanup handled by monkeypatch


# Test doubles for pytest plugin tests
# Consolidated implementation supporting all test file requirements
class DummyMarker:
    """Mock marker for pytest plugin tests."""

    def __init__(self, name: str) -> None:
        self.name = name


class DummyPath:
    """Simple path mock that stores and returns the path string."""

    def __init__(self, path: str) -> None:
        self._path = path

    def __str__(self) -> str:
        return self._path


class DummyItem:
    """Comprehensive mock pytest item for plugin tests.

    Supports all features needed by test files:
    - Basic markers and path
    - Async function detection
    - Fixture names
    - Source code
    - Node ID
    """

    def __init__(
        self,
        markers: list[str],
        path: str = "tests/test_sample.py",
        name: str = "test_x",
        is_async: bool = False,
        fixturenames: list[str] | None = None,
        source: str = "",
    ) -> None:
        self._markers = [DummyMarker(m) for m in markers]
        self.fspath = DummyPath(path)
        self.name = name
        self.fixturenames = fixturenames or []
        self.nodeid = f"{path}::{name}"
        self._source = source

        # Initialize function attribute based on async flag
        self.function: Any
        if is_async:

            async def _async_func() -> None:
                return None

            self.function = _async_func
        else:

            def _sync_func() -> None:
                return None

            self.function = _sync_func

    def iter_markers(self) -> Iterator[DummyMarker]:
        """Return iterator over markers."""
        return iter(self._markers)

    def __getattr__(self, name: str) -> Any:
        """Handle missing attributes for compatibility."""
        if name == "__code__":
            raise AttributeError
        raise AttributeError(name)


# ============================================================================
# Fixtures for app module testing with environment isolation
# ============================================================================


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Provide clean environment isolation for tests that need to test environment-dependent behavior.

    RU: Предоставляет изолированное окружение для тестов, проверяющих поведение в зависимости от env.
    EN: Provides clean environment isolation for tests that need to test environment-dependent behavior.

    This fixture safely isolates environment variables by:
    1. Capturing a mapping of original values for keys that existed before the test
    2. Removing keys that were newly added during the test
    3. Restoring original values only for keys that existed originally
    4. Re-creating keys that were removed during the test by restoring their original value

    WARNING: Potential conflicts when tests use both this fixture and monkeypatch in the same scope.
    If you use monkeypatch.setenv/delenv in your test, those changes will be tracked by monkeypatch
    and may conflict with this fixture's restoration logic. Prefer using either this fixture OR
    monkeypatch directly, not both simultaneously.

    Usage:
        def test_something(clean_env, monkeypatch):
            monkeypatch.setenv("API_KEY", "test-key")
            # Test code here
            # Environment is automatically restored after test
    """
    # Capture mapping of original values for keys that existed before the test
    original_env: dict[str, str] = {k: v for k, v in os.environ.items()}
    yield
    # After test execution, restore environment
    current_keys = set(os.environ)
    original_keys = set(original_env)
    # Remove keys that were newly added during the test
    for key in current_keys - original_keys:
        monkeypatch.delenv(key, raising=False)
    # Restore original values only for keys that existed originally
    for key in original_keys:
        if key in os.environ:
            # Key still exists, restore original value
            monkeypatch.setenv(key, original_env[key])
        else:
            # Key was removed during test, re-create it with original value
            monkeypatch.setenv(key, original_env[key])


@pytest.fixture
def fresh_app(monkeypatch: pytest.MonkeyPatch) -> Generator[ModuleType, None, None]:
    """Safely reload app module for tests that need to test module-level initialization.

    RU: Безопасно перезагружает модуль app для тестов, проверяющих инициализацию на уровне модуля.
    EN: Safely reload app module for tests that need to test module-level initialization.

    This fixture uses importlib.reload() instead of del sys.modules, which is safer and
    more predictable. It ensures the app module is reloaded with current environment variables.

    WARNING: Use this fixture sparingly. Most tests should use the regular `app` fixture
    which provides a stable FastAPI instance. Only use `fresh_app` when you need to test
    module-level initialization logic that depends on environment variables.

    Usage:
        def test_module_init(fresh_app, monkeypatch):
            monkeypatch.setenv("API_KEY", "new-key")
            importlib.reload(fresh_app)
            # Test code here
    """
    import importlib

    if "app" in sys.modules:
        module = importlib.reload(sys.modules["app"])
    else:
        module = importlib.import_module("app")
        sys.modules["app"] = module

    yield module


@pytest.fixture
def mock_visualization(monkeypatch: pytest.MonkeyPatch) -> Generator[MagicMock, None, None]:
    """Provide a mock for BMI visualization function.

    RU: Предоставляет mock для функции визуализации BMI.
    EN: Provides a mock for BMI visualization function.

    Usage:
        def test_bmi_with_mock(mock_visualization):
            mock_visualization.return_value = {"available": False}
            # Test code
            mock_visualization.assert_called_once()
    """
    from unittest.mock import MagicMock

    mock_viz = MagicMock()
    monkeypatch.setattr("app.generate_bmi_visualization", mock_viz)
    yield mock_viz


@pytest.fixture
def disable_matplotlib(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Disable matplotlib for tests that need to test fallback behavior.

    RU: Отключает matplotlib для тестов, проверяющих fallback поведение.
    EN: Disables matplotlib for tests that need to test fallback behavior.

    Usage:
        def test_bmi_without_matplotlib(disable_matplotlib):
            # Test code that should work without matplotlib
    """
    monkeypatch.setattr("app.MATPLOTLIB_AVAILABLE", False)
    yield
    # Cleanup handled by monkeypatch


@pytest.fixture
def production_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Set up production-like environment for tests.

    RU: Настраивает production-подобное окружение для тестов.
    EN: Set up production-like environment for tests.

    Usage:
        def test_production_behavior(production_env):
            # Test code that should behave like production
    """
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "false")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    yield
    # Cleanup handled by monkeypatch
