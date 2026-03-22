"""Contract tests for direct FastAPI ``GET /`` (bypassing Caddy / static apex)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import app
from app.bootstrap.direct_api_root import LEGACY_BMI_WEB_ROUTE


def test_get_slash_returns_json_probe() -> None:
    """Direct ``GET /`` must return a stable JSON envelope for operators."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    data = response.json()
    assert data["service"] == "pulseplate-api"
    assert data["surface"] == "api"
    assert "message" in data
    assert "SPA" in data["message"]
    links = data["links"]
    assert links["health"] == "/health"
    assert links["docs"] == "/docs"
    assert links["openapi"] == "/openapi.json"
    assert links["legacy_bmi_web_ui"] == LEGACY_BMI_WEB_ROUTE


def test_legacy_bmi_web_route_serves_html() -> None:
    """Embedded legacy calculator remains available for manual smoke tests."""
    client = TestClient(app)
    response = client.get(LEGACY_BMI_WEB_ROUTE)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "BMI Calculator" in response.text
