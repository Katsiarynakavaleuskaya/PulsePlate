"""Bootstrap: register canonical PRO contract routes (targets + plate).

Called from `app/main.py` to avoid adding runtime registration logic into `legacy_app.py`.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.bootstrap.route_family import route_has_dependency_call
from app.effective_routes import (
    iter_effective_route_candidates,
    route_endpoint,
    route_endpoint_for_path_method,
    route_matches_path_method,
)
from app.middleware.api_tiers import require_pro_tier

_TARGETS_ROUTE_PATH = "/api/v1/pro/nutrition/targets"
_PLATE_ROUTE_PATH = "/api/v1/pro/nutrition/plate"


def _canonical_route_state(
    routes: tuple[object, ...],
    *,
    path: str,
    endpoint: object,
) -> bool:
    matching_routes = [route for route in routes if route_matches_path_method(route, path, "POST")]
    expected_routes = [route for route in matching_routes if route_endpoint(route) is endpoint]
    expected_count = len(expected_routes)
    foreign_count = len(matching_routes) - expected_count
    if foreign_count or expected_count > 1:
        raise RuntimeError(
            f"Duplicate {path} route detected with a different PRO contract handler."
        )
    if expected_count == 1:
        route = expected_routes[0]
        if not route_has_dependency_call(route, require_pro_tier):
            raise RuntimeError(
                f"Existing {path} route does not preserve PRO contract required dependency."
            )
    return expected_count == 1


def register_pro_contract_routes(app: FastAPI) -> None:
    """Register PRO contract routes on the primary FastAPI app (idempotent)."""
    from app.routers.pro_nutrition_contracts import router as pro_contracts_router

    targets_endpoint = route_endpoint_for_path_method(
        pro_contracts_router.routes,
        _TARGETS_ROUTE_PATH,
        "POST",
    )
    plate_endpoint = route_endpoint_for_path_method(
        pro_contracts_router.routes,
        _PLATE_ROUTE_PATH,
        "POST",
    )
    if targets_endpoint is None or plate_endpoint is None:
        raise RuntimeError("PRO contract router does not define the expected route family.")

    routes = tuple(iter_effective_route_candidates(getattr(app, "routes", None) or []))
    has_targets = _canonical_route_state(
        routes,
        path=_TARGETS_ROUTE_PATH,
        endpoint=targets_endpoint,
    )
    has_plate = _canonical_route_state(
        routes,
        path=_PLATE_ROUTE_PATH,
        endpoint=plate_endpoint,
    )

    if has_targets and has_plate:
        return

    if has_targets != has_plate:
        raise RuntimeError(
            f"Partial PRO contract routes detected: "
            f"has_targets={has_targets}, has_plate={has_plate}"
        )

    app.include_router(pro_contracts_router)
