from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.routers.shopping_list_pro as shopping_list_pro


@pytest.mark.parametrize(
    ("payload", "use_pro_headers", "expected_status"),
    [
        ({"plan_data": {"daily_menus": []}}, False, (401, 403)),
        (
            {
                "plan_data": {"daily_menus": []},
                "preferences": {"group_by": "recipe", "unit_system": "metric"},
            },
            True,
            (422,),
        ),
        (
            {"plan_data": {"daily_menus": []}, "weekly_plan_id": "plan_1"},
            True,
            (422,),
        ),
        (
            {"plan_data": {"daily_menus": []}, "preferences": {"unit_system": "imperial"}},
            True,
            (422,),
        ),
    ],
)
def test_plan_to_shoplist_negative_matrix(
    client: TestClient,
    pro_headers: dict[str, str],
    payload: dict[str, Any],
    use_pro_headers: bool,
    expected_status: tuple[int, ...],
) -> None:
    """Validate stable status and envelope for key negative scenarios."""
    request_headers = pro_headers if use_pro_headers else {}
    response = client.post(
        "/api/v1/pro/meal/shopping-list",
        json=payload,
        headers=request_headers,
    )

    assert response.status_code in expected_status, response.text
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert isinstance(body, dict)
    assert "detail" in body


def test_plan_to_shoplist_unhandled_exception_no_leak(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unexpected exceptions must not leak traceback/internal paths in body."""
    import app.main
    from app.middleware.api_tiers import TEST_KEY_PRO

    def _explode(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("traceback /private/tmp/internal.py secret-token")

    monkeypatch.setattr(shopping_list_pro, "generate_shopping_list_from_plan", _explode)

    with TestClient(app.main.app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/pro/meal/shopping-list",
            json={"plan_data": {"daily_menus": []}},
            headers={"X-API-Key": TEST_KEY_PRO},
        )

    assert response.status_code == 500
    content_type = response.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        body = response.json()
        assert isinstance(body, dict)
        detail = str(body.get("detail", ""))
    else:
        detail = response.text
    lowered = detail.lower()
    assert "traceback" not in lowered
    assert "internal.py" not in lowered
    assert "secret-token" not in lowered
