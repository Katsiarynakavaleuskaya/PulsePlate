"""Focused coverage for canonical BMI route registration."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
import pytest

from app.bootstrap.route_family import route_has_dependency_call
from app.effective_routes import (
    is_api_route_candidate,
    iter_effective_route_candidates,
    route_methods,
    route_path,
)
from app.middleware.api_tiers import require_pro_tier
from app.routers.bmi_registration import register_bmi_routes


def _http_routes(app: FastAPI) -> list[object]:
    return [
        route
        for route in iter_effective_route_candidates(app.routes)
        if is_api_route_candidate(route)
    ]


def _route_counts(app: FastAPI) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = {}
    for route in _http_routes(app):
        for method in sorted(route_methods(route) - {"HEAD", "OPTIONS"}):
            key = (method, route_path(route))
            counts[key] = counts.get(key, 0) + 1
    return counts


def _route(app: FastAPI, method: str, path: str) -> object:
    method = method.upper()
    return next(
        route
        for route in _http_routes(app)
        if route_path(route) == path and method in route_methods(route)
    )


def _unguarded_bmi_pro_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/pro", tags=["pro"])

    async def _bmi() -> dict[str, str]:
        return {"status": "bmi"}

    async def _calculate() -> dict[str, str]:
        return {"status": "calculate"}

    router.post("/bmi", deprecated=True)(_bmi)
    router.post("/bmi/calculate")(_calculate)
    return router


def test_register_bmi_routes_defaults_to_free_route_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FEATURE_BMI_PRO_ENABLED", raising=False)
    app = FastAPI()

    registration = register_bmi_routes(app)

    assert registration.feature_bmi_pro_enabled is False
    assert registration.bmi_pro_router is None
    assert registration.bmi_pro_legacy_alias_router is None
    counts = _route_counts(app)
    assert counts[("POST", "/api/v1/bmi/calculate")] == 1
    assert ("POST", "/api/v1/pro/bmi") not in counts
    assert ("POST", "/api/v1/pro/bmi/calculate") not in counts
    assert ("POST", "/api/v1/bmi/pro") not in counts


def test_register_bmi_routes_enabled_registers_pro_family_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FEATURE_BMI_PRO_ENABLED", "true")
    app = FastAPI()

    first = register_bmi_routes(app)
    second = register_bmi_routes(app)

    assert second is first
    assert first.feature_bmi_pro_enabled is True
    assert first.bmi_pro_router is not None
    assert first.bmi_pro_legacy_alias_router is not None
    counts = _route_counts(app)
    assert counts[("POST", "/api/v1/bmi/calculate")] == 1
    assert counts[("POST", "/api/v1/pro/bmi")] == 1
    assert counts[("POST", "/api/v1/pro/bmi/calculate")] == 1
    assert counts[("POST", "/api/v1/bmi/pro")] == 1


def test_register_bmi_routes_preserves_pro_dependency_and_alias_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FEATURE_BMI_PRO_ENABLED", "yes")
    app = FastAPI()

    register_bmi_routes(app)

    free_route = _route(app, "POST", "/api/v1/bmi/calculate")
    legacy_pro_route = _route(app, "POST", "/api/v1/pro/bmi")
    canonical_pro_route = _route(app, "POST", "/api/v1/pro/bmi/calculate")
    alias_route = _route(app, "POST", "/api/v1/bmi/pro")

    assert not route_has_dependency_call(free_route, require_pro_tier)
    assert legacy_pro_route.deprecated is True
    assert route_has_dependency_call(legacy_pro_route, require_pro_tier)
    assert route_has_dependency_call(canonical_pro_route, require_pro_tier)
    assert alias_route.deprecated is True
    assert alias_route.openapi_extra == {
        "x-alias-of": "/api/v1/pro/bmi",
        "x-migration-path": "Migrate to POST /api/v1/pro/bmi (same contract)",
    }
    assert route_has_dependency_call(alias_route, require_pro_tier)


def test_register_bmi_routes_rejects_empty_free_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.routers.bmi as bmi_module

    monkeypatch.setattr(bmi_module, "router", APIRouter())
    monkeypatch.delenv("FEATURE_BMI_PRO_ENABLED", raising=False)

    with pytest.raises(
        RuntimeError,
        match="BMI router from app\\.routers\\.bmi must be a non-empty APIRouter",
    ):
        register_bmi_routes(FastAPI())


def test_register_bmi_routes_reports_unexpected_source_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.routers.bmi as bmi_module

    router = APIRouter(prefix="/api/v1/bmi")

    async def _calculate() -> dict[str, str]:
        return {"status": "calculate"}

    async def _extra() -> dict[str, str]:
        return {"status": "extra"}

    router.post("/calculate")(_calculate)
    router.get("/extra")(_extra)
    monkeypatch.setattr(bmi_module, "router", router)
    monkeypatch.delenv("FEATURE_BMI_PRO_ENABLED", raising=False)

    with pytest.raises(
        RuntimeError,
        match=(
            "BMI router from app\\.routers\\.bmi route family mismatch: "
            "missing none; unexpected GET /api/v1/bmi/extra"
        ),
    ):
        register_bmi_routes(FastAPI())


def test_register_bmi_routes_rejects_foreign_existing_bmi_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FEATURE_BMI_PRO_ENABLED", raising=False)
    app = FastAPI()

    async def _shadow_bmi() -> dict[str, str]:
        return {"status": "shadow"}

    app.add_api_route("/api/v1/bmi/calculate", _shadow_bmi, methods=["POST"])

    with pytest.raises(
        RuntimeError,
        match="Duplicate /api/v1/bmi/calculate route detected with a different bmi handler",
    ):
        register_bmi_routes(app)


def test_register_bmi_routes_rejects_partial_existing_pro_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FEATURE_BMI_PRO_ENABLED", "on")
    app = FastAPI()

    async def _shadow_pro_bmi() -> dict[str, str]:
        return {"status": "shadow"}

    app.add_api_route("/api/v1/pro/bmi", _shadow_pro_bmi, methods=["POST"])

    with pytest.raises(RuntimeError, match="Partial bmi pro route registration detected"):
        register_bmi_routes(app)


def test_register_bmi_routes_rejects_unguarded_pro_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.routers.bmi_pro as bmi_pro_module

    monkeypatch.setenv("FEATURE_BMI_PRO_ENABLED", "true")
    monkeypatch.setattr(bmi_pro_module, "router", _unguarded_bmi_pro_router())

    with pytest.raises(
        RuntimeError,
        match="Existing /api/v1/pro/bmi route does not preserve bmi pro required dependency",
    ):
        register_bmi_routes(FastAPI())
