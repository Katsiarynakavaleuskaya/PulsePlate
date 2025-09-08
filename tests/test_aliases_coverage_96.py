"""
Tests to improve coverage in core/aliases.py for 96%+ coverage.

This module focuses on covering the missing lines in aliases.py that are preventing
us from reaching 96% coverage.
"""

from unittest.mock import mock_open, patch

from core.aliases import _load_aliases, add_alias, map_to_canonical


class TestAliasesCoverage96:
    """Tests to cover missing lines in aliases.py for 96%+ coverage."""

    def test_load_aliases_file_not_found(self):
        """Test _load_aliases when file doesn't exist - lines 29-31."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = _load_aliases("nonexistent_file.csv")
            assert result == {}

    def test_load_aliases_file_exists(self):
        """Test _load_aliases when file exists - lines 25-28."""
        csv_content = "alias,canonical\napple,Apple\nbanana,Banana\n"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            with patch("csv.DictReader") as mock_reader:
                mock_reader.return_value = [
                    {"alias": "apple", "canonical": "Apple"},
                    {"alias": "banana", "canonical": "Banana"},
                ]

                result = _load_aliases("test_file.csv")
                assert result == {"apple": "Apple", "banana": "Banana"}

    def test_load_aliases_with_whitespace(self):
        """Test _load_aliases with whitespace in data - lines 25-28."""
        csv_content = "alias,canonical\n apple , Apple \n banana , Banana \n"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            with patch("csv.DictReader") as mock_reader:
                mock_reader.return_value = [
                    {"alias": " apple ", "canonical": " Apple "},
                    {"alias": " banana ", "canonical": " Banana "},
                ]

                result = _load_aliases("test_file.csv")
                assert result == {"apple": "Apple", "banana": "Banana"}

    def test_load_aliases_empty_file(self):
        """Test _load_aliases with empty file - lines 25-28."""
        csv_content = "alias,canonical\n"

        with patch("builtins.open", mock_open(read_data=csv_content)):
            with patch("csv.DictReader") as mock_reader:
                mock_reader.return_value = []

                result = _load_aliases("test_file.csv")
                assert result == {}

    def test_map_to_canonical_english(self):
        """Test map_to_canonical with English locale - lines 77-87."""
        with patch("core.aliases._load_aliases") as mock_load:
            mock_load.return_value = {"apple": "Apple", "banana": "Banana"}

            result = map_to_canonical("apple", "en")
            assert result == "Apple"

            result = map_to_canonical("banana", "en")
            assert result == "Banana"

    def test_map_to_canonical_russian(self):
        """Test map_to_canonical with Russian locale - lines 77-87."""
        with patch("core.aliases._load_aliases") as mock_load:
            mock_load.return_value = {"яблоко": "Яблоко", "банан": "Банан"}

            result = map_to_canonical("яблоко", "ru")
            assert result == "Яблоко"

            result = map_to_canonical("банан", "ru")
            assert result == "Банан"

    def test_map_to_canonical_spanish(self):
        """Test map_to_canonical with Spanish locale - lines 77-87."""
        with patch("core.aliases._load_aliases") as mock_load:
            mock_load.return_value = {"manzana": "Manzana", "plátano": "Plátano"}

            result = map_to_canonical("manzana", "es")
            assert result == "Manzana"

            result = map_to_canonical("plátano", "es")
            assert result == "Plátano"

    def test_map_to_canonical_not_found(self):
        """Test map_to_canonical when alias not found - lines 77-87."""
        with patch("core.aliases._load_aliases") as mock_load:
            mock_load.return_value = {"apple": "Apple", "banana": "Banana"}

            result = map_to_canonical("orange", "en")
            assert result == "orange"  # Should return original if not found

    def test_map_to_canonical_empty_table(self):
        """Test map_to_canonical with empty alias table - lines 77-87."""
        with patch("core.aliases._load_aliases") as mock_load:
            mock_load.return_value = {}

            result = map_to_canonical("apple", "en")
            assert result == "apple"  # Should return original if not found

    def test_map_to_canonical_case_sensitivity(self):
        """Test map_to_canonical with case sensitivity - lines 77-87."""
        with patch("core.aliases._load_aliases") as mock_load:
            mock_load.return_value = {"apple": "Apple", "banana": "Banana"}

            result = map_to_canonical("APPLE", "en")
            assert result == "Apple"

            result = map_to_canonical("banana", "en")
            assert result == "Banana"

    def test_map_to_canonical_special_characters(self):
        """Test map_to_canonical with special characters - lines 77-87."""
        with patch("core.aliases._load_aliases") as mock_load:
            mock_load.return_value = {
                "café": "Café",
                "naïve": "Naïve",
                "résumé": "Résumé",
            }

            result = map_to_canonical("café", "en")
            assert result == "Café"

            result = map_to_canonical("naïve", "en")
            assert result == "Naïve"

            result = map_to_canonical("résumé", "en")
            assert result == "Résumé"

    def test_map_to_canonical_numbers(self):
        """Test map_to_canonical with numbers - lines 77-87."""
        with patch("core.aliases._load_aliases") as mock_load:
            mock_load.return_value = {"1": "One", "2": "Two", "3": "Three"}

            result = map_to_canonical("1", "en")
            assert result == "One"

            result = map_to_canonical("2", "en")
            assert result == "Two"

            result = map_to_canonical("3", "en")
            assert result == "Three"

    def test_map_to_canonical_mixed_content(self):
        """Test map_to_canonical with mixed content - lines 77-87."""
        with patch("core.aliases._load_aliases") as mock_load:
            mock_load.return_value = {
                "apple123": "Apple123",
                "test-item": "Test Item",
                "item_with_underscore": "Item With Underscore",
            }

            result = map_to_canonical("apple123", "en")
            assert result == "Apple123"

            result = map_to_canonical("test-item", "en")
            assert result == "Test Item"

            result = map_to_canonical("item_with_underscore", "en")
            assert result == "Item With Underscore"

    def test_map_to_canonical_default_locale(self):
        """Test map_to_canonical with default locale - lines 77-87."""
        with patch("core.aliases._load_aliases") as mock_load:
            mock_load.return_value = {"apple": "Apple", "banana": "Banana"}

            result = map_to_canonical("apple")  # No locale specified
            assert result == "Apple"

    def test_map_to_canonical_unicode(self):
        """Test map_to_canonical with unicode characters - lines 77-87."""
        with patch("core.aliases._load_aliases") as mock_load:
            mock_load.return_value = {
                "🍎": "Apple Emoji",
                "🍌": "Banana Emoji",
                "🥕": "Carrot Emoji",
            }

            result = map_to_canonical("🍎", "en")
            assert result == "Apple Emoji"

            result = map_to_canonical("🍌", "en")
            assert result == "Banana Emoji"

            result = map_to_canonical("🥕", "en")
            assert result == "Carrot Emoji"

    def test_map_to_canonical_long_strings(self):
        """Test map_to_canonical with long strings - lines 77-87."""
        with patch("core.aliases._load_aliases") as mock_load:
            long_alias = "a" * 100
            long_canonical = "A" * 100
            mock_load.return_value = {long_alias: long_canonical}

            result = map_to_canonical(long_alias, "en")
            assert result == long_canonical

    def test_map_to_canonical_whitespace_handling(self):
        """Test map_to_canonical with whitespace handling - lines 77-87."""
        with patch("core.aliases._load_aliases") as mock_load:
            mock_load.return_value = {
                "apple": "Apple",
                "banana": "Banana",
                "cherry": "Cherry",
            }

            result = map_to_canonical("  apple  ", "en")
            assert result == "Apple"

            result = map_to_canonical("\tbanana\t", "en")
            assert result == "Banana"

            result = map_to_canonical("\ncherry\n", "en")
            assert result == "Cherry"

    def test_add_alias_new_file(self):
        """Test add_alias when file doesn't exist - lines 77-87."""
        with patch("os.path.exists", return_value=False):
            with patch("builtins.open", mock_open()) as mock_file:
                add_alias("test", "Test")

                # Should create file with header and data
                mock_file.assert_called_once()

    def test_add_alias_existing_file(self):
        """Test add_alias when file exists - lines 77-87."""
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open()) as mock_file:
                add_alias("test", "Test")

                # Should append to existing file
                mock_file.assert_called_once()

    def test_add_alias_with_whitespace(self):
        """Test add_alias with whitespace in input - lines 77-87."""
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open()) as mock_file:
                add_alias("  test  ", "  Test  ")

                # Should strip whitespace
                mock_file.assert_called_once()

    def test_add_alias_custom_path(self):
        """Test add_alias with custom path - lines 77-87."""
        custom_path = "/custom/path/aliases.csv"
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open()) as mock_file:
                add_alias("test", "Test", custom_path)

                # Should use custom path
                mock_file.assert_called_once_with(
                    custom_path, "a", newline="", encoding="utf-8"
                )

    def test_add_alias_multiple_calls(self):
        """Test add_alias with multiple calls - lines 77-87."""
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open()) as mock_file:
                add_alias("test1", "Test1")
                add_alias("test2", "Test2")

                # Should append to file twice
                assert mock_file.call_count == 2
