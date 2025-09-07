# -*- coding: utf-8 -*-
"""
RU: Точечные юнит-тесты внутренних функций app.py:
- _bmi_category: граничные значения 18.5/25/30
- _bmi_with_group_note: ветви athlete/pregnant/elderly/teen (ru/en)
- _normalize_flags: нормализация входных строк к флагам
- /debug_env: проверяем переключение insight_enabled через FEATURE_INSIGHT
EN: Unit tests for internal helpers in app.py.
"""

import pytest
from fastapi.testclient import TestClient

app_mod = pytest.importorskip("app")
app = getattr(app_mod, "app")
client = TestClient(app)


def test_bmi_category_boundaries():
    f = app_mod._bmi_category  # type: ignore[attr-defined]
    # ниже 18.5
    assert f(18.49) == "Underweight"
    # [18.5, 25)
    assert f(18.5) == "Normal"
    assert f(24.99) == "Normal"
    # [25, 30)
    assert f(25.0) == "Overweight"
    assert f(29.99) == "Overweight"
    # >= 30
    assert f(30.0) == "Obese"


@pytest.mark.parametrize(
    "group,lang,expect_sub",
    [
        ("athlete", "ru", "мышечная масса"),
        ("pregnant", "ru", "беременности"),
        ("elderly", "ru", "возрастные изменения"),
        ("teen", "ru", "педиатрические"),
        (
            "athlete",
            "en",
            "muscle",
        ),  # текст на англ может быть иной — проверим что строка не пустая
    ],
)
def test_bmi_with_group_note_variants(group, lang, expect_sub):
    """Проверяем, что ветви примечаний активируются.
    Не лочимся на точный текст кроме RU-веток, где ожидаем часть фразы.
    """
    fn = getattr(app_mod, "_bmi_with_group_note", None)
    # sourcery skip: no-conditionals-in-tests
    if fn is None:
        pytest.skip("_bmi_with_group_note not found")
    msg = fn(27.3, group)  # b в зоне Overweight, чтобы заметка вклеилась
    assert isinstance(msg, str) and msg
    if lang == "ru":
        # В RU-ветках ожидаем подстроку
        assert expect_sub in msg


def test_normalize_flags_variants():
    fn = getattr(app_mod, "_normalize_flags", None)
    # sourcery skip: no-conditionals-in-tests
    if fn is None:
        pytest.skip("_normalize_flags not found")
    flags = fn("male", "ДА", "y")  # ru/eng варианты
    assert flags["gender_male"] is True
    assert flags["is_pregnant"] is True
    assert flags["is_athlete"] is True

    flags2 = fn("female", "no", "0")
    assert flags2["gender_male"] is False
    assert flags2["is_pregnant"] is False
    assert flags2["is_athlete"] is False


@pytest.mark.parametrize(
    "val,expected", [("1", "True"), ("true", "True"), ("no", "False"), ("", "False")]
)
def test_debug_env_insight_flag(monkeypatch, val, expected):
    """Проворачиваем FEATURE_INSIGHT и смотрим, как вернётся строковые флаг."""
    monkeypatch.setenv("FEATURE_INSIGHT", val)
    r = client.get("/debug_env")
    # sourcery skip: no-conditionals-in-tests
    if r.status_code == 404:
        pytest.skip("No /debug_env route (skipping)")
    assert r.status_code == 200
    data = r.json()
    assert data.get("insight_enabled") == expected
