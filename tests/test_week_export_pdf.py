"""Tests for weekly plan PDF export."""

from pathlib import Path
from typing import List, Any

import pytest
from fastapi.testclient import TestClient

from reportlab.platypus import Paragraph, Table

from app import app
from app.routers import plan_export as plan


client = TestClient(app)


def _signed_pdf_url(lang: str = "en") -> str:
    response = client.post("/api/v1/export/sign", json={"path": "/api/v1/plan/week/export.pdf"})
    assert response.status_code == 200
    url = response.json()["url"]
    if lang:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}lang={lang}"
    return url


def test_week_export_pdf_ok() -> None:
    url = _signed_pdf_url()
    response = client.get(url)
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "application/pdf" in content_type
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 2000


def test_register_font_uses_custom_font(monkeypatch, tmp_path) -> None:
    font_file = tmp_path / "dejavu.ttf"
    font_file.write_bytes(b"dummy")
    monkeypatch.setattr(plan, "FONT_PATH", font_file)

    registered: List[str] = []

    def fake_get_fonts() -> List[str]:
        return registered.copy()

    def fake_register(font_obj: Any) -> None:  # pragma: no cover - simple append
        registered.append(plan.FONT_NAME)

    monkeypatch.setattr(plan.pdfmetrics, "getRegisteredFontNames", fake_get_fonts)
    monkeypatch.setattr(plan.pdfmetrics, "registerFont", fake_register)
    monkeypatch.setattr(plan, "TTFont", lambda name, path: (name, path))

    assert plan._register_font() == plan.FONT_NAME  # type: ignore[access-private-member]
    assert plan.FONT_NAME in registered


def test_pdf_uses_page_breaks(monkeypatch) -> None:
    def fake_plan() -> dict[str, Any]:
        return {
            "days": [
                {
                    "date": f"2025-09-{i:02d}",
                    "meals": [
                        {
                            "name": "Meal",
                            "items": [
                                {
                                    "name": "Item",
                                    "qty": 1,
                                    "unit": "g",
                                    "energy_kcal": 100,
                                }
                            ],
                        }
                    ],
                }
                for i in range(1, 6)
            ]
        }

    monkeypatch.setattr(plan, "_get_week_plan", fake_plan)
    monkeypatch.setattr(plan, "_register_font", lambda: "Helvetica")

    url = _signed_pdf_url()
    response = client.get(url)
    assert response.status_code == 200
    assert response.content.count(b"/Type /Page") >= 2


def test_pdf_includes_brand_header_and_totals(monkeypatch) -> None:
    captured_story: List[Any] = []

    class DummyDoc:
        def __init__(self, buf, **kwargs):
            self._buf = buf
            pagesize = kwargs.get("pagesize", None)
            if pagesize is not None:
                width = pagesize[0]
            else:  # pragma: no cover - fallback
                width = 595.27  # default A4 width in points
            left = kwargs.get("leftMargin", 0)
            right = kwargs.get("rightMargin", 0)
            self.width = width - left - right

        def build(self, story):  # type: ignore[override]
            captured_story.extend(story)
            self._buf.write(b"%PDF-Fake")

    monkeypatch.setattr(plan, "SimpleDocTemplate", DummyDoc)
    monkeypatch.setattr(plan, "_register_font", lambda: "Helvetica")

    url = _signed_pdf_url()
    response = client.get(url)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")

    header_table = next(
        (
            node
            for node in captured_story
            if isinstance(node, Table)
            and len(node._cellvalues) >= 2
            and len(node._cellvalues[0]) >= 2
            and hasattr(node._cellvalues[0][1], "getPlainText")
            and "PulsePlate" in node._cellvalues[0][1].getPlainText()
        ),
        None,
    )
    assert header_table is not None
    assert plan.SLOGAN["en"] in header_table._cellvalues[1][1].getPlainText()

    totals_table = next(
        (
            node
            for node in captured_story
            if isinstance(node, Table)
            and len(getattr(node, "_cellvalues", [])) >= 2
            and node._cellvalues[0] == ["ккал", "Б", "У", "Ж"]
        ),
        None,
    )
    assert totals_table is not None


def test_find_logo_path_prefers_existing(tmp_path, monkeypatch) -> None:
    missing = tmp_path / "missing.png"
    present = tmp_path / "fitchef.png"
    present.write_bytes(b"fake")

    monkeypatch.setattr(plan, "LOGO_CANDIDATES", (missing, present))

    assert plan._find_logo_path() == present


def test_find_logo_path_returns_none_when_absent(monkeypatch) -> None:
    monkeypatch.setattr(plan, "LOGO_CANDIDATES", (Path("no_such_logo.png"),))
    assert plan._find_logo_path() is None


def test_branded_header_without_logo(monkeypatch) -> None:
    monkeypatch.setattr(plan, "_find_logo_path", lambda: None)
    monkeypatch.setattr(plan, "Image", lambda *args, **kwargs: None)

    styles = plan.getSampleStyleSheet()
    styles.add(plan.ParagraphStyle(name="BaseTest", fontName="Helvetica"))
    for key in ("Heading1", "Heading2", "Heading3", "Heading4", "Normal"):
        styles[key].fontName = "Helvetica"

    story: List[Any] = []
    plan._branded_header(story, styles, "Helvetica", doc_width=500, lang="en")

    assert story
    assert any(isinstance(node, plan.Table) for node in story)


def test_branded_header_with_logo(monkeypatch, tmp_path) -> None:
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"fake")

    captured: dict[str, str] = {}

    def fake_image(path, *args, **kwargs):
        captured["path"] = path
        return "IMAGE"

    monkeypatch.setattr(plan, "_find_logo_path", lambda: logo)
    monkeypatch.setattr(plan, "Image", fake_image)

    styles = plan.getSampleStyleSheet()
    styles.add(plan.ParagraphStyle(name="BaseTestWithLogo", fontName="Helvetica"))
    for key in ("Heading1", "Heading2", "Heading3", "Heading4", "Normal"):
        styles[key].fontName = "Helvetica"

    story: List[Any] = []
    plan._branded_header(story, styles, "Helvetica", doc_width=500, lang="en")

    assert captured["path"] == str(logo)


def test_branded_header_localizes_slogan() -> None:
    styles = plan.getSampleStyleSheet()
    for key in ("Heading1", "Heading2", "Heading3", "Heading4", "Normal"):
        styles[key].fontName = "Helvetica"

    story: List[Any] = []
    plan._branded_header(story, styles, "Helvetica", doc_width=500, lang="de")

    header_table = next(
        node
        for node in story
        if isinstance(node, plan.Table)
        and len(node._cellvalues) >= 2
        and len(node._cellvalues[0]) >= 2
        and hasattr(node._cellvalues[0][1], "getPlainText")
        and "PulsePlate" in node._cellvalues[0][1].getPlainText()
    )
    assert plan.SLOGAN["de"] in header_table._cellvalues[1][1].getPlainText()


def test_slogan_fallback_to_default() -> None:
    assert plan._slogan("ru") == plan.SLOGAN["ru"]
    assert plan._slogan("de") == plan.SLOGAN["de"]
    assert plan._slogan("unknown") == plan.SLOGAN[plan.DEFAULT_LANG]


def test_pdf_honors_lang_query(monkeypatch) -> None:
    captured_story: List[Any] = []

    class DummyDoc:
        def __init__(self, buf, **kwargs):
            self._buf = buf
            width = kwargs.get("pagesize", (595.27,))[0]
            left = kwargs.get("leftMargin", 0)
            right = kwargs.get("rightMargin", 0)
            self.width = width - left - right

        def build(self, story):  # type: ignore[override]
            captured_story.extend(story)
            self._buf.write(b"%PDF-Fake")

    monkeypatch.setattr(plan, "SimpleDocTemplate", DummyDoc)
    monkeypatch.setattr(plan, "_register_font", lambda: "Helvetica")

    url = _signed_pdf_url("ru")
    response = client.get(url)
    assert response.status_code == 200

    header_table = next(
        node
        for node in captured_story
        if isinstance(node, plan.Table)
        and len(node._cellvalues) >= 2
        and len(node._cellvalues[0]) >= 2
        and hasattr(node._cellvalues[0][1], "getPlainText")
        and "PulsePlate" in node._cellvalues[0][1].getPlainText()
    )
    assert plan.SLOGAN["ru"] in header_table._cellvalues[1][1].getPlainText()
