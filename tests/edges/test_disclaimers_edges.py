import pytest

from core import disclaimers as d


def test_get_disclaimer_text_medical_and_privacy_en():
    text = d.get_disclaimer_text("medical", language="en")
    assert "IMPORTANT MEDICAL DISCLAIMER" in text
    text2 = d.get_disclaimer_text("privacy", language="en")
    assert "PRIVACY NOTICE" in text2


def test_get_disclaimer_text_invalid_type_raises_keyerror():
    with pytest.raises(KeyError):
        d.get_disclaimer_text("unknown", language="en")


def test_get_comprehensive_disclaimer_with_special_populations_ru():
    combined = d.get_comprehensive_disclaimer(["pregnancy", "elderly"], language="ru")
    # Contains headers and special sections
    assert "БЕРЕМЕННОСТИ" in combined or "беременности" in combined
    assert "ПОЖИЛЫХ" in combined or "пожилых" in combined
