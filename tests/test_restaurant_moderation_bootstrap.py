from __future__ import annotations

from collections.abc import Generator, Mapping
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.bootstrap.route_family import route_has_dependency_call
import app.main as app_main
from app.routers import restaurants

_STATUS_PATH = restaurants.RESTAURANT_MODERATION_STATUS_PATH


@dataclass
class _ApiStore:
    review_response: Mapping[str, Any] | None = None
    review_error: Exception | None = None
    review_calls: int = 0

    def review_submission(
        self,
        submission_id: str,
        *,
        status: str,
        reviewer_notes: str | None,
    ) -> Mapping[str, Any] | None:
        self.review_calls += 1
        if self.review_error is not None:
            raise self.review_error
        return self.review_response


@pytest.fixture
def _moderation_client(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("API_KEY", "test_key")
    try:
        yield client
    finally:
        client.app.dependency_overrides.pop(restaurants.get_restaurant_store, None)


def _submission_row(status: str = "approved") -> dict[str, Any]:
    return {
        "id": "s1",
        "entity_type": "restaurant_menu",
        "canonical_name": "Protein Burger",
        "barcode": None,
        "off_url": None,
        "payload": {"kcal": 540},
        "status": status,
        "reviewer_notes": "ok",
        "created_at": "2026-02-24T00:00:00+00:00",
        "updated_at": "2026-02-24T00:05:00+00:00",
        "audit": [],
    }


def _matching_moderation_routes(target_app: FastAPI) -> list[APIRoute]:
    return [
        route
        for route in target_app.routes
        if isinstance(route, APIRoute)
        and route.path == _STATUS_PATH
        and "PATCH" in (route.methods or set())
    ]


def _register_moderation(target_app: FastAPI) -> None:
    app_main._include_restaurant_moderation_router_if_needed(target_app)


def _router_with_moderation_route(
    *,
    method: str = "PATCH",
    include_in_schema: bool = False,
    responses: dict[int, dict[str, str]] | None = None,
    include_unexpected: bool = False,
) -> APIRouter:
    router = APIRouter(tags=["restaurants"])

    async def _handler() -> dict[str, str]:
        return {"status": "ok"}

    router.add_api_route(
        _STATUS_PATH,
        _handler,
        methods=[method],
        include_in_schema=include_in_schema,
        responses=(
            {
                404: {"description": "Submission not found"},
                422: {"description": "Invalid transition"},
            }
            if responses is None
            else responses
        ),
    )
    if include_unexpected:

        async def _unexpected() -> dict[str, str]:
            return {"status": "unexpected"}

        router.get("/api/v1/restaurants/submissions/unexpected")(_unexpected)
    return router


def test_restaurant_moderation_registration_is_canonical_and_idempotent() -> None:
    app = FastAPI()

    _register_moderation(app)
    _register_moderation(app)

    routes = _matching_moderation_routes(app)
    assert len(routes) == 1
    route = routes[0]
    assert route.endpoint.__module__ == "app.routers.restaurants"
    assert route.endpoint.__qualname__ == "review_restaurant_submission"
    assert route.include_in_schema is False
    assert set(route.responses) == {404, 422}
    assert route_has_dependency_call(route, app_main._legacy_module._get_api_key_dynamic)
    assert _STATUS_PATH not in app.openapi().get("paths", {})


def test_live_app_keeps_restaurant_moderation_route_hidden_and_protected() -> None:
    routes = _matching_moderation_routes(app_main.app)

    assert len(routes) == 1
    route = routes[0]
    assert route.include_in_schema is False
    assert set(route.responses) == {404, 422}
    assert route_has_dependency_call(route, app_main._legacy_module._get_api_key_dynamic)
    assert _STATUS_PATH not in app_main.app.openapi().get("paths", {})


def test_restaurant_moderation_registration_rejects_missing_api_key_dependency_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_main._legacy_module, "_get_api_key_dynamic", None)

    with pytest.raises(
        RuntimeError,
        match="Restaurant moderation API key dependency is unavailable",
    ):
        _register_moderation(FastAPI())


def test_restaurant_moderation_registration_rejects_source_visibility_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app_main,
        "restaurant_moderation_router",
        _router_with_moderation_route(include_in_schema=True),
    )

    with pytest.raises(
        RuntimeError,
        match="Restaurant moderation router does not preserve OpenAPI visibility",
    ):
        _register_moderation(FastAPI())


def test_restaurant_moderation_registration_rejects_missing_response_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app_main,
        "restaurant_moderation_router",
        _router_with_moderation_route(responses={404: {"description": "Submission not found"}}),
    )

    with pytest.raises(
        RuntimeError,
        match="Restaurant moderation router does not preserve 422 response metadata",
    ):
        _register_moderation(FastAPI())


def test_restaurant_moderation_registration_rejects_unexpected_source_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app_main,
        "restaurant_moderation_router",
        _router_with_moderation_route(include_unexpected=True),
    )

    with pytest.raises(
        RuntimeError,
        match="Restaurant moderation router does not define the expected route family",
    ):
        _register_moderation(FastAPI())


def test_restaurant_moderation_registration_rejects_wrong_method_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app_main,
        "restaurant_moderation_router",
        _router_with_moderation_route(method="GET"),
    )

    with pytest.raises(
        RuntimeError,
        match="Restaurant moderation router does not define the expected route family",
    ):
        _register_moderation(FastAPI())


def test_restaurant_moderation_registration_rejects_partial_existing_state() -> None:
    app = FastAPI()

    async def _existing_get() -> dict[str, str]:
        return {"status": "partial"}

    app.get(_STATUS_PATH, include_in_schema=False)(_existing_get)

    with pytest.raises(
        RuntimeError,
        match="Partial restaurant moderation route registration detected",
    ):
        _register_moderation(app)


def test_restaurant_moderation_registration_rejects_existing_foreign_handler() -> None:
    app = FastAPI()

    async def _foreign_handler() -> dict[str, str]:
        return {"status": "foreign"}

    app.patch(
        _STATUS_PATH,
        include_in_schema=False,
        responses={
            404: {"description": "Submission not found"},
            422: {"description": "Invalid transition"},
        },
        dependencies=[Depends(app_main._legacy_module._get_api_key_dynamic)],
    )(_foreign_handler)

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different restaurant moderation handler",
    ):
        _register_moderation(app)


def test_restaurant_moderation_registration_rejects_existing_missing_dependency() -> None:
    app = FastAPI()
    app.include_router(app_main.restaurant_moderation_router)

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve restaurant moderation required dependency",
    ):
        _register_moderation(app)


def test_restaurant_moderation_route_rejects_missing_and_wrong_api_key(
    _moderation_client: TestClient,
) -> None:
    store = _ApiStore(review_response=_submission_row())
    _moderation_client.app.dependency_overrides[restaurants.get_restaurant_store] = lambda: store

    missing_response = _moderation_client.patch(
        "/api/v1/restaurants/submissions/s1/status",
        json={"status": "approved"},
    )
    wrong_response = _moderation_client.patch(
        "/api/v1/restaurants/submissions/s1/status",
        json={"status": "approved"},
        headers={"X-API-Key": "wrong"},
    )

    assert missing_response.status_code == 403
    assert wrong_response.status_code == 403
    assert store.review_calls == 0


def test_restaurant_moderation_route_valid_key_preserves_404_and_422_behavior(
    _moderation_client: TestClient,
) -> None:
    store = _ApiStore(review_response=None)
    _moderation_client.app.dependency_overrides[restaurants.get_restaurant_store] = lambda: store

    missing_response = _moderation_client.patch(
        "/api/v1/restaurants/submissions/missing/status",
        json={"status": "approved"},
        headers={"X-API-Key": "test_key"},
    )
    store.review_error = ValueError("internal transition detail")
    invalid_transition_response = _moderation_client.patch(
        "/api/v1/restaurants/submissions/s1/status",
        json={"status": "approved"},
        headers={"X-API-Key": "test_key"},
    )

    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "Submission not found"
    assert invalid_transition_response.status_code == 422
    assert invalid_transition_response.json()["detail"] == "Invalid submission transition"


@pytest.mark.parametrize("status_value", ("approved", "rejected"))
def test_restaurant_moderation_route_valid_key_preserves_success_behavior(
    _moderation_client: TestClient,
    status_value: str,
) -> None:
    store = _ApiStore(review_response=_submission_row(status=status_value))
    _moderation_client.app.dependency_overrides[restaurants.get_restaurant_store] = lambda: store

    response = _moderation_client.patch(
        "/api/v1/restaurants/submissions/s1/status",
        json={"status": status_value, "reviewer_notes": "ok"},
        headers={"X-API-Key": "test_key"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == "s1"
    assert response.json()["status"] == status_value
    assert store.review_calls == 1
