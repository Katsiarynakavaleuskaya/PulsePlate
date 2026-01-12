"""Bootstrap: register canonical PRO contract routes (targets + plate).

Called from `app/main.py` to avoid adding runtime registration logic into `legacy_app.py`.
"""

from __future__ import annotations

from fastapi import FastAPI


def register_pro_contract_routes(app: FastAPI) -> None:
    """Register PRO contract routes on the primary FastAPI app (idempotent)."""
    has_targets = any(
        getattr(r, "path", None) == "/api/v1/pro/nutrition/targets"
        and "POST" in (getattr(r, "methods", None) or set())
        for r in getattr(app, "routes", None) or []
    )
    has_plate = any(
        getattr(r, "path", None) == "/api/v1/pro/nutrition/plate"
        and "POST" in (getattr(r, "methods", None) or set())
        for r in getattr(app, "routes", None) or []
    )

    if has_targets and has_plate:
        return

    if has_targets != has_plate:
        raise RuntimeError(
            f"Partial PRO contract routes detected: "
            f"has_targets={has_targets}, has_plate={has_plate}"
        )

    from app.routers.pro_nutrition_contracts import router as pro_contracts_router

    app.include_router(pro_contracts_router)
