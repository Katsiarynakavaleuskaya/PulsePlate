import math
from pathlib import Path
import sys
from typing import Any, Dict, cast

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
    methods: dict[str, Any] = cast(dict[str, Any], res["methods"])  # typing help for pyright
    vals = list(methods.values())
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
    methods: dict[str, Any] = cast(dict[str, Any], res["methods"])  # ensure Mapping[str, Any]
    # us_navy should not be in methods because hip_cm missing
    assert "us_navy" not in methods
    # but deurenberg and ymca should be
    assert "deurenberg" in methods
    assert "ymca" in methods


# --- error handling branches ---


def test_estimate_all_skips_non_numeric_bmi_inputs():
    """Ensure invalid BMI data is ignored instead of crashing calculations."""
    data = {"bmi": "oops", "age": "thirty", "gender": "male"}
    res = estimate_all(data)
    assert res["methods"] == {}
    assert res["median"] is None


def test_estimate_all_skips_bad_dimension_inputs():
    """Invalid anthropometric numbers should be skipped gracefully."""
    data = {"height_cm": "bad", "neck_cm": 34, "waist_cm": 74, "gender": "male"}
    res = estimate_all(data)
    assert res["methods"] == {}
    assert res["median"] is None


def test_estimate_all_skips_invalid_weight_data():
    """Invalid weight inputs should trigger the final guard clause."""
    data = {"weight_kg": object(), "waist_cm": 82, "gender": "female"}
    res = estimate_all(data)
    assert res["methods"] == {}
    assert res["median"] is None


# --- TODO: строгие диапазоны ---
# Перенести в отдельный файл и включать в CI позже:
#  - Deurenberg: сверить с первоисточником (Deurenberg et al., 1991)
#  - US Navy: официальная формула DoD
#  - YMCA: исторические коэффициенты; сверить единицы (lb/in vs kg/cm)
