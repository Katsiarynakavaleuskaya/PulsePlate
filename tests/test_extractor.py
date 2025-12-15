"""Unit tests for ingredient extractor module.

Tests defensive parsing and edge cases at the extraction layer.
"""

import math

from app.core.shopping_list.extractor import extract_ingredients_from_plan


def test_extract_ingredients_filters_nan_inf() -> None:
    """Test that NaN and inf values are filtered out by isfinite check."""
    # Direct test bypassing JSON serialization
    plan_data = {
        "daily_menus": [
            {
                "meals": [
                    {
                        "title": "test_meal",
                        "grams": {
                            "valid": 100.0,
                            "nan_value": float("nan"),
                            "inf_value": float("inf"),
                            "neg_inf": float("-inf"),
                        },
                    }
                ]
            }
        ]
    }

    result = extract_ingredients_from_plan(plan_data)

    # Should only extract valid ingredient
    assert len(result) == 1
    assert result[0]["key"] == "valid"
    assert result[0]["quantity"] == 100.0


def test_extract_ingredients_skips_non_string_keys() -> None:
    """Test that non-string ingredient keys are skipped."""
    # Simulate dict with non-string keys (possible from malformed data)
    plan_data = {
        "daily_menus": [
            {
                "meals": [
                    {
                        "title": "test_meal",
                        "grams": {
                            "valid_string": 100.0,
                            123: 50.0,  # numeric key - will be skipped
                            None: 25.0,  # None key - will be skipped
                        },
                    }
                ]
            }
        ]
    }

    result = extract_ingredients_from_plan(plan_data)

    # Should only extract valid string key
    keys = [item["key"] for item in result]
    assert "valid_string" in keys
    assert 123 not in keys
    assert None not in keys
