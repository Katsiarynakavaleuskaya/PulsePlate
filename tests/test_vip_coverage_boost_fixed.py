# -*- coding: utf-8 -*-
"""
VIP Coverage Boost Tests - Fixed Endpoints

RU: Исправленные тесты для VIP модуля с правильными эндпоинтами
EN: Fixed VIP module tests with correct endpoints
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.effective_routes import route_endpoint_for_path_method
from app.schemas.vip import AutoRepairWeeklyRequest
from tests._helpers.vip_contracts import (
    assert_json_response_payload,
    build_auto_repair_weekly_request_payload,
)


class TestVIPCoverageBoostFixed:
    """Fixed VIP coverage tests with correct endpoint paths."""

    def test_vip_weekly_plan_missing_function(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP weekly plan когда make_weekly_menu недоступен"""
        with patch("app.routers.vip.make_weekly_menu", None):
            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json={
                    "sex": "male",
                    "age": 30,
                    "height_cm": 175.0,
                    "weight_kg": 70.0,
                    "activity": "moderate",
                    "goal": "maintain",
                    "user_id": "test",
                    "preferences": {},
                    "calories": 2000,
                },
                headers=vip_headers,
            )
            assert response.status_code == 200

    def test_vip_shoplist_weekly_new_api_format(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP shoplist weekly endpoint with new API format"""

        # Enable VIP module
        def mock_is_vip_module_enabled() -> bool:
            return True

        monkeypatch.setattr(
            "app.routers.vip_shoplist.is_vip_module_enabled",
            mock_is_vip_module_enabled,
        )

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
        data = assert_json_response_payload(response)
        assert "days" in data

    def test_vip_regions_missing_function(
        self,
        app: FastAPI,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP regions когда get_available_regions недоступен.

        Patch the actual route endpoint globals (not just the module attribute) to avoid
        flakiness if the suite ends up with multiple loaded module instances.
        """
        endpoint = route_endpoint_for_path_method(
            app.routes,
            "/api/v1/vip/regions",
            "GET",
        )

        assert endpoint is not None, "VIP regions route endpoint not found"
        monkeypatch.setitem(getattr(endpoint, "__globals__", {}), "get_available_regions", None)

        response = client.get(
            "/api/v1/vip/regions",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "error", f"Expected error, got: {data}"
        assert data["code"] == "region_provider_unavailable"
        assert data["detail"] == data["message"]
        assert data["error"] == data["code"]
        assert data["regions"] == []

    def test_vip_recipe_synthesis_missing_function(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест текущего deterministic echo contract для VIP recipe synthesis."""
        ingredients = ["chicken", "rice"]

        response = client.post(
            "/api/v1/vip/recipes/synthesize",
            json={"ingredients": ingredients},
            headers=vip_headers,
        )

        assert response.status_code == 200
        payload = assert_json_response_payload(response)
        assert payload["status"] == "success"
        assert payload["echo"] == {"ingredients": ingredients}
        assert payload["recipe"]["name"] == "Echo Recipe"
        assert payload["recipe"]["ingredients"] == ingredients

    def test_vip_auto_repair_missing_function(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест deterministic fallback когда get_auto_repair_engine недоступен."""
        mutation_probe = build_auto_repair_weekly_request_payload()
        request_payload = build_auto_repair_weekly_request_payload()
        mutation_probe["targets"]["iron_mg"][0] = 999.0
        mutation_probe["week_plan"]["days"][0]["meals"][0]["nutrients"]["iron_mg"] = 999.0
        assert request_payload["targets"]["iron_mg"] == [6.0, 8.0, 45.0]
        assert request_payload["week_plan"]["days"][0]["meals"][0]["nutrients"]["iron_mg"] == 8.0
        AutoRepairWeeklyRequest.model_validate(request_payload)

        complete_success_result = {
            "status": "success",
            "repaired_plan": request_payload["week_plan"],
            "original_plan": request_payload["week_plan"],
            "changes_made": [],
            "remaining_gaps": {},
            "strategy_used": "balanced",
            "iterations": 0,
            "message": "Already compliant",
            "suggestions": [],
        }
        fallback_auto_repair = MagicMock(return_value=complete_success_result)

        with (
            patch("app.routers.vip.get_auto_repair_engine", None),
            patch("app.routers.vip.auto_repair_week_plan", fallback_auto_repair),
        ):
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=request_payload,
                headers=vip_headers,
            )

            assert response.status_code == 200
            payload = assert_json_response_payload(response)
            assert payload["status"] == "success"
            assert payload["repair_result"] == complete_success_result
            assert payload["echo"] == request_payload
            fallback_auto_repair.assert_called_once()
            assert fallback_auto_repair.call_args.args[1].get_target("iron_mg") == 8.0

    def test_vip_with_all_functions_working(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP endpoints с функциональными мок-функциями"""
        # Моксим функции чтобы они возвращали данные
        mock_make_weekly_menu = MagicMock()
        mock_make_weekly_menu.return_value = {"plan_id": "test123", "meals": []}

        mock_get_available_regions = MagicMock()
        mock_get_available_regions.return_value = ["BY", "RU"]

        auto_repair_payload = build_auto_repair_weekly_request_payload()
        mock_get_auto_repair_engine = MagicMock()
        mock_repair_engine = MagicMock()
        complete_success_result = {
            "status": "success",
            "repaired_plan": auto_repair_payload["week_plan"],
            "original_plan": auto_repair_payload["week_plan"],
            "changes_made": [],
            "remaining_gaps": {},
            "strategy_used": "balanced",
            "iterations": 0,
            "message": "Already compliant",
            "suggestions": [],
        }
        mock_repair_engine.auto_repair_week_plan.return_value = complete_success_result
        mock_get_auto_repair_engine.return_value = mock_repair_engine

        with (
            patch("app.routers.vip.make_weekly_menu", mock_make_weekly_menu),
            patch("app.routers.vip.get_available_regions", mock_get_available_regions),
            patch("app.routers.vip.get_auto_repair_engine", mock_get_auto_repair_engine),
        ):
            # Тест weekly plan
            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json={
                    "sex": "male",
                    "age": 30,
                    "height_cm": 175.0,
                    "weight_kg": 70.0,
                    "activity": "moderate",
                    "goal": "maintain",
                    "user_id": "test",
                    "preferences": {},
                    "calories": 2000,
                },
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
            data = assert_json_response_payload(response)
            assert "days" in data

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
            recipe_payload = assert_json_response_payload(response)
            assert recipe_payload["status"] == "success"
            assert recipe_payload["recipe"]["ingredients"] == ["chicken", "rice"]

            # Тест auto repair
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json=auto_repair_payload,
                headers=vip_headers,
            )
            assert response.status_code == 200
            repair_payload = assert_json_response_payload(response)
            assert repair_payload["status"] == "success"
            assert repair_payload["repair_result"] == complete_success_result
            assert repair_payload["echo"] == auto_repair_payload
            mock_get_auto_repair_engine.assert_called_once_with()
            mock_repair_engine.auto_repair_week_plan.assert_called_once()
            repair_targets = mock_repair_engine.auto_repair_week_plan.call_args.args[1]
            assert repair_targets.get_target("iron_mg") == 8.0

    def test_vip_error_handling_paths(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP error handling когда функции поднимают исключения"""
        # Моксим функции чтобы они поднимали исключения
        mock_make_weekly_menu = MagicMock()
        mock_make_weekly_menu.side_effect = RuntimeError("Test error")

        with patch("app.routers.vip.make_weekly_menu", mock_make_weekly_menu):
            # Тест weekly plan error
            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json={
                    "sex": "male",
                    "age": 30,
                    "height_cm": 175.0,
                    "weight_kg": 70.0,
                    "activity": "moderate",
                    "goal": "maintain",
                    "user_id": "test",
                    "preferences": {},
                    "calories": 2000,
                },
                headers=vip_headers,
            )
            assert response.status_code == 200

            # Тест shoplist error (new API format)
            from app.routers import vip_shoplist

            def mock_is_vip_module_enabled() -> bool:
                return True

            monkeypatch.setattr(
                vip_shoplist,
                "is_vip_module_enabled",
                mock_is_vip_module_enabled,
            )

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

    def test_vip_health_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP health endpoint"""
        response = client.get(
            "/api/v1/vip/health",
            headers=vip_headers,
        )
        assert response.status_code == 200
        assert "status" in assert_json_response_payload(response)
