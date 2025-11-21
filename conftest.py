"""
Global test configuration and fixtures for the project.
"""

import contextlib
import importlib
import importlib.util
import logging
import os
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Union, cast

import pytest
from _pytest.monkeypatch import notset as _monkey_notset
from fastapi.testclient import TestClient
from starlette.types import ASGIApp

_original_monkeypatch_setattr = pytest.MonkeyPatch.setattr

# Required database tables for tests
REQUIRED_TABLES = ["users", "recipes", "meals", "food_items", "context"]


def _mock_get_api_key(api_key: str = "") -> str:
    """Mock API key validator for test fixtures."""
    if not api_key or len(api_key.strip()) < 3:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key


def pytest_configure(config: pytest.Config) -> None:
    """
    Ensure test database is configured & created before any module imports.

    Runs before collection and can prevent app.py from binding to the wrong DB.
    This hook runs earlier than fixtures and ensures DATABASE_URL is set before
    any module-level imports of app.py or core.db occur.
    """
    # Set test environment variables early
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("CLIENT_FINGERPRINT_SALT", "test-salt-for-ci-only-not-for-production")

    # Configure test database path
    db_path_env = os.environ.get("TEST_DB_PATH", "cache/test_app.sqlite")
    db_path = Path(db_path_env)

    # Get worker ID from pytest-xdist if running in parallel
    worker_info = getattr(config, "workerinput", {}) or {}
    worker_id = worker_info.get("workerid", "")
    if worker_id:
        import re

        safe_worker = re.sub(r"[^A-Za-z0-9_-]", "", worker_id) or "worker"
        db_path = db_path.with_name(f"{db_path.stem}_{safe_worker}{db_path.suffix}")

    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path

    db_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path = db_path.resolve()

    # Set DATABASE_URL before any imports
    os.environ["DATABASE_URL"] = f"sqlite:///{resolved_path}"
    os.environ["TEST_DB_PATH"] = str(resolved_path)

    # Remove stale DB file if it exists
    with contextlib.suppress(OSError):
        resolved_path.unlink(missing_ok=True)
    # Import/reload core.db and core.models so init_db() uses our DATABASE_URL
    if "core.db" in sys.modules:
        core_db = importlib.reload(sys.modules["core.db"])
    else:
        core_db = importlib.import_module("core.db")

    # Register models
    if "core.models" in sys.modules:
        importlib.reload(sys.modules["core.models"])
    else:
        import core.models  # noqa: F401

    # Initialize database schema
    try:
        core_db.init_db()

        # Verify tables were created
        from sqlalchemy import inspect

        with core_db.session_scope() as session:
            inspector = inspect(session.get_bind())
            tables = inspector.get_table_names()
            missing_tables = [t for t in REQUIRED_TABLES if t not in tables]
            if missing_tables:
                raise RuntimeError(
                    f"Required tables missing after init_db(): {missing_tables}. "
                    f"Found tables: {tables}. Database: {core_db.DATABASE_URL}"
                )
            tables_list = ", ".join(tables)
            logging.info(
                "✅ Test database initialized in pytest_configure "
                f"with {len(tables)} tables: {tables_list}"
            )
    except Exception as e:
        logging.error("Database initialization in pytest_configure failed: %s", e, exc_info=True)
        # Continue - session fixture will retry

    # If app was accidentally loaded, reload it to ensure it uses the initialized DB
    if "app" in sys.modules:
        importlib.reload(sys.modules["app"])

    # Enable debug logging for tests that assert on debug logs
    logging.getLogger().setLevel(logging.DEBUG)


def _coerce_side_effect(side_effect: object) -> Callable[..., Any]:
    """Convert a side_effect spec into a callable suitable for monkeypatch."""

    if isinstance(side_effect, type) and issubclass(side_effect, BaseException):

        def _raise_from_type(*_args: object, **_kwargs: object) -> None:
            raise side_effect()

        return _raise_from_type

    if isinstance(side_effect, BaseException):

        def _raise_from_instance(*_args: object, **_kwargs: object) -> None:
            raise side_effect

        return _raise_from_instance

    if callable(side_effect):
        return cast(Callable[..., Any], side_effect)

    raise TypeError("side_effect must be an exception class/instance or a callable")


def _setattr_with_side_effect(
    self: pytest.MonkeyPatch,
    target: str | object,
    name: object | str = _monkey_notset,
    value: object = _monkey_notset,
    raising: bool = True,
    *,
    side_effect: object | None = None,
) -> None:
    """Extend MonkeyPatch.setattr to support side_effect keyword."""

    if side_effect is not None:
        if value is not _monkey_notset:
            raise TypeError("Cannot pass both value and side_effect to monkeypatch.setattr")
        value = _coerce_side_effect(side_effect)

    # Handle case when target is a dotted path string and name is notset
    # e.g., monkeypatch.setattr("app.MATPLOTLIB_AVAILABLE", False)
    # In this case, pytest expects: target="app", name="MATPLOTLIB_AVAILABLE", value=False
    if (
        isinstance(target, str)
        and "." in target
        and name is _monkey_notset
        and value is not _monkey_notset
    ):
        # Split dotted path: "module.attr" -> module_name, attr_name
        module_name, attr_name = target.rsplit(".", 1)
        try:
            imported_module = importlib.import_module(module_name)
            module: Union[ModuleType, str] = imported_module
        except ImportError:
            # If module can't be imported, pass the string name directly
            # pytest.MonkeyPatch.setattr accepts both ModuleType and str
            module = module_name
        _original_monkeypatch_setattr(self, module, attr_name, value, raising)
        return

    # Standard case: pass through to original setattr
    # target can be str or object, but setattr accepts various types
    # Use cast to satisfy type checker while maintaining runtime flexibility
    if name is _monkey_notset:
        _original_monkeypatch_setattr(self, cast(Any, target), value, raising=raising)
    else:
        _original_monkeypatch_setattr(self, cast(Any, target), cast(str, name), value, raising)


pytest.MonkeyPatch.setattr = _setattr_with_side_effect  # type: ignore[method-assign]


class AppLoadError(ImportError):
    """Raised when app.py cannot be loaded."""

    pass


@pytest.fixture(scope="session", autouse=True)
def init_test_database(request: pytest.FixtureRequest) -> None:
    """Initialize test database tables before running tests.

    This fixture relies on pytest_configure to set DATABASE_URL and TEST_DB_PATH.
    It only verifies the database is initialized and tables exist, without
    re-deriving paths or re-initializing (to avoid double worker suffix).

    For pytest-xdist, each worker gets its own database file via pytest_configure.
    """
    import logging

    # Ensure test environment variables are set
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("ENVIRONMENT", "test")

    try:
        # Use DATABASE_URL and TEST_DB_PATH already set by pytest_configure
        # pytest_configure already handled worker suffix and DB initialization
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL not set. pytest_configure should have set it before this fixture runs."
            )

        # Import core.db to verify it uses the correct database
        import importlib

        if "core.db" in sys.modules:
            core_db = importlib.reload(sys.modules["core.db"])
        else:
            import core.db as core_db

        # Verify initialization succeeded by checking if tables exist
        from sqlalchemy import inspect

        missing_tables: list[str] = []
        with core_db.session_scope() as session:
            inspector = inspect(session.get_bind())
            tables = inspector.get_table_names()

            # Check for required tables
            missing_tables = [t for t in REQUIRED_TABLES if t not in tables]
            if missing_tables:
                # If tables are missing, try to initialize (pytest_configure may have failed)
                logging.warning(
                    f"Required tables missing: {missing_tables}. "
                    f"Attempting to initialize database..."
                )

        # Initialize outside of session context
        if missing_tables:
            core_db.init_db()
            # Re-check after initialization in a new session
            with core_db.session_scope() as session:
                inspector = inspect(session.get_bind())
                tables = inspector.get_table_names()
                missing_tables = [t for t in REQUIRED_TABLES if t not in tables]
                if missing_tables:
                    raise RuntimeError(
                        f"Required tables missing after init_db(): {missing_tables}. "
                        f"Found tables: {tables}. "
                        f"Database URL: {core_db.DATABASE_URL}"
                    )
                tables_str = ", ".join(tables)
                logging.info(f"✅ Database verified with {len(tables)} tables: {tables_str}")
        else:
            tables_str = ", ".join(tables)
            logging.info(f"✅ Database verified with {len(tables)} tables: {tables_str}")

        # Reload app module if needed to ensure it uses the initialized DB
        if "app" in sys.modules:
            importlib.reload(sys.modules["app"])
            logging.info("Reloaded app module after database verification")
    except Exception as e:
        # Log error and re-raise to fail fast in CI; tests requiring DB will not run
        logging.error(f"Failed to verify test database: {e}", exc_info=True)
        raise


@pytest.fixture(scope="session")
def dynamic_app() -> ASGIApp:
    """Load FastAPI app dynamically from app.py"""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    spec = importlib.util.spec_from_file_location("app_module", "app.py")
    if spec is None or spec.loader is None:
        raise AppLoadError()

    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)

    # Apply API key override for this app instance
    dependency_overrides = getattr(app_module.app, "dependency_overrides", None)
    get_api_key_fn = getattr(app_module, "get_api_key", None)
    if dependency_overrides is not None and get_api_key_fn is not None:
        dependency_overrides[get_api_key_fn] = _mock_get_api_key

    return cast(ASGIApp, app_module.app)


@pytest.fixture
def dynamic_client(dynamic_app: ASGIApp) -> Iterator[TestClient]:
    """TestClient using dynamically loaded app"""
    client = TestClient(dynamic_app)
    try:
        yield client
    finally:
        client.close()


@pytest.fixture(autouse=True)
def reset_environment() -> Iterator[None]:  # sourcery skip: use-contextlib-suppress
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
    os.environ.setdefault("CLIENT_FINGERPRINT_SALT", "test-salt-for-ci-only-not-for-production")

    # Do not import app here to avoid creating DB engine before DB init.
    # Dependency override for get_api_key will be applied later when the app is loaded
    # by the app fixtures (see dynamic_app/app fixture). Keeping this empty prevents
    # premature app import during autouse environment reset.

    yield

    # Restore environment
    os.environ.clear()
    os.environ |= old_env

    # Clear dependency overrides (only if app was loaded by test fixtures)
    # Do not import app here to avoid premature import
    if "app" in sys.modules:
        app_module = sys.modules["app"]
        fastapi_app = getattr(app_module, "app", None)
        if fastapi_app is not None:
            dependency_overrides = getattr(fastapi_app, "dependency_overrides", None)
            if dependency_overrides is not None:
                dependency_overrides.clear()

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
def production_environment() -> Iterator[None]:  # sourcery skip: dict-assign-update-to-union
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
def test_environment() -> Iterator[None]:  # sourcery skip: dict-assign-update-to-union
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
def premium_disabled_environment() -> Iterator[None]:  # sourcery skip: dict-assign-update-to-union
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
def test_client() -> Iterator[TestClient]:
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
def isolated_test_client() -> Iterator[TestClient]:
    """Fixture for creating isolated TestClient instances with clean app state."""
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
def app_client(test_client: TestClient) -> TestClient:
    """Alias for test_client to maintain compatibility with existing tests."""
    return test_client
