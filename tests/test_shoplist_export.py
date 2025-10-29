"""Tests for the public shoplist export endpoints."""

from typing import List

import pytest

pytest.importorskip("app.routers.shoplist_export")
from app.routers import shoplist_export as export


def test_shoplist_json_structure(client):
    response = client.get("/api/v1/shoplist", headers={"X-API-Key": "test_key"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("groups"), list)
    assert data["groups"], "Expected at least one group in response"
    assert isinstance(data.get("items"), list)
    assert data["items"], "Expected flattened items list"


def test_export_csv_headers_and_rows(client):
    response = client.get(
        "/api/v1/shoplist/export.csv",
        headers={"X-API-Key": "test_key"},
    )
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "text/csv" in content_type
    disposition = response.headers.get("content-disposition", "")
    assert "attachment" in disposition

    lines = [line for line in response.text.splitlines() if line]
    assert lines, "CSV payload should not be empty"
    assert lines[0] == "aisle,name,qty,unit,note"
    assert len(lines) > 1, "CSV should contain data rows"


def test_export_pdf_headers(client):
    response = client.get(
        "/api/v1/shoplist/export.pdf",
        headers={"X-API-Key": "test_key"},
    )
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "application/pdf" in content_type
    disposition = response.headers.get("content-disposition", "")
    assert "attachment" in disposition
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 1000


def test_export_pdf_auth_errors(client):
    # Missing key
    response = client.get("/api/v1/shoplist/export.pdf")
    assert response.status_code == 403
    # Wrong key
    response = client.get("/api/v1/shoplist/export.pdf", headers={"X-API-Key": "wrong"})
    assert response.status_code == 403


def test_flatten_shop_items_skip_invalid() -> None:
    groups = [
        {
            "aisle": "Test",
            "items": [
                {"name": "Valid", "qty": 1, "unit": "pcs"},
                "unexpected",  # type: ignore[list-item]
            ],
        }
    ]

    rows = export._flatten_shop_items(groups)  # type: ignore[access-private-member]
    assert len(rows) == 1
    assert rows[0]["name"] == "Valid"


def test_register_font_returns_custom(monkeypatch, tmp_path) -> None:
    font_file = tmp_path / "dummy.ttf"
    font_file.write_bytes(b"fake-font")

    monkeypatch.setattr(export, "FONT_PATH", font_file)

    registered: List[str] = []

    def fake_get_names() -> List[str]:
        return registered.copy()

    def fake_register(tt_font) -> None:  # pragma: no cover - simple state mutation
        registered.append(export.FONT_NAME)

    monkeypatch.setattr(export.pdfmetrics, "getRegisteredFontNames", fake_get_names)
    monkeypatch.setattr(export.pdfmetrics, "registerFont", fake_register)
    monkeypatch.setattr(export, "TTFont", lambda name, path: (name, path))

    result = export._register_font_if_available()  # type: ignore[access-private-member]
    assert result == export.FONT_NAME
    assert export.FONT_NAME in registered


def test_render_pdf_uses_groups_when_items_missing(monkeypatch) -> None:
    # Force Helvetica to avoid interacting with real font files during this test.
    monkeypatch.setattr(export, "_register_font_if_available", lambda: "Helvetica")

    many_items = [{"name": f"Item {i}", "qty": i + 1, "unit": "g"} for i in range(70)]
    shop = {
        "store": "Demo",
        "currency": "USD",
        "groups": [{"aisle": "Bulk", "items": many_items}],
        "items": [],
    }

    pdf_bytes = export._render_pdf(shop)  # type: ignore[access-private-member]
    assert pdf_bytes.startswith(b"%PDF")
    # Multi-page output contains multiple /Type /Page markers; ensure at least two.
    assert pdf_bytes.count(b"/Type /Page") >= 2
