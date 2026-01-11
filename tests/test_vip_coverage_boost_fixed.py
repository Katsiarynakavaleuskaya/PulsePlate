# -*- coding: utf-8 -*-
"""
VIP Coverage Boost Tests - Fixed Endpoints

RU: Исправленные тесты для VIP модуля с правильными эндпоинтами
EN: Fixed VIP module tests with correct endpoints
"""

from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp

from app.middleware import api_tiers


def _get_app():
    """Safely get the FastAPI app instance."""
    import app

    if app.app is None:
        raise RuntimeError("FastAPI app is not initialized")
    return app.app


class TestVIPCoverageBoostFixed:
    """Fixed VIP coverage tests with correct endpoint paths."""

    def test_vip_weekly_plan_missing_function(self, vip_headers) -> None:
        """Тест VIP weekly plan когда make_weekly_menu недоступен"""
        with patch("app.routers.vip.make_weekly_menu", None):
            client = TestClient(_get_app())

            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json={"user_id": "test", "preferences": {}, "calories": 2000},
                headers=vip_headers,
            )
            assert response.status_code == 200

    def test_vip_shoplist_weekly_new_api_format(
        self, monkeypatch: pytest.MonkeyPatch, vip_headers
    ) -> None:
        """Тест VIP shoplist weekly endpoint with new API format"""
        import app

        # Enable VIP module
        def mock_is_vip_module_enabled() -> bool:
            return True

        monkeypatch.setattr(
            "app.routers.vip_shoplist.is_vip_module_enabled",
            mock_is_vip_module_enabled,
        )

        # Override VIP tier dependency
        async def mock_require_vip_tier() -> str:
            return "vip"

        app.app.dependency_overrides[api_tiers.require_vip_tier] = mock_require_vip_tier

        try:
            client = TestClient(cast(ASGIApp, app.app))

            # Use new API format for vip_shoplist router
            response = client.post(
                "/api/v1/vip/shoplist/weekly",
                json={
                    "days": [
                        {
                            "items": [
                                {
                                    "food_id": "chicken",
                                    "qty": {"value": "500", "unit": "G"},
                                    "form": "RAW",
                                }
                            ],
                            "packaging_rules": [
                                {
                                    "food_id": "chicken",
                                    "pack_size": {"value": "500", "unit": "G"},
                                    "rounding": "CEIL",
                                    "min_packs": 1,
                                }
                            ],
                        }
                    ]
                },
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert "days" in data
        finally:
            app.app.dependency_overrides.pop(api_tiers.require_vip_tier, None)

    def test_vip_regions_missing_function(self, monkeypatch: pytest.MonkeyPatch, vip_headers) -> None:
        """Тест VIP regions когда get_available_regions недоступен.

        Patch the actual route endpoint globals (not just the module attribute) to avoid
        flakiness if the suite ends up with multiple loaded module instances.
        """
        app = _get_app()
        endpoint = None
        for route in getattr(app, "routes", []):
            if getattr(route, "path", None) != "/api/v1/vip/regions":
                continue
            methods = getattr(route, "methods", None) or set()
            if "GET" not in methods:
                continue
            endpoint = getattr(route, "endpoint", None)
            break

        assert endpoint is not None, "VIP regions route endpoint not found"
        monkeypatch.setitem(getattr(endpoint, "__globals__", {}), "get_available_regions", None)

        client = TestClient(app)

        response = client.get(
            "/api/v1/vip/regions",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error", f"Expected error, got: {data}"
        assert data["code"] == "region_provider_unavailable"
        assert data["detail"] == data["message"]
        assert data["error"] == data["code"]
        assert data["regions"] == []

    def test_vip_recipe_synthesis_missing_function(self, vip_headers) -> None:
        """Тест VIP recipe synthesis когда get_recipe_synthesizer недоступен"""
        with patch("app.routers.vip.get_recipe_synthesizer", None):
            client = TestClient(_get_app())

            response = client.post(
                "/api/v1/vip/recipes/synthesize",
                json={"ingredients": ["chicken", "rice"]},
                headers=vip_headers,
            )
            assert response.status_code == 200

    def test_vip_auto_repair_missing_function(self, vip_headers) -> None:
        """Тест VIP auto repair когда get_auto_repair_engine недоступен"""
        with patch("app.routers.vip.get_auto_repair_engine", None):
            client = TestClient(_get_app())

            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json={"plan_id": "test123"},
                headers=vip_headers,
            )
            assert response.status_code == 200

    def test_vip_with_all_functions_working(self, monkeypatch: pytest.MonkeyPatch, vip_headers) -> None:
        """Тест VIP endpoints с функциональными мок-функциями"""
        import app

        # Моксим функции чтобы они возвращали данные
        mock_make_weekly_menu = MagicMock()
        mock_make_weekly_menu.return_value = {"plan_id": "test123", "meals": []}

        mock_get_available_regions = MagicMock()
        mock_get_available_regions.return_value = ["BY", "RU"]

        mock_get_recipe_synthesizer = MagicMock()
        mock_synthesizer = MagicMock()
        mock_synthesizer.synthesize_from_ingredients.return_value = {
            "recipe": {"name": "Test Recipe", "ingredients": []}
        }
        mock_get_recipe_synthesizer.return_value = mock_synthesizer

        mock_get_auto_repair_engine = MagicMock()
        mock_repair_engine = MagicMock()
        mock_repair_engine.auto_repair_week_plan.return_value = {"status": "success", "repairs": []}
        mock_get_auto_repair_engine.return_value = mock_repair_engine

        mock_shoplist_generator = MagicMock()
        mock_shoplist_generator.return_value.generate.return_value = {"items": []}

        with (
            patch("app.routers.vip.make_weekly_menu", mock_make_weekly_menu),
            patch("app.routers.vip.ShoplistGenerator", mock_shoplist_generator),
            patch("app.routers.vip.get_available_regions", mock_get_available_regions),
            patch("app.routers.vip.get_recipe_synthesizer", mock_get_recipe_synthesizer),
            patch("app.routers.vip.get_auto_repair_engine", mock_get_auto_repair_engine),
        ):
            client = TestClient(_get_app())

            # Тест weekly plan
            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json={"user_id": "test", "preferences": {}, "calories": 2000},
                headers=vip_headers,
            )
            assert response.status_code == 200

            # Тест shoplist (new API format)
            from app.routers import vip_shoplist

            def mock_is_vip_module_enabled() -> bool:
                return True

            monkeypatch.setattr(
                vip_shoplist,
                "is_vip_module_enabled",
                mock_is_vip_module_enabled,
            )

            async def mock_require_vip_tier() -> str:
                return "vip"

            app.app.dependency_overrides[api_tiers.require_vip_tier] = mock_require_vip_tier

            try:
                # Create fresh TestClient after setting dependency_overrides
                shoplist_client = TestClient(cast(ASGIApp, app.app))

                response = shoplist_client.post(
                    "/api/v1/vip/shoplist/weekly",
                    json={
                        "days": [
                            {
                                "items": [
                                    {
                                        "food_id": "chicken",
                                        "qty": {"value": "500", "unit": "G"},
                                        "form": "RAW",
                                    }
                                ],
                                "packaging_rules": [
                                    {
                                        "food_id": "chicken",
                                        "pack_size": {"value": "500", "unit": "G"},
                                        "rounding": "CEIL",
                                        "min_packs": 1,
                                    }
                                ],
                            }
                        ]
                    },
                    headers=vip_headers,
                )
                assert response.status_code == 200
                data = response.json()
                assert "days" in data
            finally:
                app.app.dependency_overrides.pop(api_tiers.require_vip_tier, None)

            # Тест regions
            response = client.get(
                "/api/v1/vip/regions",
                headers=vip_headers,
            )
            assert response.status_code == 200

            # Тест recipe synthesis
            response = client.post(
                "/api/v1/vip/recipes/synthesize",
                json={"ingredients": ["chicken", "rice"]},
                headers=vip_headers,
            )
            assert response.status_code == 200

            # Тест auto repair
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json={"plan_id": "test123"},
                headers=vip_headers,
            )
            assert response.status_code == 200

    def test_vip_error_handling_paths(self, monkeypatch: pytest.MonkeyPatch, vip_headers) -> None:
        """Тест VIP error handling когда функции поднимают исключения"""
        # Моксим функции чтобы они поднимали исключения
        mock_make_weekly_menu = MagicMock()
        mock_make_weekly_menu.side_effect = RuntimeError("Test error")

        mock_shoplist_generator = MagicMock()
        mock_shoplist_generator.side_effect = ValueError("Test shoplist error")

        with (
            patch("app.routers.vip.make_weekly_menu", mock_make_weekly_menu),
            patch("app.routers.vip.ShoplistGenerator", mock_shoplist_generator),
        ):
            client = TestClient(_get_app())

            # Тест weekly plan error
            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json={"user_id": "test", "preferences": {}, "calories": 2000},
                headers=vip_headers,
            )
            assert response.status_code == 200

            # Тест shoplist error (new API format)
            import app
            from app.routers import vip_shoplist

            def mock_is_vip_module_enabled() -> bool:
                return True

            monkeypatch.setattr(
                vip_shoplist,
                "is_vip_module_enabled",
                mock_is_vip_module_enabled,
            )

            async def mock_require_vip_tier() -> str:
                return "vip"

            app.app.dependency_overrides[api_tiers.require_vip_tier] = mock_require_vip_tier

            try:
                # Invalid enum should return 422
                response = client.post(
                    "/api/v1/vip/shoplist/weekly",
                    json={
                        "days": [
                            {
                                "items": [
                                    {
                                        "food_id": "chicken",
                                        "qty": {"value": "500", "unit": "INVALID"},
                                        "form": "RAW",
                                    }
                                ]
                            }
                        ]
                    },
                    headers=vip_headers,
                )
                assert response.status_code == 422
            finally:
                app.app.dependency_overrides.pop(api_tiers.require_vip_tier, None)

    def test_vip_health_endpoint(self, vip_headers) -> None:
        """Тест VIP health endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/health",
            headers=vip_headers,
        )
        assert response.status_code == 200
        assert "status" in response.json()
