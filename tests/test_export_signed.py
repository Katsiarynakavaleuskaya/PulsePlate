import pytest
from fastapi.testclient import TestClient

from app.routers import plan_export
from app.routers import shoplist_export
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
    url = _signed_url(export_client, plan_export.WEEK_EXPORT_CSV_PATH)
    response = export_client.get(url, headers={"X-API-Key": "test_key"})
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")


def test_signed_pdf_flow(export_client: TestClient) -> None:
    url = _signed_url(export_client, plan_export.WEEK_EXPORT_PDF_PATH)
    response = export_client.get(url, headers={"X-API-Key": "test_key"})
    assert response.status_code == 200
    assert "application/pdf" in response.headers.get("content-type", "")
    assert response.content.startswith(b"%PDF")


def test_missing_token_rejected(export_client: TestClient) -> None:
    if not PRIVATE_EXPORTS_ENABLED:
        return
    response = export_client.get(plan_export.WEEK_EXPORT_CSV_PATH)
    assert response.status_code == 403


def test_signed_shoplist_pdf_flow(export_client: TestClient) -> None:
    url = _signed_url(export_client, shoplist_export.SHOPLIST_EXPORT_PDF_PATH)
    response = export_client.get(url, headers={"X-API-Key": "test_key"})
    assert response.status_code == 200
    assert "application/pdf" in response.headers.get("content-type", "")
    assert response.content.startswith(b"%PDF")


def test_sign_route_rejects_non_allowlisted_path(export_client: TestClient) -> None:
    response = export_client.post(
        "/api/v1/export/sign",
        json={"path": "/api/v1/users", "ttl_seconds": 60},
        headers={"X-API-Key": "test_key"},
    )
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"] == "path is not signable"
