from __future__ import annotations

import datetime
import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.utils.helpers import _short_git_sha
from core.db import get_session
from settings import get_runtime_env_name

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


def _health_payload() -> dict[str, Any]:
    environment = get_runtime_env_name()

    git_sha = _short_git_sha(os.getenv("GIT_SHA"))

    return {
        "status": "ok",
        "version": "1.0.0",  # TODO: Read from pyproject.toml
        "git_sha": git_sha,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "environment": environment,
    }


@router.get("/health", include_in_schema=False)
async def health() -> dict[str, Any]:
    """Health check endpoint with version info for debugging."""

    return _health_payload()


@router.get("/api/v1/health", include_in_schema=False)
async def health_v1() -> dict[str, Any]:
    """Health check endpoint (v1 alias) with version info for debugging."""

    return _health_payload()


@router.get("/health/db", include_in_schema=False)
async def database_health(session: Session = Depends(get_session)) -> dict[str, str]:
    """Lightweight database connectivity check."""

    try:
        import core.db_fallback as _fallback_mod

        if _fallback_mod.is_fallback_active() or os.getenv("DB_HEALTH_DEGRADED") == "1":
            raise HTTPException(status_code=503, detail="Database unavailable")

        exec_fn = getattr(session, "execute", None)
        if exec_fn is None or not callable(exec_fn):
            raise HTTPException(status_code=503, detail="Database unavailable")
        if getattr(session, "bind", None) is None:
            raise HTTPException(status_code=503, detail="Database unavailable")
        await run_in_threadpool(session.execute, text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - defensive path hit via tests
        logger.error("Database health check failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok"}


@router.get("/ready", include_in_schema=False)
async def ready(session: Session = Depends(get_session)) -> dict[str, object]:
    """Readiness probe for orchestrators (alias for /health/db).

    Returns 200 if DB is available, 503 otherwise.
    Use this for Kubernetes/Docker readiness checks.
    Hidden from OpenAPI - semantics live in /health/db.
    """

    readiness_payload = await database_health(session=session)
    insight_runtime: dict[str, object] = {"status": "unavailable"}

    try:
        from llm import get_insight_runtime_readiness

        insight_runtime = get_insight_runtime_readiness()
    except Exception as exc:
        logger.warning("Insight runtime readiness unavailable on /ready: %s", exc)

    return {
        **readiness_payload,
        "insight_runtime": insight_runtime,
    }
