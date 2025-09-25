"""Tests for weekly plan CSV export."""

from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def _signed_csv_url() -> str:
    response = client.post("/api/v1/export/sign", json={"path": "/api/v1/plan/week/export.csv"})
    assert response.status_code == 200
    return response.json()["url"]


def test_week_export_csv_ok() -> None:
    url = _signed_csv_url()
    response = client.get(url)
    assert response.status_code == 200

    content_type = response.headers.get("content-type", "")
    disposition = response.headers.get("content-disposition", "")
    assert "text/csv" in content_type
    assert "attachment" in disposition

    lines = response.text.splitlines()
    assert lines
    assert lines[0] == "date,day_idx,meal,item,qty,unit,energy_kcal,protein_g,carbs_g,fat_g,note"
