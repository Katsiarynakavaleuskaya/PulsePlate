"""
Canonical FastAPI entrypoint for the app package.

Keep imports deterministic: do NOT use importlib exec_module, do NOT mutate sys.path.
"""

from __future__ import annotations

from fastapi import FastAPI

from legacy_app import app as _legacy_app  # re-export FastAPI instance from legacy root module

# Register observability infrastructure (middleware + /metrics endpoint)
# This must be done here, not in legacy_app.py, to keep legacy as a thin proxy
from app.bootstrap.metrics import register_metrics

app: FastAPI = _legacy_app

register_metrics(app)

__all__ = ["app"]
