# -*- coding: utf-8 -*-
"""
Combined app endpoint tests: health, monitoring, root, and package shim edges.

RU: Объединенные тесты для app эндпоинтов: health, monitoring, root и package shim edges
EN: Combined tests for app endpoints: health, monitoring, root and package shim edges

These are "easy coverage" tests that cover basic monitoring endpoints and app package behavior.
"""

import asyncio
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any, cast
from xml.etree import ElementTree
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app as apppkg
from app.effective_routes import (
    is_api_route_candidate,
    iter_effective_route_candidates,
    route_endpoint,
    route_include_in_schema,
    route_methods,
    route_path,
)
from app.routers import health as health_router
from app.routers.admin_operations import ADMIN_OPERATION_ROUTE_SPECS
from app.services import admin_operations as admin_operations_service
from app.routers.legal import build_terms_endpoint_payload
from app.bootstrap import public_discovery
from core.compliance import build_privacy_endpoint_payload
import pytest


def _find_route(client: TestClient, path: str, method: str = "GET") -> object:
    app = cast(FastAPI, client.app)
    matches = [
        route
        for route in iter_effective_route_candidates(app.routes)
        if is_api_route_candidate(route)
        and route_path(route) == path
        and method.upper() in route_methods(route)
    ]
    assert len(matches) == 1
    return matches[0]


class TestHealthAndMonitoringEndpoints:
    """Test health and monitoring endpoints for easy coverage boost"""

    def test_health_ok(self, client: TestClient) -> None:
        """Test /health endpoint returns status ok"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        # Verify new fields exist (version, git_sha, timestamp, environment)
        assert {"version", "git_sha", "timestamp", "environment"}.issubset(data.keys())

    def test_v1_health_ok(self, client: TestClient) -> None:
        """Test /api/v1/health endpoint returns status ok"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        # Verify new fields exist (version, git_sha, timestamp, environment)
        assert {"version", "git_sha", "timestamp", "environment"}.issubset(data.keys())

    def test_health_routes_are_owned_by_canonical_router(self, client: TestClient) -> None:
        """Operational health/readiness routes are served by app.routers.health."""
        for path in ("/health", "/api/v1/health", "/health/db", "/ready"):
            route = _find_route(client, path)
            assert getattr(route_endpoint(route), "__module__", None) == "app.routers.health"

    def test_health_routes_stay_hidden_from_public_openapi(self, client: TestClient) -> None:
        """Health/readiness routes remain runtime-only, not public OpenAPI paths."""
        app = cast(FastAPI, client.app)
        paths = app.openapi()["paths"]

        assert "/health" not in paths
        assert "/api/v1/health" not in paths
        assert "/health/db" not in paths
        assert "/ready" not in paths

    def test_database_health_rejects_degraded_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """DB degraded mode keeps the readiness failure contract."""
        monkeypatch.setenv("DB_HEALTH_DEGRADED", "1")

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(health_router.database_health(session=cast(Session, object())))

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail == "Database unavailable"

    def test_database_health_rejects_session_without_execute(self) -> None:
        """DB readiness fails closed when the session cannot execute SQL."""

        class _NoExecuteSession:
            bind = object()

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(health_router.database_health(session=cast(Session, _NoExecuteSession())))

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail == "Database unavailable"

    def test_database_health_rejects_unbound_session(self) -> None:
        """DB readiness fails closed when the session has no bound engine."""

        class _UnboundSession:
            bind = None

            def execute(self, query: object) -> None:
                raise AssertionError(f"unexpected execute call: {query!r}")

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(health_router.database_health(session=cast(Session, _UnboundSession())))

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail == "Database unavailable"

    @pytest.mark.skipif(
        os.getenv("METRICS_ENABLED", "true").lower() != "true",
        reason="Metrics disabled in this build",
    )
    def test_metrics_endpoint(self, client: TestClient) -> None:
        """Test /metrics endpoint - returns Prometheus metrics or error"""
        response = client.get("/metrics")
        assert response.status_code == 200
        # Either Prometheus metrics or error message about unavailable client
        content = response.text
        assert (
            "python_gc_objects_collected_total" in content
            or "Prometheus client not available" in content
        )

    def test_root_returns_direct_api_probe(self, client: TestClient) -> None:
        """Test GET / returns JSON when hitting FastAPI directly (Caddy serves SPA at apex)."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert data["surface"] == "api"

    def test_legacy_bmi_page_renders(self, client: TestClient) -> None:
        """Legacy HTML BMI calculator remains on /legacy/bmi-calculator."""
        response = client.get("/legacy/bmi-calculator")
        assert response.status_code == 200
        content = response.text
        assert "<title" in content
        assert "BMI Calculator" in content
        assert "form" in content.lower()

    def test_sitemap_endpoint_serves_public_routes(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test /sitemap.xml serves the canonical public discovery surface."""
        monkeypatch.delenv("PRODUCTION_DOMAIN", raising=False)

        response = client.get("/sitemap.xml")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/xml")

        sitemap_root = ElementTree.fromstring(response.text)
        namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        loc_values = {
            loc.text
            for loc in sitemap_root.findall("sitemap:url/sitemap:loc", namespace)
            if loc.text is not None
        }
        assert loc_values == {
            "http://testserver/",
            "http://testserver/privacy",
            "http://testserver/terms",
            "http://testserver/legacy/bmi-calculator",
        }

    def test_sitemap_endpoint_prefers_configured_production_domain(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Configured production host wins over direct-origin/testserver hostnames."""
        monkeypatch.setenv("PRODUCTION_DOMAIN", "pulseplate.app")

        response = client.get("/sitemap.xml")

        assert response.status_code == 200
        sitemap_root = ElementTree.fromstring(response.text)
        namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        loc_values = {
            loc.text
            for loc in sitemap_root.findall("sitemap:url/sitemap:loc", namespace)
            if loc.text is not None
        }
        assert loc_values == {
            "https://pulseplate.app/",
            "https://pulseplate.app/privacy",
            "https://pulseplate.app/terms",
            "https://pulseplate.app/legacy/bmi-calculator",
        }

    def test_favicon_endpoint(self, client: TestClient) -> None:
        """Runtime favicon is canonical, empty, and hidden from public OpenAPI."""
        route = _find_route(client, "/favicon.ico")
        endpoint = route_endpoint(route)
        assert getattr(endpoint, "__module__", None) == "app.routers.favicon"
        assert getattr(endpoint, "__name__", None) == "favicon"
        assert route_include_in_schema(route) is False
        source_route = getattr(route, "original_route", route)
        dependant = getattr(source_route, "dependant", None)
        assert not getattr(dependant, "dependencies", ())

        response = client.get("/favicon.ico")
        assert response.status_code == 204
        assert response.content == b""

        app = cast(FastAPI, client.app)
        assert "/favicon.ico" not in app.openapi()["paths"]

    def test_privacy_endpoint(self, client: TestClient) -> None:
        """Test /privacy endpoint returns canonical legal publication payload."""
        response = client.get("/privacy")
        assert response.status_code == 200
        assert response.headers["content-type"].lower().startswith("application/json")

        assert response.json() == jsonable_encoder(build_privacy_endpoint_payload())

    def test_terms_endpoint(self, client: TestClient) -> None:
        """Test /terms endpoint returns canonical legal publication payload."""
        response = client.get("/terms")
        assert response.status_code == 200
        assert response.headers["content-type"].lower().startswith("application/json")

        assert response.json() == build_terms_endpoint_payload().model_dump()

    def test_legal_routes_are_owned_by_canonical_router(self, client: TestClient) -> None:
        """/privacy and /terms are served by app.routers.legal, not legacy_app."""
        for path in ("/privacy", "/terms"):
            route = _find_route(client, path)
            assert getattr(route_endpoint(route), "__module__", None) == "app.routers.legal"

    def test_legal_routes_stay_hidden_from_public_openapi(self, client: TestClient) -> None:
        """Legal publication routes remain runtime-only, not public OpenAPI paths."""
        app = cast(FastAPI, client.app)
        paths = app.openapi()["paths"]

        assert "/privacy" not in paths
        assert "/terms" not in paths


class TestDebugEndpoint:
    """Test debug endpoints for development"""

    def test_debug_env_endpoint(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test /debug_env returns environment info"""
        monkeypatch.setenv("ENABLE_DEBUG_ENDPOINT", "true")

        route = _find_route(client, "/debug_env")
        assert getattr(route_endpoint(route), "__module__", None) == "app.routers.admin_operations"
        assert route_include_in_schema(route) is False

        response = client.get("/debug_env")
        assert response.status_code == 200
        data = response.json()
        assert set(data) == {
            "FEATURE_INSIGHT",
            "LLM_PROVIDER",
            "PERPLEXITY_MODEL",
            "PERPLEXITY_ENDPOINT",
            "insight_enabled",
        }

    def test_debug_env_fails_closed_in_production_like_env(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("ENABLE_DEBUG_ENDPOINT", raising=False)

        response = client.get("/debug_env")

        assert response.status_code == 404
        assert response.json() == {"detail": "Not found"}

    def test_admin_debug_operational_routes_are_owned_by_canonical_router(
        self,
        client: TestClient,
    ) -> None:
        for path, method in ADMIN_OPERATION_ROUTE_SPECS:
            route = _find_route(client, path, method)
            assert (
                getattr(route_endpoint(route), "__module__", None) == "app.routers.admin_operations"
            )
            assert route_include_in_schema(route) is False

    def test_admin_debug_operational_routes_stay_hidden_from_public_openapi(
        self,
        client: TestClient,
    ) -> None:
        app = cast(FastAPI, client.app)
        paths = app.openapi()["paths"]

        for path, _method in ADMIN_OPERATION_ROUTE_SPECS:
            assert path not in paths


class TestAdminOperationsService:
    """Focused service coverage for canonical hidden admin/debug route logic."""

    def test_cleanup_logs_route_accepts_valid_api_key(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("API_KEY", "test_key")

        class _RetentionManager:
            def cleanup_expired_logs(self, data_class=None) -> int:
                assert data_class is None
                return 5

        monkeypatch.setattr(
            admin_operations_service,
            "get_retention_manager",
            lambda: _RetentionManager(),
        )

        response = client.post(
            "/admin/logs/cleanup",
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "deleted_files": 5,
            "data_class": "ALL",
            "message": "Deleted 5 expired log file(s)",
        }

        invalid_response = client.post(
            "/admin/logs/cleanup",
            headers={"X-API-Key": "test_key"},
            params={"data_class": "UNKNOWN"},
        )
        assert invalid_response.status_code == 200
        assert invalid_response.json()["status"] == "error"
        assert invalid_response.json()["data_class"] == "UNKNOWN"

    def test_admin_operation_route_wrappers_delegate_to_services(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("API_KEY", "test_key")

        async def _admin_status() -> dict[str, str]:
            return {"status": "ok", "scheduler": "available"}

        async def _get_database_status():
            from fastapi.responses import JSONResponse

            return JSONResponse({"db": "ok"})

        async def _force_database_update(*, source: str | None = None):
            from fastapi.responses import JSONResponse

            return JSONResponse({"source": source})

        async def _check_for_updates():
            from fastapi.responses import JSONResponse

            return JSONResponse({"updates": True})

        async def _rollback_database(*, source: str, target_version: str) -> dict[str, Any]:
            return {"source": source, "target_version": target_version, "success": True}

        monkeypatch.setattr(admin_operations_service, "admin_status", _admin_status)
        monkeypatch.setattr(admin_operations_service, "get_database_status", _get_database_status)
        monkeypatch.setattr(
            admin_operations_service, "force_database_update", _force_database_update
        )
        monkeypatch.setattr(admin_operations_service, "check_for_updates", _check_for_updates)
        monkeypatch.setattr(admin_operations_service, "rollback_database", _rollback_database)

        headers = {"X-API-Key": "test_key"}

        assert client.get("/api/v1/admin/status", headers=headers).json() == {
            "status": "ok",
            "scheduler": "available",
        }
        assert client.get("/api/v1/admin/db-status", headers=headers).json() == {"db": "ok"}
        assert client.post(
            "/api/v1/admin/force-update",
            headers=headers,
            params={"source": "usda"},
        ).json() == {"source": "usda"}
        assert client.get("/api/v1/admin/check-updates", headers=headers).json() == {
            "updates": True
        }
        assert client.post(
            "/api/v1/admin/rollback",
            headers=headers,
            params={"source": "usda", "target_version": "1.0.0"},
        ).json() == {"source": "usda", "target_version": "1.0.0", "success": True}

    def test_legacy_compatibility_shims_delegate_to_admin_services(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Legacy direct-call admin/debug helpers delegate to canonical services."""

        import legacy_app
        from fastapi.responses import JSONResponse

        calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

        async def _cleanup_expired_logs(*, data_class: str | None = None) -> dict[str, Any]:
            calls.append(("cleanup", (), {"data_class": data_class}))
            return {"status": "success", "data_class": data_class}

        async def _admin_status() -> dict[str, str]:
            calls.append(("admin_status", (), {}))
            return {"status": "ok", "scheduler": "available"}

        async def _debug_env() -> JSONResponse:
            calls.append(("debug", (), {}))
            return JSONResponse({"debug": "ok"})

        async def _get_database_status() -> JSONResponse:
            calls.append(("db_status", (), {}))
            return JSONResponse({"db": "ok"})

        async def _force_database_update(*, source: str | None = None) -> JSONResponse:
            calls.append(("force", (), {"source": source}))
            return JSONResponse({"source": source})

        async def _check_for_updates() -> JSONResponse:
            calls.append(("updates", (), {}))
            return JSONResponse({"updates": True})

        async def _rollback_database(*, source: str, target_version: str) -> dict[str, Any]:
            calls.append(("rollback", (), {"source": source, "target_version": target_version}))
            return {"success": True}

        monkeypatch.setattr(
            admin_operations_service,
            "cleanup_expired_logs",
            _cleanup_expired_logs,
        )
        monkeypatch.setattr(admin_operations_service, "admin_status", _admin_status)
        monkeypatch.setattr(admin_operations_service, "debug_env", _debug_env)
        monkeypatch.setattr(
            admin_operations_service,
            "get_database_status",
            _get_database_status,
        )
        monkeypatch.setattr(
            admin_operations_service,
            "force_database_update",
            _force_database_update,
        )
        monkeypatch.setattr(
            admin_operations_service,
            "check_for_updates",
            _check_for_updates,
        )
        monkeypatch.setattr(
            admin_operations_service,
            "rollback_database",
            _rollback_database,
        )

        cleanup_payload = asyncio.run(legacy_app.cleanup_expired_logs(data_class="PUBLIC"))
        admin_status_payload = asyncio.run(legacy_app.admin_status())
        debug_response = asyncio.run(legacy_app.debug_env())
        db_status_response = asyncio.run(legacy_app.get_database_status())
        force_response = asyncio.run(legacy_app.force_database_update(source="usda"))
        updates_response = asyncio.run(legacy_app.check_for_updates())
        rollback_payload = asyncio.run(
            legacy_app.rollback_database(
                source="usda",
                target_version="1.0.0",
            )
        )

        assert cleanup_payload == {"status": "success", "data_class": "PUBLIC"}
        assert admin_status_payload == {"status": "ok", "scheduler": "available"}
        assert debug_response.body == b'{"debug":"ok"}'
        assert db_status_response.body == b'{"db":"ok"}'
        assert force_response.body == b'{"source":"usda"}'
        assert updates_response.body == b'{"updates":true}'
        assert rollback_payload == {"success": True}
        assert calls == [
            ("cleanup", (), {"data_class": "PUBLIC"}),
            ("admin_status", (), {}),
            ("debug", (), {}),
            ("db_status", (), {}),
            ("force", (), {"source": "usda"}),
            ("updates", (), {}),
            ("rollback", (), {"source": "usda", "target_version": "1.0.0"}),
        ]

    def test_admin_status_success_generic_failure_and_http_exception(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async def _scheduler_available() -> object:
            return object()

        async def _scheduler_missing() -> None:
            return None

        async def _raise_http_exception() -> object:
            raise HTTPException(status_code=418, detail="scheduler rejected")

        monkeypatch.setattr(admin_operations_service, "get_update_scheduler", _scheduler_available)

        assert asyncio.run(admin_operations_service.admin_status()) == {
            "status": "ok",
            "scheduler": "available",
        }

        monkeypatch.setattr(admin_operations_service, "get_update_scheduler", _scheduler_missing)
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(admin_operations_service.admin_status())
        assert exc_info.value.status_code == 503
        assert exc_info.value.detail == "Scheduler unavailable"

        monkeypatch.setattr(
            admin_operations_service,
            "get_update_scheduler",
            _raise_http_exception,
        )

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(admin_operations_service.admin_status())

        assert exc_info.value.status_code == 418
        assert exc_info.value.detail == "scheduler rejected"

    def test_database_status_success_and_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        class _Scheduler:
            def get_status(self) -> dict[str, str]:
                return {"status": "ok"}

        async def _get_scheduler_success() -> _Scheduler:
            return _Scheduler()

        async def _get_scheduler_failure() -> object:
            raise RuntimeError("db status unavailable")

        monkeypatch.setattr(
            admin_operations_service,
            "get_update_scheduler",
            _get_scheduler_success,
        )

        response = asyncio.run(admin_operations_service.get_database_status())
        assert response.status_code == 200
        assert response.body == b'{"status":"ok"}'

        monkeypatch.setattr(
            admin_operations_service,
            "get_update_scheduler",
            _get_scheduler_failure,
        )

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(admin_operations_service.get_database_status())

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to get database status"

    def test_force_database_update_success_and_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        class _Scheduler:
            async def force_update(self, source: str | None = None) -> dict[str, Any]:
                assert source == "usda"
                return {
                    "usda": SimpleNamespace(
                        success=True,
                        old_version="1.0.0",
                        new_version="1.0.1",
                        records_added=1,
                        records_updated=2,
                        records_removed=0,
                        duration_seconds=0.25,
                        errors=[],
                    )
                }

        async def _get_scheduler_success() -> _Scheduler:
            return _Scheduler()

        async def _get_scheduler_failure() -> object:
            raise RuntimeError("force failed")

        monkeypatch.setattr(
            admin_operations_service,
            "get_update_scheduler",
            _get_scheduler_success,
        )

        response = asyncio.run(admin_operations_service.force_database_update(source="usda"))
        assert response.status_code == 200
        assert b'"Force update completed for usda"' in response.body
        assert b'"records_added":1' in response.body

        monkeypatch.setattr(
            admin_operations_service,
            "get_update_scheduler",
            _get_scheduler_failure,
        )

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(admin_operations_service.force_database_update(source="usda"))

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Force update failed"

    def test_check_for_updates_success_and_error_paths(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        class _UpdateManager:
            async def check_for_updates(self) -> dict[str, bool]:
                return {"usda": True, "off": False}

        class _Scheduler:
            update_manager = _UpdateManager()

        async def _get_scheduler_success() -> _Scheduler:
            return _Scheduler()

        async def _get_scheduler_without_manager() -> object:
            return SimpleNamespace(update_manager=None)

        async def _get_scheduler_none() -> None:
            return None

        async def _raise_http_exception() -> object:
            raise HTTPException(status_code=409, detail="updates rejected")

        monkeypatch.setattr(
            admin_operations_service,
            "get_update_scheduler",
            _get_scheduler_success,
        )

        response = asyncio.run(admin_operations_service.check_for_updates())
        assert response.status_code == 200
        assert b'"total_sources_with_updates":1' in response.body

        monkeypatch.setattr(
            admin_operations_service,
            "get_update_scheduler",
            _get_scheduler_without_manager,
        )

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(admin_operations_service.check_for_updates())

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Update check failed"

        monkeypatch.setattr(
            admin_operations_service,
            "get_update_scheduler",
            _get_scheduler_none,
        )
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(admin_operations_service.check_for_updates())
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Update check failed"

        monkeypatch.setattr(
            admin_operations_service,
            "get_update_scheduler",
            _raise_http_exception,
        )
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(admin_operations_service.check_for_updates())
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Update check failed"

    def test_rollback_database_success_and_error_paths(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        class _VersionedRollbackManager:
            versions_file = tmp_path / "database-versions.json"
            versions: dict[str, object] = {}

            def _load_versions(self) -> dict[str, object]:
                return {}

        class _SyncRollbackManager(_VersionedRollbackManager):
            def rollback_database(self, source: str, target_version: str) -> bool:
                assert (source, target_version) == ("usda", "1.0.0")
                return True

        class _FalseRollbackManager(_VersionedRollbackManager):
            def rollback_database(self, source: str, target_version: str) -> bool:
                return False

        class _RaisingRollbackManager(_VersionedRollbackManager):
            def rollback_database(self, source: str, target_version: str) -> bool:
                raise RuntimeError("rollback boom")

        class _AwaitableRollbackManager(_VersionedRollbackManager):
            def rollback_database(self, source: str, target_version: str) -> object:
                async def _success() -> bool:
                    return True

                return _success()

        async def _scheduler_with_manager(manager: object) -> object:
            return SimpleNamespace(update_manager=manager)

        async def _scheduler_none() -> None:
            return None

        monkeypatch.setattr(
            admin_operations_service,
            "get_update_scheduler",
            lambda: _scheduler_with_manager(_SyncRollbackManager()),
        )
        assert asyncio.run(admin_operations_service.rollback_database("usda", "1.0.0")) == {
            "message": "Successfully rolled back usda to version 1.0.0",
            "success": True,
        }

        monkeypatch.setattr(
            admin_operations_service,
            "get_update_scheduler",
            lambda: _scheduler_with_manager(_AwaitableRollbackManager()),
        )
        assert asyncio.run(admin_operations_service.rollback_database("usda", "1.0.0")) == {
            "message": "Successfully rolled back usda to version 1.0.0",
            "success": True,
        }

        monkeypatch.setattr(
            admin_operations_service,
            "get_update_scheduler",
            _scheduler_none,
        )
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(admin_operations_service.rollback_database("usda", "1.0.0"))
        assert exc_info.value.status_code == 500
        assert "could not get scheduler" in str(exc_info.value.detail)

        monkeypatch.setattr(
            admin_operations_service,
            "get_update_scheduler",
            lambda: _scheduler_with_manager(None),
        )
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(admin_operations_service.rollback_database("usda", "1.0.0"))
        assert exc_info.value.status_code == 500
        assert "No update manager available" in str(exc_info.value.detail)

        monkeypatch.setattr(
            admin_operations_service,
            "get_update_scheduler",
            lambda: _scheduler_with_manager(SimpleNamespace()),
        )
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(admin_operations_service.rollback_database("usda", "1.0.0"))
        assert exc_info.value.status_code == 500
        assert "not supported" in str(exc_info.value.detail)

        monkeypatch.setattr(
            admin_operations_service,
            "get_update_scheduler",
            lambda: _scheduler_with_manager(_RaisingRollbackManager()),
        )
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(admin_operations_service.rollback_database("usda", "1.0.0"))
        assert exc_info.value.status_code == 500
        assert "Rollback failed" in str(exc_info.value.detail)

        monkeypatch.setattr(
            admin_operations_service,
            "get_update_scheduler",
            lambda: _scheduler_with_manager(_FalseRollbackManager()),
        )
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(admin_operations_service.rollback_database("usda", "1.0.0"))
        assert exc_info.value.status_code == 500
        assert "Rollback operation failed for usda" in str(exc_info.value.detail)


class TestAppPackageShimEdges:
    """Test app package shim (__init__.py): passthrough attr and spec proxy name."""

    def test_app_package_spec_proxy_and_getattr_passthrough(self) -> None:
        """Test that accessing __spec__.name returns 'app' and keeps module bound."""
        # Accessing __spec__.name returns 'app' and keeps module bound
        spec = apppkg.__spec__
        assert spec is not None and spec.name == "app"

        # Test public API access instead of internal implementation
        assert hasattr(apppkg, "app")
        assert apppkg.app is not None

    def test_app_package_spec_proxy_attrs_exist(self) -> None:
        """Test that spec proxy attributes are accessible without raising."""
        spec = apppkg.__spec__
        assert spec is not None
        # origin/loader/submodule_search_locations should be accessible without raising
        _ = spec.origin
        _ = spec.loader
        loc = spec.submodule_search_locations or []
        assert isinstance(loc, (list, tuple))

    def test_app_package_all_and_sysmodules_binding(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test __all__ exports and sys.modules binding behavior."""
        # Ensure __all__ exposes app
        exported = getattr(apppkg, "__all__", [])
        assert "app" in exported

        # Verify sys.modules["app"] points to the package
        assert sys.modules.get("app") is apppkg

    def test_app_getattr_missing_raises_attributeerror(self) -> None:
        """Test that getattr raises AttributeError for missing attributes."""
        with pytest.raises(AttributeError):
            getattr(apppkg, "__definitely_missing_attribute__")  # noqa: B009


class TestPublicDiscoveryHelpers:
    """Unit coverage for public sitemap helper branches."""

    @staticmethod
    def _request_for_host(host: str, *, scheme: str = "https") -> Request:
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": scheme,
            "path": public_discovery.SITEMAP_ROUTE_PATH,
            "raw_path": public_discovery.SITEMAP_ROUTE_PATH.encode("utf-8"),
            "root_path": "",
            "query_string": b"",
            "headers": [(b"host", host.encode("utf-8"))],
            "client": ("127.0.0.1", 12345),
            "server": (host, 443 if scheme == "https" else 80),
        }
        return Request(scope)

    def test_build_public_url_normalizes_base_and_path(self) -> None:
        """Builder normalizes base/path separators before joining URLs."""
        public_url = public_discovery._build_public_url(
            base_url="https://pulseplate.app",
            path="privacy",
        )
        assert public_url == "https://pulseplate.app/privacy"

    def test_build_public_sitemap_xml_escapes_query_values(self) -> None:
        """XML builder escapes query separators and keeps canonical loc entries."""
        sitemap_xml = public_discovery.build_public_sitemap_xml(
            base_url="https://pulseplate.app",
            paths=("privacy", "/terms?utm=summer&ref=share"),
        )

        assert sitemap_xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert "<loc>https://pulseplate.app/privacy</loc>" in sitemap_xml
        assert "<loc>https://pulseplate.app/terms?utm=summer&amp;ref=share</loc>" in sitemap_xml

    def test_resolve_public_sitemap_base_url_prefers_sanitized_production_domain(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Configured production domain wins after quote/scheme/trailing-slash cleanup."""
        monkeypatch.setenv(public_discovery.PRODUCTION_DOMAIN_ENV, ' "http://pulseplate.app/" ')

        resolved_base_url = public_discovery.resolve_public_sitemap_base_url(
            self._request_for_host("direct-origin.internal")
        )

        assert resolved_base_url == "https://pulseplate.app"

    def test_resolve_public_sitemap_base_url_falls_back_to_request_host(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Missing production domain falls back to the direct request base URL."""
        monkeypatch.delenv(public_discovery.PRODUCTION_DOMAIN_ENV, raising=False)

        resolved_base_url = public_discovery.resolve_public_sitemap_base_url(
            self._request_for_host("edge.pulseplate.test")
        )

        assert resolved_base_url == "https://edge.pulseplate.test/"

    def test_serve_public_sitemap_returns_xml_response(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Async response helper returns XML with canonical public URLs."""
        monkeypatch.delenv(public_discovery.PRODUCTION_DOMAIN_ENV, raising=False)

        response = asyncio.run(
            public_discovery.serve_public_sitemap(self._request_for_host("edge.pulseplate.test"))
        )

        assert response.media_type == "application/xml"
        body = bytes(response.body)
        assert body.startswith(b'<?xml version="1.0" encoding="UTF-8"?>')
        assert b"https://edge.pulseplate.test/privacy" in body
