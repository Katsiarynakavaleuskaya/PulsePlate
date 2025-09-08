# -*- coding: utf-8 -*-
import pytest

from core.i18n import t, validate_translation_key


def test_i18n_invalid_language_keyerror():
    with pytest.raises(KeyError):
        t("de", "bmi_normal")


def test_i18n_missing_key_keyerror():
    with pytest.raises(KeyError):
        t("en", "nonexistent_key")


def test_i18n_validate_translation_key():
    assert validate_translation_key("bmi_normal") is True
    assert validate_translation_key("__definitely_missing__") is False
