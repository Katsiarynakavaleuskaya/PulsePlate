"""
Alias Mapping Tests

RU: Тесты маппинга синонимов.
EN: Alias mapping tests.
"""

import os
import tempfile
from typing import Any, cast

import pytest

from core.aliases import _load_aliases, add_alias, map_to_canonical


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
    assert map_to_canonical(cast(Any, None)) == "unknown"

    # Test whitespace
    assert map_to_canonical("  Spinach  ") == "spinach_raw"

    # Test special characters
    assert map_to_canonical("Spinach, raw") == "spinach_raw"
    assert map_to_canonical("Spinach - raw") == "spinach_raw"


def test_load_aliases_file_not_found():
    """Test _load_aliases when file doesn't exist."""
    # Test with non-existent file
    aliases = _load_aliases("/non/existent/path.csv")
    assert aliases == {}


def test_add_alias_new_file():
    """Test add_alias creating new file."""
    # Create temporary file path
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        temp_path = f.name

    try:
        # Remove the file to test creation
        os.unlink(temp_path)

        # Add alias to non-existent file
        add_alias("test_alias", "test_canonical", temp_path)

        # Verify file was created and contains the alias
        aliases = _load_aliases(temp_path)
        assert "test_alias" in aliases
        assert aliases["test_alias"] == "test_canonical"

    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_add_alias_existing_file():
    """Test add_alias appending to existing file."""
    # Create temporary file with initial content
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("alias,canonical\n")
        f.write("existing,existing_canonical\n")
        temp_path = f.name

    try:
        # Add new alias to existing file
        add_alias("new_alias", "new_canonical", temp_path)

        # Verify both aliases exist
        aliases = _load_aliases(temp_path)
        assert "existing" in aliases
        assert aliases["existing"] == "existing_canonical"
        assert "new_alias" in aliases
        assert aliases["new_alias"] == "new_canonical"

    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_add_alias_default_path(monkeypatch, tmp_path):
    """Test add_alias with default path without mutating real data."""
    temp_file = tmp_path / "aliases.csv"
    temp_path_str = temp_file.as_posix()

    # Route default path resolution to a temp file so the repository data stays untouched.
    from core import aliases as aliases_mod

    monkeypatch.setattr(aliases_mod.os.path, "join", lambda *args: temp_path_str)

    add_alias("test_alias", "test_canonical", cast(Any, None))

    content = temp_file.read_text(encoding="utf-8")
    assert "alias,canonical" in content
    assert "test_alias,test_canonical" in content


if __name__ == "__main__":
    pytest.main([__file__])
