# -*- coding: utf-8 -*-
"""
Tests for BMI visualization spec builder and endpoint integration.
"""

import pytest

from app.services.bmi_visualization import build_bmi_scale_v1


def test_build_bmi_scale_v1_structure():
    """Test that spec has correct structure."""
    spec = build_bmi_scale_v1(23.4)

    assert spec.kind == "bmi_scale_v1"
    assert spec.bmi == 23.4
    assert spec.min == 0.0
    assert spec.max == 60.0
    assert len(spec.ranges) == 4
    assert spec.marker.value == 23.4


def test_ranges_monotonic_no_gaps():
    """Test that ranges are monotonic with no gaps."""
    spec = build_bmi_scale_v1(25.0)

    # Check each range: from_ < to
    for range_spec in spec.ranges:
        assert range_spec.from_ < range_spec.to, f"Range {range_spec.key}: from_ >= to"

    # Check sequence: end of previous == start of next
    for i in range(len(spec.ranges) - 1):
        assert spec.ranges[i].to == spec.ranges[i + 1].from_, f"Gap between range {i} and {i + 1}"

    # Check boundaries
    assert spec.ranges[0].from_ == spec.min, "First range should start at min"
    assert spec.ranges[-1].to == spec.max, "Last range should end at max"


def test_marker_equals_bmi():
    """Test that marker value equals rounded BMI."""
    test_cases = [18.5, 22.3, 25.0, 30.0, 35.7]

    for bmi in test_cases:
        spec = build_bmi_scale_v1(bmi)
        assert spec.marker.value == round(
            bmi, 1
        ), f"Marker value {spec.marker.value} != rounded BMI {round(bmi, 1)}"
        assert spec.bmi == round(bmi, 1), f"Spec BMI {spec.bmi} != rounded BMI {round(bmi, 1)}"


def test_build_bmi_scale_v1_edge_cases():
    """Test builder handles edge cases safely."""
    # Normal cases
    spec1 = build_bmi_scale_v1(0.0)
    assert spec1.bmi == 0.0
    assert spec1.marker.value == 0.0

    spec2 = build_bmi_scale_v1(60.0)
    assert spec2.bmi == 60.0
    assert spec2.marker.value == 60.0

    # Very small BMI
    spec3 = build_bmi_scale_v1(10.12345)
    assert spec3.bmi == 10.1  # rounded to 1 decimal
    assert spec3.marker.value == 10.1


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
