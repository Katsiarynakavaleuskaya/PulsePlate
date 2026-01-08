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
        assert req.athlete == "no"  # athlete still accepts string
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
        """Test that athlete accepts both string and bool (not normalized in schema, normalized in router)."""
        # Note: athlete normalization happens in router, not schema
        req_str = BMICalculateRequest(weight_kg=70, height_cm=175, age=30, athlete="yes")
        assert req_str.athlete == "yes"  # Schema keeps original value

        req_bool = BMICalculateRequest(weight_kg=70, height_cm=175, age=30, athlete=True)
        assert req_bool.athlete is True


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
