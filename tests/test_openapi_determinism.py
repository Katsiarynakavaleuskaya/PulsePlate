"""Test that OpenAPI generation is deterministic across multiple runs."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

_OPENAPI_MAKE_CMD = ["make", "openapi"]
_OPENAPI_PIPELINE_ATTEMPTS = 2
_SUBPROCESS_LOG_TAIL_LINES = 120


def _sha256(path: Path) -> str:
    """Calculate SHA256 hash of file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tail_log(log_text: str) -> str:
    """Return a bounded tail for subprocess logs to keep pytest output readable."""
    lines = log_text.splitlines()
    return "\n".join(lines[-_SUBPROCESS_LOG_TAIL_LINES:])


def _run_openapi_pipeline(repo_root: Path) -> None:
    """
    Run `make openapi` with bounded retry and actionable failure diagnostics.

    RU: В CI иногда бывают транзиентные падения npm/make.
    Делаем 1 ретрай, но если команда стабильно падает — падаем с хвостом stdout/stderr.
    EN: CI can hit transient npm/make failures.
    We retry once, but still fail-closed with stdout/stderr tail if persistent.
    """
    last_process: subprocess.CompletedProcess[str] | None = None
    for _attempt in range(1, _OPENAPI_PIPELINE_ATTEMPTS + 1):
        process = subprocess.run(
            _OPENAPI_MAKE_CMD,
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        last_process = process
        if process.returncode == 0:
            return

    assert last_process is not None  # pragma: no cover - defensive, loop always runs
    stdout_tail = _tail_log(last_process.stdout)
    stderr_tail = _tail_log(last_process.stderr)
    pytest.fail(
        "\n".join(
            [
                f"`{' '.join(_OPENAPI_MAKE_CMD)}` failed "
                f"after {_OPENAPI_PIPELINE_ATTEMPTS} attempts "
                f"(exit={last_process.returncode}).",
                "--- stdout (tail) ---",
                stdout_tail or "<empty>",
                "--- stderr (tail) ---",
                stderr_tail or "<empty>",
            ]
        )
    )


def test_openapi_and_schema_ts_are_deterministic() -> None:
    """
    Verify that full OpenAPI pipeline produces identical output across runs.

    This test ensures that:
    - Normalization in scripts/generate_openapi.py works correctly
    - openapi-typescript generates deterministic schema.ts with --alphabetize flag
    - No drift occurs in openapi.json or schema.ts
    - Full pipeline (make openapi) is deterministic for CI and local development
    """
    # This test is meant for the dedicated CI job that has Node/npm installed.
    if not (shutil.which("node") and shutil.which("npm") and shutil.which("make")):
        pytest.skip("OpenAPI determinism test requires node/npm/make toolchain")

    repo_root = Path(__file__).resolve().parents[1]
    openapi_path = repo_root / "frontend" / "src" / "api" / "openapi.json"
    schema_path = repo_root / "frontend" / "src" / "api" / "schema.ts"

    # Run full pipeline twice (same as CI)
    _run_openapi_pipeline(repo_root)
    # Sanity-check: generator must produce FULL schema (no schema-only markers) and include
    # key endpoints that were previously excluded behind schema-only mode.
    schema = json.loads(openapi_path.read_text(encoding="utf-8"))
    info = schema.get("info") or {}
    assert info.get("x-openapi-mode") != "schema-only"
    paths = schema.get("paths") or {}
    assert "/api/v1/pro/meal/weekly" in paths
    assert "/api/v1/pro/nutrition/daily" in paths
    assert "/api/v1/pro/nutrition/meal-log" in paths
    assert "/api/v1/pro/bmi/calculate" in paths
    assert "/api/v1/premium/plan/week-flexible" not in paths
    assert "/api/v1/business/analyze" not in paths
    assert "/api/v1/foods" not in paths
    assert "/api/v1/restaurants/search" not in paths

    h1: tuple[str, str] = (_sha256(openapi_path), _sha256(schema_path))

    _run_openapi_pipeline(repo_root)
    h2: tuple[str, str] = (_sha256(openapi_path), _sha256(schema_path))

    if h1 != h2:
        lines: list[str] = ["Drift detected:"]
        if h1[0] != h2[0]:
            lines.append(f"  openapi.json: {h1[0]} != {h2[0]}")
        if h1[1] != h2[1]:
            lines.append(f"  schema.ts: {h1[1]} != {h2[1]}")
        lines.append("This indicates non-deterministic generation.")
        lines.append(
            "Check scripts/generate_openapi.py and frontend/package.json "
            "(openapi-typescript version/flags)."
        )
        pytest.fail("\n".join(lines))


def test_register_pro_routes_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure PRO route registration short-circuits when already registered."""
    from fastapi import FastAPI
    from fastapi.routing import APIRouter

    from app.routers.pro_registration import register_pro_routes

    # Ensure feature flags do not accidentally alter the cached early-return path.
    monkeypatch.setenv("FEATURE_PREMIUM_WEEK_ENABLED", "true")

    app = FastAPI()

    # Set cache to force idempotent early-return branch
    sentinel_pro = APIRouter()
    sentinel_week = APIRouter()
    app.state._pro_routes_registered = True
    app.state._cached_pro_router = sentinel_pro
    app.state._cached_premium_week_router = sentinel_week

    before = len(app.router.routes)
    pro_router, premium_week_router = register_pro_routes(app)
    after = len(app.router.routes)

    assert after == before
    assert pro_router is sentinel_pro
    assert premium_week_router is sentinel_week
