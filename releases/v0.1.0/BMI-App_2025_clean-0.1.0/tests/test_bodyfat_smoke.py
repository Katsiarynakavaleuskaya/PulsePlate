from bodyfat import bf_deurenberg, bf_us_navy, bf_ymca, estimate_all


def assert_soft(x):
    assert 0 < float(x) < 100


def test_deurenberg_soft():
    assert_soft(bf_deurenberg(bmi=22.5, age=28, gender="female"))


def test_us_navy_soft_male():
    assert_soft(bf_us_navy(height_cm=170, neck_cm=34, waist_cm=82, gender="male"))


def test_us_navy_soft_female():
    assert_soft(bf_us_navy(height_cm=170, neck_cm=34, waist_cm=74, hip_cm=94, gender="female"))


def test_ymca_soft_male():
    assert_soft(bf_ymca(weight_kg=70, waist_cm=82, gender="male"))


def test_aggregate_soft():
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
    for v in res["methods"].values():
        assert_soft(v)
    if res.get("median") is not None:
        assert_soft(res["median"])
