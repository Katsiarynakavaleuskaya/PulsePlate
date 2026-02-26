from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest


def test_pro_food_attribution_requires_api_key(client: TestClient) -> None:
    response = client.get("/api/v1/pro/attribution")
    assert response.status_code in {401, 403}


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
    assert response.headers.get("content-type", "").startswith("application/json")
    payload = response.json()

    assert "generated_at_utc" in payload
    assert isinstance(payload["generated_at_utc"], str)
    generated_at = payload["generated_at_utc"]
    assert generated_at.endswith("+00:00")
    assert "." not in generated_at
    parsed = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    assert parsed.microsecond == 0
    assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)
    assert payload["sources"] == [
        {
            "source": "Open Food Facts",
            "license": "Open Database License (ODbL) v1.0",
            "attribution": "Contains Open Food Facts data licensed under ODbL v1.0.",
            "source_url": "https://world.openfoodfacts.org/",
        }
    ]
