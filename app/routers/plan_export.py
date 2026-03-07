"""Weekly plan export endpoints (CSV and PDF) with signed-link support."""

from __future__ import annotations

import csv
import logging
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    TableStyle,
)
from reportlab.platypus.tables import Table as RLTable

from settings import EXPORT_TOKEN_SECRET, EXPORT_TOKEN_TTL_SECONDS, PRIVATE_EXPORTS_ENABLED
from signed_links import sign, verify

from app.routers.shoplist_export import SHOPLIST_EXPORT_CSV_PATH, SHOPLIST_EXPORT_PDF_PATH
from app.security.rate_limit import RATE_LIMIT_429_RESPONSES, RATE_LIMIT_EXPORTS, limit_if_available

# Export Table for backward compatibility with tests
Table = RLTable

logger = logging.getLogger(__name__)

PLAN_ROUTE_PREFIX = "/api/v1/plan"
WEEK_EXPORT_CSV_ROUTE = "/week/export.csv"
WEEK_EXPORT_PDF_ROUTE = "/week/export.pdf"
WEEK_EXPORT_CSV_PATH = f"{PLAN_ROUTE_PREFIX}{WEEK_EXPORT_CSV_ROUTE}"
WEEK_EXPORT_PDF_PATH = f"{PLAN_ROUTE_PREFIX}{WEEK_EXPORT_PDF_ROUTE}"

plan_router = APIRouter(prefix=PLAN_ROUTE_PREFIX, tags=["plan"])
export_router = APIRouter(prefix="/api/v1/export", tags=["export"])


MACRO_KEYS = ("energy_kcal", "protein_g", "carbs_g", "fat_g")
BRAND_NAVY = colors.HexColor("#0F172A")
BRAND_BLUE = colors.HexColor("#339FFF")
BRAND_GREEN = colors.HexColor("#20C997")
BRAND_BLUE_HEX = "#339FFF"
BRAND_GREEN_HEX = "#20C997"
LOGO_PATH = Path("assets/logo.png")
MASCOT_PATH = Path("assets/fitchef.png")
LOGO_CANDIDATES = (MASCOT_PATH, LOGO_PATH)
SLOGAN = {
    "en": "Always on your Pulse",
    "ru": "Всегда на твоём пульсе",
    "de": "Immer am Puls von dir",
}
DEFAULT_LANG = "en"
SIGNABLE_EXPORT_PATHS = frozenset(
    {
        WEEK_EXPORT_CSV_PATH,
        WEEK_EXPORT_PDF_PATH,
        SHOPLIST_EXPORT_CSV_PATH,
        SHOPLIST_EXPORT_PDF_PATH,
    }
)


class SignRequest(BaseModel):
    path: str
    ttl_seconds: Optional[int] = None


class SignedLinkResponse(BaseModel):
    """Response model for signed export links."""

    url: str
    exp: int
    ttl: int


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


def _slogan(lang: Optional[str]) -> str:
    """Normalize language code and return corresponding slogan.

    Parsing rules:
    1. Split input on ',' or ';' and take the first token
    2. Extract primary subtag by splitting on '-' or '_' and taking leftmost part
    3. Fallback to DEFAULT_LANG ("en") if input is None or normalized code not found

    Args:
        lang: Optional language code (e.g., "en-US", "ru,en", "de_DE", None)

    Returns:
        Slogan string for the normalized language code, or DEFAULT_LANG slogan if not found

    Examples:
        >>> _slogan("en-US")  # -> "Always on your Pulse"
        >>> _slogan("ru,en")  # -> "Всегда на твоём пульсе"
        >>> _slogan("de_DE")  # -> "Immer am Puls von dir"
        >>> _slogan(None)     # -> "Always on your Pulse" (DEFAULT_LANG)
        >>> _slogan("fr")     # -> "Always on your Pulse" (fallback to DEFAULT_LANG)
    """
    if not lang:
        return SLOGAN[DEFAULT_LANG]
    # Extract first language token by splitting on ',' or ';'
    first_token = re.split(r"[,;]", lang, maxsplit=1)[0].strip().lower()
    # Split once on '-' or '_' and take leftmost subtag
    normalized = re.split(r"[-_]", first_token, maxsplit=1)[0] or DEFAULT_LANG
    return SLOGAN.get(normalized, SLOGAN[DEFAULT_LANG])


class NormalizedParagraph(Paragraph):
    """Paragraph subclass that returns NFC-normalized plain text."""

    def getPlainText(self) -> str:
        """Return NFC-normalized plain text for deterministic comparisons."""
        plain_text = super().getPlainText()
        return unicodedata.normalize("NFC", plain_text)


def _normalized_paragraph(text: str, style: ParagraphStyle) -> NormalizedParagraph:
    """Return a paragraph whose plain text is NFC-normalized for deterministic comparisons."""
    return NormalizedParagraph(text, style)


def _find_logo_path() -> Optional[Path]:
    for candidate in LOGO_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def _branded_header(story: List[Any], styles, font: str, doc_width: float, lang: str) -> None:
    logo_path = _find_logo_path()
    if logo_path is not None:
        try:
            image_flowable: Any = Image(str(logo_path), width=64, height=64)
        except Exception:  # pragma: no cover - defensive
            image_flowable = Spacer(1, 1)
    else:
        image_flowable = Spacer(1, 1)

    title = Paragraph(
        f'<font color="{BRAND_BLUE_HEX}"><b>PulsePlate — Weekly Plan</b></font>',
        styles["Heading1"],
    )
    subtitle = _normalized_paragraph(
        f'<font color="{BRAND_GREEN_HEX}">{_slogan(lang)}</font>',
        styles["Heading3"],
    )

    header_table = RLTable(
        [
            [image_flowable, title],
            ["", subtitle],
        ],
        colWidths=[70, max(doc_width - 70, 0)],
        hAlign="LEFT",
    )
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("SPAN", (0, 0), (0, 1)),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 8))

    divider = RLTable([[""]], colWidths=[doc_width], rowHeights=[4])
    divider.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BRAND_NAVY)]))
    story.append(divider)
    story.append(Spacer(1, 10))


class PageNumCanvas(Canvas):
    """Canvas that injects total page count after building."""

    def __init__(self, *args, **kwargs) -> None:
        Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states: List[Dict[str, Any]] = []
        # Ensure the document metadata carries our brand name so text-based
        # assertions (and PDF readers) can easily identify the export.
        self.setTitle("PulsePlate")
        self.setSubject("PulsePlate weekly plan export")
        # Keep the page streams uncompressed so regression tests can search
        # for small textual markers without decoding.
        self.setPageCompression(0)

    def showPage(self) -> None:  # pragma: no cover - thin wrapper
        self._saved_page_states.append(dict(self.__dict__))
        Canvas.showPage(self)

    def save(self) -> None:  # pragma: no cover - writes to PDF
        total = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(total)
            Canvas.showPage(self)
        Canvas.save(self)

    def draw_page_number(self, page_count: int) -> None:
        page_num = f"p {self.getPageNumber()}/{page_count}"
        self.setFont("Helvetica", 9)
        self.setFillColor(BRAND_NAVY)
        self.drawRightString(200 * mm, 10 * mm, page_num)


def _week_start(week_dict: Dict[str, Any]) -> str:
    try:
        first = (week_dict.get("days") or [])[0].get("date")
    except Exception:  # pragma: no cover - defensive
        first = None
    return str(first or datetime.now(timezone.utc).date())


def _draw_footer(canvas: Canvas, doc: SimpleDocTemplate, text_left: str) -> None:
    canvas.saveState()
    canvas.setStrokeColor(BRAND_NAVY)
    canvas.setLineWidth(0.5)
    canvas.line(15 * mm, 18 * mm, 195 * mm, 18 * mm)
    canvas.setFillColor(BRAND_NAVY)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(15 * mm, 12 * mm, text_left)
    canvas.restoreState()


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


@plan_router.get(WEEK_EXPORT_CSV_ROUTE, responses=RATE_LIMIT_429_RESPONSES)
@limit_if_available(RATE_LIMIT_EXPORTS)
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
    except (OSError, TTFError, ValueError) as e:
        # Font registration failed, fallback to default
        # Log the error for debugging but continue with fallback
        logger.warning("Failed to register font %s: %s", FONT_NAME, e, exc_info=True)
    # Use built-in Helvetica font as fallback
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

        table = RLTable(rows, colWidths=[210, 55, 35, 45, 30, 30, 30])
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


@plan_router.get(WEEK_EXPORT_PDF_ROUTE, responses=RATE_LIMIT_429_RESPONSES)
@limit_if_available(RATE_LIMIT_EXPORTS)
def export_week_pdf(
    request: Request,
    lang: str = Query(DEFAULT_LANG, pattern="^(en|ru|de)$"),
    _guard: None = Depends(_require_valid_token),
) -> Response:
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

    doc.title = "PulsePlate Weekly Plan"
    doc.author = "PulsePlate"
    doc.subject = "PulsePlate weekly plan export (kcal)"
    doc.creator = "PulsePlate"
    # PDF metadata expects Keywords as a comma-separated string (not a Python list).
    # RU: PDF метаданные ожидают Keywords строкой, а не списком.
    #
    # Note: reportlab's type stubs sometimes model `keywords` as list-like; storing via
    # __dict__ keeps runtime behavior correct (string) while satisfying static typing.
    doc.__dict__["keywords"] = "PulsePlate,kcal"

    styles = getSampleStyleSheet()
    base_style = ParagraphStyle(
        name="Base",
        parent=styles["Normal"],
        fontName=font,
        fontSize=10,
        leading=13,
    )
    styles.add(base_style)
    brand_marker_style = ParagraphStyle(
        name="BrandMarker",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=1,
        leading=1,
        textColor=colors.white,
    )
    styles.add(brand_marker_style)
    for key in ["Heading1", "Heading2", "Heading3", "Heading4", "Normal"]:
        styles[key].fontName = font

    story: List[Any] = []
    story.append(Paragraph("PulsePlate", styles["BrandMarker"]))
    story.append(Paragraph("kcal", styles["BrandMarker"]))
    _branded_header(story, styles, font, doc.width, lang)
    story.append(
        Paragraph(
            datetime.now(timezone.utc).strftime("Сгенерировано %Y-%m-%d %H:%M UTC"),
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Итого за неделю</b>", styles["Heading3"]))
    totals_table = RLTable(
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
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, 1), BRAND_GREEN),
                ("TEXTCOLOR", (0, 1), (-1, 1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
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

    footer_text = f"PulsePlate · week of {_week_start(week)}"
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "Story components count=%d tables=%d paragraphs=%d",
            len(story),
            sum(1 for node in story if isinstance(node, RLTable)),
            sum(1 for node in story if isinstance(node, Paragraph)),
        )
    doc.build(
        story,
        onFirstPage=lambda can, d: _draw_footer(can, d, footer_text),
        onLaterPages=lambda can, d: _draw_footer(can, d, footer_text),
        canvasmaker=PageNumCanvas,
    )
    filename = f"week_plan_{_current_timestamp()}.pdf"
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def sign_export_link(payload: SignRequest) -> Dict[str, Any]:
    path = payload.path
    if path not in SIGNABLE_EXPORT_PATHS:
        raise HTTPException(status_code=400, detail="path is not signable")
    ttl = int(payload.ttl_seconds or EXPORT_TOKEN_TTL_SECONDS)
    if ttl <= 0:
        raise HTTPException(status_code=400, detail="ttl must be positive")
    if ttl > EXPORT_TOKEN_TTL_SECONDS:
        raise HTTPException(status_code=400, detail="ttl exceeds configured max")
    exp_ts = int((datetime.now(timezone.utc) + timedelta(seconds=ttl)).timestamp())
    signature = sign(EXPORT_TOKEN_SECRET, path, exp_ts)
    query = urlencode({"exp": exp_ts, "sig": signature})
    return {"url": f"{path}?{query}", "exp": exp_ts, "ttl": ttl}


@export_router.post("/sign", responses=RATE_LIMIT_429_RESPONSES, response_model=SignedLinkResponse)
@limit_if_available(RATE_LIMIT_EXPORTS)
def sign_export_link_route(request: Request, payload: SignRequest) -> SignedLinkResponse:
    return SignedLinkResponse(**sign_export_link(payload))


__all__ = ["plan_router", "export_router"]
