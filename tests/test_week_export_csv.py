"""Tests for weekly CSV export."""

import pytest

# export_client fixture moved to tests/conftest.py


def _signed_csv_url(client):
    response = client.post(
        "/api/v1/export/sign",
        json={"path": "/api/v1/plan/week/export.csv"},
        headers={"X-API-Key": "test_key"},
    )
    assert response.status_code == 200
    return response.json()["url"]


def test_week_export_csv_ok(export_client):
    url = _signed_csv_url(export_client)
    response = export_client.get(url, headers={"X-API-Key": "test_key"})
    assert response.status_code == 200
    lines = response.text.splitlines()
    assert lines[0].startswith("# WEEK_TOTALS")
    assert lines[1] == "date,day_idx,meal,item,qty,unit,energy_kcal,protein_g,carbs_g,fat_g,note"
    assert len(lines) >= 3
