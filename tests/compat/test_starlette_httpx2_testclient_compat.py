"""Production app TestClient compatibility canary for Starlette/httpx2."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from textwrap import dedent

REPO_ROOT = Path(__file__).resolve().parents[2]
PAYLOAD_PREFIX = "PULSEPLATE_HTTPX2_TESTCLIENT_COMPAT="


def _extract_payload(stdout: str) -> dict[str, object]:
    for line in stdout.splitlines():
        if line.startswith(PAYLOAD_PREFIX):
            payload = line.removeprefix(PAYLOAD_PREFIX)
            return json.loads(payload)
    raise AssertionError(f"missing compatibility payload in stdout:\n{stdout}")


def test_app_main_testclient_uses_httpx2_without_starlette_deprecation() -> None:
    child_code = dedent("""
        from __future__ import annotations

        import json
        import warnings

        from starlette.exceptions import StarletteDeprecationWarning

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", StarletteDeprecationWarning)
            from fastapi.testclient import TestClient
            import starlette.testclient as starlette_testclient
            import app.main as app_main

            with TestClient(app_main.app) as client:
                health_response = client.get("/health")
                openapi_response = client.get("/openapi.json")

        warning_messages = [
            str(item.message)
            for item in caught
            if issubclass(item.category, StarletteDeprecationWarning)
            or (
                "testclient" in str(item.message).casefold()
                and "httpx2" in str(item.message).casefold()
            )
        ]
        payload = {
            "backend_module": starlette_testclient.httpx.__name__,
            "health_status": health_response.status_code,
            "health_content_type": health_response.headers.get("content-type", ""),
            "health_json": health_response.json(),
            "openapi_status": openapi_response.status_code,
            "openapi_content_type": openapi_response.headers.get("content-type", ""),
            "openapi_json": {
                "has_openapi": "openapi" in openapi_response.json(),
                "has_paths": "paths" in openapi_response.json(),
            },
            "warning_messages": warning_messages,
        }
        print("PULSEPLATE_HTTPX2_TESTCLIENT_COMPAT=" + json.dumps(payload, sort_keys=True))
        """)
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "test",
            "ENVIRONMENT": "test",
            "SERVER_SALT": "StrongServerSaltForHttpx2Tests123456789!",
            "TESTING": "true",
        }
    )

    result = subprocess.run(
        [sys.executable, "-c", child_code],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, (
        "production TestClient compatibility subprocess failed\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    payload = _extract_payload(result.stdout)

    assert payload["backend_module"] == "httpx2"
    assert payload["health_status"] == 200
    assert "application/json" in str(payload["health_content_type"]).lower()
    assert isinstance(payload["health_json"], dict)
    assert payload["health_json"].get("status") == "ok"
    assert payload["openapi_status"] == 200
    assert "application/json" in str(payload["openapi_content_type"]).lower()
    assert payload["openapi_json"] == {"has_openapi": True, "has_paths": True}
    assert payload["warning_messages"] == []
