#!/usr/bin/env python3
"""Unit tests for core.bayesian_recommendations."""

from enum import Enum

import pytest

from core import bayesian_recommendations as br


class DummyError(Enum):
    """Minimal enum to exercise get_error_type_key."""

    ASSERTION_ERROR = "assertion_error"


def test_get_recommendations_known_key_and_fallback_language() -> None:
    """Known key with unknown language should fall back to DEFAULT_LANGUAGE."""
    default_lang = br.DEFAULT_LANGUAGE
    expected = br.RECOMMENDATIONS[default_lang]["error_type.assertion_error"]

    recs = br.get_recommendations("error_type.assertion_error", language="xx")

    assert recs == expected
    assert isinstance(recs, list)


def test_get_recommendations_missing_key_returns_fallback() -> None:
    """Unknown recommendation key should return provided fallback list."""
    fallback = ["Default recommendation"]
    recs = br.get_recommendations("nonexistent.key", language="ru", fallback=fallback)
    assert recs == fallback


def test_get_recommendations_uses_default_language_when_none() -> None:
    """None language should default to DEFAULT_LANGUAGE."""
    expected = br.RECOMMENDATIONS[br.DEFAULT_LANGUAGE]["error_type.assertion_error"]
    recs = br.get_recommendations("error_type.assertion_error", language=None)
    assert recs == expected


def test_get_recommendations_fallbacks_to_default_language(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    If the requested language lacks a key, recommendations should fall back to the default language.
    """
    default_lang = br.DEFAULT_LANGUAGE
    # Check if there's another language available
    other_langs = [lang for lang in br.RECOMMENDATIONS if lang != default_lang]
    if not other_langs:
        pytest.skip("Only default language available, cannot test fallback")

    other_lang = other_langs[0]
    missing_key = "error_type.attribute_error"

    # Remove the key from the other language to force default-language fallback
    other_lang_copy = dict(br.RECOMMENDATIONS[other_lang])
    other_lang_copy.pop(missing_key, None)
    monkeypatch.setitem(br.RECOMMENDATIONS, other_lang, other_lang_copy)

    recs = br.get_recommendations(missing_key, language=other_lang)
    assert recs == br.RECOMMENDATIONS[default_lang][missing_key]


def test_get_error_and_symptom_keys() -> None:
    """Ensure key helpers prefix values correctly."""
    assert br.get_error_type_key(DummyError.ASSERTION_ERROR) == "error_type.assertion_error"
    assert br.get_symptom_key("async_context") == "symptom.async_context"


def test_get_all_keys_nonempty_and_prefixed() -> None:
    """All exported keys should be prefixed appropriately and non-empty."""
    error_keys = br.get_all_error_type_keys()
    symptom_keys = br.get_all_symptom_keys()

    assert error_keys and all(key.startswith("error_type.") for key in error_keys)
    assert symptom_keys and all(key.startswith("symptom.") for key in symptom_keys)

