"""
Canonical FastAPI entrypoint for the app package.

Keep imports deterministic: do NOT use importlib exec_module, do NOT mutate sys.path.
"""

from __future__ import annotations

from legacy_app import app  # re-export FastAPI instance from legacy root module

# Register observability middleware (must be outermost to capture all requests/exceptions)
# NOTE: FastAPI/Starlette builds middleware stack in reverse order, so the
# last added middleware becomes the outermost wrapper.
from app.middleware.metrics import metrics_middleware

app.middleware("http")(metrics_middleware)

__all__ = ["app"]
