# -*- coding: utf-8 -*-
"""
Pytest configuration for PulsePlate

RU: Глобальная конфигурация тестов
EN: Global test configuration
"""

import os
import socket
import tempfile
from contextlib import suppress
from importlib import reload
from pathlib import Path

import pytest


# Ensure asyncio tests are supported even if plugin auto-discovery fails
pytest_plugins = ["pytest_asyncio"]


# Set VIP_MODULE_ENABLED globally for all tests
os.environ["VIP_MODULE_ENABLED"] = "true"
# Ensure default test-like environment variables for CI consistency
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ALLOW_DEV_API_KEY", "true")
# Default to strict: anonymous disabled unless tests explicitly enable
os.environ.setdefault("ALLOW_ANONYMOUS_API_KEYS", "false")
os.environ.setdefault("API_KEY", "test_key")
os.environ.setdefault("FEATURE_PREMIUM_NUTRITION", "true")

# Ensure PYTHONPATH contains required segments for tests that assert on it
_pp = os.environ.get("PYTHONPATH", "")
_needle = ".:core:app:tests"
if _needle not in _pp:
    os.environ["PYTHONPATH"] = f"{_needle}:{_pp}" if _pp else _needle

# Configure database location for tests (isolated SQLite file).
_TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="pulseplate-test-db-"))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TEST_DB_DIR / 'tests.db'}")

with suppress(Exception):
    from core import db as db_module

    reload(db_module)
    db_module.init_db()

# Configure Hypothesis defaults to avoid flaky deadline-based failures on CI or
# slower local machines.
with suppress(Exception):  # pragma: no cover - test helper config
    from hypothesis import HealthCheck, settings

    settings.register_profile(
        "ci",
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    settings.load_profile("ci")


# --- Autouse fixtures to harden tests ---


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable outbound network during tests.

    Prevents accidental HTTP calls causing flakiness or slowness.
    """

    class GuardedSocket(socket.socket):  # type: ignore[misc]
        def connect(self, *args, **kwargs):  # noqa: D401
            raise RuntimeError("Network access is disabled during tests")

    monkeypatch.setattr(socket, "socket", GuardedSocket, raising=True)


@pytest.fixture(autouse=True)
def _patch_update_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch background update scheduler (if present) to no-op in tests."""
    with suppress(Exception):
        from core.food_apis import scheduler as sched  # type: ignore

        def _noop(*_a, **_kw):
            return None

        for name in ("start", "stop", "_update_loop"):
            if hasattr(sched, name):
                monkeypatch.setattr(sched, name, _noop, raising=False)


# --- Helper fixtures ---


@pytest.fixture(autouse=True)
def _reset_anonymous_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure ALLOW_ANONYMOUS_API_KEYS doesn't leak between tests.

    RU: Сбрасывает флаг анонимного доступа перед каждым тестом.
    EN: Clears env so each test opts-in explicitly if needed.
    """
    monkeypatch.delenv("ALLOW_ANONYMOUS_API_KEYS", raising=False)


@pytest.fixture()
def api_headers() -> dict[str, str]:
    """Default API headers for authenticated requests in tests.

    RU: Стандартные заголовки с ключом API для тестов.
    EN: Provides X-API-Key header using env or fallback test_key.
    """
    return {"X-API-Key": os.getenv("API_KEY", "test_key")}
