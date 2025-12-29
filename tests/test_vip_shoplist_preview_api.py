from __future__ import annotations

from typing import cast

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp


def _make_client() -> TestClient:
    import app

    return TestClient(cast(ASGIApp, app.app))


def test_vip_shoplist_preview_flag_off_returns_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIP_MODULE_ENABLED", "false")
    monkeypatch.setenv("API_KEY", "test_vip_key")

    client = _make_client()
    r = client.get("/api/v1/vip/shoplist/preview", headers={"X-API-Key": "test_vip_key"})
    assert r.status_code == 404


def test_vip_shoplist_preview_flag_on_returns_200_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "test_vip_key")

    client = _make_client()
    r1 = client.get("/api/v1/vip/shoplist/preview", headers={"X-API-Key": "test_vip_key"})
    r2 = client.get("/api/v1/vip/shoplist/preview", headers={"X-API-Key": "test_vip_key"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json() == r2.json()

    payload = r1.json()
    assert payload["meta"]["preview"] is True
    assert payload["meta"]["prices_included"] is False
    assert payload["meta"]["currency"] is None
    assert isinstance(payload["items"], list)
    assert len(payload["items"]) >= 1
    assert {"category", "name", "quantity"} <= set(payload["items"][0].keys())
