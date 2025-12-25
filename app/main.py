"""
Canonical FastAPI entrypoint for the app package.

Keep imports deterministic: do NOT use importlib exec_module, do NOT mutate sys.path.
"""

from __future__ import annotations

from legacy_app import app  # re-export FastAPI instance from legacy root module

__all__ = ["app"]
