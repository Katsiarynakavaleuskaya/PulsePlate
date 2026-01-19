# -*- coding: utf-8 -*-
"""
Tests for BMI visualization spec builder and endpoint integration.
"""

import pytest

from app.services.bmi_visualization import build_bmi_scale_v1


def test_build_bmi_scale_v1_structure():
    """Test that spec has correct structure."""
    from core.bmi.engine import calculate_bmi_result

    result = calculate_bmi_result(
        weight_kg=70.0,
        height_cm=175.0,
        age=30,
        gender="male",
        pregnant=False,
        athlete=False,
        waist_cm=None,
        hip_cm=None,
        lang="en",
    )
    spec = build_bmi_scale_v1(result)

    assert spec is not None
    assert spec.kind == "bmi_scale_v1"
    assert spec.bmi == round(result.bmi, 1)
    assert spec.min == 0.0
    assert spec.max == 60.0
    assert len(spec.ranges) == 4
    assert spec.marker.value == round(result.bmi, 1)


def test_ranges_monotonic_no_gaps():
    """Test that ranges are monotonic with no gaps."""
    from core.bmi.engine import calculate_bmi_result

    result = calculate_bmi_result(
        weight_kg=70.0,
        height_cm=175.0,
        age=30,
        gender="male",
        pregnant=False,
        athlete=False,
        waist_cm=None,
        hip_cm=None,
        lang="en",
    )
    spec = build_bmi_scale_v1(result)

    assert spec is not None
    # Check each range: from_ < to
    for range_spec in spec.ranges:
        assert range_spec.from_ < range_spec.to, f"Range {range_spec.key}: from_ >= to"

    # Check sequence: end of previous == start of next
    for i in range(len(spec.ranges) - 1):
        assert spec.ranges[i].to == pytest.approx(
            spec.ranges[i + 1].from_
        ), f"Gap between range {i} and {i + 1}"

    # Check boundaries
    assert spec.ranges[0].from_ == spec.min, "First range should start at min"
    assert spec.ranges[-1].to == spec.max, "Last range should end at max"


def test_marker_equals_bmi():
    """Test that marker value equals rounded BMI."""
    from core.bmi.engine import calculate_bmi_result

    test_cases = [
        (70.0, 175.0, 30),  # BMI ~22.9
        (80.0, 180.0, 25),  # BMI ~24.7
        (90.0, 170.0, 35),  # BMI ~31.1
    ]

    for weight, height, age in test_cases:
        result = calculate_bmi_result(
            weight_kg=weight,
            height_cm=height,
            age=age,
            gender="male",
            pregnant=False,
            athlete=False,
            waist_cm=None,
            hip_cm=None,
            lang="en",
        )
        spec = build_bmi_scale_v1(result)
        assert spec is not None
        rounded_bmi = round(result.bmi, 1)
        assert (
            spec.marker.value == rounded_bmi
        ), f"Marker value {spec.marker.value} != rounded BMI {rounded_bmi}"
        assert spec.bmi == rounded_bmi, f"Spec BMI {spec.bmi} != rounded BMI {rounded_bmi}"


def test_build_bmi_scale_v1_edge_cases():
    """Test builder handles edge cases safely."""
    from core.bmi.engine import calculate_bmi_result

    # Very low BMI
    result1 = calculate_bmi_result(
        weight_kg=40.0,
        height_cm=180.0,
        age=30,
        gender="male",
        pregnant=False,
        athlete=False,
        waist_cm=None,
        hip_cm=None,
        lang="en",
    )
    spec1 = build_bmi_scale_v1(result1)
    assert spec1 is not None
    assert spec1.bmi == round(result1.bmi, 1)
    assert spec1.marker.value == round(result1.bmi, 1)

    # High BMI
    result2 = calculate_bmi_result(
        weight_kg=120.0,
        height_cm=170.0,
        age=30,
        gender="male",
        pregnant=False,
        athlete=False,
        waist_cm=None,
        hip_cm=None,
        lang="en",
    )
    spec2 = build_bmi_scale_v1(result2)
    assert spec2 is not None
    assert spec2.bmi == round(result2.bmi, 1)
    assert spec2.marker.value == round(result2.bmi, 1)


def test_bmi_calculate_returns_visualization():
    """Test that /api/v1/bmi/calculate returns visualization field."""
    # Use canonical import pattern from project
    from app import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    response = client.post(
        "/api/v1/bmi/calculate",
        json={
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": "male",  # BMICalculateRequest uses "gender", not "sex"
            "lang": "en",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert "visualization" in data, "Response should contain visualization field"
    assert data["visualization"] is not None, "Visualization should not be None"
    assert (
        data["visualization"]["kind"] == "bmi_scale_v1"
    ), "Visualization kind should be bmi_scale_v1"
    assert "ranges" in data["visualization"], "Visualization should contain ranges"
    assert "marker" in data["visualization"], "Visualization should contain marker"
    assert len(data["visualization"]["ranges"]) == 4, "Should have 4 ranges"

    # Verify alias "from" is used (not "from_")
    first_range = data["visualization"]["ranges"][0]
    assert "from" in first_range, "Range should use 'from' alias (not 'from_')"
    assert "from_" not in first_range, "Range should not contain 'from_' field"


def test_bmi_scale_v1_spec_validation():
    """Test that BMIScaleV1Spec validation works correctly."""
    from app.schemas.bmi import BMIScaleV1Spec, BMIRangeSpec, BMIMarkerSpec
    from pydantic import ValidationError

    # Valid spec
    # Note: ranges completeness (full 0-60 coverage) not validated in v1
    valid_spec = BMIScaleV1Spec(
        kind="bmi_scale_v1",
        bmi=23.4,
        min=0.0,
        max=60.0,
        ranges=[
            BMIRangeSpec.model_validate({"key": "bmi.normal", "from": 18.5, "to": 25.0}),
        ],
        marker=BMIMarkerSpec(value=23.4),
    )
    assert valid_spec.bmi == 23.4
    assert valid_spec.marker.value == 23.4

    # Invalid: min >= max
    with pytest.raises(ValidationError, match="must be less than maximum"):
        BMIScaleV1Spec(
            kind="bmi_scale_v1",
            bmi=23.4,
            min=60.0,
            max=0.0,
            ranges=[
                BMIRangeSpec.model_validate({"key": "bmi.normal", "from": 18.5, "to": 25.0}),
            ],
            marker=BMIMarkerSpec(value=23.4),
        )

    # Invalid: bmi outside bounds
    with pytest.raises(ValidationError, match="must be between min"):
        BMIScaleV1Spec(
            kind="bmi_scale_v1",
            bmi=70.0,  # > max
            min=0.0,
            max=60.0,
            ranges=[
                BMIRangeSpec.model_validate({"key": "bmi.normal", "from": 18.5, "to": 25.0}),
            ],
            marker=BMIMarkerSpec(value=70.0),
        )

    # Invalid: marker.value != bmi
    with pytest.raises(ValidationError, match="must equal BMI"):
        BMIScaleV1Spec(
            kind="bmi_scale_v1",
            bmi=23.4,
            min=0.0,
            max=60.0,
            ranges=[
                BMIRangeSpec.model_validate({"key": "bmi.normal", "from": 18.5, "to": 25.0}),
            ],
            marker=BMIMarkerSpec(value=25.0),  # != bmi
        )


def test_range_constructor_accepts_from_():
    """Test that BMIRangeSpec accepts from_= in direct constructor."""
    from app.schemas.bmi import BMIRangeSpec

    r = BMIRangeSpec(key="bmi.normal", from_=18.5, to=25.0)
    assert r.from_ == 18.5
    assert r.to == 25.0
    # Verify alias works in serialization
    dumped = r.model_dump(by_alias=True)
    assert dumped["from"] == 18.5
    assert "from_" not in dumped
    assert dumped["to"] == 25.0


def test_bmi_calculate_graceful_fallback_when_visualization_builder_fails(monkeypatch):
    """Test that endpoint gracefully handles visualization builder failure."""
    from app import app
    from fastapi.testclient import TestClient
    import app.routers.bmi as bmi_router

    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(bmi_router, "build_bmi_scale_v1", _boom)

    client = TestClient(app)
    resp = client.post(
        "/api/v1/bmi/calculate",
        json={"weight_kg": 70.0, "height_cm": 175.0, "age": 30, "gender": "male", "lang": "en"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "visualization" in data
    assert data["visualization"] is None
    # Verify other fields are still present
    assert "bmi" in data
    assert data["bmi"] > 0


def test_visualization_adult_ranges_match_core():
    """Test that adult visualization ranges match core thresholds."""
    from core.bmi.engine import calculate_bmi_result, get_bmi_visual_ranges

    result = calculate_bmi_result(
        weight_kg=70.0,
        height_cm=175.0,
        age=30,  # adult
        gender="male",
        pregnant=False,
        athlete=False,
        waist_cm=None,
        hip_cm=None,
        lang="en",
    )

    spec = build_bmi_scale_v1(result)
    assert spec is not None

    # Verify ranges match core thresholds (parity-by-design)
    core_ranges = get_bmi_visual_ranges(result.group, result.age_band)
    assert core_ranges is not None

    assert len(spec.ranges) == 4
    assert len(core_ranges) == 4

    # Compare each range with core (using approx for float safety)
    for spec_range, (core_start, core_end, core_key) in zip(spec.ranges, core_ranges):
        assert spec_range.from_ == pytest.approx(core_start)
        assert spec_range.to == pytest.approx(core_end)
        assert spec_range.key == core_key


def test_visualization_athlete_ranges_match_core():
    """Test that athlete visualization ranges match core thresholds."""
    from core.bmi.engine import calculate_bmi_result, get_bmi_visual_ranges

    result = calculate_bmi_result(
        weight_kg=80.0,
        height_cm=180.0,
        age=25,  # adult
        gender="male",
        pregnant=False,
        athlete=True,  # athlete group
        waist_cm=None,
        hip_cm=None,
        lang="en",
    )

    spec = build_bmi_scale_v1(result)
    assert spec is not None

    # Verify key difference: athlete normal_max is 27.0 (not 25.0)
    core_ranges = get_bmi_visual_ranges(result.group, result.age_band)
    assert core_ranges is not None

    # Check normal range end (index 1)
    assert spec.ranges[1].to == pytest.approx(core_ranges[1][1])  # 27.0
    assert spec.ranges[1].to == pytest.approx(27.0)  # Explicit check for documentation


def test_visualization_elderly_ranges_match_core():
    """Test that elderly visualization ranges match core thresholds."""
    from core.bmi.engine import calculate_bmi_result, get_bmi_visual_ranges

    result = calculate_bmi_result(
        weight_kg=65.0,
        height_cm=165.0,
        age=70,  # elderly age_band
        gender="female",
        pregnant=False,
        athlete=False,
        waist_cm=None,
        hip_cm=None,
        lang="en",
    )

    spec = build_bmi_scale_v1(result)
    assert spec is not None

    # Verify elderly-specific thresholds via core parity
    core_ranges = get_bmi_visual_ranges(result.group, result.age_band)
    assert core_ranges is not None

    # Check underweight and normal ranges (elderly: 17.5, 26.0)
    assert spec.ranges[0].to == pytest.approx(core_ranges[0][1])  # 17.5
    assert spec.ranges[1].to == pytest.approx(core_ranges[1][1])  # 26.0

    # Explicit checks for documentation
    assert spec.ranges[0].to == pytest.approx(17.5)
    assert spec.ranges[1].to == pytest.approx(26.0)


@pytest.mark.parametrize(
    "group_input",
    [
        ("too_young", 10, "male"),
        ("child", 12, "male"),  # age 12 maps to "child" age_band, not 13
        ("teen", 16, "male"),
        ("pregnant", 25, "female"),
    ],
)
def test_visualization_none_for_category_none_groups(group_input):
    """Test that visualization is None for groups where category=None."""
    group_name, age, gender = group_input
    from core.bmi.engine import calculate_bmi_result

    result = calculate_bmi_result(
        weight_kg=50.0,
        height_cm=150.0,
        age=age,
        gender=gender,
        pregnant=(group_name == "pregnant"),
        athlete=False,
        waist_cm=None,
        hip_cm=None,
        lang="en",
    )

    # Verify category is None (for documentation)
    assert result.category is None

    # Verify visualization is None (checked by group, not category)
    spec = build_bmi_scale_v1(result)
    assert spec is None


# --- Coverage tail guards: defensive fallback branches ---
