import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parent.parent))

from bodyfat import bf_deurenberg, bf_us_navy, bf_ymca, estimate_all


def assert_percent(x):
    assert isinstance(x, (int, float))
    assert math.isfinite(x)
    assert 0 < x < 100


# --- smoke на отдельные формулы ---


def test_deurenberg_smoke():
    val = bf_deurenberg(bmi=22.5, age=28, gender="female")
    assert_percent(val)


def test_us_navy_male_smoke():
    val = bf_us_navy(height_cm=170, neck_cm=34, waist_cm=82, gender="male")
    assert_percent(val)


def test_us_navy_female_smoke():
    val = bf_us_navy(height_cm=170, neck_cm=34, waist_cm=74, hip_cm=94, gender="female")
    assert_percent(val)


def test_us_navy_female_missing_hip():
    with pytest.raises(ValueError, match="hip_cm required for female"):
        bf_us_navy(height_cm=170, neck_cm=34, waist_cm=74, gender="female")


def test_ymca_male_smoke():
    val = bf_ymca(weight_kg=70, waist_cm=82, gender="male")
    assert_percent(val)


def test_ymca_female_smoke():
    val = bf_ymca(weight_kg=65, waist_cm=74, gender="female")
    assert_percent(val)


# --- интеграционный smoke ---


def test_estimate_all_smoke():
    data = {
        "height_cm": 170,
        "neck_cm": 34,
        "waist_cm": 74,
        "hip_cm": 94,
        "weight_kg": 65,
        "age": 28,
        "gender": "female",
        "bmi": 22.5,
    }
    res = estimate_all(data)
    assert "methods" in res and isinstance(res["methods"], dict)
    # если хотя бы одна методика дала число — ок
    vals = list(res["methods"].values())
    assert any(isinstance(v, (int, float)) and 0 < v < 100 for v in vals)
    # если есть медиана — тоже должна быть корректным процентом
    if res.get("median") is not None:
        assert_percent(res["median"])


def test_estimate_all_female_no_hip():
    data = {
        "height_cm": 170,
        "neck_cm": 34,
        "waist_cm": 74,
        "weight_kg": 65,
        "age": 28,
        "gender": "female",
        "bmi": 22.5,
    }
    res = estimate_all(data)
    assert "methods" in res
    # us_navy should not be in methods because hip_cm missing
    assert "us_navy" not in res["methods"]
    # but deurenberg and ymca should be
    assert "deurenberg" in res["methods"]
    assert "ymca" in res["methods"]


# --- TODO: строгие диапазоны ---
# Перенести в отдельный файл и включать в CI позже:
#  - Deurenberg: сверить с первоисточником (Deurenberg et al., 1991)
#  - US Navy: официальная формула DoD
#  - YMCA: исторические коэффициенты; сверить единицы (lb/in vs kg/cm)
