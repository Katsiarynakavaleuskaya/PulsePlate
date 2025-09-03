"""
Export Functions for Nutrition Data (simplified version)

RU: Функции экспорта данных о питании в различные форматы.
EN: Export functions for nutrition data to various formats.

This module provides functionality to export nutrition data to CSV and PDF formats
for user download and record keeping.
"""

from __future__ import annotations
from io import StringIO
from pathlib import Path
from typing import Iterable
import csv

# PDF: лёгкая табличка через reportlab
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def to_csv_day(plate: dict) -> str:
    """RU: CSV по дню (заголовок + блюда).
       EN: Day CSV (header + meals)."""
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["kcal", "protein_g", "fat_g", "carbs_g", "fiber_g"])
    m = plate["macros"]
    w.writerow([plate["kcal"], m["protein_g"], m["fat_g"], m["carbs_g"], m["fiber_g"]])
    w.writerow([])
    w.writerow(["meal_title", "kcal", "protein_g", "fat_g", "carbs_g"])
    for meal in plate["meals"]:
        w.writerow([meal["title"], meal["kcal"], meal["protein_g"], meal["fat_g"], meal["carbs_g"]])
    return buf.getvalue()

def to_csv_week(week: dict) -> str:
    """RU: CSV по неделе: день за днём суммарно.
       EN: Week CSV: day-by-day summary."""
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["day", "kcal", "protein_g", "fat_g", "carbs_g", "fiber_g"])
    for i, day in enumerate(week["days"], start=1):
        m = day["macros"]
        w.writerow([i, day["kcal"], m["protein_g"], m["fat_g"], m["carbs_g"], m.get("fiber_g", 0)])
    return buf.getvalue()

def to_pdf_day(plate: dict, path: Path) -> None:
    """RU: Простой PDF со сводкой и таблицей блюд.
       EN: Simple PDF with summary and meals table."""
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    elems = []
    elems.append(Paragraph("Daily Plate Summary", styles["Title"]))
    m = plate["macros"]
    elems.append(Paragraph(f"Target kcal: {plate['kcal']}", styles["Normal"]))
    elems.append(Paragraph(f"Protein/Fat/Carbs/Fiber: {m['protein_g']}g / {m['fat_g']}g / {m['carbs_g']}g / {m['fiber_g']}g", styles["Normal"]))
    elems.append(Spacer(1, 12))
    data = [["Meal", "kcal", "Protein (g)", "Fat (g)", "Carbs (g)"]]
    for meal in plate["meals"]:
        data.append([meal["title"], meal["kcal"], meal["protein_g"], meal["fat_g"], meal["carbs_g"]])
    table = Table(data, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
    ]))
    elems.append(table)
    doc.build(elems)

def to_pdf_week(week: dict, path: Path) -> None:
    """RU: PDF по неделе (суммы по дням).
       EN: Week PDF (day summaries)."""
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    elems = [Paragraph("Weekly Plan Summary", styles["Title"]), Spacer(1, 12)]
    data = [["Day", "kcal", "Protein (g)", "Fat (g)", "Carbs (g)", "Fiber (g)"]]
    for i, day in enumerate(week["days"], start=1):
        m = day["macros"]
        data.append([i, day["kcal"], m["protein_g"], m["fat_g"], m["carbs_g"], m.get("fiber_g", 0)])
    table = Table(data, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
    ]))
    elems.append(table)
    doc.build(elems)