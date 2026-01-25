import pytest
from fastapi.testclient import TestClient

from settings import PRIVATE_EXPORTS_ENABLED

# export_client fixture moved to tests/conftest.py


def _signed_url(client, path: str) -> str:
    response = client.post(
        "/api/v1/export/sign",
        json={"path": path, "ttl_seconds": 60},
        headers={"X-API-Key": "test_key"},
    )
    assert response.status_code == 200
    return response.json()["url"]


def test_signed_csv_flow(export_client: TestClient) -> None:
    url = _signed_url(export_client, "/api/v1/plan/week/export.csv")
    response = export_client.get(url, headers={"X-API-Key": "test_key"})
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")


def test_signed_pdf_flow(export_client: TestClient) -> None:
    url = _signed_url(export_client, "/api/v1/plan/week/export.pdf")
    response = export_client.get(url, headers={"X-API-Key": "test_key"})
    assert response.status_code == 200
    assert "application/pdf" in response.headers.get("content-type", "")
    assert response.content.startswith(b"%PDF")


def test_missing_token_rejected(export_client: TestClient) -> None:
    if not PRIVATE_EXPORTS_ENABLED:
        return
    response = export_client.get("/api/v1/plan/week/export.csv")
    assert response.status_code == 403
