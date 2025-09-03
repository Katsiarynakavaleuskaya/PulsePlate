import pytest

from core import bmi_extras_simple as bx


def test_wht_ratio_valid_and_invalid():
    assert bx.wht_ratio(80, 170) == 0.47
    assert bx.wht_ratio(90, 170) == 0.53
    with pytest.raises(ValueError):
        bx.wht_ratio(0, 170)
    with pytest.raises(ValueError):
        bx.wht_ratio(80, 0)


def test_whr_ratio_valid_and_invalid():
    assert bx.whr_ratio(80, 100) == 0.8
    assert bx.whr_ratio(90, 90) == 1.0
    with pytest.raises(ValueError):
        bx.whr_ratio(0, 100)
    with pytest.raises(ValueError):
        bx.whr_ratio(80, -1)


def test_ffmi_basic_and_bounds():
    # 80kg, 20% bf, 180cm -> FFM=64, FFMI=64/(1.8^2)=19.8 -> rounded 19.8
    assert bx.ffmi(80, 180, 20) == 19.8
    # Input validation
    with pytest.raises(ValueError):
        bx.ffmi(0, 170, 20)
    with pytest.raises(ValueError):
        bx.ffmi(70, 0, 20)
    with pytest.raises(ValueError):
        bx.ffmi(70, 170, -1)
    with pytest.raises(ValueError):
        bx.ffmi(70, 170, 100)


@pytest.mark.parametrize(
    "bmi,whtr,whr,sex,expected_risk,expected_note_contains",
    [
        # Low risk by WHtR
        (24.0, 0.45, None, "male", "low", []),
        # Moderate risk by WHtR between 0.5 and 0.6
        (24.0, 0.55, 0.8, "female", "moderate", ["WHtR ≥ 0.5"]),
        # High risk by WHtR >= 0.6
        (24.0, 0.62, 0.8, "male", "high", ["WHtR ≥ 0.6"]),
        # WHR pushes risk to high for male threshold 0.9
        (24.0, 0.55, 0.95, "male", "high", ["WHR ≥ 0.9"]),
        # BMI >= 35 sets high
        (36.0, 0.45, 0.8, "female", "high", ["BMI ≥ 35"]),
        # BMI 30–34.9 bumps from low to moderate
        (31.0, 0.45, 0.8, "female", "moderate", ["BMI 30–34.9"]),
        # Female WHR threshold 0.85
        (24.0, 0.55, 0.86, "female", "high", ["WHR ≥ 0.85"]),
    ],
)
def test_stage_obesity_scenarios(bmi, whtr, whr, sex, expected_risk, expected_note_contains):
    risk, notes = bx.stage_obesity(bmi=bmi, whtr=whtr, whr=whr, sex=sex)  # type: ignore[arg-type]
    assert risk == expected_risk
    for fragment in expected_note_contains:
        assert any(fragment in n for n in notes)

