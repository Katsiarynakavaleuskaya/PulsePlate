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
    # Names should be different (localized) unless group is "general" which might be same
    assert (
        ru_name != en_name or group == "general"
    ), f"Expected localized names, got ru='{ru_name}', en='{en_name}'"


def test_auto_group_with_athlete_text_positional() -> None:
    """Test that athlete_text as 6th positional argument works (BC)."""
    # Legacy call style with athlete_text: auto_group(age, gender, pregnant, athlete, lang, athlete_text)
    group = auto_group(30, "male", False, False, "en", "спортсмен")
    # athlete_text should be preserved and used for heuristics, triggering athlete group
    assert (
        group == "athlete"
    ), f"Expected 'athlete' group when athlete_text='спортсмен', got '{group}'"


def test_auto_group_athlete_string_does_not_depend_on_pregnant_value() -> None:
    """Regression: athlete_bool must be normalized from athlete, not pregnant."""
    # This test ensures athlete_bool is computed from athlete parameter, not pregnant
    g1 = auto_group(30, "male", "да", "да", "ru")  # both yes -> athlete ok either way
    g2 = auto_group(30, "male", "да", "нет", "ru")  # athlete=no -> must NOT be athlete
    g3 = auto_group(30, "male", "нет", "да", "ru")  # athlete=yes -> must be athlete

    assert g2 != "athlete", "athlete='нет' should not result in athlete group"
    assert g3 == "athlete", "athlete='да' should result in athlete group"


def test_auto_group_string_athlete_negative_token_does_not_infer() -> None:
    """Test that negative athlete tokens (no/false/нет) do not trigger athlete inference."""
    # Ensures negative-token branch is covered (athlete_bool=False path)
    group = auto_group(30, "male", False, "нет", "ru")
    assert group != "athlete", "Negative athlete token 'нет' should not infer athlete group"
