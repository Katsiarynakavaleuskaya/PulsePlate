from __future__ import annotations

import asyncio
import importlib
import json
import os
import subprocess
import sys
import textwrap
from types import ModuleType

import pytest
from fastapi import HTTPException


def _import_or_reload_module(name: str) -> ModuleType:
    module = sys.modules.get(name)
    if module is not None:
        return importlib.reload(module)

    parent_name, _, child_name = name.rpartition(".")
    if parent_name and child_name:
        parent_module = importlib.import_module(parent_name)
        stale_child = getattr(parent_module, child_name, None)
        if getattr(stale_child, "__name__", None) == name:
            delattr(parent_module, child_name)

    return importlib.import_module(name)


def _reload_legacy_app() -> ModuleType:
    """Reload legacy_app after env changes.

    RU: Перезагружаем legacy_app после изменения env, чтобы import-time wiring
    перечитал канонические runtime helpers.
    EN: Reload legacy_app after env changes so import-time wiring re-evaluates
    canonical runtime helpers.
    """

    return _import_or_reload_module("legacy_app")


def _run_application_probe(
    runtime_env: str,
    *,
    path_present: bool = True,
    pytest_marker: bool = False,
    include_main: bool = False,
    enable_test_routes: bool = False,
) -> dict[str, object]:
    """Observe import-time ownership in one fresh interpreter."""

    main_probe = (
        """
        import app.main as app_main
        from app.effective_routes import iter_effective_route_candidates, route_path
        has_test_route = any(
            route_path(route) == "/api/v1/test/health"
            for route in iter_effective_route_candidates(app_main.app.routes)
        )
        """
        if include_main
        else "has_test_route = None"
    )
    scenario = textwrap.dedent(f"""
        import json
        import logging
        import dotenv
        calls = []
        dotenv.load_dotenv = lambda *args, **kwargs: calls.append("load")
        from app.bootstrap import application
        import legacy_app
        {main_probe}
        print("ENV_RESULT=" + json.dumps({{
            "calls": len(calls),
            "runtime_env": application.RUNTIME_ENV,
            "legacy_env": legacy_app._app_env,
            "metadata_alias": legacy_app._application_metadata is application.APPLICATION_METADATA,
            "root_level": logging.getLevelName(logging.getLogger().level),
            "has_test_route": has_test_route,
        }}, sort_keys=True))
    """)
    env = os.environ.copy()
    for name in (
        "APP_ENV",
        "DEBUG",
        "ENABLE_DEBUG_ENDPOINT",
        "ENABLE_TEST_ROUTES",
        "ENV",
        "ENVIRONMENT",
        "PYTEST_CURRENT_TEST",
    ):
        env.pop(name, None)
    env["ENVIRONMENT"] = runtime_env
    env["PRIVATE_EXPORTS_ENABLED"] = "false"
    if not path_present:
        env.pop("PATH", None)
    if pytest_marker:
        env["PYTEST_CURRENT_TEST"] = "ownership-probe"
    if enable_test_routes:
        env["ENABLE_TEST_ROUTES"] = "1"

    completed = subprocess.run(
        [sys.executable, "-c", scenario],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result_line = next(
        line for line in completed.stdout.splitlines() if line.startswith("ENV_RESULT=")
    )
    result: dict[str, object] = json.loads(result_line.removeprefix("ENV_RESULT="))
    return result


@pytest.fixture(autouse=True)
def _reset_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep env-based legacy app tests deterministic.

    RU: Жёстко изолируем env, чтобы legacy import-time gates читали только
    нужные значения текущего теста.
    EN: Hard-isolate env so legacy import-time gates only see the values set by
    the current test.
    """

    for name in (
        "APP_ENV",
        "ENVIRONMENT",
        "ENV",
        "ENABLE_TEST_ROUTES",
        "ENABLE_DEBUG_ENDPOINT",
        "PYTEST_CURRENT_TEST",
        "DEBUG",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize(
    ("runtime_env", "dotenv_calls", "root_level"),
    (
        ("local", 1, "INFO"),
        ("dev", 1, "INFO"),
        ("development", 1, "INFO"),
        ("production", 0, "INFO"),
        ("staging", 0, "INFO"),
        ("test", 0, "DEBUG"),
        ("testing", 0, "DEBUG"),
        ("unknown", 0, "INFO"),
    ),
)
def test_canonical_application_owns_environment_setup(
    runtime_env: str, dotenv_calls: int, root_level: str
) -> None:
    result = _run_application_probe(runtime_env)
    assert result == {
        "calls": dotenv_calls,
        "runtime_env": runtime_env,
        "legacy_env": runtime_env,
        "metadata_alias": True,
        "root_level": root_level,
        "has_test_route": None,
    }


@pytest.mark.parametrize(
    ("path_present", "pytest_marker"),
    ((False, False), (True, True)),
)
def test_local_dotenv_gate_requires_path_and_non_pytest(
    path_present: bool, pytest_marker: bool
) -> None:
    assert (
        _run_application_probe("local", path_present=path_present, pytest_marker=pytest_marker)[
            "calls"
        ]
        == 0
    )


def test_canonical_bootstrap_staging_test_router_respects_environment_flag() -> None:
    assert _run_application_probe("staging", include_main=True)["has_test_route"] is False
    assert (
        _run_application_probe("staging", include_main=True, enable_test_routes=True)[
            "has_test_route"
        ]
        is True
    )


def test_debug_env_uses_environment_when_app_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")

    app_module = _reload_legacy_app()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(app_module.debug_env())

    assert exc_info.value.status_code == 404


def test_health_prefers_environment_over_app_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("APP_ENV", "local")

    health_module = importlib.import_module("app.routers.health")
    response = asyncio.run(health_module.health())
    assert response["environment"] == "production"


def test_test_router_request_gate_prefers_environment_over_app_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("APP_ENV", "local")

    from app.routers import test as test_router

    importlib.reload(test_router)

    with pytest.raises(HTTPException) as exc_info:
        test_router._ensure_non_production()

    assert exc_info.value.status_code == 404


def test_test_router_request_gate_blocks_staging_without_enable_even_if_app_env_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("APP_ENV", "local")

    from app.routers import test as test_router

    importlib.reload(test_router)

    with pytest.raises(HTTPException) as exc_info:
        test_router._ensure_non_production()

    assert exc_info.value.status_code == 404

    monkeypatch.setenv("ENABLE_TEST_ROUTES", "1")
    importlib.reload(test_router)
    test_router._ensure_non_production()
