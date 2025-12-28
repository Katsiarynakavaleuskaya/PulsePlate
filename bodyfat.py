from __future__ import annotations

from fastapi import APIRouter

from core.bodyfat import bf_deurenberg, bf_us_navy, bf_ymca, estimate_all as _estimate_all

__all__ = [
    "deurenberg",
    "us_navy",
    "ymca",
    "estimate_all",
    "get_router",
]


def get_router() -> APIRouter:
    # Lazy import keeps this module usable for pure math tests even if FastAPI router
    # wiring changes elsewhere.
    try:
        from app.routers.bodyfat import get_router as _get_router
    except ImportError as e:
        raise ImportError(
            "Bodyfat router moved to `app.routers.bodyfat.get_router`. "
            "Update imports to use the package path."
        ) from e

    return _get_router()


# ---- export aliases for tests/back-compat ----
deurenberg = bf_deurenberg
us_navy = bf_us_navy
ymca = bf_ymca
estimate_all = _estimate_all
