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
