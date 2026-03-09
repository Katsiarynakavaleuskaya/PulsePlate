from __future__ import annotations

import time
from typing import Any, Dict

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from tests.helpers.fitchef_runtime_helpers import make_mock_run_shopping_followup_task


class TestShoppingListProRouterIsolated:
    """Isolated tests for the PRO shopping list router.

    These tests mount only the /api/v1/pro/meal/shopping-list endpoint on a fresh
    FastAPI app and override auth/dependencies as needed.
    """

    app: FastAPI
    client: TestClient
    mod: Any

    @pytest.fixture(autouse=True)
    def _no_sleep(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Prevent accidental time.sleep calls from causing flakiness under xdist."""

        monkeypatch.setattr(time, "sleep", lambda *_a, **_kw: None)

    def setup_method(self) -> None:
        import app.routers.shopping_list_pro as shopping_mod

        self.mod = shopping_mod
        self.app = FastAPI()
        self.app.include_router(self.mod.router)
        self.app.dependency_overrides = {}
        self.client = TestClient(self.app)

    def teardown_method(self) -> None:
        self.client.close()
        self.app.dependency_overrides.clear()

    def _pro_ok(self) -> None:
        """Bypass PRO tier checks by overriding require_pro_tier."""

        self.app.dependency_overrides[self.mod.require_pro_tier] = lambda: "test_pro_key"

    def _assert_generator_not_called_on_guard(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure generate_shopping_list_from_plan is never called on guard failures."""

        def _unexpected_generator_call(*_args: Any, **_kwargs: Any) -> None:
            raise AssertionError(
                "generate_shopping_list_from_plan must not be called on 4xx/5xx guard failures"
            )

        monkeypatch.setattr(
            self.mod,
            "generate_shopping_list_from_plan",
            _unexpected_generator_call,
        )

    def test_generate_shopping_list_requires_pro_auth(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Requests without PRO auth should be rejected before generator is called."""

        # Do not override require_pro_tier here: we want the auth guard to run.
        def _boom(**_kwargs: Any) -> None:
            raise AssertionError(
                "generate_shopping_list_from_plan must not be called without PRO access"
            )

        monkeypatch.setattr(self.mod, "generate_shopping_list_from_plan", _boom)

        payload: Dict[str, Any] = {"plan_data": {"days": []}}

        resp = self.client.post("/api/v1/pro/meal/shopping-list", json=payload)
        assert resp.status_code in (401, 403), resp.text

    def test_generate_shopping_list_200_inline_plan(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Happy path: inline plan_data with valid preferences returns 200."""

        self._pro_ok()

        expected: Dict[str, Any] = {
            "categories": [],
            "total_items": 1,
            "generated_at": "2025-01-01T00:00:00Z",
            "meta": {
                "source": "inline_plan",
                "unit_system": "metric",
                "warnings": [],
            },
        }

        captured: Dict[str, Any] = {}
        monkeypatch.setattr(
            self.mod.fitchef_runtime,
            "run_shopping_followup_task",
            make_mock_run_shopping_followup_task(
                shopping_list=expected,
                capture=captured,
            ),
        )

        payload: Dict[str, Any] = {
            "plan_data": {"days": []},
            "preferences": {
                "group_by": "category",
                "unit_system": "metric",
                "exclude_items": [],
                "dietary_tags": [],
            },
        }

        resp = self.client.post("/api/v1/pro/meal/shopping-list", json=payload)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total_items"] == 1
        assert body["meta"]["source"] == "inline_plan"
        assert body["meta"]["unit_system"] == "metric"
        assert captured["task_type"] == "shopping_followup"
        assert captured["plan_data"] == {"days": []}
        assert captured["preferences"].unit_system == "metric"
        assert captured["shopping_list_builder"] is self.mod.generate_shopping_list_from_plan

    def test_generate_shopping_list_422_group_by_recipe_not_supported(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """group_by='recipe' should be rejected with 422, as per router guard."""

        self._assert_generator_not_called_on_guard(monkeypatch)
        self._pro_ok()

        payload: Dict[str, Any] = {
            "plan_data": {"days": []},
            "preferences": {
                "group_by": "recipe",
                "unit_system": "metric",
                "exclude_items": [],
                "dietary_tags": [],
            },
        }

        resp = self.client.post("/api/v1/pro/meal/shopping-list", json=payload)
        assert resp.status_code == 422, resp.text
        assert "group_by='recipe' is not supported yet" in resp.json()["detail"]

    def test_generate_shopping_list_422_imperial_not_supported(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """unit_system='imperial' should be rejected with 422."""

        self._assert_generator_not_called_on_guard(monkeypatch)
        self._pro_ok()

        payload: Dict[str, Any] = {
            "plan_data": {"days": []},
            "preferences": {
                "group_by": "category",
                "unit_system": "imperial",
                "exclude_items": [],
                "dietary_tags": [],
            },
        }

        resp = self.client.post("/api/v1/pro/meal/shopping-list", json=payload)
        assert resp.status_code == 422, resp.text
        assert "unit_system='imperial' is not supported yet" in resp.json()["detail"]

    def test_generate_shopping_list_422_exclude_or_tags_not_supported(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """exclude_items or dietary_tags should currently be rejected with 422."""

        self._assert_generator_not_called_on_guard(monkeypatch)
        self._pro_ok()

        payload: Dict[str, Any] = {
            "plan_data": {"days": []},
            "preferences": {
                "group_by": "category",
                "unit_system": "metric",
                "exclude_items": ["milk"],
                "dietary_tags": [],
            },
        }

        resp = self.client.post("/api/v1/pro/meal/shopping-list", json=payload)
        assert resp.status_code == 422, resp.text
        assert "exclude_items and dietary_tags are not supported yet" in resp.json()["detail"]

    def test_generate_shopping_list_501_weekly_plan_id_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """weekly_plan_id path is stubbed and should return 501 Not Implemented."""

        self._assert_generator_not_called_on_guard(monkeypatch)
        self._pro_ok()

        payload: Dict[str, Any] = {
            "weekly_plan_id": "plan_abc123",
            "preferences": {
                "group_by": "category",
                "unit_system": "metric",
                "exclude_items": [],
                "dietary_tags": [],
            },
        }

        resp = self.client.post("/api/v1/pro/meal/shopping-list", json=payload)
        assert resp.status_code == 501, resp.text
        assert "weekly_plan_id support not yet implemented" in resp.json()["detail"]

    def test_generate_shopping_list_422_xor_validation_no_sources(self) -> None:
        """Pydantic model should enforce XOR: missing both sources → 422."""

        self._pro_ok()

        payload: Dict[str, Any] = {
            "preferences": {
                "group_by": "category",
                "unit_system": "metric",
                "exclude_items": [],
                "dietary_tags": [],
            },
        }

        resp = self.client.post("/api/v1/pro/meal/shopping-list", json=payload)
        assert resp.status_code == 422, resp.text
        # Detail format is Pydantic error list; we just check it mentions weekly_plan_id/plan_data.
        detail_str = str(resp.json()["detail"]).lower()
        assert "weekly_plan_id" in detail_str or "plan_data" in detail_str

    def test_generate_shopping_list_422_xor_validation_both_sources(self) -> None:
        """Pydantic model should enforce XOR: both sources provided → 422."""

        self._pro_ok()

        payload: Dict[str, Any] = {
            "weekly_plan_id": "plan_abc123",
            "plan_data": {"days": []},
            "preferences": {
                "group_by": "category",
                "unit_system": "metric",
                "exclude_items": [],
                "dietary_tags": [],
            },
        }

        resp = self.client.post("/api/v1/pro/meal/shopping-list", json=payload)
        assert resp.status_code == 422, resp.text
        # Detail format is Pydantic error list; we just check it mentions weekly_plan_id/plan_data.
        detail_str = str(resp.json()["detail"]).lower()
        assert "weekly_plan_id" in detail_str or "plan_data" in detail_str


@pytest.mark.asyncio
async def test_generate_shopping_list_plan_data_none_guard() -> None:
    """Guard against missing plan_data when validation is bypassed."""
    from app.routers.shopping_list_pro import generate_shopping_list
    from app.schemas.shopping_list import ShoppingListPreferences, ShoppingListRequest

    request = ShoppingListRequest.model_construct(
        weekly_plan_id=None,
        plan_data=None,
        preferences=ShoppingListPreferences(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await generate_shopping_list(request)

    assert exc_info.value.status_code == 500
    assert "plan_data is None" in exc_info.value.detail


def test_generate_shopping_list_runtime_exception_no_leak(
    app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
    pro_headers: dict[str, str],
) -> None:
    """Unexpected runtime errors stay sanitized. / Ошибки runtime остаются без утечки деталей."""

    import app.routers.shopping_list_pro as shopping_mod

    async def _explode(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("traceback /private/tmp/internal.py secret-token")

    monkeypatch.setattr(shopping_mod.fitchef_runtime, "run_shopping_followup_task", _explode)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/pro/meal/shopping-list",
            json={"plan_data": {"daily_menus": []}},
            headers=pro_headers,
        )

    assert response.status_code == 500
    content_type = response.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        detail = str(response.json().get("detail", ""))
    else:
        detail = response.text
    lowered = detail.lower()
    assert "traceback" not in lowered
    assert "internal.py" not in lowered
    assert "secret-token" not in lowered
