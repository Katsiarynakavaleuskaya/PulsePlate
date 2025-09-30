from typing import Any, Dict, cast
from bodyfat import bf_deurenberg, bf_us_navy, bf_ymca, estimate_all


def assert_soft(x: float) -> None:
    assert 0 < x < 100


def test_deurenberg_soft() -> None:
    assert_soft(bf_deurenberg(bmi=22.5, age=28, gender="female"))


def test_us_navy_soft_male() -> None:
    assert_soft(bf_us_navy(height_cm=170, neck_cm=34, waist_cm=82, gender="male"))


def test_us_navy_soft_female() -> None:
    assert_soft(bf_us_navy(height_cm=170, neck_cm=34, waist_cm=74, hip_cm=94, gender="female"))


def test_ymca_soft_male() -> None:
    assert_soft(bf_ymca(weight_kg=70, waist_cm=82, gender="male"))


def test_aggregate_soft() -> None:
    data = {
        "height_cm": 170,
        "neck_cm": 34,
        "waist_cm": 74,
        "hip_cm": 94,
        "gender": "female",
        "weight_kg": 65,
        "height_m": 1.70,
        "age": 28,
    }
    res = estimate_all(data)
    assert "methods" in res
    methods: Dict[str, Any] = cast(Dict[str, Any], res["methods"])  # typing aid for pyright
    for v in methods.values():
        assert_soft(v)
    if res.get("median") is not None:
        assert_soft(cast(float, res["median"]))
