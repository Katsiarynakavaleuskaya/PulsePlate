"""
Additional tests to improve coverage of core.exports module.
"""

from unittest.mock import patch

import pytest

from core.exports import (
    REPORTLAB_AVAILABLE,
    _import_reportlab_modules,
    to_csv_day,
    to_csv_week,
    to_pdf_day,
    to_pdf_week,
)


def test_exports_coverage_improvement():
    """Additional tests to ensure full coverage of core.exports module."""

    # Test to_csv_day with various inputs
    meal_plan = {
        "meals": [
            {
                "name": "Breakfast",
                "food_item": "Oatmeal",
                "kcal": 300,
                "protein_g": 10,
                "carbs_g": 50,
                "fat_g": 5,
            },
            {
                "name": "Lunch",
                "food_item": "Chicken Salad",
                "kcal": 450,
                "protein_g": 35,
                "carbs_g": 20,
                "fat_g": 25,
            },
        ],
        "total_kcal": 750,
        "total_protein": 45,
        "total_carbs": 70,
        "total_fat": 30,
    }

    csv_data = to_csv_day(meal_plan)
    assert isinstance(csv_data, bytes)

    # Test to_csv_week with various inputs
    weekly_plan = {
        "daily_menus": [
            {
                "date": "2023-01-01",
                "meals": [
                    {
                        "name": "Breakfast",
                        "food_item": "Oatmeal",
                        "kcal": 300,
                        "protein_g": 10,
                        "carbs_g": 50,
                        "fat_g": 5,
                        "cost": 1.5,
                    }
                ],
            }
        ],
        "shopping_list": {"oats": 500},
        "total_cost": 150.0,
        "adherence_score": 92.5,
    }

    csv_data = to_csv_week(weekly_plan)
    assert isinstance(csv_data, bytes)

    # Test PDF functions if ReportLab is available
    if REPORTLAB_AVAILABLE:
        pdf_data = to_pdf_day(meal_plan)
        assert isinstance(pdf_data, bytes)
        assert len(pdf_data) > 0

        pdf_data = to_pdf_week(weekly_plan)
        assert isinstance(pdf_data, bytes)
        assert len(pdf_data) > 0

    # Test _import_reportlab_modules function
    if REPORTLAB_AVAILABLE:
        classes = _import_reportlab_modules()
        assert isinstance(classes, dict)
        assert "colors" in classes
        assert "letter" in classes
        assert "getSampleStyleSheet" in classes
    else:
        with pytest.raises(ImportError):
            _import_reportlab_modules()


def test_exports_import_error_cases():
    """Test export functions when ReportLab is not available."""
    # Mock REPORTLAB_AVAILABLE to False to simulate missing ReportLab
    with patch("core.exports.REPORTLAB_AVAILABLE", False):
        from core.exports import _import_reportlab_modules, to_pdf_day, to_pdf_week

        # Test that PDF functions raise ImportError when ReportLab is not available
        meal_plan = {"meals": []}
        weekly_plan = {"daily_menus": []}

        with pytest.raises(ImportError) as exc_info:
            to_pdf_day(meal_plan)
        assert "ReportLab is required for PDF export" in str(exc_info.value)

        with pytest.raises(ImportError) as exc_info:
            to_pdf_week(weekly_plan)
        assert "ReportLab is required for PDF export" in str(exc_info.value)

        with pytest.raises(ImportError) as exc_info:
            _import_reportlab_modules()
        assert "ReportLab is required for PDF export" in str(exc_info.value)
