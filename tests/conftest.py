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
from typing import Any, Callable, Generator, Iterable, cast
import tempfile

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError, UnboundExecutionError

import core.recipe_synth as recipe_synth
from core.test_guards import EXTERNAL_HTTP_BLOCKED_IN_TESTS_MESSAGE

# ============================================================================
# CI NETWORK GUARD (prevents flaky real external calls)
# ============================================================================
# Nightly runs have previously flaked due to unintended external HTTP calls (e.g., USDA 429).
# In CI we forbid outbound network access from tests; allow localhost + in-process TestClient only.


@pytest.fixture(autouse=True)
def _block_external_network_in_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    enabled = bool(os.getenv("CI")) or os.getenv("BLOCK_TEST_NETWORK", "").lower() in {
        "1",
        "true",
        "yes",
    }
    if not enabled or os.getenv("ALLOW_TEST_NETWORK", "").lower() in {"1", "true", "yes"}:
        return

    # Allow localhost for things like docker-compose or explicit local services, and
    # allow the in-process Starlette/FastAPI TestClient host (http://testserver).
    allowed_hosts = {"127.0.0.1", "localhost", "::1", "testserver"}
    extra_hosts = os.getenv("TEST_NETWORK_ALLOWED_HOSTS", "")
    if extra_hosts.strip():
        allowed_hosts |= {h.strip() for h in extra_hosts.split(",") if h.strip()}

    def _is_external_url(url: str | object) -> bool:
        s = str(url)
        if s.startswith(("http://", "https://")):
            from urllib.parse import urlparse

            parsed = urlparse(s)
            host = parsed.hostname
            if not host:
                return True
            return host not in allowed_hosts
        return False

    httpx = None
    try:
        import httpx as _httpx

        httpx = _httpx
    except Exception:  # pragma: no cover
        pass

    if httpx is not None:
        real_client_request = httpx.Client.request
        real_async_request = httpx.AsyncClient.request

        def client_request(
            self: httpx.Client,
            method: str,
            url: str | httpx.URL,
            *args: object,
            **kwargs: object,
        ) -> httpx.Response:
            if _is_external_url(url):
                raise AssertionError(
                    f"{EXTERNAL_HTTP_BLOCKED_IN_TESTS_MESSAGE}: {method} {url} "
                    "(set ALLOW_TEST_NETWORK=true to bypass in CI; "
                    "or add host via TEST_NETWORK_ALLOWED_HOSTS=host1,host2)"
                )
            return real_client_request(self, method, url, *args, **kwargs)

        async def async_request(
            self: httpx.AsyncClient,
            method: str,
            url: str | httpx.URL,
            *args: object,
            **kwargs: object,
        ) -> httpx.Response:
            if _is_external_url(url):
                raise AssertionError(
                    f"{EXTERNAL_HTTP_BLOCKED_IN_TESTS_MESSAGE}: {method} {url} "
                    "(set ALLOW_TEST_NETWORK=true to bypass in CI; "
                    "or add host via TEST_NETWORK_ALLOWED_HOSTS=host1,host2)"
                )
            return await real_async_request(self, method, url, *args, **kwargs)

        monkeypatch.setattr(httpx.Client, "request", client_request, raising=True)
        monkeypatch.setattr(httpx.AsyncClient, "request", async_request, raising=True)

    requests = None
    try:
        import requests as _requests

        requests = _requests
    except Exception:  # pragma: no cover
        pass

    if requests is not None:
        real_requests_request = requests.sessions.Session.request

        def session_request(
            self: requests.sessions.Session,
            method: str,
            url: str,
            *args: object,
            **kwargs: object,
        ) -> requests.Response:
            if _is_external_url(url):
                raise AssertionError(
                    f"{EXTERNAL_HTTP_BLOCKED_IN_TESTS_MESSAGE}: {method} {url} "
                    "(set ALLOW_TEST_NETWORK=true to bypass in CI; "
                    "or add host via TEST_NETWORK_ALLOWED_HOSTS=host1,host2)"
                )
            return real_requests_request(self, method, url, *args, **kwargs)

        monkeypatch.setattr(requests.sessions.Session, "request", session_request, raising=True)


# NOTE: core.db is imported LAZILY (inside fixtures) to avoid creating Base
# before pytest_configure sets DATABASE_URL. Direct module-level import here
# would create a Base instance before conftest's reload, causing dual-Base issues.

# Ensure key feature flags are enabled during test collection
os.environ.setdefault("FEATURE_BMI_PRO_ENABLED", "true")
os.environ.setdefault("BUSINESS_MODULE_ENABLED", "true")
os.environ.setdefault("VIP_MODULE_ENABLED", "true")

# Configure logger for test cleanup operations
logger = logging.getLogger(__name__)


# ============================================================================
# DATABASE INITIALIZATION FOR API TESTS
# ============================================================================
@pytest.fixture(autouse=True, scope="session")
def _init_db_for_api_suite(configure_sqlite_database: Any) -> None:
    """
    RU: Глобальная инициализация DB для API тестов (legacy expectation: SessionLocal is ready).
    EN: Initialize DB once for API tests; keeps legacy tests stable without import-time side effects.

    This fixture ensures SessionLocal is available for API tests that expect implicit DB initialization.
    Unit tests for core.db should use reset_db_for_tests() explicitly and should not depend on this.

    CRITICAL: Import core.models here to ensure models are registered with the canonical Base
    before any tests run. This prevents dual-Base issues.

    CRITICAL: Depends on configure_sqlite_database to ensure per-worker DATABASE_URL is set first.
    """
    import core.db as core_db
    import core.models  # noqa: F401  # Ensure models are registered with Base

    # Initialize DB if not already initialized
    # init_db() is idempotent, so safe to call multiple times
    core_db.init_db()


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


@pytest.fixture(autouse=True)
def _reset_recipe_synth_singleton() -> Generator[None, None, None]:
    """Reset RecipeSynthesizer singleton before and after each test.

    Prevents cross-test contamination when tests initialize the synthesizer with different
    templates_dir values (e.g., custom/templates vs data/recipe_templates), which would
    otherwise cause ValueError in VIP endpoints under xdist sharding.
    """
    # Best-effort reset before test
    try:
        recipe_synth.reset_recipe_synthesizer()
    except Exception:
        # Defensive: singleton reset should not break tests even if implementation changes
        logger.debug("Failed to reset recipe synthesizer before test", exc_info=True)

    yield

    # Best-effort reset after test
    try:
        recipe_synth.reset_recipe_synthesizer()
    except Exception:
        logger.debug("Failed to reset recipe synthesizer after test", exc_info=True)


@pytest.fixture(scope="session", autouse=True)
def configure_sqlite_database(request: pytest.FixtureRequest) -> Generator[Any, None, None]:
    """Configure and initialize a per-worker SQLite database for the test session.

    Yields:
        The DB module for use by dependent fixtures (e.g., _cleanup_users).
    """
    # RU: Жёсткий reset глобального engine между тестами.
    # EN: Hard reset of global engine between tests.
    import core.db as core_db

    engine = getattr(core_db, "_RAW_ENGINE", None)
    if engine is not None:
        engine.dispose()
        core_db._RAW_ENGINE = None

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

    # Import DB module (no reload needed - init_db() handles URL changes).
    #
    # Rationale:
    # - Several tests/modules may import ORM models during collection; reloading
    #   core.db/core.models would rebind model classes and break existing references.
    # - core.db.init_db() already recreates the engine/session when DATABASE_URL changes.
    import core.db as db_module

    # Remove existing database file if it exists to ensure clean state
    if resolved_path.exists():
        try:
            resolved_path.unlink()
            logger.debug(
                f"Removed existing test database file for worker {worker_id}: {resolved_path}"
            )
        except Exception as e:
            logger.debug(f"Could not remove existing database file: {e}")

    # Import all models ONCE to register with Base.metadata
    # The order matters: core.models first, then app.models package
    import core.models  # noqa: F401
    import app.models  # noqa: F401 - imports all models via __init__.py

    db_module.init_db()

    # Verification: ensure all expected tables exist
    # RU: Проверка, что init_db() создала все таблицы (без повторного create_all).
    # EN: Verify that init_db() created all tables (without redundant create_all).
    from core.db import Base
    from sqlalchemy import inspect as sa_inspect

    engine = getattr(db_module, "_RAW_ENGINE", None) or getattr(db_module, "engine", None)
    if engine is not None:
        inspector = sa_inspect(engine)
        expected = set(Base.metadata.tables.keys())
        actual = set(inspector.get_table_names())
        missing = expected - actual
        if missing:
            pytest.fail(
                "SQLite test DB missing required tables: "
                f"{sorted(missing)}. "
                "This indicates a test DB setup / model import problem."
            )

    # Ensure SQLite file is writable for tests
    try:
        resolved_path.chmod(0o666)
    except Exception as e:
        logger.debug(f"Could not set permissions on test database: {e}")

    # Expose the DB module to dependent fixtures (e.g., _cleanup_users)
    # so they can use a consistent session_scope and engine configuration.
    yield db_module

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

        # NOTE: Do not clear SessionLocal binding - it breaks API tests that expect
        # SessionLocal to be available in teardown. Engine disposal is sufficient cleanup.

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
    """Set up test environment variables before any tests run.

    This fixture runs automatically for the entire session to ensure
    API_KEY and APP_ENV are configured before the app module is loaded.
    """
    # Set API key and environment for the entire test session
    os.environ["API_KEY"] = "test_key"
    os.environ["APP_ENV"] = "test"
    os.environ["DEBUG"] = "true"
    yield
    # Clean up after all tests: dispose all database connections
    try:
        import core.db

        if hasattr(core.db, "_RAW_ENGINE") and core.db._RAW_ENGINE:
            core.db._RAW_ENGINE.dispose()
        if hasattr(core.db, "engine") and core.db.engine:
            core.db.engine.dispose()
    except Exception:
        pass  # Best-effort cleanup
    # Clean up environment variables
    for key in ["API_KEY", "APP_ENV", "DEBUG"]:
        if key in os.environ:
            del os.environ[key]


_CACHED_APP_MODULE: ModuleType | None = None


@pytest.fixture(scope="session")
def app_module() -> ModuleType:
    """Import app package and return stable module instance."""
    global _CACHED_APP_MODULE

    # Reuse cached module if we already loaded it
    if _CACHED_APP_MODULE is not None:
        if "app" not in sys.modules:
            sys.modules["app"] = _CACHED_APP_MODULE
        return _CACHED_APP_MODULE

    # Import app directly (standard import, no sys.path manipulation)
    import app as app_mod

    _CACHED_APP_MODULE = app_mod
    return app_mod


@pytest.fixture(autouse=True)
def _ensure_app_module(app_module: ModuleType) -> None:
    """Ensure sys.modules always contains the cached app module."""
    sys.modules["app"] = app_module


@pytest.fixture
def app(app_module: ModuleType) -> FastAPI:
    """Return the FastAPI app instance with observability bootstrap and API key mock.

    Uses app.main:app (canonical entrypoint with metrics bootstrap),
    not legacy_app.app directly.
    """
    # Import the canonical entrypoint with observability bootstrap
    import app.main

    app_instance = app.main.app

    # Apply lenient API key mode
    def mock_get_api_key(api_key: str = "") -> str:
        if not api_key or len(api_key.strip()) < 3:
            from fastapi import HTTPException

            raise HTTPException(status_code=403, detail="Invalid API Key")
        return api_key

    if hasattr(app_instance, "dependency_overrides") and hasattr(app_module, "get_api_key"):
        app_instance.dependency_overrides[app_module.get_api_key] = mock_get_api_key

    return cast(FastAPI, app_instance)


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """Return a TestClient for the FastAPI app (always closed).

    Using TestClient as a context manager ensures lifespan startup/shutdown runs
    deterministically and prevents leaking background threads across tests.
    """
    with TestClient(app) as test_client:
        yield test_client


# --- VIP shoplist test fixtures ---


def _iter_route_dependencies(route: APIRoute) -> Iterable[Callable]:
    """
    RU: Извлекаем callables зависимостей, навешанных на маршрут (route.dependencies).
    EN: Extract dependency callables attached at route level.
    """
    for dep in getattr(route, "dependencies", []) or []:
        fn = getattr(dep, "dependency", None)
        if callable(fn):
            yield fn


def _find_route_by_endpoint_name(app: FastAPI, endpoint_name: str) -> APIRoute | None:
    """
    RU: Находим маршрут по имени endpoint-функции.
    EN: Find route by endpoint function name.
    """
    for route in app.routes:
        if isinstance(route, APIRoute):
            endpoint = getattr(route, "endpoint", None)
            if callable(endpoint) and getattr(endpoint, "__name__", "") == endpoint_name:
                return route
    return None


@pytest.fixture
def client_with_vip_access(app_module: ModuleType) -> Generator[TestClient, None, None]:
    """
    Create test client with VIP tier access bypassed AND API key bypassed,
    including route-level dependencies.

    RU: Создаёт тестовый клиент с обходом проверки VIP tier и API-key
    (включая route-level зависимости).

    Uses canonical entrypoint (app.main:app) with observability bootstrap.
    """
    import app.main
    import app.routers.vip_shoplist as vip_router

    app_instance = app.main.app

    # ⚠️ NO *args/**kwargs — иначе FastAPI требует query args/kwargs
    async def mock_require_vip_tier() -> str:
        return "test_vip_key"

    async def mock_api_key() -> str:
        return "test_api_key"

    # Override VIP tier dependency (bypass auth check)
    app_instance.dependency_overrides[vip_router.require_vip_tier] = mock_require_vip_tier
    # NOTE: We do NOT override require_vip_module_enabled - it should check the feature flag
    # Tests can use monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", ...)

    route_level_deps: list[Callable] = []
    try:
        route = _find_route_by_endpoint_name(app_instance, "vip_shoplist_generate")
        assert route is not None, "Route for endpoint 'vip_shoplist_generate' not found"

        # Route has API-key dependency applied at route level (via app.include_router);
        # override it here to avoid requiring headers/env in tests.
        route_level_deps = list(_iter_route_dependencies(route))
        for dep_fn in route_level_deps:
            app_instance.dependency_overrides[dep_fn] = mock_api_key

        with TestClient(app_instance) as client:
            yield client
    finally:
        app_instance.dependency_overrides.pop(vip_router.require_vip_tier, None)
        for dep_fn in route_level_deps:
            app_instance.dependency_overrides.pop(dep_fn, None)


@pytest.fixture
def api_key() -> str:
    """Return the test API key value.

    The actual environment setup is done by setup_test_environment fixture.
    This fixture just provides the key value for tests to use in headers.
    """
    return "test_key"


@pytest.fixture
def pro_headers() -> dict[str, str]:
    """Return headers with valid PRO API key for testing PRO endpoints.

    RU: Возвращает заголовки с валидным PRO API ключом для тестирования PRO endpoints.
    EN: Returns headers with valid PRO API key for testing PRO endpoints.

    Use this fixture in all tests that call PRO endpoints and expect 200/422/404
    (not 403 auth errors). PRO guard requires tier-based validation.
    """
    from app.middleware.api_tiers import TEST_KEY_PRO

    return {"X-API-Key": TEST_KEY_PRO}


@pytest.fixture
def vip_headers() -> dict[str, str]:
    """Return headers with valid VIP API key for testing VIP endpoints.

    RU: Возвращает заголовки с валидным VIP API ключом для тестирования VIP endpoints.
    EN: Returns headers with valid VIP API key for testing VIP endpoints.

    Use this fixture in all tests that call VIP endpoints and expect 200/422/404
    (not 403 auth errors). VIP guard requires tier-based validation.
    """
    from app.middleware.api_tiers import TEST_KEY_VIP

    return {"X-API-Key": TEST_KEY_VIP}


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
    configured_db = configure_sqlite_database

    def _truncate() -> None:
        with configured_db.session_scope() as session:
            session.execute(text("DELETE FROM users"))

    try:
        _truncate()
    except (OperationalError, ProgrammingError, UnboundExecutionError) as e:
        # Fail-fast policy (P0 nightly): if schema is missing, try init_db() once and fail
        # loudly if tables are still missing. This prevents silent "warn+continue" masking.
        logger.warning(f"Database not accessible or users table missing during test setup: {e}")
        try:
            configured_db.init_db()
            try:
                _truncate()
            except Exception as retry_err:  # pragma: no cover - defensive
                pytest.fail(
                    "Test DB schema bootstrap failed: 'users' table still missing after init_db(). "
                    f"Original error: {e}. Retry error: {retry_err}"
                )
        except Exception as init_err:
            pytest.fail(
                "Test DB schema bootstrap failed: init_db() raised during users cleanup setup. "
                f"Original error: {e}. init_db error: {init_err}"
            )
    except Exception as e:
        # Handle any other unexpected exceptions
        logger.error(f"Unexpected error during test setup cleanup: {e}", exc_info=True)

    yield

    # Cleanup after test - log errors to reduce flakiness when SQLite is locked
    try:
        _truncate()
    except (OperationalError, ProgrammingError, UnboundExecutionError) as e:
        # Avoid hard failures on teardown to reduce flakiness in CI when SQLite is locked
        # or when the table doesn't exist
        logger.warning(
            f"Test cleanup skipped - database not accessible or users table missing: {e}"
        )
    except Exception as e:
        # Handle any other unexpected exceptions during teardown
        logger.warning(f"Unexpected error during test teardown cleanup: {e}")


def _enable_vip(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Enable VIP module for tests.

    RU: Включает VIP модуль для тестов.
    EN: Enables VIP module for tests.

    This helper must be side-effect free: it only flips feature flags via
    monkeypatch and must not mutate the FastAPI app/router state.
    """
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)


def _disable_vip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable VIP module flag via router module patch."""
    monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: False)


# ============================================================================
# Catalog fixtures (PR-7)
# ============================================================================


@pytest.fixture()
def fixtures_dir() -> Path:
    """
    RU: Корень tests/fixtures.
    EN: Root directory for test fixtures.
    """
    return Path(__file__).parent / "fixtures"


def build_demo_catalog_sqlite(path: Path, *, fixtures_dir: Path) -> None:
    """
    RU: Собирает SQLite каталог из tiny CSV fixtures без сети.
    EN: Builds SQLite catalog from tiny CSV fixtures (offline).

    Args:
        path: Path to output SQLite database file
        fixtures_dir: Root directory for test fixtures

    Raises:
        RuntimeError: If no catalog CSV fixtures found
    """
    from core.catalog.loaders.carrefour_es import CarrefourESLoader
    from core.catalog.loaders.walmart_us import WalmartUSLoader
    from core.catalog.storage.sqlite_writer import write_snapshot

    carrefour_csv = fixtures_dir / "catalog_raw" / "carrefour_es_sample.csv"
    walmart_csv = fixtures_dir / "catalog_raw" / "walmart_us_sample.csv"

    snapshots = []
    if carrefour_csv.exists():
        snapshots.append(CarrefourESLoader(carrefour_csv).load())
    if walmart_csv.exists():
        snapshots.append(WalmartUSLoader(walmart_csv).load())

    if not snapshots:
        raise RuntimeError("No catalog CSV fixtures found under tests/fixtures/catalog_raw/")

    merged = _merge_snapshots(*snapshots)
    write_snapshot(path, merged)


def _merge_snapshots(*snapshots) -> Any:
    """
    RU: Склеиваем snapshots в один для удобства тестов.
    EN: Merge snapshots (regions/stores/skus/aliases) into one.

    Args:
        *snapshots: Variable number of CatalogSnapshot instances

    Returns:
        Merged CatalogSnapshot with deduplicated regions/stores/skus/aliases
    """
    from core.catalog.provider import CatalogSnapshot

    regions = []
    stores = []
    skus = []
    aliases = []
    seen_region = set()
    seen_store = set()
    seen_sku = set()
    seen_alias = set()

    for snap in snapshots:
        for r in snap.regions:
            if r.region_id not in seen_region:
                regions.append(r)
                seen_region.add(r.region_id)

        for s in snap.stores:
            if s.store_id not in seen_store:
                stores.append(s)
                seen_store.add(s.store_id)

        for sku in snap.skus:
            if sku.sku_id not in seen_sku:
                skus.append(sku)
                seen_sku.add(sku.sku_id)

        for alias, sku_id in snap.aliases:
            # alias uniqueness in sqlite is (region_id, alias), but here we keep raw list.
            key = (alias, sku_id)
            if key not in seen_alias:
                aliases.append((alias, sku_id))
                seen_alias.add(key)

    return CatalogSnapshot(regions=regions, stores=stores, skus=skus, aliases=aliases)
