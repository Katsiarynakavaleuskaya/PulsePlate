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
from typing import Any
from unittest.mock import AsyncMock

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from app.services import admin_operations
from app.services import scheduler_access

REPO_ROOT = Path(__file__).resolve().parents[1]


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
