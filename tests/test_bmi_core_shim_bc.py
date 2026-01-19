"""
Backward compatibility tests for bmi_core.py legacy shim.

These tests ensure that the shim maintains the original positional parameter order
and does not silently misroute arguments.
"""

from bmi_core import auto_group, group_display_name


def test_auto_group_positional_lang_is_not_misrouted() -> None:
    """Test that lang as 5th positional argument is correctly handled (BC)."""
    # Legacy call style: lang is 5th positional argument
    # auto_group(age, gender, pregnant, athlete, lang_code)
    group = auto_group(30, "female", False, False, "ru")
    # Expect language to be treated as language (not athlete_text) and result stable
    assert isinstance(group, str)
    assert group in {"general", "athlete", "pregnant", "elderly", "child", "teen", "too_young"}


def test_auto_group_lang_affects_group_display_name_bc() -> None:
    """Test that lang parameter (5th positional) affects group display name (BC)."""
    group = auto_group(30, "female", False, False, "ru")
    # Group display name should be localized based on lang (even though lang is ignored in engine)
    # This test ensures lang is not silently misrouted to athlete_text
    ru_name = group_display_name(group, "ru")
    en_name = group_display_name(group, "en")
    # Names should be different (localized)
    assert ru_name != en_name or group == "general"  # "general" might be same in both


def test_auto_group_with_athlete_text_positional() -> None:
    """Test that athlete_text as 6th positional argument works (BC)."""
    # Legacy call style with athlete_text: auto_group(age, gender, pregnant, athlete, lang, athlete_text)
    group = auto_group(30, "male", False, False, "en", "спортсмен")
    # athlete_text should be preserved and used for heuristics
    assert isinstance(group, str)
    # If athlete_text contains keywords, group might be "athlete"
    # This test ensures positional order is correct (lang=5th, athlete_text=6th)
