"""Tests for core.data_sanitizer module."""

import pytest

from core.data_sanitizer import ValidationError, sanity_filter_plate_data


def test_sanity_filter_valid_plate_data() -> None:
    """Test that valid plate data passes validation."""
    valid_data = {
        "kcal": 2000,
        "macros": {
            "protein_g": 125,
            "fat_g": 67,
            "carbs_g": 250,
            "fiber_g": 25,
        },
        "portions": {
            "protein_palm": 2.1,
            "fat_thumbs": 1.3,
            "carb_cups": 4.2,
            "veg_cups": 3.0,
        },
        "layout": [
            {
                "kind": "plate_sector",
                "fraction": 0.35,
                "label": "Protein",
                "tooltip": "Lean protein",
            },
            {
                "kind": "bowl",
                "fraction": 1.0,
                "label": "Vegetables",
                "tooltip": "Non-starchy veg",
            },
        ],
        "meals": [
            {
                "title": "Breakfast",
                "kcal": 600,
                "protein_g": 30,
                "fat_g": 20,
                "carbs_g": 75,
            },
            {
                "title": "Lunch",
                "kcal": 700,
                "protein_g": 40,
                "fat_g": 25,
                "carbs_g": 85,
                "fiber_g": 10,
            },
        ],
        "day_micros": {
            "iron_mg": 18.0,
            "calcium_mg": 1000.0,
        },
        "meals_per_day": 3,
    }
    result = sanity_filter_plate_data(valid_data)

    # Verify structure is preserved
    assert result["kcal"] == 2000
    assert result["macros"]["protein_g"] == 125
    assert len(result["layout"]) == 2
    assert len(result["meals"]) == 2
    assert result["meals_per_day"] == 3


def test_sanity_filter_missing_required_keys() -> None:
    """Test that missing required keys raises ValidationError."""
    invalid_data = {
        "kcal": 2000,
        "macros": {"protein_g": 125},  # Missing fat_g, carbs_g, fiber_g
        "portions": {"protein_palm": 2.0},
        "layout": [],
        "meals": [],
    }

    with pytest.raises(ValidationError, match="Missing required macro keys"):
        sanity_filter_plate_data(invalid_data)


def test_sanity_filter_invalid_types() -> None:
    """Test that invalid types raise ValidationError."""
    invalid_data = {
        "kcal": "not_an_int",  # Should be int
        "macros": {
            "protein_g": 125,
            "fat_g": 67,
            "carbs_g": 250,
            "fiber_g": 25,
        },
        "portions": {
            "protein_palm": 2.0,
            "fat_thumbs": 1.0,
            "carb_cups": 4.0,
            "veg_cups": 3.0,
        },
        "layout": [],
        "meals": [],
    }

    with pytest.raises(ValidationError, match="validation failed"):
        sanity_filter_plate_data(invalid_data)


def test_sanity_filter_out_of_range_values() -> None:
    """Test that out-of-range values raise ValidationError."""
    invalid_data = {
        "kcal": 15000,  # Too high (max 10000)
        "macros": {
            "protein_g": 125,
            "fat_g": 67,
            "carbs_g": 250,
            "fiber_g": 25,
        },
        "portions": {
            "protein_palm": 2.0,
            "fat_thumbs": 1.0,
            "carb_cups": 4.0,
            "veg_cups": 3.0,
        },
        "layout": [],
        "meals": [],
    }

    with pytest.raises(ValidationError, match="validation failed"):
        sanity_filter_plate_data(invalid_data)


def test_sanity_filter_html_injection() -> None:
    """Test that HTML/JS injection attempts are sanitized."""
    malicious_data = {
        "kcal": 2000,
        "macros": {
            "protein_g": 125,
            "fat_g": 67,
            "carbs_g": 250,
            "fiber_g": 25,
        },
        "portions": {
            "protein_palm": 2.0,
            "fat_thumbs": 1.0,
            "carb_cups": 4.0,
            "veg_cups": 3.0,
        },
        "layout": [
            {
                "kind": "plate_sector",
                "fraction": 0.5,
                "label": "<script>alert('xss')</script>Protein",
                "tooltip": "onclick='malicious()' Safe tooltip",
            },
        ],
        "meals": [
            {
                "title": "<img src=x onerror=alert(1)>Breakfast",
                "kcal": 600,
                "protein_g": 30,
                "fat_g": 20,
                "carbs_g": 75,
            },
        ],
    }

    result = sanity_filter_plate_data(malicious_data)

    # Verify HTML/JS tags are stripped (not raw HTML tags present)
    assert "<script>" not in result["layout"][0]["label"]
    assert "</script>" not in result["layout"][0]["label"]
    assert "<img" not in result["meals"][0]["title"]
    # Verify dangerous event handlers are removed
    assert "onclick=" not in result["layout"][0]["tooltip"]
    assert "onerror=" not in result["meals"][0]["title"]
    # Should contain safe text (potentially escaped)
    assert (
        "Protein" in result["layout"][0]["label"]
        or "protein" in result["layout"][0]["label"].lower()
    )
    assert (
        "Breakfast" in result["meals"][0]["title"]
        or "breakfast" in result["meals"][0]["title"].lower()
    )
    # Verify no executable JavaScript remains (no unescaped parentheses for function calls)
    assert "alert('" not in result["layout"][0]["label"]
    assert "alert(1)" not in result["meals"][0]["title"]


def test_sanity_filter_oversized_strings() -> None:
    """Test that oversized strings raise ValidationError."""
    oversized_data = {
        "kcal": 2000,
        "macros": {
            "protein_g": 125,
            "fat_g": 67,
            "carbs_g": 250,
            "fiber_g": 25,
        },
        "portions": {
            "protein_palm": 2.0,
            "fat_thumbs": 1.0,
            "carb_cups": 4.0,
            "veg_cups": 3.0,
        },
        "layout": [
            {
                "kind": "plate_sector",
                "fraction": 0.5,
                "label": "A" * 1000,  # Exceeds MAX_STRING_LENGTH (500)
                "tooltip": "Normal",
            },
        ],
        "meals": [],
    }

    with pytest.raises(ValidationError, match="validation failed"):
        sanity_filter_plate_data(oversized_data)


def test_sanity_filter_unexpected_keys() -> None:
    """Test that unexpected keys are dropped (extra='forbid')."""
    data_with_extra = {
        "kcal": 2000,
        "macros": {
            "protein_g": 125,
            "fat_g": 67,
            "carbs_g": 250,
            "fiber_g": 25,
        },
        "portions": {
            "protein_palm": 2.0,
            "fat_thumbs": 1.0,
            "carb_cups": 4.0,
            "veg_cups": 3.0,
        },
        "layout": [],
        "meals": [],
        "unexpected_key": "This should cause an error",  # Extra key
    }

    # With extra='forbid', this should raise an error
    with pytest.raises(ValidationError, match="validation failed"):
        sanity_filter_plate_data(data_with_extra)


def test_sanity_filter_invalid_layout_kind() -> None:
    """Test that invalid layout kind raises ValidationError."""
    invalid_data = {
        "kcal": 2000,
        "macros": {
            "protein_g": 125,
            "fat_g": 67,
            "carbs_g": 250,
            "fiber_g": 25,
        },
        "portions": {
            "protein_palm": 2.0,
            "fat_thumbs": 1.0,
            "carb_cups": 4.0,
            "veg_cups": 3.0,
        },
        "layout": [
            {
                "kind": "invalid_kind",  # Not in allowed set
                "fraction": 0.5,
                "label": "Test",
                "tooltip": "Test",
            },
        ],
        "meals": [],
    }

    with pytest.raises(ValidationError, match="validation failed"):
        sanity_filter_plate_data(invalid_data)


def test_sanity_filter_invalid_fraction() -> None:
    """Test that invalid fraction (outside 0-1) raises ValidationError."""
    invalid_data = {
        "kcal": 2000,
        "macros": {
            "protein_g": 125,
            "fat_g": 67,
            "carbs_g": 250,
            "fiber_g": 25,
        },
        "portions": {
            "protein_palm": 2.0,
            "fat_thumbs": 1.0,
            "carb_cups": 4.0,
            "veg_cups": 3.0,
        },
        "layout": [
            {
                "kind": "plate_sector",
                "fraction": 1.5,  # Exceeds 1.0
                "label": "Test",
                "tooltip": "Test",
            },
        ],
        "meals": [],
    }

    with pytest.raises(ValidationError, match="validation failed"):
        sanity_filter_plate_data(invalid_data)


def test_sanity_filter_too_many_meals() -> None:
    """Test that too many meals raises ValidationError."""
    meals = [
        {
            "title": f"Meal {i}",
            "kcal": 200,
            "protein_g": 10,
            "fat_g": 5,
            "carbs_g": 25,
        }
        for i in range(15)  # Exceeds MAX_MEALS (10)
    ]

    invalid_data = {
        "kcal": 2000,
        "macros": {
            "protein_g": 125,
            "fat_g": 67,
            "carbs_g": 250,
            "fiber_g": 25,
        },
        "portions": {
            "protein_palm": 2.0,
            "fat_thumbs": 1.0,
            "carb_cups": 4.0,
            "veg_cups": 3.0,
        },
        "layout": [],
        "meals": meals,
    }

    with pytest.raises(ValidationError, match="validation failed"):
        sanity_filter_plate_data(invalid_data)


def test_sanity_filter_non_dict_input() -> None:
    """Test that non-dict input raises ValidationError."""
    with pytest.raises(ValidationError, match="Input must be a dictionary"):
        sanity_filter_plate_data(["not", "a", "dict"])  # type: ignore[arg-type]


def test_sanity_filter_meal_with_micros() -> None:
    """Test that meals with micronutrient data are validated correctly."""
    valid_data = {
        "kcal": 2000,
        "macros": {
            "protein_g": 125,
            "fat_g": 67,
            "carbs_g": 250,
            "fiber_g": 25,
        },
        "portions": {
            "protein_palm": 2.0,
            "fat_thumbs": 1.0,
            "carb_cups": 4.0,
            "veg_cups": 3.0,
        },
        "layout": [],
        "meals": [
            {
                "title": "Breakfast",
                "kcal": 600,
                "protein_g": 30,
                "fat_g": 20,
                "carbs_g": 75,
                "micros": {
                    "iron_mg": 5.0,
                    "vitamin_c_mg": 30.0,
                },
            },
        ],
    }

    result = sanity_filter_plate_data(valid_data)
    assert result["meals"][0]["micros"]["iron_mg"] == 5.0


def test_sanity_filter_default_values() -> None:
    """Test that default values are applied correctly."""
    minimal_data = {
        "kcal": 2000,
        "macros": {
            "protein_g": 125,
            "fat_g": 67,
            "carbs_g": 250,
            "fiber_g": 25,
        },
        "portions": {
            "protein_palm": 2.0,
            "fat_thumbs": 1.0,
            "carb_cups": 4.0,
            "veg_cups": 3.0,
        },
        "layout": [],
        "meals": [],
        # day_micros and meals_per_day omitted - should use defaults
    }

    result = sanity_filter_plate_data(minimal_data)
    # day_micros validator returns empty dict for None input (line 237-238 in data_sanitizer.py)
    # but model_dump(exclude_none=True) treats empty dict as None for Optional fields
    # and excludes it from the output
    assert "day_micros" not in result or result["day_micros"] is None
    assert result["meals_per_day"] == 3  # Default value
