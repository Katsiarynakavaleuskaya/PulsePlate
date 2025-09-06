"""
Export Functions for Nutrition Data

RU: Функции экспорта данных о питании в различные форматы.
EN: Export functions for nutrition data to various formats.

This module provides functionality to export nutrition data to CSV and PDF formats
for user download and record keeping.
"""

from __future__ import annotations

import csv
import io
from typing import Any, Dict, Optional

# Check if reportlab is available
REPORTLAB_AVAILABLE = False
REPORTLAB_CLASSES = {}

# Try to import reportlab
try:
    from reportlab.lib import colors  # type: ignore
    from reportlab.lib.pagesizes import letter  # type: ignore
    from reportlab.lib.styles import getSampleStyleSheet  # type: ignore
    from reportlab.platypus import (
        Paragraph,  # type: ignore
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_AVAILABLE = True
    REPORTLAB_CLASSES.update(
        {
            "colors": colors,
            "letter": letter,
            "getSampleStyleSheet": getSampleStyleSheet,
            "Paragraph": Paragraph,
            "SimpleDocTemplate": SimpleDocTemplate,
            "Spacer": Spacer,
            "Table": Table,
            "TableStyle": TableStyle,
        }
    )
except ImportError:
    REPORTLAB_AVAILABLE = False


def _import_reportlab_modules():
    """Return reportlab modules, importing them if necessary."""
    global REPORTLAB_CLASSES
    if not REPORTLAB_AVAILABLE:
        raise ImportError(
            "ReportLab is required for PDF export. "
            "Install with 'pip install reportlab'"
        )
    return REPORTLAB_CLASSES


def to_csv_day(meal_plan: Dict[str, Any], filename: Optional[str] = None) -> bytes:
    """
    RU: Экспортирует дневной план питания в CSV.
    EN: Export daily meal plan to CSV.

    Args:
        meal_plan: Daily meal plan data
        filename: Optional filename for the export

    Returns:
        CSV data as bytes
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(
        ["Meal", "Food Item", "Calories", "Protein (g)", "Carbs (g)", "Fat (g)"]
    )

    # Write meal data
    for meal in meal_plan.get("meals", []):
        writer.writerow(
            [
                meal.get("name", ""),
                meal.get("food_item", ""),
                meal.get("kcal", 0),
                meal.get("protein_g", 0),
                meal.get("carbs_g", 0),
                meal.get("fat_g", 0),
            ]
        )

    # Write summary
    writer.writerow([])
    writer.writerow(
        [
            "Total",
            "",
            meal_plan.get("total_kcal", 0),
            meal_plan.get("total_protein", 0),
            meal_plan.get("total_carbs", 0),
            meal_plan.get("total_fat", 0),
        ]
    )

    csv_data = output.getvalue()
    output.close()

    return csv_data.encode("utf-8")


def to_csv_week(weekly_plan: Dict[str, Any], filename: Optional[str] = None) -> bytes:
    """
    RU: Экспортирует недельный план питания в CSV.
    EN: Export weekly meal plan to CSV.

    Args:
        weekly_plan: Weekly meal plan data
        filename: Optional filename for the export

    Returns:
        CSV data as bytes
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(
        [
            "Day",
            "Meal",
            "Food Item",
            "Calories",
            "Protein (g)",
            "Carbs (g)",
            "Fat (g)",
            "Cost",
        ]
    )

    # Write daily meal data
    for day_menu in weekly_plan.get("daily_menus", []):
        day = day_menu.get("date", "")
        for meal in day_menu.get("meals", []):
            writer.writerow(
                [
                    day,
                    meal.get("name", ""),
                    meal.get("food_item", ""),
                    meal.get("kcal", 0),
                    meal.get("protein_g", 0),
                    meal.get("carbs_g", 0),
                    meal.get("fat_g", 0),
                    meal.get("cost", 0),
                ]
            )

    # Write shopping list
    writer.writerow([])
    writer.writerow(["Shopping List"])
    writer.writerow(["Item", "Quantity", "Estimated Cost"])

    for item, quantity in weekly_plan.get("shopping_list", {}).items():
        writer.writerow([item, quantity, ""])

    # Write summary
    writer.writerow([])
    writer.writerow(["Weekly Summary"])
    writer.writerow(["Total Cost", weekly_plan.get("total_cost", 0)])
    writer.writerow(["Adherence Score", weekly_plan.get("adherence_score", 0)])

    csv_data = output.getvalue()
    output.close()

    return csv_data.encode("utf-8")


def to_pdf_day(meal_plan: Dict[str, Any], filename: Optional[str] = None) -> bytes:
    """
    RU: Экспортирует дневной план питания в PDF.
    EN: Export daily meal plan to PDF.

    Args:
        meal_plan: Daily meal plan data
        filename: Optional filename for the export

    Returns:
        PDF data as bytes
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError(
            "ReportLab is required for PDF export. "
            "Install with 'pip install reportlab'"
        )

    # Lazy import reportlab modules
    reportlab_classes = _import_reportlab_modules()
    colors = reportlab_classes["colors"]
    letter = reportlab_classes["letter"]
    getSampleStyleSheet = reportlab_classes["getSampleStyleSheet"]
    Paragraph = reportlab_classes["Paragraph"]
    SimpleDocTemplate = reportlab_classes["SimpleDocTemplate"]
    Spacer = reportlab_classes["Spacer"]
    Table = reportlab_classes["Table"]
    TableStyle = reportlab_classes["TableStyle"]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Get styles
    styles = getSampleStyleSheet()

    # Title
    title = Paragraph("Daily Meal Plan", styles["Title"])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Meal table
    meal_data = [
        ["Meal", "Food Item", "Calories", "Protein (g)", "Carbs (g)", "Fat (g)"]
    ]

    for meal in meal_plan.get("meals", []):
        meal_data.append(
            [
                meal.get("name", ""),
                meal.get("food_item", ""),
                str(meal.get("kcal", 0)),
                str(meal.get("protein_g", 0)),
                str(meal.get("carbs_g", 0)),
                str(meal.get("fat_g", 0)),
            ]
        )

    # Add total row
    meal_data.append(
        [
            "Total",
            "",
            str(meal_plan.get("total_kcal", 0)),
            str(meal_plan.get("total_protein", 0)),
            str(meal_plan.get("total_carbs", 0)),
            str(meal_plan.get("total_fat", 0)),
        ]
    )

    meal_table = Table(meal_data)
    meal_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 14),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )

    elements.append(meal_table)

    # Build PDF
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()

    return pdf_data


def to_pdf_week(weekly_plan: Dict[str, Any], filename: Optional[str] = None) -> bytes:
    """
    RU: Экспортирует недельный план питания в PDF.
    EN: Export weekly meal plan to PDF.

    Args:
        weekly_plan: Weekly meal plan data
        filename: Optional filename for the export

    Returns:
        PDF data as bytes
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError(
            "ReportLab is required for PDF export. "
            "Install with 'pip install reportlab'"
        )

    # Lazy import reportlab modules
    reportlab_classes = _import_reportlab_modules()
    colors = reportlab_classes["colors"]
    letter = reportlab_classes["letter"]
    getSampleStyleSheet = reportlab_classes["getSampleStyleSheet"]
    Paragraph = reportlab_classes["Paragraph"]
    SimpleDocTemplate = reportlab_classes["SimpleDocTemplate"]
    Spacer = reportlab_classes["Spacer"]
    Table = reportlab_classes["Table"]
    TableStyle = reportlab_classes["TableStyle"]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Get styles
    styles = getSampleStyleSheet()

    # Title
    title = Paragraph("Weekly Meal Plan", styles["Title"])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Daily meals table
    meal_data = [
        [
            "Day",
            "Meal",
            "Food Item",
            "Calories",
            "Protein (g)",
            "Carbs (g)",
            "Fat (g)",
            "Cost",
        ]
    ]

    for day_menu in weekly_plan.get("daily_menus", []):
        day = day_menu.get("date", "")
        for meal in day_menu.get("meals", []):
            meal_data.append(
                [
                    day,
                    meal.get("name", ""),
                    meal.get("food_item", ""),
                    str(meal.get("kcal", 0)),
                    str(meal.get("protein_g", 0)),
                    str(meal.get("carbs_g", 0)),
                    str(meal.get("fat_g", 0)),
                    str(meal.get("cost", 0)),
                ]
            )

    meal_table = Table(meal_data)
    meal_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )

    elements.append(meal_table)
    elements.append(Spacer(1, 12))

    # Shopping list
    shopping_title = Paragraph("Shopping List", styles["Heading2"])
    elements.append(shopping_title)

    shopping_data = [["Item", "Quantity"]]
    for item, quantity in weekly_plan.get("shopping_list", {}).items():
        shopping_data.append([item, str(quantity)])

    shopping_table = Table(shopping_data)
    shopping_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )

    elements.append(shopping_table)
    elements.append(Spacer(1, 12))

    # Summary
    summary_data = [
        ["Total Cost", str(weekly_plan.get("total_cost", 0))],
        ["Adherence Score", str(weekly_plan.get("adherence_score", 0))],
    ]

    summary_table = Table(summary_data)
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 0), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )

    elements.append(summary_table)

    # Build PDF
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()

    return pdf_data
