"""Weekly plan export endpoints (CSV and PDF) with signed-link support."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO, StringIO
from pathlib import Path
from urllib.parse import urlencode
import csv
from typing import Any, Dict, Iterable, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from settings import EXPORT_TOKEN_SECRET, EXPORT_TOKEN_TTL_SECONDS, PRIVATE_EXPORTS_ENABLED
from signed_links import sign, verify

plan_router = APIRouter(prefix="/api/v1/plan", tags=["plan"])
export_router = APIRouter(prefix="/api/v1/export", tags=["export"])


MACRO_KEYS = ("energy_kcal", "protein_g", "carbs_g", "fat_g")


class SignRequest(BaseModel):
    path: str
    ttl_seconds: Optional[int] = None


FONTS_DIR = Path("assets/fonts")
FONT_PATH = FONTS_DIR / "DejaVuSans.ttf"
FONT_NAME = "DejaVuSans"


def _current_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_add(acc: float, value: Any) -> float:
    if value is None:
        return acc
    try:
        return acc + float(value)
    except Exception:  # pragma: no cover - defensive
        return acc


def sum_day_macros(day: Dict[str, Any]) -> Dict[str, float]:
    totals = {key: 0.0 for key in MACRO_KEYS}
    for meal in day.get("meals") or []:
        for item in meal.get("items") or []:
            for key in MACRO_KEYS:
                totals[key] = _safe_add(totals[key], item.get(key))
    return totals


def sum_week_macros(week: Dict[str, Any]) -> Dict[str, float]:
    totals = {key: 0.0 for key in MACRO_KEYS}
    for day in week.get("days") or []:
        day_totals = sum_day_macros(day)
        for key in MACRO_KEYS:
            totals[key] = _safe_add(totals[key], day_totals.get(key))
    return totals


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


def _require_valid_token(request: Request) -> None:
    if not PRIVATE_EXPORTS_ENABLED:
        return
    exp = request.query_params.get("exp")
    sig = request.query_params.get("sig")
    if not exp or not sig:
        raise HTTPException(status_code=403, detail="missing token")
    try:
        exp_ts = int(exp)
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=403, detail="bad token") from exc
    if not verify(EXPORT_TOKEN_SECRET, request.url.path, exp_ts, sig):
        raise HTTPException(status_code=403, detail="invalid or expired token")


@plan_router.get("/week/export.csv")
def export_week_csv(request: Request, _guard: None = Depends(_require_valid_token)) -> Response:
    week = _get_week_plan()
    totals = sum_week_macros(week)
    buffer = StringIO()
    totals_str = ", ".join(f"{key}={round(value, 2)}" for key, value in totals.items())
    buffer.write(f"# WEEK_TOTALS: {totals_str}\n")
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
def export_week_pdf(request: Request, _guard: None = Depends(_require_valid_token)) -> Response:
    week = _get_week_plan()
    font = _register_font()
    totals = sum_week_macros(week)

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

    story.append(Paragraph("<b>Итого за неделю</b>", styles["Heading3"]))
    totals_table = Table(
        [
            ["ккал", "Б", "У", "Ж"],
            [
                str(round(totals.get("energy_kcal", 0.0), 0)),
                str(round(totals.get("protein_g", 0.0), 1)),
                str(round(totals.get("carbs_g", 0.0), 1)),
                str(round(totals.get("fat_g", 0.0), 1)),
            ],
        ],
        colWidths=[60, 60, 60, 60],
    )
    totals_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    story.append(totals_table)
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


@export_router.post("/sign")
def sign_export_link(payload: SignRequest) -> Dict[str, Any]:
    path = payload.path
    if not path.startswith("/api/"):
        raise HTTPException(status_code=400, detail="path must start with /api/")
    ttl = int(payload.ttl_seconds or EXPORT_TOKEN_TTL_SECONDS)
    if ttl <= 0:
        raise HTTPException(status_code=400, detail="ttl must be positive")
    exp_ts = int((datetime.now(timezone.utc) + timedelta(seconds=ttl)).timestamp())
    signature = sign(EXPORT_TOKEN_SECRET, path, exp_ts)
    query = urlencode({"exp": exp_ts, "sig": signature})
    return {"url": f"{path}?{query}", "exp": exp_ts, "ttl": ttl}


__all__ = ["plan_router", "export_router"]
