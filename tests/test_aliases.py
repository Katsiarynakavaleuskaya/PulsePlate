"""
Alias Mapping Tests

RU: Тесты маппинга синонимов.
EN: Alias mapping tests.
"""

import os
import tempfile

import pytest

from core.aliases import _load_aliases, map_to_canonical


def test_map_to_canonical_basic():
    """Test basic alias mapping."""
    # Test direct mapping from aliases file
    assert map_to_canonical("Spinach") == "spinach_raw"
    assert map_to_canonical("Chicken Breast") == "chicken_breast"
    assert map_to_canonical("Greek Yogurt") == "greek_yogurt"


def test_map_to_canonical_fallback():
    """Test fallback to snake_case conversion."""
    # Test fallback when no alias exists
    assert map_to_canonical("Broccoli") == "broccoli"
    assert map_to_canonical("Sweet Potato") == "sweet_potato"
    assert map_to_canonical("Brown Rice") == "brown_rice"


def test_map_to_canonical_with_custom_aliases():
    """Test with custom aliases file."""
    # Create temporary aliases file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("alias,canonical\n")
        f.write("espinacas,spinach_raw\n")
        f.write("pollo,chicken_breast\n")
        temp_path = f.name

    try:
        # Load aliases from temp file
        aliases = _load_aliases(temp_path)

        # Test that custom aliases work
        # Note: We can't easily test the actual map_to_canonical function here
        # because it uses a cached version of _load_aliases with the default path
        assert "espinacas" in aliases
        assert aliases["espinacas"] == "spinach_raw"
        assert "pollo" in aliases
        assert aliases["pollo"] == "chicken_breast"
    finally:
        # Clean up temp file
        os.unlink(temp_path)


def test_map_to_canonical_edge_cases():
    """Test edge cases."""
    # Test empty string
    assert map_to_canonical("") == "unknown"

    # Test None
    assert map_to_canonical(None) == "unknown"

    # Test whitespace
    assert map_to_canonical("  Spinach  ") == "spinach_raw"

    # Test special characters
    assert map_to_canonical("Spinach, raw") == "spinach_raw"
    assert map_to_canonical("Spinach - raw") == "spinach_raw"


if __name__ == "__main__":
    pytest.main([__file__])
