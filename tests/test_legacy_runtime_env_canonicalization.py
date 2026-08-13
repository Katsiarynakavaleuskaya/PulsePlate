from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from typing import Any

import pytest


def _run_fresh_runtime(
    body: str,
    *,
    environment: str,
    app_env: str | None = None,
    enable_test_routes: bool = False,
) -> Any:
    scenario = textwrap.dedent(f"""
        import json
        {body}
        print("RUNTIME_RESULT=" + json.dumps(result, sort_keys=True))
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
    env["ENVIRONMENT"] = environment
    env["PRIVATE_EXPORTS_ENABLED"] = "false"
    if app_env is not None:
        env["APP_ENV"] = app_env
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
        line for line in completed.stdout.splitlines() if line.startswith("RUNTIME_RESULT=")
    )
    return json.loads(result_line.removeprefix("RUNTIME_RESULT="))


@pytest.mark.parametrize(
    ("runtime_env", "expected_dotenv_calls", "expected_root_level"),
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
def test_canonical_application_owns_runtime_env_dotenv_and_root_logging(
    runtime_env: str,
    expected_dotenv_calls: int,
    expected_root_level: str,
) -> None:
    result = _run_fresh_runtime(
        """
        import logging
        import dotenv
        calls = []
        dotenv.load_dotenv = lambda *args, **kwargs: calls.append("load")
        from app.bootstrap import application
        import legacy_app
        result = {
            "calls": len(calls),
            "canonical_env": application.RUNTIME_ENV,
            "legacy_env": legacy_app._app_env,
            "metadata_alias": legacy_app._application_metadata is application.APPLICATION_METADATA,
            "root_level": logging.getLevelName(logging.getLogger().level),
        }
        """,
        environment=runtime_env,
    )

    assert result == {
        "calls": expected_dotenv_calls,
        "canonical_env": runtime_env,
        "legacy_env": runtime_env,
        "metadata_alias": True,
        "root_level": expected_root_level,
    }


def test_canonical_bootstrap_staging_test_router_respects_environment_flag() -> None:
    body = """
        import app.main as app_main
        from app.effective_routes import iter_effective_route_candidates, route_path
        result = any(
            route_path(route) == "/api/v1/test/health"
            for route in iter_effective_route_candidates(app_main.app.routes)
        )
    """

    assert _run_fresh_runtime(body, environment="staging") is False
    assert _run_fresh_runtime(body, environment="staging", enable_test_routes=True) is True


def test_debug_env_uses_environment_when_app_env_missing() -> None:
    status_code = _run_fresh_runtime(
        """
        import asyncio
        from fastapi import HTTPException
        import legacy_app
        try:
            asyncio.run(legacy_app.debug_env())
        except HTTPException as exc:
            result = exc.status_code
        else:
            result = None
        """,
        environment="production",
    )

    assert status_code == 404


def test_health_prefers_environment_over_app_env() -> None:
    environment = _run_fresh_runtime(
        """
        import asyncio
        from app.routers.health import health
        result = asyncio.run(health())["environment"]
        """,
        environment="production",
        app_env="local",
    )

    assert environment == "production"


def test_test_router_request_gate_prefers_environment_over_app_env() -> None:
    status_code = _run_fresh_runtime(
        """
        from fastapi import HTTPException
        from app.routers.test import _ensure_non_production
        try:
            _ensure_non_production()
        except HTTPException as exc:
            result = exc.status_code
        else:
            result = None
        """,
        environment="production",
        app_env="local",
    )

    assert status_code == 404


def test_test_router_request_gate_blocks_staging_without_enable_even_if_app_env_local() -> None:
    body = """
        from fastapi import HTTPException
        from app.routers.test import _ensure_non_production
        try:
            _ensure_non_production()
        except HTTPException as exc:
            result = exc.status_code
        else:
            result = None
    """

    assert _run_fresh_runtime(body, environment="staging", app_env="local") == 404
    assert (
        _run_fresh_runtime(
            body,
            environment="staging",
            app_env="local",
            enable_test_routes=True,
        )
        is None
    )
