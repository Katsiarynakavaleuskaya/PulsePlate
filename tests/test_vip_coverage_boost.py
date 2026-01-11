"""
Тесты для повышения покрытия VIP router
Фокус: VIP endpoints, fallback paths, error handling
"""

import os
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp

from app.middleware import api_tiers


class TestVIPCoverageBoost:
    """Тесты для покрытия недостающих веток VIP модуля"""

    def setup_method(self):
        # Устанавливаем переменные окружения для VIP модуля
        os.environ["VIP_MODULE_ENABLED"] = "true"
        os.environ["API_KEY"] = "test_key"

    def teardown_method(self):
        # Очищаем переменные окружения (все, что были установлены в setup_method)
        os.environ.pop("API_KEY", None)
        os.environ.pop("VIP_MODULE_ENABLED", None)

    def test_vip_health_endpoint(self, vip_headers: dict[str, str]) -> None:
        """Тест VIP health endpoint"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        response = client.get("/api/v1/vip/health", headers=vip_headers)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_vip_weekly_plan_missing_function(self, vip_headers: dict[str, str]) -> None:
        """Тест VIP weekly plan когда make_weekly_menu недоступен"""
        with patch("app.routers.vip.make_weekly_menu", None):
            import app

            client = TestClient(cast(ASGIApp, app.app))

            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json={"user_id": "test", "preferences": {}, "calories": 2000},
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_vip_shoplist_weekly_new_api_format(
        self,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
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

    def test_vip_regions_endpoint_success(self, vip_headers: dict[str, str]) -> None:
        """Тест VIP regions endpoint: возвращает success и список регионов"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        response = client.get(
            "/api/v1/vip/regions",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Function is now implemented and returns success with regions list
        assert data["status"] == "success", f"Expected success, got: {data}"
        assert "regions" in data, f"Expected 'regions' key in response, got: {data}"
        assert isinstance(data["regions"], list), f"Expected regions to be a list, got: {data}"
        if data["regions"]:
            assert all(
                isinstance(r, str) for r in data["regions"]
            ), "Expected all regions to be strings"
        # Verify response structure matches API contract
        if "total_regions" in data:
            assert data["total_regions"] == len(data["regions"])

    def test_vip_recipe_synthesis_missing_function(self, vip_headers: dict[str, str]) -> None:
        """Тест VIP recipe synthesis когда get_recipe_synthesizer недоступен"""
        with patch("app.routers.vip.get_recipe_synthesizer", None):
            import app

            client = TestClient(cast(ASGIApp, app.app))

            response = client.post(
                "/api/v1/vip/recipes/synthesize",
                json={
                    "ingredients": [
                        {"name": "chicken", "amount": 200, "unit": "g"},
                        {"name": "rice", "amount": 150, "unit": "g"},
                    ],
                    "cuisine_preference": "asian",
                    "difficulty_preference": "easy",
                    "servings": 2,
                },
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_vip_auto_repair_missing_function(self, vip_headers: dict[str, str]) -> None:
        """Тест VIP auto repair когда get_auto_repair_engine недоступен"""
        with patch("app.routers.vip.get_auto_repair_engine", None):
            import app

            client = TestClient(cast(ASGIApp, app.app))

            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json={"plan_id": "test123"},
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"  # Exception handling path

    def test_vip_with_all_functions_working(
        self,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP endpoints с функциональными мок-функциями"""
        # Моксим функции чтобы они возвращали данные
        mock_make_weekly_menu = MagicMock()
        mock_make_weekly_menu.return_value = {"plan_id": "test123", "meals": []}

        mock_shoplist_generator = MagicMock()
        mock_shoplist_instance = MagicMock()
        mock_shoplist_instance.generate_weekly.return_value = {"items": [], "total": 0}
        mock_shoplist_generator.return_value = mock_shoplist_instance

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

        with (
            patch("app.routers.vip.make_weekly_menu", mock_make_weekly_menu),
            patch("app.routers.vip.ShoplistGenerator", mock_shoplist_generator),
            patch("app.routers.vip.get_available_regions", mock_get_available_regions),
            patch("app.routers.vip.get_recipe_synthesizer", mock_get_recipe_synthesizer),
            patch("app.routers.vip.get_auto_repair_engine", mock_get_auto_repair_engine),
        ):
            import app
            from app.routers import vip_shoplist

            client = TestClient(cast(ASGIApp, app.app))

            # Тест weekly plan
            response = client.post(
                "/api/v1/vip/weekly-plan",
                json={
                    "sex": "male",
                    "age": 30,
                    "height_cm": 175.0,
                    "weight_kg": 70.0,
                    "activity": "moderate",
                    "goal": "maintain",
                    "user_id": "test",
                    "preferences": {},
                },
                headers=vip_headers,
            )
            assert response.status_code == 200

            # Тест shoplist (new API format)
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

            # Тест regions
            response = client.get(
                "/api/v1/vip/regions",
                headers=vip_headers,
            )
            assert response.status_code == 200

            # Тест recipe synthesis
            response = client.post(
                "/api/v1/vip/recipes/synthesize",
                json={
                    "ingredients": [
                        {"name": "chicken", "amount": 200, "unit": "g"},
                        {"name": "rice", "amount": 150, "unit": "g"},
                    ],
                    "cuisine_preference": "asian",
                    "difficulty_preference": "easy",
                    "servings": 2,
                },
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

    def test_vip_error_handling_paths(
        self,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
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
            import app
            from app.routers import vip_shoplist

            client = TestClient(cast(ASGIApp, app.app))

            # Тест weekly plan error
            response = client.post(
                "/api/v1/vip/weekly-plan",
                json={
                    "sex": "male",
                    "age": 30,
                    "height_cm": 175.0,
                    "weight_kg": 70.0,
                    "activity": "moderate",
                    "goal": "maintain",
                    "user_id": "test",
                    "preferences": {},
                },
                headers=vip_headers,
            )
            assert response.status_code == 200

            # Тест shoplist error (new API format)
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
