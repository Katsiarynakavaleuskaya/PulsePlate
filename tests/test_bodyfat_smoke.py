from typing import Dict, Any
from typing import Dict, Any
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bodyfat import bf_deurenberg, bf_us_navy, bf_ymca, estimate_all
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bodyfat import bf_deurenberg, bf_us_navy, bf_ymca, estimate_all
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bodyfat import bf_deurenberg, bf_us_navy, bf_ymca, estimate_all
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bodyfat import bf_deurenberg, bf_us_navy, bf_ymca, estimate_all

def assert_between(x: float, lo: float, hi: float):
    assert lo < x < hi, f"value {x} not in ({lo}, {hi})"

def test_deurenberg_soft():
    v = bf_deurenberg(bmi=22.5, age=28, gender="female")
    assert_between(v, 0, 100)

def test_us_navy_soft_male():
    v = bf_us_navy(height_cm=170, neck_cm=34, waist_cm=82, gender="male")
    assert_between(v, 0, 100)

def test_us_navy_soft_female():
    v = bf_us_navy(height_cm=170, neck_cm=34, waist_cm=74, hip_cm=94, gender="female")
    assert_between(v, 0, 100)

def test_ymca_soft_male():
    v = bf_ymca(weight_kg=70, waist_cm=82, gender="male")
    assert_between(v, 0, 100)

def test_aggregate_soft():
    data: Dict[str, Any] = {"height_cm":170, "neck_cm":34, "waist_cm":74, "hip_cm":94,
                            "gender":"female", "weight_kg":65, "height_m":1.70, "age":28}
    res = estimate_all(data)
    assert isinstance(res, dict)
    assert "methods" in res and isinstance(res["methods"], dict)
    assert res.get("median") is None or (0 < res["median"] < 100)
