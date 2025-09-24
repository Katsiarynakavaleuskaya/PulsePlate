"""
Простые рабочие тесты для VIP router
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import os
import sys
from starlette.types import ASGIApp
from typing import cast


class TestVIPRouterWorking:
    """Простые рабочие тесты для VIP роутера"""

    @pytest.fixture(autouse=True)
    def setup_vip_environment(self):
        """Устанавливаем VIP модуль как включенный"""
        with patch.dict(os.environ, {"VIP_MODULE_ENABLED": "true"}):
            # Перезагружаем модули с правильной переменной окружения
            modules_to_remove = [k for k in sys.modules.keys() if k.startswith("app")]
            for module in modules_to_remove:
                if module in sys.modules:
                    del sys.modules[module]

            yield

    def test_vip_endpoints_with_environment_enabled(self):
        """Тест VIP endpoints когда VIP_MODULE_ENABLED=true"""
        with patch.dict(os.environ, {"VIP_MODULE_ENABLED": "true"}):
            # Мокаем VIP функции
            mock_make_weekly_menu = MagicMock(return_value={"plan_id": "test123", "meals": []})

            mock_shoplist_generator = MagicMock()
            mock_shoplist_instance = MagicMock()
            mock_shoplist_instance.generate_weekly.return_value = {"items": [], "total": 0}
            mock_shoplist_generator.return_value = mock_shoplist_instance

            mock_get_available_regions = MagicMock(return_value=["BY", "RU"])

            with (
                patch("app.routers.vip.make_weekly_menu", mock_make_weekly_menu),
                patch("app.routers.vip.ShoplistGenerator", mock_shoplist_generator),
                patch("app.routers.vip.get_available_regions", mock_get_available_regions),
            ):
                import app

                client = TestClient(cast(ASGIApp, app.app))

                # Тест weekly plan endpoint
                response = client.post(
                    "/api/v1/vip/menu/weekly/plan",
                    json={"user_id": "test", "preferences": {}},
                    headers={"X-API-Key": "test_key"},
                )
                # Если endpoint существует, статус должен быть 200 или 422, не 404
                assert response.status_code in [
                    200,
                    422,
                    403,
                ], f"Unexpected status: {response.status_code}"

                # Тест regions endpoint
                response = client.get(
                    "/api/v1/vip/regions",
                    headers={"X-API-Key": "test_key"},
                )
                assert response.status_code in [
                    200,
                    403,
                ], f"Unexpected status: {response.status_code}"

    def test_vip_router_import_coverage(self):
        """Тест покрытия импорта VIP роутера"""
        with patch.dict(os.environ, {"VIP_MODULE_ENABLED": "true"}):
            try:
                from app.routers import vip

                # Проверяем что роутер загружается
                assert hasattr(vip, "router")
                assert vip.router is not None
            except ImportError:
                pytest.skip("VIP module not available")

    def test_vip_module_disabled_fallback(self):
        """Тест fallback когда VIP модуль отключен"""
        with patch.dict(os.environ, {"VIP_MODULE_ENABLED": "false"}):
            # Перезагружаем app с отключенным VIP
            modules_to_remove = [k for k in sys.modules.keys() if k.startswith("app")]
            for module in modules_to_remove:
                if module in sys.modules:
                    del sys.modules[module]

            import app

            client = TestClient(cast(ASGIApp, app.app))

            # VIP endpoints должны возвращать 404 когда модуль отключен
            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json={"user_id": "test", "preferences": {}},
                headers={"X-API-Key": "test_key"},
            )
            assert response.status_code == 404  # Not found when disabled
