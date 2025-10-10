"""Tests for weekly plan PDF export."""

from io import BytesIO
import os
from pathlib import Path
import sys
from typing import Any

from fastapi.testclient import TestClient
import pytest
from reportlab.platypus import Paragraph, Table


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app from app.py file
import importlib.util


spec = importlib.util.spec_from_file_location("app_module", "app.py")
if spec is None or spec.loader is None:
    raise ImportError("Cannot load app.py")

app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app
from app.routers import plan_export as plan


client = TestClient(app)


# export_client fixture moved to tests/conftest.py


from datetime import UTC

from fastapi.testclient import TestClient


def _signed_pdf_url(client: TestClient, lang: str = "en") -> str:
    response = client.post(
        "/api/v1/export/sign",
        json={"path": "/api/v1/plan/week/export.pdf"},
        headers={"X-API-Key": "test_key"},
    )
    assert response.status_code == 200
    url: str = response.json()["url"]
    if lang:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}lang={lang}"
    return url


def test_week_export_pdf_ok(export_client: TestClient) -> None:
    url = _signed_pdf_url(export_client)
    response = export_client.get(url, headers={"X-API-Key": "test_key"})
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "application/pdf" in content_type
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 2000


def test_register_font_uses_custom_font(monkeypatch, tmp_path) -> None:
    font_file = tmp_path / "dejavu.ttf"
    font_file.write_bytes(b"dummy")
    monkeypatch.setattr(plan, "FONT_PATH", font_file)

    registered: list[str] = []

    def fake_get_fonts() -> list[str]:
        return registered.copy()

    def fake_register(font_obj: Any) -> None:  # pragma: no cover - simple append
        registered.append(plan.FONT_NAME)

    monkeypatch.setattr(plan.pdfmetrics, "getRegisteredFontNames", fake_get_fonts)
    monkeypatch.setattr(plan.pdfmetrics, "registerFont", fake_register)
    monkeypatch.setattr(plan, "TTFont", lambda name, path: (name, path))

    assert plan._register_font() == plan.FONT_NAME
    assert plan.FONT_NAME in registered


def test_register_font_falls_back_on_exception(monkeypatch, tmp_path) -> None:
    """Test _register_font returns 'Helvetica' when font registration fails."""
    font_file = tmp_path / "dejavu.ttf"
    font_file.write_bytes(b"dummy")
    monkeypatch.setattr(plan, "FONT_PATH", font_file)

    def fake_register(font_obj: Any) -> None:
        raise OSError("Font registration failed")

    monkeypatch.setattr(plan.pdfmetrics, "registerFont", fake_register)
    # Mock getRegisteredFontNames to return empty list (font not registered yet)
    monkeypatch.setattr(plan.pdfmetrics, "getRegisteredFontNames", lambda: [])

    monkeypatch.setattr(plan, "TTFont", lambda name, path: (name, path))

    # Should return "Helvetica" when registration fails
    assert plan._register_font() == "Helvetica"


def test_register_font_falls_back_on_missing_file(monkeypatch) -> None:
    """Test _register_font returns 'Helvetica' when font file doesn't exist."""
    # Mock FONT_PATH to return non-existent path
    fake_path = Path("/non/existent/font.ttf")
    monkeypatch.setattr(plan, "FONT_PATH", fake_path)

    # Mock getRegisteredFontNames to return empty list (font not registered yet)
    monkeypatch.setattr(plan.pdfmetrics, "getRegisteredFontNames", lambda: [])

    # Should return "Helvetica" when file doesn't exist
    assert plan._register_font() == "Helvetica"


def test_pdf_uses_page_breaks(export_client: TestClient, monkeypatch) -> None:
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

    url = _signed_pdf_url(export_client)
    response = export_client.get(url, headers={"X-API-Key": "test_key"})
    assert response.status_code == 200
    assert response.content.count(b"/Type /Page") >= 2


def test_pdf_includes_brand_header_and_totals(export_client: TestClient) -> None:
    response = export_client.get(_signed_pdf_url(export_client), headers={"X-API-Key": "test_key"})
    assert response.status_code == 200
    content = response.content.decode("latin-1", "ignore")
    assert "PulsePlate" in content
    assert "kcal" in content or "ккал" in content


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

    story: list[Any] = []
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

    story: list[Any] = []
    plan._branded_header(story, styles, "Helvetica", doc_width=500, lang="en")

    assert captured["path"] == str(logo)


def test_branded_header_localizes_slogan() -> None:
    styles = plan.getSampleStyleSheet()
    for key in ("Heading1", "Heading2", "Heading3", "Heading4", "Normal"):
        styles[key].fontName = "Helvetica"

    story: list[Any] = []
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


def test_pdf_honors_lang_query(export_client: TestClient, monkeypatch) -> None:
    captured_story: list[Any] = []

    class DummyDoc:
        def __init__(self, buf, **kwargs):
            self._buf = buf
            width = kwargs.get("pagesize", (595.27,))[0]
            left = kwargs.get("leftMargin", 0)
            right = kwargs.get("rightMargin", 0)
            self.width = width - left - right

        def build(self, story, onFirstPage=None, onLaterPages=None, canvasmaker=None):
            captured_story.extend(story)
            canvas_cls = canvasmaker or plan.Canvas
            canvas = canvas_cls(BytesIO())
            if onFirstPage:
                onFirstPage(canvas, self)
            if onLaterPages:
                onLaterPages(canvas, self)
            canvas.save()

    monkeypatch.setattr(plan, "SimpleDocTemplate", DummyDoc)
    monkeypatch.setattr(plan, "_register_font", lambda: "Helvetica")

    url = _signed_pdf_url(export_client, "ru")
    response = export_client.get(url, headers={"X-API-Key": "test_key"})
    assert response.status_code == 200

    assert any(
        isinstance(node, plan.Paragraph) and "PulsePlate" in node.getPlainText()
        for node in captured_story
    )
    assert any(
        isinstance(node, plan.Paragraph)
        and ("ккал" in node.getPlainText() or "kcal" in node.getPlainText())
        for node in captured_story
    )
    assert any(
        isinstance(node, plan.Table)
        and len(node._cellvalues) >= 2
        and len(node._cellvalues[1]) >= 2
        and hasattr(node._cellvalues[1][1], "getPlainText")
        and plan.SLOGAN["ru"] in node._cellvalues[1][1].getPlainText()
        for node in captured_story
    )


def test_week_start_prefers_first_day() -> None:
    week = {"days": [{"date": "2025-10-01"}, {"date": "2025-10-02"}]}
    assert plan._week_start(week) == "2025-10-01"


def test_week_start_defaults_today() -> None:
    from datetime import datetime, timezone

    assert plan._week_start({}) == str(datetime.now(UTC).date())


def test_draw_footer_writes_left_text() -> None:
    class StubCanvas:
        def __init__(self):
            self.ops: list[Any] = []
            self.last_text: Any = None

        def saveState(self):
            self.ops.append("save")

        def restoreState(self):
            self.ops.append("restore")

        def setStrokeColor(self, color):
            self.stroke = color

        def setLineWidth(self, width):
            self.width = width

        def line(self, x1, y1, x2, y2):
            self.line_args = (x1, y1, x2, y2)

        def setFillColor(self, color):
            self.fill = color

        def setFont(self, name, size):
            self.font = (name, size)

        def drawString(self, x, y, text):
            self.last_text = (x, y, text)

    stub = StubCanvas()
    msg = "PulsePlate · week of 2025-09-29"
    plan._draw_footer(stub, None, msg)
    assert stub.last_text == (15 * plan.mm, 12 * plan.mm, msg)
    assert "save" in stub.ops and "restore" in stub.ops


def test_page_num_canvas_writes_numbers() -> None:
    buffer = BytesIO()
    canvas = plan.PageNumCanvas(buffer)
    canvas.drawString(50, 50, "page1")
    canvas.showPage()
    canvas.drawString(50, 50, "page2")
    canvas.showPage()
    canvas.save()
    pdf_text = buffer.getvalue().decode("latin-1", "ignore")
    assert "p 1/2" in pdf_text
    assert "p 2/2" in pdf_text
