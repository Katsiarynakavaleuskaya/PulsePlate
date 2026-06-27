"""Bootstrap: register canonical PRO contract routes (targets + plate).

Called from `app/main.py` to avoid adding runtime registration logic into `legacy_app.py`.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.effective_routes import iter_effective_route_candidates, route_methods, route_path


def register_pro_contract_routes(app: FastAPI) -> None:
    """Register PRO contract routes on the primary FastAPI app (idempotent)."""
    routes = tuple(iter_effective_route_candidates(getattr(app, "routes", None) or []))
    has_targets = any(
        route_path(route) == "/api/v1/pro/nutrition/targets" and "POST" in route_methods(route)
        for route in routes
    )
    has_plate = any(
        route_path(route) == "/api/v1/pro/nutrition/plate" and "POST" in route_methods(route)
        for route in routes
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
