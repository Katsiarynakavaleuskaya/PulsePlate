"""Ownership and security contracts for canonical admin scheduler access."""

from __future__ import annotations

import ast
import asyncio
import importlib
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import threading
from typing import Any, cast
from unittest.mock import AsyncMock

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from app.services import admin_operations
from app.services import scheduler_access
from core.food_apis import scheduler_runtime

REPO_ROOT = Path(__file__).resolve().parents[1]


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object:
        return self.value


class _LeaseConnection:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.events: list[str] = []
        self.parameters: list[dict[str, int]] = []
        self.invalidations = 0
        self.invalidate_error: Exception | None = None

    def execute(self, statement: object, parameters: dict[str, int]) -> _ScalarResult:
        sql = str(statement)
        if "pg_try_advisory_lock" in sql:
            self.events.append("acquire")
        elif "pg_advisory_unlock" in sql:
            self.events.append("release")
        else:
            raise AssertionError(f"unexpected lease SQL: {sql}")
        self.parameters.append(parameters.copy())
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return _ScalarResult(response)

    def invalidate(self) -> None:
        self.invalidations += 1
        if self.invalidate_error is not None:
            raise self.invalidate_error


class _LeaseSession:
    def __init__(self, connection: _LeaseConnection) -> None:
        self.lease_connection = connection
        self.closed = False
        self.close_error: Exception | None = None

    def connection(self) -> _LeaseConnection:
        return self.lease_connection

    def close(self) -> None:
        self.closed = True
        if self.close_error is not None:
            raise self.close_error


def _configure_external_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://db.example/pulseplate")
    monkeypatch.setenv("FOOD_UPDATE_SCHEDULER_MODE", "external")


def _run_python(source: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "test",
            "API_KEY": "test-key",  # pragma: allowlist secret
            "SERVER_SALT": "test-salt",  # pragma: allowlist secret
            "TESTING": "true",
        }
    )
    return subprocess.run(
        [sys.executable, "-c", source],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_scheduler_access_delegates_to_core_at_call_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core_scheduler = importlib.import_module("core.food_apis.scheduler")
    sentinel = object()

    async def fake_core_getter() -> Any:
        return sentinel

    monkeypatch.setattr(core_scheduler, "get_update_scheduler", fake_core_getter)

    assert asyncio.run(scheduler_access.get_update_scheduler()) is sentinel


@pytest.mark.parametrize("first_module", ["app", "legacy_app"])
def test_scheduler_access_identity_is_import_order_independent(first_module: str) -> None:
    source = textwrap.dedent(f"""
        import importlib

        importlib.import_module({first_module!r})
        import app
        import legacy_app
        from app.services import scheduler_access

        assert app.get_update_scheduler is legacy_app.get_update_scheduler
        assert app.get_update_scheduler is scheduler_access.get_update_scheduler
        """)

    result = _run_python(source)

    assert result.returncode == 0, result.stderr


def test_optional_scheduler_is_not_an_import_time_dependency() -> None:
    source = textwrap.dedent("""
        import asyncio
        import importlib.abc
        import sys

        class SchedulerBlocker(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == "core.food_apis.scheduler":
                    raise ImportError("scheduler intentionally unavailable")
                return None

        sys.meta_path.insert(0, SchedulerBlocker())

        import app
        getter = app.get_update_scheduler
        assert "core.food_apis.scheduler" not in sys.modules

        import legacy_app
        from app.services import scheduler_access

        assert getter is legacy_app.get_update_scheduler
        assert getter is scheduler_access.get_update_scheduler
        assert "core.food_apis.scheduler" not in sys.modules

        try:
            asyncio.run(getter())
        except ImportError as exc:
            assert str(exc) == "scheduler intentionally unavailable"
        else:
            raise AssertionError("scheduler access unexpectedly failed open")
        """)

    result = _run_python(source)

    assert result.returncode == 0, result.stderr


def test_scheduler_access_sources_keep_ownership_narrow() -> None:
    access_tree = ast.parse(
        (REPO_ROOT / "app/services/scheduler_access.py").read_text(encoding="utf-8")
    )
    runtime_core_imports: list[ast.Import | ast.ImportFrom] = []

    class _ModuleRuntimeImportVisitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            return None

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            return None

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            return None

        def visit_If(self, node: ast.If) -> None:
            if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
                for statement in node.orelse:
                    self.visit(statement)
                return
            self.generic_visit(node)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            if node.module == "core.food_apis.scheduler":
                runtime_core_imports.append(node)

        def visit_Import(self, node: ast.Import) -> None:
            if any(alias.name == "core.food_apis.scheduler" for alias in node.names):
                runtime_core_imports.append(node)

    _ModuleRuntimeImportVisitor().visit(access_tree)
    assert runtime_core_imports == []

    admin_source = (REPO_ROOT / "app/services/admin_operations.py").read_text(encoding="utf-8")
    assert "sys.modules" not in admin_source
    for forbidden_name in (
        "_get_scheduler",
        "_resolve_scheduler_getter",
        "_select_scheduler_getter_from_modules",
    ):
        assert forbidden_name not in admin_source


def test_legacy_scheduler_access_has_no_mutable_override_state() -> None:
    legacy_app = importlib.import_module("legacy_app")

    assert legacy_app.get_update_scheduler is scheduler_access.get_update_scheduler
    for forbidden_name in (
        "_scheduler_getter",
        "_test_scheduler_override",
        "_DEFAULT_GET_UPDATE_SCHEDULER",
    ):
        assert not hasattr(legacy_app, forbidden_name)


@pytest.mark.parametrize(
    ("method", "path", "params"),
    [
        ("GET", "/api/v1/admin/status", None),
        ("GET", "/api/v1/admin/db-status", None),
        ("POST", "/api/v1/admin/force-update", None),
        ("GET", "/api/v1/admin/check-updates", None),
        (
            "POST",
            "/api/v1/admin/rollback",
            {"source": "usda", "target_version": "1.0.0"},
        ),
    ],
)
@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "invalid"}])
def test_admin_auth_rejects_before_scheduler_access(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    params: dict[str, str] | None,
    headers: dict[str, str],
) -> None:
    monkeypatch.setenv("API_KEY", "expected-key")
    getter = AsyncMock()
    monkeypatch.setattr(admin_operations, "get_update_scheduler", getter)

    response = client.request(method, path, params=params, headers=headers)

    assert response.status_code == 403
    assert getter.await_count == 0


@pytest.mark.parametrize(
    ("operation", "expected_detail"),
    [
        (admin_operations.get_database_status, "Failed to get database status"),
        (admin_operations.force_database_update, "Force update failed"),
        (admin_operations.check_for_updates, "Update check failed"),
    ],
)
@pytest.mark.parametrize(
    "failure",
    [
        RuntimeError("secret-scheduler-token"),
        HTTPException(status_code=418, detail="secret-scheduler-token"),
    ],
)
def test_admin_operational_failures_use_sanitized_envelopes(
    monkeypatch: pytest.MonkeyPatch,
    operation: Any,
    expected_detail: str,
    failure: Exception,
) -> None:
    async def failing_getter() -> Any:
        raise failure

    monkeypatch.setattr(admin_operations, "get_update_scheduler", failing_getter)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(operation())

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == expected_detail
    assert "secret-scheduler-token" not in str(exc_info.value.detail)


def test_scheduler_mode_defaults_are_environment_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FOOD_UPDATE_SCHEDULER_MODE", raising=False)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    assert (
        scheduler_runtime.resolve_scheduler_mode() is scheduler_runtime.SchedulerMode.IN_PROCESS_DEV
    )

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://db.example/pulseplate")
    assert scheduler_runtime.resolve_scheduler_mode() is scheduler_runtime.SchedulerMode.EXTERNAL


@pytest.mark.parametrize(
    "raw_mode",
    ["", " external", "external ", "EXTERNAL", "cron", "in-process"],
)
def test_scheduler_mode_rejects_non_exact_values(
    monkeypatch: pytest.MonkeyPatch,
    raw_mode: str,
) -> None:
    _configure_external_scheduler(monkeypatch)
    monkeypatch.setenv("FOOD_UPDATE_SCHEDULER_MODE", raw_mode)

    with pytest.raises(
        scheduler_runtime.SchedulerConfigurationError,
        match="must be one of",
    ):
        scheduler_runtime.resolve_scheduler_mode()


def test_scheduler_mode_rejects_unsafe_runtime_database_pairs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_external_scheduler(monkeypatch)
    monkeypatch.setenv("FOOD_UPDATE_SCHEDULER_MODE", "in_process_dev")
    with pytest.raises(
        scheduler_runtime.SchedulerConfigurationError,
        match="non-production",
    ):
        scheduler_runtime.resolve_scheduler_mode()

    monkeypatch.setenv("FOOD_UPDATE_SCHEDULER_MODE", "external")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///production.db")
    with pytest.raises(
        scheduler_runtime.SchedulerConfigurationError,
        match="requires PostgreSQL",
    ):
        scheduler_runtime.resolve_scheduler_mode()

    monkeypatch.setenv("FOOD_UPDATE_SCHEDULER_MODE", "disabled")
    with pytest.raises(
        scheduler_runtime.SchedulerConfigurationError,
        match="requires PostgreSQL",
    ):
        scheduler_runtime.resolve_scheduler_mode()

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("ENVIRONMENT", "local")
    assert scheduler_runtime.resolve_scheduler_mode() is scheduler_runtime.SchedulerMode.DISABLED

    monkeypatch.setenv("DATABASE_URL", "not a sqlalchemy url")
    with pytest.raises(
        scheduler_runtime.SchedulerConfigurationError,
        match="invalid scheduler database",
    ):
        scheduler_runtime.resolve_scheduler_mode()


@pytest.mark.parametrize(
    ("mode", "owner"),
    [
        (scheduler_runtime.SchedulerMode.EXTERNAL, "worker"),
        (scheduler_runtime.SchedulerMode.IN_PROCESS_DEV, "api_process"),
        (scheduler_runtime.SchedulerMode.DISABLED, "none"),
    ],
)
def test_configured_periodic_owner_is_configuration_only(
    mode: scheduler_runtime.SchedulerMode,
    owner: str,
) -> None:
    assert scheduler_runtime.configured_periodic_owner(mode) == owner


def test_postgres_lease_uses_one_public_session_for_acquire_body_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core import db as core_db

    _configure_external_scheduler(monkeypatch)
    connection = _LeaseConnection([True, True])
    session = _LeaseSession(connection)
    monkeypatch.setattr(
        core_db,
        "get_session_factory",
        lambda: cast(Any, lambda: session),
    )

    async def operation() -> str:
        connection.events.append("body")
        return "updated"

    result = asyncio.run(scheduler_runtime.run_with_update_lease(operation))

    assert result == "updated"
    assert connection.events == ["acquire", "body", "release"]
    assert connection.parameters == [
        {"lease_key": scheduler_runtime.FOOD_UPDATE_ADVISORY_LOCK_KEY},
        {"lease_key": scheduler_runtime.FOOD_UPDATE_ADVISORY_LOCK_KEY},
    ]
    assert connection.invalidations == 0
    assert session.closed is True


def test_postgres_lease_io_uses_one_worker_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_external_scheduler(monkeypatch)
    io_thread_ids: list[int] = []
    body_thread_ids: list[int] = []
    event_loop_thread_id = threading.get_ident()

    class _TrackingConnection(_LeaseConnection):
        def execute(self, statement: object, parameters: dict[str, int]) -> _ScalarResult:
            io_thread_ids.append(threading.get_ident())
            return super().execute(statement, parameters)

    class _TrackingSession(_LeaseSession):
        def connection(self) -> _LeaseConnection:
            io_thread_ids.append(threading.get_ident())
            return super().connection()

        def close(self) -> None:
            io_thread_ids.append(threading.get_ident())
            super().close()

    connection = _TrackingConnection([True, True])
    session = _TrackingSession(connection)

    def session_factory() -> _TrackingSession:
        io_thread_ids.append(threading.get_ident())
        return session

    async def operation() -> str:
        body_thread_ids.append(threading.get_ident())
        return "updated"

    assert (
        asyncio.run(
            scheduler_runtime.run_with_update_lease(
                operation,
                session_factory=cast(Any, session_factory),
            )
        )
        == "updated"
    )

    assert body_thread_ids == [event_loop_thread_id]
    assert len(set(io_thread_ids)) == 1
    assert event_loop_thread_id not in io_thread_ids
    assert connection.events == ["acquire", "release"]
    assert session.closed is True


def test_postgres_lease_cancellation_during_acquire_invalidates_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_external_scheduler(monkeypatch)
    acquire_started = threading.Event()
    allow_acquire_to_finish = threading.Event()
    operation_called = False

    class _BlockingAcquireConnection(_LeaseConnection):
        def execute(self, statement: object, parameters: dict[str, int]) -> _ScalarResult:
            if "pg_try_advisory_lock" in str(statement):
                acquire_started.set()
                if not allow_acquire_to_finish.wait(timeout=5):
                    raise AssertionError("timed out waiting to finish lease acquisition")
            return super().execute(statement, parameters)

    connection = _BlockingAcquireConnection([True])
    session = _LeaseSession(connection)

    async def operation() -> None:
        nonlocal operation_called
        operation_called = True

    async def scenario() -> None:
        lease_task = asyncio.create_task(
            scheduler_runtime.run_with_update_lease(
                operation,
                session_factory=cast(Any, lambda: session),
            )
        )
        while not acquire_started.is_set():
            await asyncio.sleep(0)
        lease_task.cancel()
        allow_acquire_to_finish.set()
        with pytest.raises(asyncio.CancelledError):
            await lease_task

    asyncio.run(scenario())

    assert operation_called is False
    assert connection.events == ["acquire"]
    assert connection.invalidations == 1
    assert session.closed is True


def test_postgres_lease_contention_never_runs_or_unlocks_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_external_scheduler(monkeypatch)
    connection = _LeaseConnection([False])
    session = _LeaseSession(connection)
    called = False

    async def operation() -> None:
        nonlocal called
        called = True

    with pytest.raises(
        scheduler_runtime.UpdateLeaseContended,
        match="update_already_in_progress",
    ):
        asyncio.run(
            scheduler_runtime.run_with_update_lease(
                operation,
                session_factory=cast(Any, lambda: session),
            )
        )

    assert called is False
    assert connection.events == ["acquire"]
    assert connection.invalidations == 0
    assert session.closed is True


@pytest.mark.parametrize(
    "acquire_result",
    [None, RuntimeError("acquire failed")],
)
def test_postgres_lease_uncertain_acquire_invalidates_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    acquire_result: object,
) -> None:
    _configure_external_scheduler(monkeypatch)
    connection = _LeaseConnection([acquire_result])
    session = _LeaseSession(connection)

    async def operation() -> None:
        raise AssertionError("operation must not run")

    with pytest.raises(scheduler_runtime.UpdateLeaseAcquireError):
        asyncio.run(
            scheduler_runtime.run_with_update_lease(
                operation,
                session_factory=cast(Any, lambda: session),
            )
        )

    assert connection.invalidations == 1
    assert session.closed is True


def test_postgres_lease_factory_failure_is_an_acquire_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_external_scheduler(monkeypatch)

    def broken_factory() -> Any:
        raise RuntimeError("factory unavailable")

    async def operation() -> None:
        raise AssertionError("operation must not run")

    with pytest.raises(scheduler_runtime.UpdateLeaseAcquireError):
        asyncio.run(
            scheduler_runtime.run_with_update_lease(
                operation,
                session_factory=cast(Any, broken_factory),
            )
        )


@pytest.mark.parametrize(
    "release_result",
    [None, RuntimeError("release failed")],
)
def test_postgres_lease_uncertain_release_invalidates_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    release_result: object,
) -> None:
    _configure_external_scheduler(monkeypatch)
    connection = _LeaseConnection([True, release_result])
    session = _LeaseSession(connection)

    async def operation() -> str:
        return "updated"

    with pytest.raises(scheduler_runtime.UpdateLeaseReleaseError):
        asyncio.run(
            scheduler_runtime.run_with_update_lease(
                operation,
                session_factory=cast(Any, lambda: session),
            )
        )

    assert connection.events == ["acquire", "release"]
    assert connection.invalidations == 1
    assert session.closed is True


def test_postgres_lease_preserves_primary_error_when_unlock_is_uncertain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_external_scheduler(monkeypatch)
    connection = _LeaseConnection([True, RuntimeError("release failed")])
    session = _LeaseSession(connection)

    async def operation() -> None:
        raise ValueError("primary update failure")

    with pytest.raises(ValueError, match="primary update failure"):
        asyncio.run(
            scheduler_runtime.run_with_update_lease(
                operation,
                session_factory=cast(Any, lambda: session),
            )
        )

    assert connection.invalidations == 1
    assert session.closed is True


def test_postgres_lease_best_effort_cleanup_does_not_mask_acquire_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _configure_external_scheduler(monkeypatch)
    connection = _LeaseConnection([None])
    connection.invalidate_error = RuntimeError("invalidate failed")
    session = _LeaseSession(connection)
    session.close_error = RuntimeError("close failed")

    async def operation() -> None:
        raise AssertionError("operation must not run")

    with caplog.at_level("ERROR", logger="core.food_apis.scheduler_runtime"):
        with pytest.raises(scheduler_runtime.UpdateLeaseAcquireError):
            asyncio.run(
                scheduler_runtime.run_with_update_lease(
                    operation,
                    session_factory=cast(Any, lambda: session),
                )
            )

    assert "Could not invalidate uncertain update-lease connection" in caplog.text
    assert "Could not close update-lease session" in caplog.text


def test_local_lease_is_non_blocking_and_reusable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("FOOD_UPDATE_SCHEDULER_MODE", "in_process_dev")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    events: list[str] = []

    async def inner() -> None:
        events.append("inner")

    async def outer() -> str:
        events.append("outer")
        with pytest.raises(scheduler_runtime.UpdateLeaseContended):
            await scheduler_runtime.run_with_update_lease(inner)
        return "outer-complete"

    assert asyncio.run(scheduler_runtime.run_with_update_lease(outer)) == "outer-complete"
    assert asyncio.run(scheduler_runtime.run_with_update_lease(inner)) is None
    assert events == ["outer", "inner"]


def test_process_local_lease_requires_explicit_dev_or_test(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "preview")
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("FOOD_UPDATE_SCHEDULER_MODE", "disabled")

    async def operation() -> None:
        raise AssertionError("operation must not run")

    with pytest.raises(
        scheduler_runtime.SchedulerConfigurationError,
        match="process-local update lease",
    ):
        asyncio.run(scheduler_runtime.run_with_update_lease(operation))


def test_invalidate_connection_ignores_missing_connection() -> None:
    assert scheduler_runtime._invalidate_connection(None) is None


def test_admin_force_update_maps_only_definite_contention_to_409(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ContendedScheduler:
        async def force_update(self, source: str | None = None) -> dict[str, object]:
            del source
            raise scheduler_runtime.UpdateLeaseContended()

    async def getter() -> _ContendedScheduler:
        return _ContendedScheduler()

    monkeypatch.setattr(admin_operations, "get_update_scheduler", getter)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(admin_operations.force_database_update())

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "update_already_in_progress"


def test_admin_rollback_runs_inside_lease_and_maps_contention_to_409(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class _Manager:
        versions: dict[str, object] = {}

        def _load_versions(self) -> dict[str, object]:
            events.append("refresh")
            return {}

        async def rollback_database(self, source: str, target_version: str) -> bool:
            events.append(f"rollback:{source}:{target_version}")
            return True

    class _Scheduler:
        update_manager = _Manager()

    async def getter() -> _Scheduler:
        return _Scheduler()

    async def run_lease(operation: Any) -> Any:
        events.append("lease")
        return await operation()

    monkeypatch.setattr(admin_operations, "get_update_scheduler", getter)
    monkeypatch.setattr(admin_operations, "run_with_update_lease", run_lease)

    result = asyncio.run(admin_operations.rollback_database("usda", "v1"))

    assert result["success"] is True
    assert events == ["lease", "refresh", "rollback:usda:v1"]

    async def contend(_operation: Any) -> Any:
        raise scheduler_runtime.UpdateLeaseContended()

    events.clear()
    monkeypatch.setattr(admin_operations, "run_with_update_lease", contend)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(admin_operations.rollback_database("usda", "v1"))

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "update_already_in_progress"
    assert events == []


def test_lease_refresh_preserves_sequential_manager_version_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from core.food_apis import scheduler as scheduler_module
    from core.food_apis.update_manager import (
        DatabaseUpdateManager,
        DatabaseVersion,
        UpdateResult,
    )

    first_manager = DatabaseUpdateManager(cache_dir=tmp_path)
    second_manager = DatabaseUpdateManager(cache_dir=tmp_path)
    first_scheduler = object.__new__(
        scheduler_module.DatabaseUpdateScheduler,
    )
    second_scheduler = object.__new__(
        scheduler_module.DatabaseUpdateScheduler,
    )
    first_scheduler.update_manager = first_manager
    second_scheduler.update_manager = second_manager

    def version_for(source: str, version: str) -> DatabaseVersion:
        return DatabaseVersion(
            source=source,
            version=version,
            last_updated="2026-08-01T00:00:00+00:00",
            record_count=1,
            checksum=version,
            metadata={},
        )

    def install_writer(manager: DatabaseUpdateManager, version: str) -> None:
        async def write(source: str, force: bool = False) -> UpdateResult:
            assert force is True
            manager.versions[source] = version_for(source, version)
            manager._save_versions()
            return UpdateResult(
                success=True,
                source=source,
                old_version=None,
                new_version=version,
                records_added=1,
                records_updated=0,
                records_removed=0,
                errors=[],
                duration_seconds=0.0,
            )

        monkeypatch.setattr(manager, "update_database", write)

    async def run_lease(operation: Any) -> Any:
        return await operation()

    install_writer(first_manager, "v1")
    install_writer(second_manager, "v2")
    monkeypatch.setattr(scheduler_module, "run_with_update_lease", run_lease)

    async def scenario() -> None:
        observed: DatabaseUpdateManager | None = None
        try:
            await first_scheduler.force_update("usda")
            await second_scheduler.force_update("openfoodfacts")
            observed = DatabaseUpdateManager(cache_dir=tmp_path)
            assert sorted(observed.versions) == ["openfoodfacts", "usda"]
            assert observed.versions["usda"].version == "v1"
            assert observed.versions["openfoodfacts"].version == "v2"
        finally:
            if observed is not None:
                await observed.close()
            await first_manager.close()
            await second_manager.close()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("outcome", "expected_delay"),
    [
        (True, 60.0),
        (False, 30.0 * 60.0),
        (RuntimeError("update check failed"), 30.0 * 60.0),
    ],
)
def test_scheduler_loop_backs_off_after_incomplete_attempt(
    monkeypatch: pytest.MonkeyPatch,
    outcome: bool | Exception,
    expected_delay: float,
) -> None:
    from core.food_apis import scheduler as scheduler_module

    scheduler = scheduler_module.DatabaseUpdateScheduler(
        retry_interval_minutes=30,
        install_signal_handlers=False,
    )
    scheduler.is_running = True
    if isinstance(outcome, Exception):
        scheduler._run_update_check = AsyncMock(side_effect=outcome)
    else:
        scheduler._run_update_check = AsyncMock(return_value=outcome)
    delays: list[float] = []

    async def record_sleep(delay: float) -> None:
        delays.append(delay)
        scheduler.is_running = False

    try:
        with monkeypatch.context() as context:
            context.setattr(scheduler_module.asyncio, "sleep", record_sleep)
            asyncio.run(scheduler._update_loop())
    finally:
        asyncio.run(scheduler.update_manager.close())

    assert delays == [expected_delay]
    scheduler._run_update_check.assert_awaited_once()


def test_scheduler_due_cycle_updates_watermark_only_after_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.food_apis import scheduler as scheduler_module

    scheduler = scheduler_module.DatabaseUpdateScheduler(install_signal_handlers=False)
    scheduler.update_manager.check_for_updates = AsyncMock(return_value={"usda": False})
    lease_calls = 0

    async def run_lease(operation: Any) -> Any:
        nonlocal lease_calls
        lease_calls += 1
        return await operation()

    monkeypatch.setattr(scheduler_module, "run_with_update_lease", run_lease)
    try:
        assert asyncio.run(scheduler._run_update_check()) is True
        assert scheduler.last_update_check is not None
        assert asyncio.run(scheduler._run_update_check()) is True
        assert scheduler.update_manager.check_for_updates.await_count == 1
        assert lease_calls == 2

        scheduler.last_update_check = None
        scheduler.update_manager.check_for_updates = AsyncMock(return_value={"usda": True})
        monkeypatch.setattr(scheduler, "_run_source_update", AsyncMock(return_value=False))
        assert asyncio.run(scheduler._run_update_check()) is False
        assert scheduler.last_update_check is None

        monkeypatch.setattr(scheduler, "_run_source_update", AsyncMock(return_value=True))
        assert asyncio.run(scheduler._run_update_check()) is True
        assert scheduler.last_update_check is not None
    finally:
        asyncio.run(scheduler.update_manager.close())


def test_scheduler_contention_and_lease_errors_do_not_advance_watermark(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.food_apis import scheduler as scheduler_module

    scheduler = scheduler_module.DatabaseUpdateScheduler(install_signal_handlers=False)

    async def contend(_operation: Any) -> Any:
        raise scheduler_runtime.UpdateLeaseContended()

    monkeypatch.setattr(scheduler_module, "run_with_update_lease", contend)
    try:
        assert asyncio.run(scheduler._run_update_check()) is False
        assert scheduler.last_update_check is None
        with pytest.raises(scheduler_runtime.UpdateLeaseContended):
            asyncio.run(scheduler._run_update_check(propagate_lease_errors=True))

        async def fail_lease(_operation: Any) -> Any:
            raise scheduler_runtime.UpdateLeaseAcquireError("lease failed")

        monkeypatch.setattr(scheduler_module, "run_with_update_lease", fail_lease)
        assert asyncio.run(scheduler._run_update_check()) is False
        with pytest.raises(scheduler_runtime.UpdateLeaseAcquireError):
            asyncio.run(scheduler._run_update_check(propagate_lease_errors=True))
        assert scheduler.last_update_check is None

        async def cancel_lease(_operation: Any) -> Any:
            raise asyncio.CancelledError

        monkeypatch.setattr(scheduler_module, "run_with_update_lease", cancel_lease)
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(scheduler._run_update_check())
    finally:
        asyncio.run(scheduler.update_manager.close())


def test_scheduler_global_singleton_never_installs_api_signal_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.food_apis import scheduler as scheduler_module

    setup_calls = 0

    def record_setup(_scheduler: object) -> None:
        nonlocal setup_calls
        setup_calls += 1

    monkeypatch.setattr(
        scheduler_module.DatabaseUpdateScheduler,
        "_setup_signal_handlers",
        record_setup,
    )
    monkeypatch.setattr(scheduler_module, "_scheduler_instance", None)

    direct = scheduler_module.DatabaseUpdateScheduler()
    singleton = asyncio.run(scheduler_module.get_update_scheduler())
    try:
        assert setup_calls == 1
        assert singleton is asyncio.run(scheduler_module.get_update_scheduler())
    finally:
        asyncio.run(direct.update_manager.close())
        asyncio.run(singleton.update_manager.close())


def test_scheduler_status_degrades_invalid_configuration_without_claiming_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.food_apis import scheduler as scheduler_module

    def raise_invalid_mode() -> scheduler_runtime.SchedulerMode:
        raise scheduler_runtime.SchedulerConfigurationError("invalid")

    scheduler = scheduler_module.DatabaseUpdateScheduler(install_signal_handlers=False)
    monkeypatch.setattr(
        scheduler_module,
        "resolve_scheduler_mode",
        raise_invalid_mode,
    )
    try:
        status = scheduler.get_status()["scheduler"]
        assert status["configured_mode"] == "invalid"
        assert status["configured_periodic_owner"] == "none"
    finally:
        asyncio.run(scheduler.update_manager.close())


def test_worker_main_selects_one_cli_action_and_maps_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.food_apis import scheduler as scheduler_module

    async def serve_success() -> int:
        return 7

    async def once_success() -> int:
        return 8

    logging_configs: list[dict[str, object]] = []

    def record_logging_config(**kwargs: object) -> None:
        logging_configs.append(kwargs)

    monkeypatch.setattr(scheduler_module.logging, "basicConfig", record_logging_config)
    monkeypatch.setattr(scheduler_module, "_serve_worker", serve_success)
    monkeypatch.setattr(scheduler_module, "_run_worker_once", once_success)
    assert scheduler_module.worker_main(["--serve"]) == 7
    assert scheduler_module.worker_main(["--once"]) == 8
    assert logging_configs
    assert all(config["level"] == scheduler_module.logging.INFO for config in logging_configs)

    with pytest.raises(SystemExit):
        scheduler_module.worker_main([])
    with pytest.raises(SystemExit):
        scheduler_module.worker_main(["--serve", "--once"])

    cases: list[tuple[BaseException, int]] = [
        (scheduler_runtime.SchedulerConfigurationError("bad mode"), 2),
        (scheduler_runtime.UpdateLeaseAcquireError("lease failed"), 1),
        (KeyboardInterrupt(), 130),
        (RuntimeError("worker failed"), 1),
    ]
    for failure, expected_exit in cases:

        async def fail(failure: BaseException = failure) -> int:
            raise failure

        monkeypatch.setattr(scheduler_module, "_serve_worker", fail)
        assert scheduler_module.worker_main(["--serve"]) == expected_exit


def test_worker_database_initialization_uses_public_db_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core import db as core_db
    from core.food_apis import scheduler as scheduler_module

    calls = 0

    def init() -> None:
        nonlocal calls
        calls += 1

    monkeypatch.setattr(core_db, "init_db", init)
    scheduler_module._initialize_worker_database()
    assert calls == 1


def test_serve_worker_owns_signals_and_does_not_double_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.food_apis import scheduler as scheduler_module

    state = "running"
    instances: list[Any] = []
    initialized = 0

    class _Manager:
        def __init__(self) -> None:
            self.close_calls = 0

        async def close(self) -> None:
            self.close_calls += 1

    class _Worker:
        def __init__(self, *, install_signal_handlers: bool) -> None:
            assert install_signal_handlers is True
            self.is_running = False
            self._update_task: asyncio.Task[None] | None = None
            self._shutdown_task: asyncio.Task[None] | None = None
            self.update_manager = _Manager()
            self.stop_calls = 0
            instances.append(self)

        async def start(self) -> None:
            if state == "missing_task":
                return
            self._update_task = asyncio.create_task(asyncio.sleep(0))
            if state == "already_stopped":
                self.is_running = False
                self._shutdown_task = asyncio.create_task(self.update_manager.close())
            else:
                self.is_running = True

        async def stop(self) -> None:
            self.stop_calls += 1
            self.is_running = False
            await self.update_manager.close()

    def initialize() -> None:
        nonlocal initialized
        initialized += 1

    monkeypatch.setattr(
        scheduler_module,
        "resolve_scheduler_mode",
        lambda: scheduler_runtime.SchedulerMode.EXTERNAL,
    )
    monkeypatch.setattr(scheduler_module, "_initialize_worker_database", initialize)
    monkeypatch.setattr(scheduler_module, "DatabaseUpdateScheduler", _Worker)

    assert asyncio.run(scheduler_module._serve_worker()) == 0
    assert instances[-1].stop_calls == 1
    assert instances[-1].update_manager.close_calls == 1

    state = "already_stopped"
    assert asyncio.run(scheduler_module._serve_worker()) == 0
    assert instances[-1].stop_calls == 0
    assert instances[-1].update_manager.close_calls == 1

    state = "missing_task"
    with pytest.raises(RuntimeError, match="task was not created"):
        asyncio.run(scheduler_module._serve_worker())
    assert instances[-1].update_manager.close_calls == 1
    assert initialized == 3

    monkeypatch.setattr(
        scheduler_module,
        "resolve_scheduler_mode",
        lambda: scheduler_runtime.SchedulerMode.DISABLED,
    )
    with pytest.raises(
        scheduler_runtime.SchedulerConfigurationError,
        match="requires external",
    ):
        asyncio.run(scheduler_module._serve_worker())
    assert initialized == 3


def test_worker_signal_handler_tracks_cleanup_task_to_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.food_apis import scheduler as scheduler_module

    handlers: dict[int, Any] = {}
    monkeypatch.setattr(scheduler_module, "is_test_runtime", lambda: False)
    monkeypatch.setattr(
        scheduler_module.signal,
        "signal",
        lambda signum, handler: handlers.__setitem__(signum, handler),
    )

    async def scenario() -> None:
        scheduler = scheduler_module.DatabaseUpdateScheduler()
        scheduler._loop = asyncio.get_running_loop()
        scheduler.is_running = True
        handler = handlers[scheduler_module.signal.SIGTERM]

        handler(scheduler_module.signal.SIGTERM, None)
        await asyncio.sleep(0)
        shutdown_task = scheduler._shutdown_task
        assert shutdown_task is not None

        handler(scheduler_module.signal.SIGTERM, None)
        assert scheduler._shutdown_task is shutdown_task
        await shutdown_task
        assert scheduler.is_running is False

    asyncio.run(scenario())


def test_once_worker_exit_contract_and_mode_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.food_apis import scheduler as scheduler_module

    outcome: object = True
    instances: list[Any] = []

    class _Manager:
        def __init__(self) -> None:
            self.close_calls = 0

        async def close(self) -> None:
            self.close_calls += 1

    class _Worker:
        def __init__(self, *, install_signal_handlers: bool) -> None:
            assert install_signal_handlers is False
            self.update_manager = _Manager()
            instances.append(self)

        async def _run_update_check(self, *, propagate_lease_errors: bool) -> bool:
            assert propagate_lease_errors is True
            if isinstance(outcome, BaseException):
                raise outcome
            return bool(outcome)

    monkeypatch.setattr(scheduler_module, "_initialize_worker_database", lambda: None)
    monkeypatch.setattr(scheduler_module, "DatabaseUpdateScheduler", _Worker)
    monkeypatch.setattr(
        scheduler_module,
        "resolve_scheduler_mode",
        lambda: scheduler_runtime.SchedulerMode.EXTERNAL,
    )

    assert asyncio.run(scheduler_module._run_worker_once()) == 0
    assert instances[-1].update_manager.close_calls == 1

    outcome = False
    assert asyncio.run(scheduler_module._run_worker_once()) == 1
    assert instances[-1].update_manager.close_calls == 1

    outcome = scheduler_runtime.UpdateLeaseContended()
    assert asyncio.run(scheduler_module._run_worker_once()) == 0
    assert instances[-1].update_manager.close_calls == 1

    monkeypatch.setattr(
        scheduler_module,
        "resolve_scheduler_mode",
        lambda: scheduler_runtime.SchedulerMode.IN_PROCESS_DEV,
    )
    with pytest.raises(
        scheduler_runtime.SchedulerConfigurationError,
        match="unavailable",
    ):
        asyncio.run(scheduler_module._run_worker_once())
