from __future__ import annotations

from fastapi.testclient import TestClient
import pytest


def test_pro_food_attribution_requires_api_key(client: TestClient) -> None:
    response = client.get("/api/v1/pro/attribution")
    assert response.status_code == 401
    assert response.json()["detail"] == "API key required for PRO tier access"


def test_pro_food_attribution_returns_license_payload(
    client: TestClient,
    pro_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers import pro_food_attribution

    monkeypatch.setattr(
        pro_food_attribution.food_store,
        "get_food_source_attributions",
        lambda: [
            {
                "source": "Open Food Facts",
                "license": "Open Database License (ODbL) v1.0",
                "attribution": "Contains Open Food Facts data licensed under ODbL v1.0.",
                "source_url": "https://world.openfoodfacts.org/",
            }
        ],
    )

    response = client.get("/api/v1/pro/attribution", headers=pro_headers)
    assert response.status_code == 200, response.text
    payload = response.json()

    assert "generated_at_utc" in payload
    assert isinstance(payload["generated_at_utc"], str)
    assert payload["sources"] == [
        {
            "source": "Open Food Facts",
            "license": "Open Database License (ODbL) v1.0",
            "attribution": "Contains Open Food Facts data licensed under ODbL v1.0.",
            "source_url": "https://world.openfoodfacts.org/",
        }
    ]
