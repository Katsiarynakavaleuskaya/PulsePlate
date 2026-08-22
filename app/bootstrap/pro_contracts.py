"""Bootstrap the exact canonical PRO nutrition route family.

Called from `app/main.py` to avoid adding runtime registration logic into `legacy_app.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, FastAPI
from starlette.routing import Match
from starlette.types import Scope

from app.bootstrap.route_family import route_has_dependency_call
from app.effective_routes import (
    is_api_route_candidate,
    iter_effective_route_candidates,
    route_endpoint,
    route_endpoint_for_path_method,
    route_include_in_schema,
    route_methods,
    route_path,
)
from app.middleware.api_tiers import require_pro_tier

_FRAMEWORK_METHODS = frozenset({"HEAD", "OPTIONS"})


def _same_object(existing: object, expected: object) -> bool:
    return existing is expected


@dataclass(frozen=True, slots=True)
class _ProRouteSpec:
    path: str
    endpoint: object
    response_model: object


def _route_response_model(route: object) -> object:
    response_model = getattr(route, "response_model", None)
    if response_model is not None:
        return response_model
    original_route = getattr(route, "original_route", None)
    return getattr(original_route, "response_model", None)


def _source_route_specs() -> tuple[_ProRouteSpec, ...]:
    from app.routers.pro_nutrition_contracts import (
        pro_nutrition_bmr,
        pro_nutrition_gaps,
        pro_nutrition_plate,
        pro_nutrition_targets,
    )
    from app.schemas.bmr import BMRResponse
    from app.schemas.premium_contracts import (
        NutrientGapsResponse,
        PlateResponse,
        WHOTargetsResponse,
    )

    return (
        _ProRouteSpec(
            path="/api/v1/pro/nutrition/targets",
            endpoint=pro_nutrition_targets,
            response_model=WHOTargetsResponse,
        ),
        _ProRouteSpec(
            path="/api/v1/pro/nutrition/plate",
            endpoint=pro_nutrition_plate,
            response_model=PlateResponse,
        ),
        _ProRouteSpec(
            path="/api/v1/pro/nutrition/bmr",
            endpoint=pro_nutrition_bmr,
            response_model=BMRResponse,
        ),
        _ProRouteSpec(
            path="/api/v1/pro/nutrition/gaps",
            endpoint=pro_nutrition_gaps,
            response_model=NutrientGapsResponse,
        ),
    )


def _require_exact_post_method(route: object, path: str) -> None:
    methods = route_methods(route) - _FRAMEWORK_METHODS
    if methods != {"POST"}:
        raise RuntimeError(f"Existing {path} route does not preserve exact POST method ownership.")


def _validate_route_metadata(route: object, spec: _ProRouteSpec) -> None:
    if route_endpoint(route) is not spec.endpoint:
        raise RuntimeError(
            f"Duplicate {spec.path} route detected with a different PRO contract handler."
        )
    if not route_has_dependency_call(
        route,
        require_pro_tier,
        endpoint_matcher=_same_object,
    ):
        raise RuntimeError(
            f"Existing {spec.path} route does not preserve PRO contract required dependency."
        )
    if _route_response_model(route) is not spec.response_model:
        raise RuntimeError(
            f"Existing {spec.path} route does not preserve PRO contract response model."
        )
    if route_include_in_schema(route) is not True:
        raise RuntimeError(
            f"Existing {spec.path} route does not preserve PRO contract OpenAPI visibility."
        )


def _validate_source_router(
    router: APIRouter,
    specs: tuple[_ProRouteSpec, ...],
) -> None:
    routes = tuple(iter_effective_route_candidates(router.routes))
    if len(routes) != len(specs) or any(not is_api_route_candidate(route) for route in routes):
        raise RuntimeError("PRO contract router does not define the expected route family.")

    expected_order = tuple((spec.path, "POST") for spec in specs)
    actual_order: list[tuple[str, str]] = []
    for route, spec in zip(routes, specs, strict=True):
        path = route_path(route)
        _require_exact_post_method(route, path)
        actual_order.append((path, "POST"))

        endpoint = route_endpoint_for_path_method(router.routes, spec.path, "POST")
        if endpoint is None or endpoint is not spec.endpoint:
            raise RuntimeError("PRO contract router does not define the expected route family.")
        if path != spec.path:
            raise RuntimeError("PRO contract router does not define the expected route family.")
        _validate_route_metadata(route, spec)

    if tuple(actual_order) != expected_order:
        raise RuntimeError("PRO contract router does not define the expected route family.")


def _family_routes(routes: tuple[object, ...], expected_paths: frozenset[str]) -> list[object]:
    return [route for route in routes if route_path(route) in expected_paths]


def _post_scope(app: FastAPI, path: str) -> Scope:
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "root_path": "",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1),
        "server": ("testserver", 80),
        "app": app,
    }


def _first_full_match_owner(app: FastAPI, path: str) -> object | None:
    scope = _post_scope(app, path)
    raw_routes: tuple[object, ...] = tuple(getattr(app, "routes", None) or [])
    for raw_route in raw_routes:
        matches = getattr(raw_route, "matches", None)
        if not callable(matches):
            continue
        match, _child_scope = matches(dict(scope))
        if match is not Match.FULL:
            continue

        candidates: tuple[object, ...] = tuple(iter_effective_route_candidates((raw_route,)))
        for candidate in candidates:
            candidate_matches = getattr(candidate, "matches", None)
            if not callable(candidate_matches):
                continue
            candidate_match, _candidate_scope = candidate_matches(dict(scope))
            if candidate_match is Match.FULL:
                return candidate
        return raw_route
    return None


def _validate_first_full_match_owners(
    app: FastAPI,
    specs: tuple[_ProRouteSpec, ...],
) -> tuple[bool, ...]:
    matches: list[bool] = []
    for spec in specs:
        owner = _first_full_match_owner(app, spec.path)
        if owner is None:
            matches.append(False)
            continue
        if not is_api_route_candidate(owner):
            raise RuntimeError(f"Non-API route shadows expected PRO contract path: {spec.path}.")
        if route_path(owner) != spec.path:
            raise RuntimeError(
                f"First full match for {spec.path} is not the exact PRO contract path owner."
            )
        _require_exact_post_method(owner, spec.path)
        _validate_route_metadata(owner, spec)
        matches.append(True)
    return tuple(matches)


def _validate_destination_routes(
    routes: list[object],
    specs: tuple[_ProRouteSpec, ...],
) -> None:
    non_api_paths = [route_path(route) for route in routes if not is_api_route_candidate(route)]
    if non_api_paths:
        formatted_paths = ", ".join(sorted(non_api_paths))
        raise RuntimeError(f"Non-API route shadows expected PRO contract path: {formatted_paths}.")

    specs_by_path = {spec.path: spec for spec in specs}
    present_order: list[tuple[str, str]] = []
    seen_paths: set[str] = set()

    for route in routes:
        path = route_path(route)
        spec = specs_by_path[path]
        _require_exact_post_method(route, path)
        _validate_route_metadata(route, spec)
        if path in seen_paths:
            raise RuntimeError(
                f"Duplicate {path} route detected with a different PRO contract handler."
            )
        seen_paths.add(path)
        present_order.append((path, "POST"))

    expected_order = tuple((spec.path, "POST") for spec in specs)
    if set(seen_paths) != set(specs_by_path):
        existing = ", ".join(sorted(seen_paths)) or "<none>"
        missing = ", ".join(sorted(set(specs_by_path) - seen_paths)) or "<none>"
        raise RuntimeError(
            f"Partial PRO contract routes detected: existing={existing}; missing={missing}."
        )
    if tuple(present_order) != expected_order:
        raise RuntimeError(
            "Existing PRO contract route order does not preserve source route order."
        )


def register_pro_contract_routes(app: FastAPI) -> None:
    """Register the finite PRO contract family exactly once, or fail closed."""
    from app.routers.pro_nutrition_contracts import router as pro_contracts_router

    specs = _source_route_specs()
    _validate_source_router(pro_contracts_router, specs)
    expected_paths = frozenset(spec.path for spec in specs)
    first_full_matches = _validate_first_full_match_owners(app, specs)
    routes = tuple(iter_effective_route_candidates(getattr(app, "routes", None) or []))
    existing_family = _family_routes(routes, expected_paths)
    if existing_family:
        _validate_destination_routes(existing_family, specs)
        if not all(first_full_matches):
            raise RuntimeError("Partial PRO contract first-match ownership detected.")
        return
    if any(first_full_matches):
        raise RuntimeError("Partial PRO contract first-match ownership detected.")

    app.include_router(pro_contracts_router)
    registered_routes = tuple(iter_effective_route_candidates(getattr(app, "routes", None) or []))
    _validate_destination_routes(_family_routes(registered_routes, expected_paths), specs)
    if not all(_validate_first_full_match_owners(app, specs)):
        raise RuntimeError(
            "Partial PRO contract first-match ownership detected after registration."
        )
