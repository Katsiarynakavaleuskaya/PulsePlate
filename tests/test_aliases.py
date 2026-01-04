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


def test_load_aliases_schema_alias_canonical(tmp_path):
    """
    Test _load_aliases with alias,canonical schema.

    RU: Тест загрузки алиасов с схемой alias,canonical.
    EN: Test alias loading with alias,canonical schema.

    Verifies that lowercase alias maps to canonical as provided.
    """
    temp_file = tmp_path / "aliases.csv"
    temp_file.write_text(
        "alias,canonical\nleche,Milk\nPOLLO,Chicken\n  yogurt  ,  Greek Yogurt  \nManzana,Apple\n",
        encoding="utf-8",
    )

    table = _load_aliases(str(temp_file))

    # Verify lowercase alias maps to canonical as provided (not lowercased)
    assert table["leche"] == "Milk"
    assert table["pollo"] == "Chicken"  # Original was POLLO, should be lowercased
    assert table["yogurt"] == "Greek Yogurt"  # Whitespace trimmed
    assert table["manzana"] == "Apple"
    assert len(table) == 4


def test_load_aliases_schema_primary_aliases_mixed_delimiters(tmp_path):
    """
    Test _load_aliases with primary,aliases schema and mixed delimiters.

    RU: Тест загрузки алиасов с схемой primary,aliases и смешанными разделителями.
    EN: Test alias loading with primary,aliases schema and mixed delimiters.

    Verifies that:
    - Each trimmed/lowercased alias maps to primary
    - primary.lower() maps to primary
    - Mixed ';' and ',' delimiters are handled correctly
    """
    temp_file = tmp_path / "aliases.csv"
    temp_file.write_text(
        "primary,aliases\n"
        "Milk,leche;lait;молоко\n"
        "Chicken,pollo;chicken breast;курица\n"
        'Apple,"manzana,яблоко;apple"\n'
        "Greek Yogurt,yogurt;yoghurt;йогурт\n",
        encoding="utf-8",
    )

    table = _load_aliases(str(temp_file))

    # Verify each alias maps to primary
    assert table["leche"] == "Milk"
    assert table["lait"] == "Milk"
    assert table["молоко"] == "Milk"
    assert table["pollo"] == "Chicken"
    assert table["chicken breast"] == "Chicken"
    assert table["курица"] == "Chicken"
    assert table["manzana"] == "Apple"
    assert table["яблоко"] == "Apple"
    assert table["apple"] == "Apple"
    assert table["yogurt"] == "Greek Yogurt"
    assert table["yoghurt"] == "Greek Yogurt"
    assert table["йогурт"] == "Greek Yogurt"

    # Verify primary.lower() maps to primary (as provided)
    assert table["milk"] == "Milk"
    assert table["chicken"] == "Chicken"
    assert table["apple"] == "Apple"
    assert table["greek yogurt"] == "Greek Yogurt"


def test_load_aliases_handles_missing_empty_fields(tmp_path):
    """
    Test _load_aliases gracefully handles missing/empty fields.

    RU: Тест обработки отсутствующих/пустых полей.
    EN: Test graceful handling of missing/empty fields.

    Verifies that missing/empty fields are ignored.
    """
    # Test with alias,canonical schema
    temp_file1 = tmp_path / "aliases1.csv"
    temp_file1.write_text(
        "alias,canonical\n"
        "valid_alias,Valid Canonical\n"
        ",Empty Alias\n"  # Missing alias
        "empty_canonical,\n"  # Missing canonical
        ",,\n"  # Both empty
        "  ,  \n"  # Both whitespace only
        "another_valid,Another Valid\n",
        encoding="utf-8",
    )

    table1 = _load_aliases(str(temp_file1))
    # Only valid entries should be in the table
    assert table1["valid_alias"] == "Valid Canonical"
    assert table1["another_valid"] == "Another Valid"
    assert len(table1) == 2

    # Test with primary,aliases schema
    temp_file2 = tmp_path / "aliases2.csv"
    temp_file2.write_text(
        "primary,aliases\n"
        "Valid Primary,alias1;alias2\n"
        ",Empty Primary\n"  # Missing primary (should be skipped)
        "Another Primary,\n"  # Missing aliases (only primary should be mapped)
        "  ,  \n"  # Both empty
        "Final Primary,alias3;alias4\n",
        encoding="utf-8",
    )

    table2 = _load_aliases(str(temp_file2))
    # Verify valid entries
    assert table2["alias1"] == "Valid Primary"
    assert table2["alias2"] == "Valid Primary"
    assert table2["valid primary"] == "Valid Primary"  # primary.lower() mapping
    assert table2["another primary"] == "Another Primary"  # primary.lower() mapping
    assert table2["alias3"] == "Final Primary"
    assert table2["alias4"] == "Final Primary"
    assert table2["final primary"] == "Final Primary"
    # Empty primary row should be skipped entirely
    assert len(table2) == 7


def test_load_aliases_none_or_non_existent_path(tmp_path, monkeypatch):
    """
    Test _load_aliases with None or non-existent path returns empty dict.

    RU: Тест _load_aliases с None или несуществующим путем возвращает пустой словарь.
    EN: Test _load_aliases with None or non-existent path returns empty dict.
    """
    # Test with non-existent path explicitly
    result = _load_aliases("/non/existent/path/aliases.csv")
    assert result == {}

    # Test with None - mock the default path to point to non-existent file
    from core import aliases as aliases_mod

    non_existent_path = str(tmp_path / "non_existent.csv")
    original_join = aliases_mod.os.path.join

    def mock_join(*args):
        if len(args) >= 3 and "food_aliases.csv" in args:
            return non_existent_path
        return original_join(*args)

    monkeypatch.setattr(aliases_mod.os.path, "join", mock_join)
    result2 = _load_aliases(None)
    assert result2 == {}


def test_load_aliases_schema_primary_aliases_whitespace_trimming(tmp_path):
    """
    Test _load_aliases with primary,aliases schema handles whitespace correctly.

    RU: Тест обработки пробелов в схеме primary,aliases.
    EN: Test whitespace handling in primary,aliases schema.
    """
    temp_file = tmp_path / "aliases.csv"
    temp_file.write_text(
        "primary,aliases\n"
        "  Milk  ,  leche  ;  lait  \n"
        "Chicken,pollo ; chicken ; курица\n"
        "  Apple  ,manzana; яблоко \n",
        encoding="utf-8",
    )

    table = _load_aliases(str(temp_file))

    # Verify whitespace is trimmed from aliases and they're lowercased
    assert table["leche"] == "Milk"
    assert table["lait"] == "Milk"
    assert table["pollo"] == "Chicken"
    assert table["chicken"] == "Chicken"
    assert table["курица"] == "Chicken"
    assert table["manzana"] == "Apple"
    assert table["яблоко"] == "Apple"

    # Verify primary.lower() maps to primary (with trimmed primary)
    assert table["milk"] == "Milk"
    assert table["chicken"] == "Chicken"
    assert table["apple"] == "Apple"


if __name__ == "__main__":
    pytest.main([__file__])
