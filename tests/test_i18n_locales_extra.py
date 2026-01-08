import pytest

from core.i18n import normalize_lang


@pytest.mark.parametrize(
    "val,expected",
    [
        # Base languages
        ("ru", "ru"),
        ("en", "en"),
        ("es", "es"),
        # Case insensitive
        ("RU", "ru"),
        ("EN", "en"),
        ("ES", "es"),
        # Standard locales
        ("en-US", "en"),
        ("en-GB", "en"),
        ("es-MX", "es"),
        # Special cases (product goal: RU/ES/EN localization)
        ("es-ES", "es"),  # Changed: product goal (RU/ES/EN localization)
        ("es-AR", "es"),  # Changed: product goal (RU/ES/EN localization)
        ("ru-RU", "ru"),  # Changed: product goal (RU/ES/EN localization)
        # Word aliases
        ("russian", "ru"),
        ("english", "en"),
        ("spanish", "es"),
        ("español", "es"),
        ("русский", "ru"),
        # Edge cases and fallbacks
        ("xx-YY", "en"),  # Unknown locale -> English default
        ("", "en"),  # Empty string -> English default
        (None, "en"),  # None -> English default
        ("unknown", "en"),  # Unknown language -> English default
        ("fr", "en"),  # French -> English default (not supported)
        ("de", "en"),  # German -> English default (not supported)
    ],
)
def test_normalize_lang_comprehensive(val, expected):
    """Test normalize_lang with comprehensive edge cases and aliases."""
    assert normalize_lang(val) == expected


def test_normalize_lang_with_underscores():
    """Test that underscores are converted to hyphens."""
    assert normalize_lang("en_US") == "en"
    assert normalize_lang("es_MX") == "es"
    assert normalize_lang("ru_RU") == "ru"  # Changed: product goal (RU/ES/EN localization)


def test_normalize_lang_strip_whitespace():
    """Test that input is stripped of whitespace."""
    assert normalize_lang("  en  ") == "en"
    assert normalize_lang("\tru\n") == "ru"
    assert normalize_lang(" es-ES ") == "es"  # Changed: product goal (RU/ES/EN localization)
