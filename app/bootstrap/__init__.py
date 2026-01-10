"""Bootstrap modules for FastAPI app initialization.

RU: Модули инициализации FastAPI приложения.
EN: FastAPI app initialization modules.

This package contains registration functions for middleware, routes, and
other infrastructure components that must be registered on the primary
FastAPI app instance (not in legacy_app.py).
"""

from __future__ import annotations

from app.bootstrap.metrics import metrics_endpoint

__all__ = ["metrics_endpoint"]
