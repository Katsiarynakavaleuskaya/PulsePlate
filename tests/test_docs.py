from __future__ import annotations

from fastapi.testclient import TestClient


def test_openapi_json_available(client: TestClient) -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    body = r.json()
    assert "paths" in body
    assert "/api/v1/bmi" in body["paths"]


def test_docs_available(client: TestClient) -> None:
    r = client.get("/docs")
    assert r.status_code == 200
