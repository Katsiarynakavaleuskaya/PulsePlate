"""Weekly plan export endpoints (CSV and PDF)."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO, StringIO
from pathlib import Path
import csv
from typing import Any, Dict, Iterable, List

from fastapi import APIRouter, Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

plan_router = APIRouter(prefix="/api/v1/plan", tags=["plan"])

FONTS_DIR = Path("assets/fonts")
FONT_PATH = FONTS_DIR / "DejaVuSans.ttf"
FONT_NAME = "DejaVuSans"


def _current_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _get_week_plan() -> Dict[str, Any]:
    """Return a demo week plan structure.

    Replace this stub with the real planner integration when available.
    """

    return {
        "days": [
            {
                "date": "2025-09-29",
                "meals": [
                    {
                        "name": "Завтрак",
                        "items": [
                            {
                                "name": "Овсянка",
                                "qty": 60,
                                "unit": "g",
                                "energy_kcal": 230,
                                "protein_g": 8,
                                "carbs_g": 40,
                                "fat_g": 4,
                                "note": "с ягодами",
                            },
                            {
                                "name": "Йогурт",
                                "qty": 1,
                                "unit": "pcs",
                                "energy_kcal": 61,
                                "protein_g": 5,
                                "carbs_g": 4,
                                "fat_g": 3,
                            },
                        ],
                    },
                    {
                        "name": "Обед",
                        "items": [
                            {
                                "name": "Курица",
                                "qty": 150,
                                "unit": "g",
                                "energy_kcal": 248,
                                "protein_g": 35,
                                "fat_g": 10,
                                "note": "запечённая",
                            },
                        ],
                    },
                ],
            }
        ]
    }


def _iter_rows(week: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    days: List[Dict[str, Any]] = list(week.get("days") or [])
    for di, day in enumerate(days, start=1):
        date = day.get("date") or ""
        meals = day.get("meals") or []
        for meal in meals:
            meal_name = meal.get("name") or meal.get("meal") or ""
            for item in meal.get("items") or []:
                yield {
                    "date": date,
                    "day_idx": di,
                    "meal": meal_name,
                    "item": item.get("name") or item.get("title") or "",
                    "qty": item.get("qty") or "",
                    "unit": item.get("unit") or "",
                    "energy_kcal": item.get("energy_kcal") or "",
                    "protein_g": item.get("protein_g") or "",
                    "carbs_g": item.get("carbs_g") or "",
                    "fat_g": item.get("fat_g") or "",
                    "note": item.get("note") or "",
                }


@plan_router.get("/week/export.csv")
def export_week_csv() -> Response:
    week = _get_week_plan()
    buffer = StringIO()
    fieldnames = [
        "date",
        "day_idx",
        "meal",
        "item",
        "qty",
        "unit",
        "energy_kcal",
        "protein_g",
        "carbs_g",
        "fat_g",
        "note",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in _iter_rows(week):
        writer.writerow(row)

    filename = f"week_plan_{_current_timestamp()}.csv"
    return Response(
        content=buffer.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _register_font() -> str:
    try:
        if FONT_PATH.exists():
            pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))
            return FONT_NAME
    except Exception:
        pass
    return "Helvetica"


def _build_day_story(day: Dict[str, Any], styles, font: str) -> List[Any]:
    story: List[Any] = []
    date = day.get("date") or "Day"
    story.append(Paragraph(f"<b>{date}</b>", styles["Heading3"]))
    story.append(Spacer(1, 6))

    for meal in day.get("meals") or []:
        meal_name = meal.get("name") or meal.get("meal") or "Meal"
        story.append(Paragraph(meal_name, styles["Heading4"]))
        rows = [
            [
                "Название",
                "Кол-во",
                "Ед.",
                "ккал",
                "Б",
                "У",
                "Ж",
            ]
        ]
        for item in meal.get("items") or []:
            rows.append(
                [
                    str(item.get("name", "")),
                    str(item.get("qty", "")),
                    str(item.get("unit", "")),
                    str(item.get("energy_kcal", "")),
                    str(item.get("protein_g", "")),
                    str(item.get("carbs_g", "")),
                    str(item.get("fat_g", "")),
                ]
            )

        table = Table(rows, colWidths=[210, 55, 35, 45, 30, 30, 30])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 10))
    return story


@plan_router.get("/week/export.pdf")
def export_week_pdf() -> Response:
    week = _get_week_plan()
    font = _register_font()

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=28,
        rightMargin=28,
        topMargin=28,
        bottomMargin=28,
    )

    styles = getSampleStyleSheet()
    base_style = ParagraphStyle(
        name="Base",
        parent=styles["Normal"],
        fontName=font,
        fontSize=10,
        leading=13,
    )
    styles.add(base_style)
    for key in ["Heading1", "Heading2", "Heading3", "Heading4", "Normal"]:
        styles[key].fontName = font

    story: List[Any] = []
    story.append(Paragraph("<b>Недельный план питания / Weekly Plan</b>", styles["Heading2"]))
    story.append(
        Paragraph(
            datetime.now(timezone.utc).strftime("Сгенерировано %Y-%m-%d %H:%M UTC"),
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 14))

    days = week.get("days") or []
    for idx, day in enumerate(days):
        story.extend(_build_day_story(day, styles, font))
        if idx < len(days) - 1:
            story.append(PageBreak())

    doc.build(story)
    filename = f"week_plan_{_current_timestamp()}.pdf"
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


__all__ = ["plan_router"]
