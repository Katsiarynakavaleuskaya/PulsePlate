from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import textwrap
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from pydantic import BaseModel
import pytest

import app.bootstrap.openapi as openapi_policy
from app.effective_routes import iter_effective_route_candidates, route_path


class _PublicResponse(BaseModel):
    value: str


def _public_app() -> FastAPI:
    target_app = FastAPI(
        title="Custom title",
        version="9.1",
        summary="Custom summary",
        description="Custom description",
        terms_of_service="https://example.com/terms",
        contact={"name": "Support", "url": "https://example.com"},
        license_info={"name": "MIT"},
        openapi_tags=[{"name": "pro", "description": "PRO"}],
        servers=[{"url": "https://api.example.com"}],
        openapi_external_docs={"description": "External", "url": "https://example.com/docs"},
        separate_input_output_schemas=False,
    )
    target_app.openapi_version = "3.0.2"

    @target_app.get("/api/v1/pro/example", response_model=_PublicResponse, tags=["pro"])
    async def _example() -> _PublicResponse:
        return _PublicResponse(value="ok")

    return target_app


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/api/v1/bmi", True),
        ("/api/v1/insight", True),
        ("/api/v1/pro/example", True),
        ("/api/v1/vip/example", True),
        ("/api/v1/billing/example", True),
        ("/api/v1/pro", False),
        ("/api/v1/proevil/example", False),
        ("/api/v1/users", False),
        ("/health", False),
    ],
)
def test_public_openapi_path_policy_is_exact(path: str, expected: bool) -> None:
    assert openapi_policy._is_openapi_public_path(path) is expected


def test_canonical_builder_mirrors_fastapi_metadata_inputs() -> None:
    target_app = _public_app()
    openapi_policy.install_canonical_openapi_builder(target_app)

    schema = target_app.openapi()

    assert schema["openapi"] == "3.0.2"
    assert schema["info"]["title"] == "Custom title"
    assert schema["info"]["summary"] == "Custom summary"
    assert schema["info"]["termsOfService"] == "https://example.com/terms"
    assert schema["servers"] == [{"url": "https://api.example.com"}]
    assert schema["externalDocs"]["description"] == "External"
    assert "/api/v1/pro/example" in schema["paths"]


def test_first_install_replaces_unknown_early_cache_and_stays_lazy_without_cache() -> None:
    target_app = _public_app()
    unknown_cache = {"openapi": "3.0.0", "paths": {"/internal/secret": {}}}
    target_app.openapi_schema = unknown_cache

    openapi_policy.install_canonical_openapi_builder(target_app)

    assert target_app.openapi_schema is not unknown_cache
    assert "/internal/secret" not in target_app.openapi_schema["paths"]

    lazy_app = _public_app()
    openapi_policy.install_canonical_openapi_builder(lazy_app)
    assert lazy_app.openapi_schema is None
    assert lazy_app.openapi() is lazy_app.openapi_schema


def test_canonical_reinstall_preserves_equal_cache_and_replaces_public_drift() -> None:
    target_app = _public_app()
    openapi_policy.install_canonical_openapi_builder(target_app)
    first_schema = target_app.openapi()
    first_builder = target_app.openapi

    openapi_policy.install_canonical_openapi_builder(target_app)
    assert target_app.openapi_schema is first_schema
    assert target_app.openapi is first_builder

    @target_app.get("/api/v1/pro/late")
    async def _late() -> dict[str, str]:
        return {"status": "late"}

    openapi_policy.install_canonical_openapi_builder(target_app)

    assert target_app.openapi_schema is not first_schema
    assert "/api/v1/pro/late" in target_app.openapi_schema["paths"]


def test_hidden_or_disallowed_route_invalidates_equal_filtered_cache() -> None:
    target_app = _public_app()
    openapi_policy.install_canonical_openapi_builder(target_app)
    first_schema = target_app.openapi()

    @target_app.get("/internal/hidden", include_in_schema=False)
    async def _hidden() -> dict[str, str]:
        return {"status": "hidden"}

    @target_app.get("/outside/policy")
    async def _outside() -> dict[str, str]:
        return {"status": "outside"}

    openapi_policy.install_canonical_openapi_builder(target_app)

    assert target_app.openapi_schema is not first_schema
    assert target_app.openapi_schema == first_schema


def test_request_time_builder_regenerates_only_after_recursive_route_version_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_app = _public_app()
    calls = 0
    original_generate = openapi_policy._generate_canonical_openapi

    def _counted_generate(app: FastAPI) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return original_generate(app)

    monkeypatch.setattr(openapi_policy, "_generate_canonical_openapi", _counted_generate)
    openapi_policy.install_canonical_openapi_builder(target_app)

    first = target_app.openapi()
    assert target_app.openapi() is first
    assert calls == 1

    @target_app.get("/api/v1/pro/versioned")
    async def _versioned() -> dict[str, str]:
        return {"status": "versioned"}

    second = target_app.openapi()
    assert second is not first
    assert "/api/v1/pro/versioned" in second["paths"]
    assert target_app.openapi() is second
    assert calls == 2


def test_request_time_builder_regenerates_after_visibility_and_metadata_changes() -> None:
    target_app = _public_app()
    openapi_policy.install_canonical_openapi_builder(target_app)
    first = target_app.openapi()
    public_route = next(
        route
        for route in target_app.routes
        if getattr(route, "path", None) == "/api/v1/pro/example"
    )
    assert isinstance(public_route, APIRoute)

    public_route.include_in_schema = False
    second = target_app.openapi()

    assert second is not first
    assert "/api/v1/pro/example" not in second["paths"]

    target_app.title = "Updated title"
    third = target_app.openapi()

    assert third is not second
    assert third["info"]["title"] == "Updated title"
    assert target_app.openapi() is third


@pytest.mark.parametrize(
    ("field", "value", "schema_key", "expected"),
    [
        ("operation_id", "updatedOperationId", "operationId", "updatedOperationId"),
        ("openapi_extra", {"x-cache-contract": "updated"}, "x-cache-contract", "updated"),
    ],
)
def test_request_time_builder_regenerates_after_schema_route_metadata_changes(
    field: str,
    value: object,
    schema_key: str,
    expected: str,
) -> None:
    target_app = _public_app()
    openapi_policy.install_canonical_openapi_builder(target_app)
    first = target_app.openapi()
    public_route = next(
        route
        for route in target_app.routes
        if getattr(route, "path", None) == "/api/v1/pro/example"
    )
    assert isinstance(public_route, APIRoute)

    setattr(public_route, field, value)
    second = target_app.openapi()

    assert second is not first
    assert second["paths"]["/api/v1/pro/example"]["get"][schema_key] == expected
    assert target_app.openapi() is second


def test_request_time_builder_regenerates_after_public_policy_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_app = _public_app()

    @target_app.get("/future-public")
    async def _future_public() -> dict[str, str]:
        return {"status": "future"}

    openapi_policy.install_canonical_openapi_builder(target_app)
    first = target_app.openapi()
    assert "/future-public" not in first["paths"]

    monkeypatch.setattr(
        openapi_policy,
        "PUBLIC_OPENAPI_POLICY",
        openapi_policy.PublicOpenAPIPolicy(
            allowed_prefixes=openapi_policy.PUBLIC_OPENAPI_POLICY.allowed_prefixes,
            allowed_exact=(openapi_policy.PUBLIC_OPENAPI_POLICY.allowed_exact | {"/future-public"}),
        ),
    )

    second = target_app.openapi()

    assert second is not first
    assert "/future-public" in second["paths"]


def test_request_time_builder_fingerprints_included_router_visibility() -> None:
    router = APIRouter()

    @router.get("/api/v1/pro/included")
    async def _included() -> dict[str, str]:
        return {"status": "included"}

    target_app = FastAPI()
    target_app.include_router(router)
    openapi_policy.install_canonical_openapi_builder(target_app)
    first = target_app.openapi()
    effective_route = next(
        route
        for route in iter_effective_route_candidates(target_app.routes)
        if route_path(route) == "/api/v1/pro/included"
    )

    effective_route.include_in_schema = False
    second = target_app.openapi()

    assert second is not first
    assert "/api/v1/pro/included" not in second["paths"]


def test_builder_state_matrix_rejects_partial_foreign_and_wrong_app_states() -> None:
    target_app = FastAPI()

    def foreign() -> dict[str, str]:
        return {"openapi": "3.1.0"}

    setattr(target_app, "openapi", foreign)
    with pytest.raises(RuntimeError, match="foreign_builder"):
        openapi_policy.validate_openapi_builder_state(target_app)

    target_app = FastAPI()
    target_app.state._canonical_openapi_builder_installed = True
    with pytest.raises(RuntimeError, match="stale_legacy_marker"):
        openapi_policy.validate_openapi_builder_state(target_app)

    target_app = FastAPI()
    target_app.state._canonical_openapi_builder = None
    with pytest.raises(RuntimeError, match="canonical_marker_invalid"):
        openapi_policy.validate_openapi_builder_state(target_app)

    target_app = FastAPI()
    openapi_policy.install_canonical_openapi_builder(target_app)
    target_app.state._canonical_openapi_builder_installed = True
    with pytest.raises(RuntimeError, match="stale_legacy_marker"):
        openapi_policy.validate_openapi_builder_state(target_app)

    target_app = FastAPI()
    openapi_policy.install_canonical_openapi_builder(target_app)
    delattr(target_app.state, "_canonical_openapi_builder")
    with pytest.raises(RuntimeError, match="foreign_builder"):
        openapi_policy.validate_openapi_builder_state(target_app)

    target_app = FastAPI()
    openapi_policy.install_canonical_openapi_builder(target_app)
    marker = target_app.state._canonical_openapi_builder
    setattr(target_app, "openapi", foreign)
    with pytest.raises(RuntimeError, match="live_marker_mismatch"):
        openapi_policy.validate_openapi_builder_state(target_app)

    other_app = FastAPI()
    setattr(other_app, "openapi", marker)
    other_app.state._canonical_openapi_builder = marker
    with pytest.raises(RuntimeError, match="canonical_binding_invalid"):
        openapi_policy.validate_openapi_builder_state(other_app)

    target_app = FastAPI()
    openapi_policy.install_canonical_openapi_builder(target_app)
    target_app.openapi._pulseplate_openapi_builder_protocol = 1
    with pytest.raises(RuntimeError, match="canonical_binding_invalid"):
        openapi_policy.validate_openapi_builder_state(target_app)


@pytest.mark.parametrize(
    ("tracker", "expected_error"),
    [
        (None, "route_version_unavailable"),
        (lambda: "invalid", "route_version_invalid"),
    ],
)
def test_installer_rejects_invalid_route_version_tracker(
    monkeypatch: pytest.MonkeyPatch,
    tracker: object,
    expected_error: str,
) -> None:
    target_app = FastAPI()
    monkeypatch.setattr(target_app.router, "_get_routes_version", tracker)

    with pytest.raises(RuntimeError, match=expected_error):
        openapi_policy.install_canonical_openapi_builder(target_app)

    assert openapi_policy._is_default_openapi_builder(target_app, target_app.openapi)
    assert not hasattr(target_app.state, "_canonical_openapi_builder")


def test_installer_rejects_unserializable_openapi_inputs_atomically() -> None:
    target_app = FastAPI()
    target_app.openapi_tags = [{"name": object()}]

    with pytest.raises(
        RuntimeError,
        match="input_fingerprint_unserializable",
    ) as exc_info:
        openapi_policy.install_canonical_openapi_builder(target_app)

    assert isinstance(exc_info.value.__cause__, TypeError)
    assert openapi_policy._is_default_openapi_builder(target_app, target_app.openapi)
    assert not hasattr(target_app.state, "_canonical_openapi_builder")


def test_same_name_foreign_builder_is_rejected() -> None:
    target_app = FastAPI()

    class _ForeignBuilder:
        _pulseplate_openapi_builder_protocol = 1

        def __init__(self, app: FastAPI) -> None:
            self._pulseplate_target_app = app

        def __call__(self) -> dict[str, Any]:
            return {"openapi": "3.1.0"}

    _ForeignBuilder.__module__ = openapi_policy.__name__
    _ForeignBuilder.__qualname__ = "_CanonicalOpenAPIBuilder"
    foreign = _ForeignBuilder(target_app)
    setattr(target_app, "openapi", foreign)
    target_app.state._canonical_openapi_builder = foreign

    with pytest.raises(RuntimeError, match="canonical_binding_invalid"):
        openapi_policy.validate_openapi_builder_state(target_app)


def test_reload_equivalent_builder_is_replaced_without_cache_churn() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = textwrap.dedent("""
        import importlib

        from fastapi import FastAPI

        import app.bootstrap.openapi as policy


        target_app = FastAPI()
        policy.install_canonical_openapi_builder(target_app)
        original_builder = target_app.openapi
        original_schema = target_app.openapi()

        reloaded_policy = importlib.reload(policy)
        reloaded_policy.validate_openapi_builder_state(target_app)
        reloaded_policy.install_canonical_openapi_builder(target_app)

        assert target_app.openapi is not original_builder
        assert type(target_app.openapi) is reloaded_policy._CanonicalOpenAPIBuilder
        assert target_app.openapi_schema is original_schema
        assert target_app.state._canonical_openapi_builder is target_app.openapi
        """)

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_installer_generation_failure_is_atomic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_app = _public_app()
    openapi_policy.install_canonical_openapi_builder(target_app)
    original_builder = target_app.openapi
    original_marker = target_app.state._canonical_openapi_builder
    original_schema = target_app.openapi()

    def _fail_generation(app: FastAPI) -> dict[str, Any]:
        raise RuntimeError("sentinel generation failure")

    monkeypatch.setattr(openapi_policy, "_generate_canonical_openapi", _fail_generation)
    with pytest.raises(RuntimeError, match="sentinel generation failure"):
        openapi_policy.install_canonical_openapi_builder(target_app)

    assert target_app.openapi is original_builder
    assert target_app.state._canonical_openapi_builder is original_marker
    assert target_app.openapi_schema is original_schema


def test_users_policy_hides_effective_and_original_route_without_clearing_cache() -> None:
    router = APIRouter()

    @router.get("/api/v1/users/{user_id}", tags=["users"])
    async def _user(user_id: int) -> dict[str, int]:
        return {"user_id": user_id}

    target_app = FastAPI(
        description="FREE: food search, user management\nUser management endpoints (FREE tier)",
        openapi_tags=[
            {"name": "users", "description": "Users"},
            {"name": "pro", "description": "PRO"},
        ],
    )
    target_app.include_router(router)
    sentinel_cache = {"openapi": "3.1.0", "paths": {}}
    target_app.openapi_schema = sentinel_cache
    effective_route = next(
        route
        for route in iter_effective_route_candidates(target_app.routes)
        if route_path(route).startswith("/api/v1/users")
    )

    assert openapi_policy.apply_public_openapi_input_policy(target_app) is True
    assert effective_route.include_in_schema is False
    assert effective_route.original_route.include_in_schema is False
    assert target_app.openapi_schema is sentinel_cache
    assert [tag["name"] for tag in target_app.openapi_tags or []] == ["pro"]
    assert "user management" not in target_app.description
    assert "User management endpoints" not in target_app.description
    assert openapi_policy.apply_public_openapi_input_policy(target_app) is False

    target_app.router._get_routes_version()
    fresh_effective = next(
        route
        for route in iter_effective_route_candidates(target_app.routes)
        if route_path(route).startswith("/api/v1/users")
    )
    assert fresh_effective.include_in_schema is False


def test_independent_apps_never_share_builder_or_cache() -> None:
    first_app = _public_app()
    second_app = _public_app()
    openapi_policy.install_canonical_openapi_builder(first_app)
    openapi_policy.install_canonical_openapi_builder(second_app)

    assert first_app.openapi is not second_app.openapi
    assert first_app.openapi() is not second_app.openapi()


def test_schema_pruning_keeps_recursive_refs_and_drops_orphans() -> None:
    schema: dict[str, Any] = {
        "paths": {
            "/api/v1/pro/example": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Public"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Public": {"$ref": "#/components/schemas/Nested"},
                "Nested": {"$ref": "#/components/schemas/Public"},
                "Orphan": {"type": "object"},
                "Broken": "not-a-dict",
            }
        },
    }

    openapi_policy._prune_unreferenced_schema_components(schema)

    assert set(schema["components"]["schemas"]) == {"Public", "Nested"}


def test_openapi_webhooks_fail_closed() -> None:
    target_app = _public_app()

    @target_app.webhooks.post("new-subscription")
    async def _webhook() -> None:
        return None

    with pytest.raises(RuntimeError, match="webhooks_not_supported"):
        openapi_policy.validate_openapi_builder_state(target_app)
    with pytest.raises(RuntimeError, match="webhooks_not_supported"):
        openapi_policy.install_canonical_openapi_builder(target_app)


def test_warm_openapi_cache_still_rejects_late_webhooks() -> None:
    target_app = _public_app()
    openapi_policy.install_canonical_openapi_builder(target_app)
    cached_schema = target_app.openapi()

    @target_app.webhooks.post("new-subscription")
    async def _webhook() -> None:
        return None

    with pytest.raises(RuntimeError, match="webhooks_not_supported"):
        target_app.openapi()

    assert target_app.openapi_schema is cached_schema
