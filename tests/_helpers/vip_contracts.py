"""Shared VIP response contract assertions for tests."""

from __future__ import annotations

from typing import Any, Mapping


def assert_json_response_payload(response: Any) -> Any:
    """Assert JSON content type before parsing a TestClient response."""

    assert response.headers.get("content-type", "").startswith("application/json")
    return response.json()


def assert_vip_shoplist_formats_contract(payload: Mapping[str, Any]) -> None:
    """Assert the static VIP shoplist formats response contract."""

    assert payload["status"] == "success"
    assert payload["formats"] == ["json", "csv", "text"]
    assert payload["locales"] == ["ru", "en", "es"]


def assert_vip_shoplist_formats_response(response: Any) -> None:
    """Assert the static VIP shoplist formats response from TestClient."""

    payload = assert_json_response_payload(response)
    assert_vip_shoplist_formats_contract(payload)
