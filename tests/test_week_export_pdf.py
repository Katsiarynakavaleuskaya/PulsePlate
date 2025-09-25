"""Tests for weekly plan PDF export."""

from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_week_export_pdf_ok() -> None:
    response = client.get("/api/v1/plan/week/export.pdf")
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "application/pdf" in content_type
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 2000
