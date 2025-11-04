from io import BytesIO
from typing import Any, Dict, List

import pytest
from reportlab.lib.styles import getSampleStyleSheet
from starlette.requests import Request

from app.routers import plan_export


def test_branded_header_constructs_table(monkeypatch: pytest.MonkeyPatch) -> None:
    story: List[Any] = []
    styles = getSampleStyleSheet()
    styles["Heading1"].fontName = "Helvetica"
    styles["Heading3"].fontName = "Helvetica"
    monkeypatch.setattr(plan_export, "_find_logo_path", lambda: None)

    plan_export._branded_header(story, styles, "Helvetica", doc_width=400, lang="en")
    assert story  # story should have entries appended
    header_table = story[0]
    assert isinstance(header_table, plan_export.RLTable)


def test_export_week_pdf_uses_custom_doc(monkeypatch: pytest.MonkeyPatch) -> None:
    week_plan = {
        "days": [
            {
                "name": "Day 1",
                "meals": [
                    {
                        "name": "Breakfast",
                        "items": [{"energy_kcal": 100, "protein_g": 10, "carbs_g": 20, "fat_g": 5}],
                    }
                ],
            }
        ]
    }

    monkeypatch.setattr(plan_export, "_get_week_plan", lambda: week_plan)
    monkeypatch.setattr(plan_export, "_register_font", lambda: "Helvetica")

    created_docs: List[Any] = []

    class DummyDoc:
        def __init__(self, _buf: BytesIO, **kwargs: Any) -> None:
            self.kwargs = kwargs
            self.width = 400
            self.built = False

        def build(self, story: List[Any], onFirstPage=None, onLaterPages=None, canvasmaker=None):
            self.built = True
            self.story = story
            assert canvasmaker is plan_export.PageNumCanvas

    def doc_factory(*args, **kwargs):
        doc = DummyDoc(*args, **kwargs)
        created_docs.append(doc)
        return doc

    monkeypatch.setattr(plan_export, "SimpleDocTemplate", doc_factory)

    request = Request({"type": "http", "headers": []})
    response = plan_export.export_week_pdf(request=request, lang="ru", _guard=None)
    assert response.media_type == "application/pdf"
    assert created_docs and created_docs[0].kwargs["leftMargin"] == 28
    assert created_docs[0].built is True
