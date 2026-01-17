# -*- coding: utf-8 -*-
"""
RU: Тесты для BMI схем (BMICalculateRequest/Response).
EN: Tests for BMI schemas (BMICalculateRequest/Response).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.bmi import (
    BMICalculateRequest,
    BMICalculateResponse,
    BMIMarkerSpec,
    BMIRangeSpec,
    BMIScaleV1Spec,
    NumericRangeSchema,
    WaistRiskResultSchema,
)


class TestBMICalculateRequest:
    """Tests for BMICalculateRequest schema validation."""

    def test_valid_request(self) -> None:
        """Test valid request with all required fields."""
        req = BMICalculateRequest(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            gender="male",
            lang="en",
        )
        assert req.weight_kg == 70.0
        assert req.height_cm == 175.0
        assert req.age == 30
        assert req.gender == "male"
        assert req.lang == "en"

    def test_default_values(self) -> None:
        """Test default values for optional fields."""
        req = BMICalculateRequest(weight_kg=70, height_cm=175, age=30)

        assert req.gender is None  # Changed: gender default is None (normalized in router/engine)
        assert req.pregnant is False  # Changed: pregnant default is False (normalized to bool)
        assert req.athlete is False  # Changed: athlete default is False (normalized to bool)
        assert req.waist_cm is None
        assert req.lang == "en"

    def test_negative_weight_raises_validation_error(self) -> None:
        """Test that negative weight raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BMICalculateRequest(weight_kg=-10, height_cm=175, age=30)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("weight_kg",) and err["type"] == "greater_than" for err in errors)

    def test_zero_height_raises_validation_error(self) -> None:
        """Test that zero height raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BMICalculateRequest(weight_kg=70, height_cm=0, age=30)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("height_cm",) and err["type"] == "greater_than" for err in errors)

    def test_age_below_minimum_raises_validation_error(self) -> None:
        """Test that age < 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BMICalculateRequest(weight_kg=70, height_cm=175, age=0)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("age",) and err["type"] == "greater_than_equal" for err in errors)

    def test_age_above_maximum_raises_validation_error(self) -> None:
        """Test that age > 120 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BMICalculateRequest(weight_kg=70, height_cm=175, age=121)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("age",) and err["type"] == "less_than_equal" for err in errors)

    def test_negative_waist_cm_raises_validation_error(self) -> None:
        """Test that negative waist_cm raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BMICalculateRequest(weight_kg=70, height_cm=175, age=30, waist_cm=-10)

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("waist_cm",) and err["type"] == "greater_than" for err in errors)

    def test_none_waist_cm_is_valid(self) -> None:
        """Test that waist_cm=None is valid (optional field)."""
        req = BMICalculateRequest(
            weight_kg=70,
            height_cm=175,
            age=30,
            waist_cm=None,
        )
        assert req.waist_cm is None

    @pytest.mark.parametrize("lang", ["ru", "en", "es"])
    def test_valid_languages(self, lang: str) -> None:
        """Test that valid languages (ru/en/es) are accepted."""
        req = BMICalculateRequest(weight_kg=70, height_cm=175, age=30, lang=lang)
        assert req.lang == lang

    def test_invalid_language_raises_validation_error(self) -> None:
        """Test that invalid language raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BMICalculateRequest(weight_kg=70, height_cm=175, age=30, lang="fr")

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("lang",) and err["type"] == "literal_error" for err in errors)

    def test_pregnant_string_and_bool(self) -> None:
        """Test that pregnant accepts both string and bool, normalized to bool."""
        req_str = BMICalculateRequest(weight_kg=70, height_cm=175, age=30, pregnant="yes")
        assert req_str.pregnant is True  # Normalized to bool

        req_bool = BMICalculateRequest(weight_kg=70, height_cm=175, age=30, pregnant=True)
        assert req_bool.pregnant is True

    def test_athlete_string_and_bool(self) -> None:
        """Test that athlete accepts both string and bool, normalized to bool."""
        req_str = BMICalculateRequest(weight_kg=70, height_cm=175, age=30, athlete="yes")
        assert req_str.athlete is True  # Normalized to bool

        req_bool = BMICalculateRequest(weight_kg=70, height_cm=175, age=30, athlete=True)
        assert req_bool.athlete is True

        req_no = BMICalculateRequest(weight_kg=70, height_cm=175, age=30, athlete="no")
        assert req_no.athlete is False


def test_schema_normalizes_gender_w_to_female() -> None:
    """
    Contract: schema and engine exact token sets MUST stay in sync.
    'w' must normalize to 'female' at schema layer.
    """
    req = BMICalculateRequest.model_validate(
        {
            "height_cm": 170,
            "weight_kg": 65,
            "age": 30,
            "gender": "w",
            "pregnant": True,
        }
    )
    # For female tokens pregnancy remains True (no coercion)
    assert req.gender == "female"
    assert req.pregnant is True


@pytest.mark.parametrize(
    "token, expected",
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("W", "female"),  # Case-insensitive
        ("woman", "female"),
        ("F", "female"),
        ("M", "male"),
        ("man", "male"),
        ("unknown_token", "unknown_token"),  # Passthrough for unknown
    ],
)
def test_schema_gender_token_normalization_edges(token: str | None, expected: str | None) -> None:
    """
    Covers edge branches in schema token normalization:
    - None/empty/whitespace handling
    - casefold/lower
    - passthrough for unknown tokens
    """
    req = BMICalculateRequest.model_validate(
        {
            "height_cm": 170,
            "weight_kg": 65,
            "age": 30,
            "gender": token,
            "pregnant": False,
        }
    )
    assert req.gender == expected


@pytest.mark.parametrize("pregnant_value", ["yes", "да", "true", "1"])
def test_schema_pregnant_string_yes_normalizes_to_bool_true(pregnant_value: str) -> None:
    """Test that various truthy string values normalize to bool True."""
    req = BMICalculateRequest.model_validate(
        {
            "height_cm": 170,
            "weight_kg": 65,
            "age": 30,
            "gender": "female",
            "pregnant": pregnant_value,
        }
    )
    assert req.pregnant is True


@pytest.mark.parametrize("pregnant_value", ["no", "нет", "false", "0", "unknown"])
def test_schema_pregnant_non_yes_normalizes_to_bool_false(pregnant_value: str) -> None:
    """Test that falsy or unknown string values normalize to bool False."""
    req = BMICalculateRequest.model_validate(
        {
            "height_cm": 170,
            "weight_kg": 65,
            "age": 30,
            "gender": "female",
            "pregnant": pregnant_value,
        }
    )
    assert req.pregnant is False


def test_numeric_range_schema_rejects_inverted_range() -> None:
    """Test that NumericRangeSchema validates min <= max."""
    # Valid range
    valid_range = NumericRangeSchema.model_validate({"min": 18.5, "max": 25.0})
    assert valid_range.min == 18.5
    assert valid_range.max == 25.0

    # Equal values are allowed (both boundaries inclusive)
    equal_range = NumericRangeSchema.model_validate({"min": 25.0, "max": 25.0})
    assert equal_range.min == 25.0
    assert equal_range.max == 25.0

    # Inverted range should raise ValidationError
    with pytest.raises(ValidationError) as exc_info:
        NumericRangeSchema.model_validate({"min": 10, "max": 5})
    assert "must be less than or equal to maximum" in str(exc_info.value)


class TestBMICalculateResponse:
    """Tests for BMICalculateResponse schema structure."""

    def test_minimal_response(self) -> None:
        """Test minimal response structure (no waist)."""
        response = BMICalculateResponse(
            bmi=22.5,
            category="normal",
            group="general",
            group_display="General",
            interpretation="Your BMI is within the normal range.",
            wht_ratio=None,
            waist_risk=None,
            notes=[],
            age_band="adult",
        )

        assert response.bmi == 22.5
        assert response.category == "normal"
        assert response.group == "general"
        assert response.group_display == "General"
        assert response.interpretation == "Your BMI is within the normal range."
        assert response.wht_ratio is None
        assert response.waist_risk is None
        assert response.notes == []
        assert response.age_band == "adult"
        # Guard: optional fields must default to None (Pydantic v2 default=None)
        assert response.visualization is None
        assert response.interpretation_v1 is None

    def test_bmi_calculate_response_has_soft_paywall_field(self) -> None:
        """Test that BMICalculateResponse has optional soft_paywall field."""
        from app.schemas.bmi import BMICalculateResponse

        fields = BMICalculateResponse.model_fields
        assert "soft_paywall" in fields
        assert fields["soft_paywall"].is_required() is False

    def test_full_response_with_waist_risk(self) -> None:
        """Test full response structure with waist risk."""
        waist_risk_schema = WaistRiskResultSchema(
            wht_ratio=0.52,
            risk_level="moderate",
            notes=("Increased waist-related risk",),
        )
        response = BMICalculateResponse(
            bmi=25.3,
            category="overweight",
            group="general",
            group_display="General",
            interpretation="Your BMI indicates overweight.",
            wht_ratio=0.52,
            waist_risk=waist_risk_schema,
            notes=["Increased waist-related risk"],
            age_band="adult",
        )

        assert response.bmi == 25.3
        assert response.category == "overweight"
        assert response.wht_ratio == 0.52
        assert response.waist_risk is not None
        assert isinstance(response.waist_risk, WaistRiskResultSchema)
        assert response.waist_risk.risk_level == "moderate"
        assert len(response.notes) == 1
        assert "waist" in response.notes[0].lower()

    def test_category_none_for_pregnant(self) -> None:
        """Test that category=None is valid for pregnant (medical disclaimer)."""
        response = BMICalculateResponse(
            bmi=24.5,
            category=None,  # Valid for pregnant
            group="pregnant",
            group_display="Pregnant",
            interpretation="BMI is not valid during pregnancy.",
            wht_ratio=None,
            waist_risk=None,
            notes=[],
            age_band="adult",
        )

        assert response.category is None
        assert response.group == "pregnant"

    def test_category_none_for_too_young(self) -> None:
        """Test that category=None is valid for too_young (medical disclaimer)."""
        response = BMICalculateResponse(
            bmi=18.5,
            category=None,  # Valid for <12 years
            group="too_young",
            group_display="Child",
            interpretation="BMI interpretation is not available for children under 12.",
            wht_ratio=None,
            waist_risk=None,
            notes=[],
            age_band="too_young",
        )

        assert response.category is None
        assert response.group == "too_young"
        assert response.age_band == "too_young"

    def test_category_none_for_child(self) -> None:
        """Test that category=None is valid for child (12-14 years)."""
        response = BMICalculateResponse(
            bmi=19.0,
            category=None,  # Valid for child
            group="child",
            group_display="Child",
            interpretation="BMI is interpreted using pediatric references.",
            wht_ratio=None,
            waist_risk=None,
            notes=[],
            age_band="child",
        )

        assert response.category is None
        assert response.group == "child"
        assert response.age_band == "child"

    def test_category_none_for_teen(self) -> None:
        """Test that category=None is valid for teen (15-18 years)."""
        response = BMICalculateResponse(
            bmi=20.0,
            category=None,  # Valid for teen
            group="teen",
            group_display="Teenager",
            interpretation="BMI is interpreted using adolescent references.",
            wht_ratio=None,
            waist_risk=None,
            notes=[],
            age_band="teen",
        )

        assert response.category is None
        assert response.group == "teen"
        assert response.age_band == "teen"

    @pytest.mark.parametrize(
        "age_band",
        ["too_young", "child", "teen", "adult", "elderly"],
    )
    def test_all_age_bands(self, age_band: str) -> None:
        """Test that all age_band values are valid."""
        response = BMICalculateResponse(
            bmi=22.0,
            category="normal" if age_band == "adult" else None,
            group="general" if age_band == "adult" else age_band,
            group_display="Test",
            interpretation="Test interpretation.",
            wht_ratio=None,
            waist_risk=None,
            notes=[],
            age_band=age_band,
        )

        assert response.age_band == age_band

    def test_invalid_age_band_raises_validation_error(self) -> None:
        """Test that an invalid age_band value is rejected."""
        with pytest.raises(ValidationError):
            BMICalculateResponse(
                bmi=22.0,
                category="normal",
                group="general",
                group_display="General",
                interpretation="Test.",
                wht_ratio=None,
                waist_risk=None,
                notes=[],
                age_band="middle_age",  # Invalid value
            )

    def test_notes_default_factory(self) -> None:
        """Test that notes uses a per-instance default list."""
        response1 = BMICalculateResponse(
            bmi=22.0,
            category="normal",
            group="general",
            group_display="General",
            interpretation="Test.",
            wht_ratio=None,
            waist_risk=None,
            age_band="adult",
        )
        response2 = BMICalculateResponse(
            bmi=23.0,
            category="normal",
            group="general",
            group_display="General",
            interpretation="Another test.",
            wht_ratio=None,
            waist_risk=None,
            age_band="adult",
        )

        # Initial defaults are independent empty lists
        assert response1.notes == []
        assert response2.notes == []

        # Mutating one instance's notes must not affect the other
        response1.notes.append("some note")

        assert response1.notes == ["some note"]
        assert response2.notes == []


# --- Additional tests for diff-coverage on app/schemas/bmi.py ---


def test_waist_cm_optional_with_gt_constraint() -> None:
    """
    waist_cm is optional (default=None), but gt=0 must apply
    only when a value is provided (Pydantic v2 requirement).
    """
    # None is allowed (default)
    req = BMICalculateRequest.model_validate({"height_cm": 170, "weight_kg": 65, "age": 25})
    assert req.waist_cm is None

    # Positive value is allowed
    req = BMICalculateRequest.model_validate(
        {"height_cm": 170, "weight_kg": 65, "age": 25, "waist_cm": 80}
    )
    assert req.waist_cm == 80

    # Zero should fail (gt=0)
    with pytest.raises(ValidationError):
        BMICalculateRequest.model_validate(
            {"height_cm": 170, "weight_kg": 65, "age": 25, "waist_cm": 0}
        )

    # Negative should fail (gt=0)
    with pytest.raises(ValidationError):
        BMICalculateRequest.model_validate(
            {"height_cm": 170, "weight_kg": 65, "age": 25, "waist_cm": -10}
        )


def test_bmi_range_spec_rejects_invalid_range() -> None:
    """BMIRangeSpec requires from < to."""
    # Valid range
    valid = BMIRangeSpec.model_validate({"key": "bmi.normal", "from": 18.5, "to": 25.0})
    assert valid.from_ == 18.5
    assert valid.to == 25.0

    # Inverted range should fail
    with pytest.raises(ValidationError) as exc_info:
        BMIRangeSpec.model_validate({"key": "bmi.normal", "from": 25.0, "to": 18.5})
    assert "must be less than end" in str(exc_info.value)

    # Equal values should fail (from >= to)
    with pytest.raises(ValidationError):
        BMIRangeSpec.model_validate({"key": "bmi.normal", "from": 20.0, "to": 20.0})


def test_bmi_scale_v1_spec_validates_marker_mismatch() -> None:
    """BMIScaleV1Spec requires marker.value == bmi."""
    with pytest.raises(ValidationError) as exc_info:
        BMIScaleV1Spec.model_validate(
            {
                "kind": "bmi_scale_v1",
                "bmi": 23.0,
                "min": 0.0,
                "max": 60.0,
                "ranges": [{"key": "bmi.normal", "from": 18.5, "to": 25.0}],
                "marker": {"value": 24.0},  # Mismatch with bmi
            }
        )
    assert "Marker value" in str(exc_info.value) and "must equal BMI" in str(exc_info.value)


def test_bmi_scale_v1_spec_validates_bmi_out_of_bounds() -> None:
    """BMIScaleV1Spec requires bmi within [min, max]."""
    with pytest.raises(ValidationError) as exc_info:
        BMIScaleV1Spec.model_validate(
            {
                "kind": "bmi_scale_v1",
                "bmi": 61.0,  # Out of bounds (max=60)
                "min": 0.0,
                "max": 60.0,
                "ranges": [{"key": "bmi.normal", "from": 18.5, "to": 25.0}],
                "marker": {"value": 61.0},
            }
        )
    assert "must be between min" in str(exc_info.value)


def test_bmi_scale_v1_spec_validates_min_max_order() -> None:
    """BMIScaleV1Spec requires min < max."""
    with pytest.raises(ValidationError) as exc_info:
        BMIScaleV1Spec.model_validate(
            {
                "kind": "bmi_scale_v1",
                "bmi": 23.0,
                "min": 60.0,
                "max": 0.0,  # Inverted
                "ranges": [{"key": "bmi.normal", "from": 18.5, "to": 25.0}],
                "marker": {"value": 23.0},
            }
        )
    assert "must be less than maximum" in str(exc_info.value)


def test_bmi_scale_v1_spec_valid() -> None:
    """BMIScaleV1Spec accepts valid scale."""
    scale = BMIScaleV1Spec.model_validate(
        {
            "kind": "bmi_scale_v1",
            "bmi": 23.0,
            "min": 0.0,
            "max": 60.0,
            "ranges": [{"key": "bmi.normal", "from": 18.5, "to": 25.0}],
            "marker": {"value": 23.0},
        }
    )
    assert scale.bmi == 23.0
    assert scale.marker.value == 23.0
    assert len(scale.ranges) == 1


def test_schema_unknown_gender_token_is_preserved_lowercased() -> None:
    """Unknown gender tokens pass through lowercased and stripped."""
    req = BMICalculateRequest.model_validate(
        {"weight_kg": 65, "height_cm": 170, "age": 25, "gender": "  XxX  "}
    )
    assert req.gender == "xxx"


def test_bmi_marker_spec_valid() -> None:
    """BMIMarkerSpec accepts valid marker value."""
    marker = BMIMarkerSpec.model_validate({"value": 23.4})
    assert marker.value == 23.4


# --- Coverage-tail tests for _normalize_pregnant edge cases (diff-cover lines 267, 270) ---


def test_pregnant_none_normalizes_to_false() -> None:
    """
    Edge case: pregnant=None → False.
    Covers line 267 in _normalize_pregnant validator.
    """
    req = BMICalculateRequest.model_validate(
        {
            "weight_kg": 65,
            "height_cm": 170,
            "age": 30,
            "gender": "female",
            "pregnant": None,
        }
    )
    assert req.pregnant is False


def test_pregnant_whitespace_only_normalizes_to_false() -> None:
    """
    Edge case: pregnant="   " (whitespace only) → False after strip.
    Covers line 270 in _normalize_pregnant validator.
    """
    req = BMICalculateRequest.model_validate(
        {
            "weight_kg": 65,
            "height_cm": 170,
            "age": 30,
            "gender": "female",
            "pregnant": "   ",
        }
    )
    assert req.pregnant is False


def test_athlete_none_normalizes_to_false() -> None:
    """
    Edge case: athlete=None → False.
    Mirrors pregnant normalization behavior.
    """
    req = BMICalculateRequest.model_validate(
        {
            "weight_kg": 65,
            "height_cm": 170,
            "age": 30,
            "athlete": None,
        }
    )
    assert req.athlete is False


def test_athlete_whitespace_only_normalizes_to_false() -> None:
    """
    Edge case: athlete="   " (whitespace only) → False after strip.
    Mirrors pregnant normalization behavior.
    """
    req = BMICalculateRequest.model_validate(
        {
            "weight_kg": 65,
            "height_cm": 170,
            "age": 30,
            "athlete": "   ",
        }
    )
    assert req.athlete is False


def test_athlete_unknown_token_normalizes_to_false() -> None:
    """
    Edge case: athlete="maybe" (unknown token) → False.
    Mirrors pregnant normalization behavior.
    """
    req = BMICalculateRequest.model_validate(
        {
            "weight_kg": 65,
            "height_cm": 170,
            "age": 30,
            "athlete": "maybe",
        }
    )
    assert req.athlete is False
