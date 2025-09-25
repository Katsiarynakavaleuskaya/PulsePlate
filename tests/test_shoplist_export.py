"""Tests for the public shoplist export endpoints."""

from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_shoplist_json_structure():
    response = client.get("/api/v1/shoplist")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("groups"), list)
    assert data["groups"], "Expected at least one group in response"
    assert isinstance(data.get("items"), list)
    assert data["items"], "Expected flattened items list"


def test_export_csv_headers_and_rows():
    response = client.get("/api/v1/shoplist/export.csv")
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "text/csv" in content_type
    disposition = response.headers.get("content-disposition", "")
    assert "attachment" in disposition

    lines = [line for line in response.text.splitlines() if line]
    assert lines, "CSV payload should not be empty"
    assert lines[0] == "aisle,name,qty,unit,note"
    assert len(lines) > 1, "CSV should contain data rows"


def test_export_pdf_headers():
    response = client.get("/api/v1/shoplist/export.pdf")
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "application/pdf" in content_type
    disposition = response.headers.get("content-disposition", "")
    assert "attachment" in disposition
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 1000
