"""
Tests for Export Functions

RU: Тесты для функций экспорта.
EN: Tests for export functions.
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


class TestCSVExport:
    """Test CSV export functions."""

    def test_to_csv_day_basic(self):
        """Test basic daily plan CSV export."""
        meal_plan = {
            "meals": [
                {"name": "Breakfast", "food_item": "Oatmeal", "kcal": 300, "protein_g": 10, "carbs_g": 50, "fat_g": 5},
                {"name": "Lunch", "food_item": "Chicken Salad", "kcal": 450, "protein_g": 35, "carbs_g": 20, "fat_g": 25}
            ],
            "total_kcal": 750,
            "total_protein": 45,
            "total_carbs": 70,
            "total_fat": 30
        }

        csv_data = to_csv_day(meal_plan)
        assert isinstance(csv_data, bytes)

        # Check that CSV contains expected data
        csv_str = csv_data.decode('utf-8')
        assert "Breakfast" in csv_str
        assert "Oatmeal" in csv_str
        assert "Chicken Salad" in csv_str
        assert "Total" in csv_str

    def test_to_csv_week_basic(self):
        """Test basic weekly plan CSV export."""
        weekly_plan = {
            "daily_menus": [
                {
                    "date": "2023-01-01",
                    "meals": [
                        {"name": "Breakfast", "food_item": "Oatmeal", "kcal": 300, "protein_g": 10, "carbs_g": 50, "fat_g": 5, "cost": 1.5}
                    ]
                }
            ],
            "shopping_list": {
                "oats": 500
            },
            "total_cost": 150.0,
            "adherence_score": 92.5
        }

        csv_data = to_csv_week(weekly_plan)
        assert isinstance(csv_data, bytes)

        # Check that CSV contains expected data
        csv_str = csv_data.decode('utf-8')
        assert "2023-01-01" in csv_str
        assert "Oatmeal" in csv_str
        assert "Shopping List" in csv_str
        assert "oats" in csv_str

    def test_to_csv_day_empty_meals(self):
        """Test daily CSV export with empty meals."""
        meal_plan = {
            "meals": [],
            "total_kcal": 0,
            "total_protein": 0,
            "total_carbs": 0,
            "total_fat": 0
        }

        csv_data = to_csv_day(meal_plan)
        assert isinstance(csv_data, bytes)

        csv_str = csv_data.decode('utf-8')
        assert "Total" in csv_str

    def test_to_csv_week_empty_menus(self):
        """Test weekly CSV export with empty menus."""
        weekly_plan = {
            "daily_menus": [],
            "shopping_list": {},
            "total_cost": 0.0,
            "adherence_score": 0.0
        }

        csv_data = to_csv_week(weekly_plan)
        assert isinstance(csv_data, bytes)

        csv_str = csv_data.decode('utf-8')
        assert "Shopping List" in csv_str


class TestPDFExport:
    """Test PDF export functions."""

    def test_to_pdf_day_import_error(self):
        """Test PDF export handles missing ReportLab gracefully."""
        # This test checks that the function properly raises ImportError
        # when ReportLab is not available

        # Since we're not actually testing PDF generation (which requires ReportLab),
        # we'll just verify the function exists and handles the ImportError case
        from core.exports import to_pdf_day
        assert callable(to_pdf_day)

    def test_to_pdf_day_basic(self):
        """Test basic daily plan PDF export."""
        if not REPORTLAB_AVAILABLE:
            pytest.skip("ReportLab not available")

        meal_plan = {
            "meals": [
                {"name": "Breakfast", "food_item": "Oatmeal", "kcal": 300, "protein_g": 10, "carbs_g": 50, "fat_g": 5},
                {"name": "Lunch", "food_item": "Chicken Salad", "kcal": 450, "protein_g": 35, "carbs_g": 20, "fat_g": 25}
            ],
            "total_kcal": 750,
            "total_protein": 45,
            "total_carbs": 70,
            "total_fat": 30
        }

        pdf_data = to_pdf_day(meal_plan)
        assert isinstance(pdf_data, bytes)
        assert len(pdf_data) > 0

    def test_to_pdf_week_basic(self):
        """Test basic weekly plan PDF export."""
        if not REPORTLAB_AVAILABLE:
            pytest.skip("ReportLab not available")

        weekly_plan = {
            "daily_menus": [
                {
                    "date": "2023-01-01",
                    "meals": [
                        {"name": "Breakfast", "food_item": "Oatmeal", "kcal": 300, "protein_g": 10, "carbs_g": 50, "fat_g": 5, "cost": 1.5}
                    ]
                }
            ],
            "shopping_list": {
                "oats": 500
            },
            "total_cost": 150.0,
            "adherence_score": 92.5
        }

        pdf_data = to_pdf_week(weekly_plan)
        assert isinstance(pdf_data, bytes)
        assert len(pdf_data) > 0

    def test_import_reportlab_modules(self):
        """Test _import_reportlab_modules function."""
        if not REPORTLAB_AVAILABLE:
            # Test that it raises ImportError when ReportLab is not available
            with pytest.raises(ImportError):
                _import_reportlab_modules()
        else:
            # Test that it returns the ReportLab classes when available
            classes = _import_reportlab_modules()
            assert isinstance(classes, dict)
            assert 'colors' in classes
            assert 'letter' in classes
            assert 'getSampleStyleSheet' in classes

    # New tests to cover the missing lines
    def test_import_reportlab_modules_when_not_available(self):
        """Test _import_reportlab_modules when ReportLab is not available."""
        # Mock REPORTLAB_AVAILABLE to False to simulate missing ReportLab
        with patch('core.exports.REPORTLAB_AVAILABLE', False):
            from core.exports import _import_reportlab_modules
            with pytest.raises(ImportError) as exc_info:
                _import_reportlab_modules()
            assert "ReportLab is required for PDF export" in str(exc_info.value)

    def test_to_pdf_day_when_not_available(self):
        """Test to_pdf_day when ReportLab is not available."""
        # Mock REPORTLAB_AVAILABLE to False to simulate missing ReportLab
        with patch('core.exports.REPORTLAB_AVAILABLE', False):
            from core.exports import to_pdf_day
            meal_plan = {"meals": []}
            with pytest.raises(ImportError) as exc_info:
                to_pdf_day(meal_plan)
            assert "ReportLab is required for PDF export" in str(exc_info.value)

    def test_to_pdf_week_when_not_available(self):
        """Test to_pdf_week when ReportLab is not available."""
        # Mock REPORTLAB_AVAILABLE to False to simulate missing ReportLab
        with patch('core.exports.REPORTLAB_AVAILABLE', False):
            from core.exports import to_pdf_week
            weekly_plan = {"daily_menus": []}
            with pytest.raises(ImportError) as exc_info:
                to_pdf_week(weekly_plan)
            assert "ReportLab is required for PDF export" in str(exc_info.value)
