from __future__ import annotations

import logging
from collections import Counter

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import app.main as app_main
from app.bootstrap.route_family import route_has_dependency_call

_EXPECTED_TEST_ROUTE_KEYS = {
    (path, method) for path, method, _include_in_schema in app_main._TEST_ROUTE_SPECS
}
_EXPECTED_TEST_ROUTE_PATHS = {path for path, _method in _EXPECTED_TEST_ROUTE_KEYS}


@pytest.fixture(autouse=True)
def _clear_test_route_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("APP_ENV", "ENVIRONMENT", "ENV", "ENABLE_TEST_ROUTES"):
        monkeypatch.delenv(name, raising=False)


def _set_runtime_env(
    monkeypatch: pytest.MonkeyPatch,
    *,
    app_env: str | None = None,
    environment: str | None = None,
    enable_test_routes: str | None = None,
) -> None:
    if app_env is not None:
        monkeypatch.setenv("APP_ENV", app_env)
    if environment is not None:
        monkeypatch.setenv("ENVIRONMENT", environment)
    if enable_test_routes is not None:
        monkeypatch.setenv("ENABLE_TEST_ROUTES", enable_test_routes)


def _test_routes(target_app: FastAPI) -> list[APIRoute]:
    return [
        route
        for route in target_app.routes
        if isinstance(route, APIRoute) and str(route.path) in _EXPECTED_TEST_ROUTE_PATHS
    ]


def _registered_test_route_counts(target_app: FastAPI) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for route in _test_routes(target_app):
        for method in getattr(route, "methods", None) or set():
            key = (str(route.path), str(method).upper())
            if key in _EXPECTED_TEST_ROUTE_KEYS:
                counts[key] += 1
    return counts


def _assert_test_routes_registered_once(target_app: FastAPI) -> None:
    counts = _registered_test_route_counts(target_app)
    assert set(counts) == _EXPECTED_TEST_ROUTE_KEYS
    assert all(count == 1 for count in counts.values())

    for route in _test_routes(target_app):
        assert route.include_in_schema is False
        assert route_has_dependency_call(route, app_main.ensure_test_routes_non_production)


def _stub_test_router_without_dependencies() -> APIRouter:
    router = APIRouter()

    for path, method, include_in_schema in app_main._TEST_ROUTE_SPECS:

        async def _handler(route_path: str = path) -> dict[str, str]:
            return {"path": route_path}

        router.add_api_route(
            path,
            _handler,
            methods=[method],
            include_in_schema=include_in_schema,
        )

    return router


@pytest.mark.parametrize(
    ("app_env", "environment", "enable_test_routes", "expected_enabled"),
    [
        (None, None, None, True),
        ("local", None, None, True),
        ("dev", None, None, True),
        ("development", None, None, True),
        ("test", None, None, True),
        ("testing", None, None, True),
        ("ci", None, None, True),
        ("staging", None, "1", True),
        ("staging", None, None, False),
        ("staging", None, "true", False),
        ("production", None, "1", False),
        ("prod", None, "1", False),
        ("unexpected", None, "1", False),
        ("local", "production", "1", False),
        ("production", "test", "1", False),
    ],
)
def test_test_route_registration_env_matrix(
    monkeypatch: pytest.MonkeyPatch,
    app_env: str | None,
    environment: str | None,
    enable_test_routes: str | None,
    expected_enabled: bool,
) -> None:
    _set_runtime_env(
        monkeypatch,
        app_env=app_env,
        environment=environment,
        enable_test_routes=enable_test_routes,
    )
    target_app = FastAPI()

    assert app_main._test_routes_enabled_for_registration() is expected_enabled

    app_main._include_test_router_if_enabled(target_app)

    if expected_enabled:
        _assert_test_routes_registered_once(target_app)
    else:
        assert _test_routes(target_app) == []


def test_test_route_registration_is_idempotent_in_unset_local_env() -> None:
    target_app = FastAPI()

    app_main._include_test_router_if_enabled(target_app)
    app_main._include_test_router_if_enabled(target_app)

    _assert_test_routes_registered_once(target_app)


def test_staging_test_route_registration_logs_enabled_state(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _set_runtime_env(monkeypatch, app_env="staging", enable_test_routes="1")
    target_app = FastAPI()

    with caplog.at_level(logging.INFO, logger=app_main.logger.name):
        app_main._include_test_router_if_enabled(target_app)

    matching_records = [
        record
        for record in caplog.records
        if record.message == "Test routes enabled for registration"
    ]
    assert len(matching_records) == 1
    assert matching_records[0].runtime_env == "staging"
    assert matching_records[0].enable_test_routes == "1"
    _assert_test_routes_registered_once(target_app)


def test_registered_local_test_routes_fail_closed_after_production_env_flip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_app = FastAPI()
    app_main._include_test_router_if_enabled(target_app)

    monkeypatch.setenv("APP_ENV", "production")
    client = TestClient(target_app)

    response = client.get("/api/v1/test/health")

    assert response.status_code == 404


def test_registered_local_test_routes_fail_closed_after_staging_flag_removed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_app = FastAPI()
    app_main._include_test_router_if_enabled(target_app)

    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.delenv("ENABLE_TEST_ROUTES", raising=False)
    client = TestClient(target_app)

    response = client.post("/api/v1/test/rate-limit")

    assert response.status_code == 404


def test_test_router_source_specs_match_hidden_routes() -> None:
    route_specs: set[tuple[str, str, bool]] = set()
    for route in app_main.test_router.routes:
        assert isinstance(route, APIRoute)
        for method in route.methods or set():
            key = (str(route.path), str(method).upper())
            if key in _EXPECTED_TEST_ROUTE_KEYS:
                route_specs.add((str(route.path), str(method).upper(), route.include_in_schema))

    assert route_specs == set(app_main._TEST_ROUTE_SPECS)


def test_test_route_registration_rejects_partial_existing_family() -> None:
    target_app = FastAPI()
    path, method, include_in_schema = app_main._TEST_ROUTE_SPECS[0]

    async def _partial_test_route() -> dict[str, str]:
        return {"status": "partial"}

    target_app.add_api_route(
        path,
        _partial_test_route,
        methods=[method],
        include_in_schema=include_in_schema,
    )

    with pytest.raises(RuntimeError, match="Partial test route registration detected"):
        app_main._include_test_router_if_enabled(target_app)


def test_test_route_registration_rejects_foreign_handlers() -> None:
    target_app = FastAPI()

    for path, method, include_in_schema in app_main._TEST_ROUTE_SPECS:

        async def _foreign_test_route(route_path: str = path) -> dict[str, str]:
            return {"path": route_path}

        target_app.add_api_route(
            path,
            _foreign_test_route,
            methods=[method],
            include_in_schema=include_in_schema,
        )

    with pytest.raises(
        RuntimeError,
        match="Duplicate .* route detected with a different test handler",
    ):
        app_main._include_test_router_if_enabled(target_app)


def test_test_route_registration_rejects_source_visibility_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_route = next(iter(app_main.test_router.routes))
    assert isinstance(source_route, APIRoute)
    monkeypatch.setattr(source_route, "include_in_schema", True)

    with pytest.raises(RuntimeError, match="Test router does not preserve OpenAPI visibility"):
        app_main._include_test_router_if_enabled(FastAPI())


def test_test_route_registration_rejects_missing_request_time_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_main, "test_router", _stub_test_router_without_dependencies())

    with pytest.raises(
        RuntimeError,
        match="Existing .* route does not preserve test required dependency",
    ):
        app_main._include_test_router_if_enabled(FastAPI())


def test_enabled_test_routes_stay_hidden_from_openapi() -> None:
    target_app = FastAPI()
    app_main._include_test_router_if_enabled(target_app)

    paths = set(target_app.openapi().get("paths", {}))

    assert paths.isdisjoint(_EXPECTED_TEST_ROUTE_PATHS)
