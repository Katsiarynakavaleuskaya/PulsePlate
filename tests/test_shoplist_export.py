"""Tests for the public shoplist export endpoints."""

from types import SimpleNamespace
import logging
from pathlib import Path
from typing import List

import pytest

from app.routers import shoplist_export as export


class FakeTTFError(Exception):
    """Local stand-in for reportlab's TTFError in lazy-import tests."""


def _patch_lazy_reportlab(
    monkeypatch: pytest.MonkeyPatch,
    *,
    registered_names: List[str] | None = None,
    register_font=None,
    tt_font=None,
) -> List[str]:
    """Patch lazy reportlab loading with a controllable in-memory fake."""

    seen_names = registered_names if registered_names is not None else []
    fake_pdfmetrics = SimpleNamespace(
        getRegisteredFontNames=lambda: seen_names.copy(),
        registerFont=register_font or (lambda font: seen_names.append(export.FONT_NAME)),
    )
    fake_tt_font = tt_font or (lambda name, path: (name, path))
    fake_canvas = SimpleNamespace(Canvas=object)
    monkeypatch.setattr(
        export,
        "_lazy_reportlab",
        lambda: (object(), fake_pdfmetrics, fake_tt_font, FakeTTFError, fake_canvas),
    )
    return seen_names


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
    registered = _patch_lazy_reportlab(monkeypatch)

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


def test_register_font_fallback_when_font_file_missing(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that missing font file logs debug message and falls back to Helvetica."""
    fake_path = Path("/__no_such__/DejaVuSans.ttf")
    monkeypatch.setattr(export, "FONT_PATH", fake_path)
    # Do NOT mock Path.exists - let it naturally return False

    with caplog.at_level(logging.DEBUG):
        result = export._register_font_if_available()  # type: ignore[access-private-member]

    assert result == "Helvetica"
    assert "Bundled font file not found" in caplog.text
    assert str(fake_path) in caplog.text
    assert "using Helvetica fallback" in caplog.text


def test_register_font_fallback_on_ttfont_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    """Test that TTFont error triggers warning log and falls back to Helvetica."""
    font_file = tmp_path / "dummy.ttf"
    font_file.write_bytes(b"fake-font")
    monkeypatch.setattr(export, "FONT_PATH", font_file)
    _patch_lazy_reportlab(
        monkeypatch,
        tt_font=lambda name, path: (_ for _ in ()).throw(FakeTTFError("Invalid font file")),
    )

    with caplog.at_level(logging.WARNING):
        result = export._register_font_if_available()  # type: ignore[access-private-member]

    assert result == "Helvetica"
    assert "Font registration failed" in caplog.text
    assert "falling back to Helvetica" in caplog.text


def test_register_font_fallback_on_oserror(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    """Test that OSError during font registration triggers warning and fallback."""
    font_file = tmp_path / "dummy.ttf"
    font_file.write_bytes(b"fake-font")
    monkeypatch.setattr(export, "FONT_PATH", font_file)
    _patch_lazy_reportlab(
        monkeypatch,
        tt_font=lambda name, path: (_ for _ in ()).throw(OSError("Font file cannot be opened")),
    )

    with caplog.at_level(logging.WARNING):
        result = export._register_font_if_available()  # type: ignore[access-private-member]

    assert result == "Helvetica"
    assert "Font registration failed" in caplog.text
    assert "falling back to Helvetica" in caplog.text


def test_register_font_fallback_on_valueerror(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    """Test that ValueError during font registration triggers warning and fallback."""
    font_file = tmp_path / "dummy.ttf"
    font_file.write_bytes(b"fake-font")
    monkeypatch.setattr(export, "FONT_PATH", font_file)
    _patch_lazy_reportlab(
        monkeypatch,
        register_font=lambda tt_font: (_ for _ in ()).throw(ValueError("Font registration failed")),
        tt_font=lambda name, path: object(),
    )

    with caplog.at_level(logging.WARNING):
        result = export._register_font_if_available()  # type: ignore[access-private-member]

    assert result == "Helvetica"
    assert "Font registration failed" in caplog.text
    assert "falling back to Helvetica" in caplog.text


def test_export_pdf_returns_501_when_reportlab_missing(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PDF endpoint must fail closed with 501 when optional deps are unavailable."""

    monkeypatch.setattr(
        export,
        "_lazy_reportlab",
        lambda: (_ for _ in ()).throw(ImportError("reportlab is missing")),
    )

    response = client.get(
        "/api/v1/shoplist/export.pdf",
        headers={"X-API-Key": "test_key"},
    )

    assert response.status_code == 501
    assert response.json()["detail"] == "PDF export is not available"
