import tempfile
from pathlib import Path

import pytest

from core.exports import to_csv_day, to_pdf_day


def test_csv_day_ok():
    plate = {"kcal": 1900, "macros": {"protein_g":110,"fat_g":60,"carbs_g":215,"fiber_g":25},
             "meals":[{"name":"Овсянка","food_item":"Овсянка","kcal":450,"protein_g":18,"fat_g":12,"carbs_g":70}]}
    csv_data = to_csv_day(plate)
    assert isinstance(csv_data, bytes)

    # Decode bytes to string for checking content
    csv_text = csv_data.decode('utf-8')
    # Check for expected content in the CSV
    assert "Protein (g)" in csv_text  # Header
    assert "Овсянка" in csv_text      # Meal name
    assert "450" in csv_text          # Calories
    assert "18" in csv_text           # Protein


def test_pdf_day_ok(tmp_path: Path):
    plate = {"kcal": 1900, "macros": {"protein_g":110,"fat_g":60,"carbs_g":215,"fiber_g":25},
             "meals":[{"name":"Овсянка","food_item":"Овсянка","kcal":450,"protein_g":18,"fat_g":12,"carbs_g":70}]}

    # The function returns bytes, so we need to write it to a file
    pdf_data = to_pdf_day(plate)
    assert isinstance(pdf_data, bytes)
    assert len(pdf_data) > 0

    # Write to file to verify it works
    out = tmp_path / "day.pdf"
    with open(out, "wb") as f:
        f.write(pdf_data)
    assert out.exists() and out.stat().st_size > 0
