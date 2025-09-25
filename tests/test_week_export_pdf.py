"""Tests for weekly plan PDF export."""

from typing import List, Any

import pytest
from fastapi.testclient import TestClient

from app import app
from app.routers import plan_export as plan


client = TestClient(app)


def _signed_pdf_url() -> str:
    response = client.post("/api/v1/export/sign", json={"path": "/api/v1/plan/week/export.pdf"})
    assert response.status_code == 200
    return response.json()["url"]


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
