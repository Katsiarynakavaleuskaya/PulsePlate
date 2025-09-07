"""
Simple tests for the simplified exports module
"""

from pathlib import Path

from core.exports_simple import to_csv_day, to_csv_week, to_pdf_day, to_pdf_week


def test_csv_day_simple():
    """Test basic daily plan CSV export."""
    plate = {
        "kcal": 1900,
        "macros": {"protein_g": 110, "fat_g": 60, "carbs_g": 215, "fiber_g": 25},
        "meals": [
            {
                "title": "Овсянка",
                "kcal": 450,
                "protein_g": 18,
                "fat_g": 12,
                "carbs_g": 70,
            }
        ],
    }

    csv_text = to_csv_day(plate)
    assert isinstance(csv_text, str)
    assert "protein_g" in csv_text
    assert "Овсянка" in csv_text
    assert "450" in csv_text


def test_csv_week_simple():
    """Test basic weekly plan CSV export."""
    week = {
        "days": [
            {
                "kcal": 1900,
                "macros": {
                    "protein_g": 110,
                    "fat_g": 60,
                    "carbs_g": 215,
                    "fiber_g": 25,
                },
            }
        ]
    }

    csv_text = to_csv_week(week)
    assert isinstance(csv_text, str)
    assert "protein_g" in csv_text
    assert "1" in csv_text  # Day number


def test_pdf_day_simple(tmp_path: Path):
    """Test basic daily plan PDF export."""
    plate = {
        "kcal": 1900,
        "macros": {"protein_g": 110, "fat_g": 60, "carbs_g": 215, "fiber_g": 25},
        "meals": [
            {
                "title": "Овсянка",
                "kcal": 450,
                "protein_g": 18,
                "fat_g": 12,
                "carbs_g": 70,
                "fiber_g": 5,
            }
        ],
    }

    out = tmp_path / "day.pdf"
    to_pdf_day(plate, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_pdf_week_simple(tmp_path: Path):
    """Test basic weekly plan PDF export."""
    week = {
        "days": [
            {
                "kcal": 1900,
                "macros": {
                    "protein_g": 110,
                    "fat_g": 60,
                    "carbs_g": 215,
                    "fiber_g": 25,
                },
                "date": "2023-01-01",
                "items": [
                    {
                        "title": "Овсянка",
                        "kcal": 450,
                        "protein_g": 18,
                        "fat_g": 12,
                        "carbs_g": 70,
                        "fiber_g": 5,
                    }
                ],
            }
        ]
    }

    out = tmp_path / "week.pdf"
    to_pdf_week(week, out)
    assert out.exists()
    assert out.stat().st_size > 0
