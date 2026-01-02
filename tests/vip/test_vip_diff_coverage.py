# -*- coding: utf-8 -*-
"""
Diff-coverage tests for VIP module.

RU: Тесты для закрытия недостающих строк в diff-cover.
EN: Tests to cover missing lines in diff-cover.

These tests target specific lines that diff-cover reports as missing:
- app/routers/vip_registration.py:45 (idempotent registration)
- app/routers/vip_shoplist.py:70, 74-75 (PDF export success path)
"""

from __future__ import annotations

import os

from fastapi import FastAPI


class TestVIPRegistrationIdempotent:
    """Test VIP registration (covers vip_registration.py:44-45, 53-57)."""

    def test_register_vip_routes_registers_routes(self, monkeypatch):
        """Test that register_vip_routes registers VIP routes when enabled."""
        # Enable VIP module
        monkeypatch.setenv("VIP_MODULE_ENABLED", "true")

        from app.routers.vip_registration import register_vip_routes

        app = FastAPI()

        # Call register_vip_routes (covers lines 44-45: if not is_vip_module_enabled(): return)
        register_vip_routes(app)

        # Verify VIP routes are registered (covers lines 53-57: hasattr check and include_router)
        paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert any("/api/v1/vip" in path for path in paths), "VIP routes should be registered"

    def test_register_vip_routes_noop_when_disabled(self, monkeypatch):
        """Test that register_vip_routes is a no-op when VIP module disabled."""
        monkeypatch.setenv("VIP_MODULE_ENABLED", "false")

        from app.routers.vip_registration import register_vip_routes

        app = FastAPI()

        register_vip_routes(app)

        paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert not any(
            "/api/v1/vip" in path for path in paths
        ), "VIP routes should not be registered"


class TestVIPShoplistPDFExport:
    """Test VIP shoplist PDF export paths (covers vip_shoplist.py:70, 74-75, 567)."""

    def setup_method(self):
        """Setup for each test method."""
        os.environ["VIP_MODULE_ENABLED"] = "true"
        os.environ["API_KEY"] = "test_key"  # pragma: allowlist secret

    def teardown_method(self):
        """Cleanup after each test method."""
        for var in ["VIP_MODULE_ENABLED", "API_KEY"]:
            if var in os.environ:
                del os.environ[var]

    def test_vip_shoplist_export_pdf_success(self, client_with_vip_access):
        """Test successful PDF export (covers vip_shoplist.py:70, 74-75)."""
        # Create a valid shoplist request
        payload = {
            "items": [
                {
                    "food_id": "test_food_1",
                    "qty": {"value": "100", "unit": "G"},
                    "form": "RAW",
                }
            ]
        }

        # Call PDF export endpoint
        response = client_with_vip_access.post(
            "/api/v1/vip/shoplist/export?format=pdf",
            json=payload,
        )

        # Should succeed with PDF content
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert len(response.content) > 0
        assert response.content.startswith(b"%PDF"), "Response should be valid PDF"

    def test_vip_shoplist_export_pdf_import_error_returns_501(
        self, client_with_vip_access, monkeypatch
    ):
        """Test PDF export when reportlab is unavailable (covers vip_shoplist.py:567)."""

        # Force ImportError branch regardless of whether reportlab is installed.
        def _raise_import_error(*_args: object, **_kwargs: object) -> bytes:
            raise ImportError("reportlab is missing")

        monkeypatch.setattr("app.routers.vip_shoplist._export_shoplist_to_pdf", _raise_import_error)

        payload = {
            "items": [
                {
                    "food_id": "test_food_1",
                    "qty": {"value": "100", "unit": "G"},
                    "form": "RAW",
                }
            ]
        }

        response = client_with_vip_access.post(
            "/api/v1/vip/shoplist/export?format=pdf",
            json=payload,
        )

        # Should return 501 NOT IMPLEMENTED (covers line 567: except ImportError as e)
        assert response.status_code == 501
        assert "PDF export is not available" in response.json()["detail"]
