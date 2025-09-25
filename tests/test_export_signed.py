from fastapi.testclient import TestClient

from app import app
from settings import PRIVATE_EXPORTS_ENABLED

client = TestClient(app)


def _signed_url(path: str) -> str:
    response = client.post("/api/v1/export/sign", json={"path": path, "ttl_seconds": 60})
    assert response.status_code == 200
    return response.json()["url"]


def test_signed_csv_flow() -> None:
    url = _signed_url("/api/v1/plan/week/export.csv")
    response = client.get(url)
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")


def test_signed_pdf_flow() -> None:
    url = _signed_url("/api/v1/plan/week/export.pdf")
    response = client.get(url)
    assert response.status_code == 200
    assert "application/pdf" in response.headers.get("content-type", "")
    assert response.content.startswith(b"%PDF")


def test_missing_token_rejected() -> None:
    if not PRIVATE_EXPORTS_ENABLED:
        return
    response = client.get("/api/v1/plan/week/export.csv")
    assert response.status_code == 403
