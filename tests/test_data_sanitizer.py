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
    """Test that unexpected keys are rejected (extra='forbid')."""
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
    # day_micros validator returns empty dict for None input
    # model_dump(exclude_none=True) only excludes None values, not empty dicts
    assert result.get("day_micros") == {}
    assert result["meals_per_day"] == 3  # Default value


def test_sanitize_micros_none_input() -> None:
    """Test line 50: _sanitize_micros returns None for None input."""
    from core.data_sanitizer import _sanitize_micros

    result = _sanitize_micros(None, 20)
    assert result is None


def test_sanitize_micros_non_dict() -> None:
    """Test line 52: _sanitize_micros raises ValueError for non-dict."""
    from core.data_sanitizer import _sanitize_micros

    with pytest.raises(ValueError, match="Micros must be a dictionary"):
        _sanitize_micros("not a dict", 20)  # type: ignore[arg-type]


def test_sanitize_micros_too_many_items() -> None:
    """Test line 54: _sanitize_micros raises ValueError for too many items."""
    from core.data_sanitizer import _sanitize_micros

    too_many = {f"nutrient_{i}": 1.0 for i in range(30)}
    with pytest.raises(ValueError, match="Too many micronutrients"):
        _sanitize_micros(too_many, 20)


def test_sanitize_micros_non_string_key() -> None:
    """Test line 59: _sanitize_micros raises ValueError for non-string key."""
    from core.data_sanitizer import _sanitize_micros

    with pytest.raises(ValueError, match="Micronutrient keys must be strings"):
        _sanitize_micros({123: 5.0}, 20)  # type: ignore[dict-item]


def test_sanitize_micros_key_too_long() -> None:
    """Test line 64: _sanitize_micros raises ValueError for key > 100 chars."""
    from core.data_sanitizer import _sanitize_micros

    long_key = "A" * 101
    with pytest.raises(ValueError, match="Micronutrient key too long"):
        _sanitize_micros({long_key: 5.0}, 20)


def test_sanitize_micros_non_numeric_value() -> None:
    """Test line 68: _sanitize_micros raises ValueError for non-numeric value."""
    from core.data_sanitizer import _sanitize_micros

    with pytest.raises(ValueError, match="must be numeric"):
        _sanitize_micros({"iron_mg": "not numeric"}, 20)  # type: ignore[dict-item]


def test_sanitize_micros_value_out_of_range() -> None:
    """Test line 70: _sanitize_micros raises ValueError for value out of range."""
    from core.data_sanitizer import _sanitize_micros

    with pytest.raises(ValueError, match="out of range"):
        _sanitize_micros({"iron_mg": 200000}, 20)


def test_visual_shape_string_exceeds_max_length() -> None:
    """Test line 99: VisualShapeSchema raises error for string > MAX_STRING_LENGTH."""
    invalid_data = {
        "kcal": 2000,
        "macros": {"protein_g": 125, "fat_g": 67, "carbs_g": 250, "fiber_g": 25},
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
                "label": "A" * 600,  # Exceeds MAX_STRING_LENGTH
                "tooltip": "Normal",
            }
        ],
        "meals": [],
    }

    with pytest.raises(ValidationError, match="validation failed"):
        sanity_filter_plate_data(invalid_data)


def test_meal_title_exceeds_max_length() -> None:
    """Test line 126: MealSchema raises error for title > MAX_STRING_LENGTH."""
    invalid_data = {
        "kcal": 2000,
        "macros": {"protein_g": 125, "fat_g": 67, "carbs_g": 250, "fiber_g": 25},
        "portions": {
            "protein_palm": 2.0,
            "fat_thumbs": 1.0,
            "carb_cups": 4.0,
            "veg_cups": 3.0,
        },
        "layout": [],
        "meals": [
            {
                "title": "B" * 600,  # Exceeds MAX_STRING_LENGTH
                "kcal": 500,
                "protein_g": 20,
                "fat_g": 15,
                "carbs_g": 60,
            }
        ],
    }

    with pytest.raises(ValidationError, match="validation failed"):
        sanity_filter_plate_data(invalid_data)


def test_macros_non_dict() -> None:
    """Test line 161: validate_macros raises error for non-dict."""
    invalid_data = {
        "kcal": 2000,
        "macros": "not a dict",  # type: ignore[dict-item]
        "portions": {
            "protein_palm": 2.0,
            "fat_thumbs": 1.0,
            "carb_cups": 4.0,
            "veg_cups": 3.0,
        },
        "layout": [],
        "meals": [],
    }

    with pytest.raises(ValidationError, match="Missing required macro keys|validation failed"):
        sanity_filter_plate_data(invalid_data)


def test_macros_non_string_key() -> None:
    """Test line 179: validate_macros raises error for non-string key."""
    from core.data_sanitizer import PlateDataSchema

    with pytest.raises(ValueError, match="Macro keys must be strings"):
        PlateDataSchema.validate_macros(
            {123: 50, "fat_g": 67, "carbs_g": 250, "fiber_g": 25}  # type: ignore[dict-item]
        )


def test_macros_unexpected_key() -> None:
    """Test line 182: validate_macros raises error for unexpected key."""
    from core.data_sanitizer import PlateDataSchema

    with pytest.raises(ValueError, match="Unexpected macro key"):
        PlateDataSchema.validate_macros(
            {
                "protein_g": 125,
                "fat_g": 67,
                "carbs_g": 250,
                "fiber_g": 25,
                "sugar_g": 50,  # Unexpected key
            }
        )


def test_macros_non_integer_value() -> None:
    """Test line 189: validate_macros raises error for non-integer value."""
    from core.data_sanitizer import PlateDataSchema

    with pytest.raises(ValueError, match="must be an integer"):
        PlateDataSchema.validate_macros(
            {
                "protein_g": "not an int",  # type: ignore[dict-item]
                "fat_g": 67,
                "carbs_g": 250,
                "fiber_g": 25,
            }
        )


def test_macros_out_of_range() -> None:
    """Test line 192: validate_macros raises error for out of range value."""
    from core.data_sanitizer import PlateDataSchema

    with pytest.raises(ValueError, match="out of range"):
        PlateDataSchema.validate_macros(
            {"protein_g": 9999, "fat_g": 67, "carbs_g": 250, "fiber_g": 25}
        )


def test_portions_non_dict() -> None:
    """Test line 202: validate_portions raises error for non-dict."""
    invalid_data = {
        "kcal": 2000,
        "macros": {"protein_g": 125, "fat_g": 67, "carbs_g": 250, "fiber_g": 25},
        "portions": "not a dict",  # type: ignore[dict-item]
        "layout": [],
        "meals": [],
    }

    with pytest.raises(ValidationError, match="validation failed"):
        sanity_filter_plate_data(invalid_data)


def test_portions_non_string_key() -> None:
    """Test line 212: validate_portions raises error for non-string key."""
    from core.data_sanitizer import PlateDataSchema

    with pytest.raises(ValueError, match="Portion keys must be strings"):
        PlateDataSchema.validate_portions(
            {
                123: 2.0,  # type: ignore[dict-item]
                "fat_thumbs": 1.0,
                "carb_cups": 4.0,
                "veg_cups": 3.0,
            }
        )


def test_portions_unexpected_key() -> None:
    """Test line 215: validate_portions raises error for unexpected key."""
    from core.data_sanitizer import PlateDataSchema

    with pytest.raises(ValueError, match="Unexpected portion key"):
        PlateDataSchema.validate_portions(
            {
                "protein_palm": 2.0,
                "fat_thumbs": 1.0,
                "carb_cups": 4.0,
                "veg_cups": 3.0,
                "fruit_cups": 2.0,  # Unexpected
            }
        )


def test_portions_non_numeric_value() -> None:
    """Test line 219: validate_portions raises error for non-numeric value."""
    from core.data_sanitizer import PlateDataSchema

    with pytest.raises(ValueError, match="must be numeric"):
        PlateDataSchema.validate_portions(
            {
                "protein_palm": "not numeric",  # type: ignore[dict-item]
                "fat_thumbs": 1.0,
                "carb_cups": 4.0,
                "veg_cups": 3.0,
            }
        )


def test_portions_out_of_range() -> None:
    """Test line 221: validate_portions raises error for value out of range."""
    from core.data_sanitizer import PlateDataSchema

    with pytest.raises(ValueError, match="out of range"):
        PlateDataSchema.validate_portions(
            {
                "protein_palm": 100.0,  # > 50
                "fat_thumbs": 1.0,
                "carb_cups": 4.0,
                "veg_cups": 3.0,
            }
        )


def test_layout_non_list() -> None:
    """Test line 231: validate_layout raises error for non-list."""
    invalid_data = {
        "kcal": 2000,
        "macros": {"protein_g": 125, "fat_g": 67, "carbs_g": 250, "fiber_g": 25},
        "portions": {
            "protein_palm": 2.0,
            "fat_thumbs": 1.0,
            "carb_cups": 4.0,
            "veg_cups": 3.0,
        },
        "layout": "not a list",  # type: ignore[dict-item]
        "meals": [],
    }

    with pytest.raises(ValidationError, match="validation failed"):
        sanity_filter_plate_data(invalid_data)


def test_layout_non_dict_item() -> None:
    """Test line 238: validate_layout raises error for non-dict item."""
    invalid_data = {
        "kcal": 2000,
        "macros": {"protein_g": 125, "fat_g": 67, "carbs_g": 250, "fiber_g": 25},
        "portions": {
            "protein_palm": 2.0,
            "fat_thumbs": 1.0,
            "carb_cups": 4.0,
            "veg_cups": 3.0,
        },
        "layout": ["not a dict"],  # type: ignore[list-item]
        "meals": [],
    }

    with pytest.raises(ValidationError, match="validation failed"):
        sanity_filter_plate_data(invalid_data)


def test_meals_non_dict_item() -> None:
    """Test line 250, 252, 257: validate_meals raises errors for invalid meal."""
    invalid_data = {
        "kcal": 2000,
        "macros": {"protein_g": 125, "fat_g": 67, "carbs_g": 250, "fiber_g": 25},
        "portions": {
            "protein_palm": 2.0,
            "fat_thumbs": 1.0,
            "carb_cups": 4.0,
            "veg_cups": 3.0,
        },
        "layout": [],
        "meals": ["not a dict"],  # type: ignore[list-item]
    }

    with pytest.raises(ValidationError, match="validation failed"):
        sanity_filter_plate_data(invalid_data)


def test_sanity_filter_conversion_error() -> None:
    """Test line 313: Pydantic conversion error handling."""
    # This tests the generic exception handling for Pydantic validation errors
    invalid_data = {
        "kcal": 2000,
        "macros": {"protein_g": 125, "fat_g": 67, "carbs_g": 250, "fiber_g": 25},
        "portions": {
            "protein_palm": 2.0,
            "fat_thumbs": 1.0,
            "carb_cups": 4.0,
            "veg_cups": 3.0,
        },
        "layout": [],
        "meals": [
            {
                # Missing required fields
                "title": "Test",
            }
        ],
    }

    with pytest.raises(ValidationError, match="validation failed"):
        sanity_filter_plate_data(invalid_data)
