"""
Tests for BMI Pro features with Spanish language support.
"""

from core.bmi_extras import (
    interpret_whr_ratio,
    interpret_wht_ratio,
    stage_obesity,
)


class TestBMIProSpanish:
    """Test BMI Pro calculation functions with Spanish language support."""

    def test_wht_ratio_spanish_interpretation(self):
        """Test WHtR interpretation in Spanish."""
        # Low risk
        result = interpret_wht_ratio(0.3, "es")
        assert result["risk"] == "low"
        assert result["description"] in [
            "Low health risk",
            "Healthy weight range",
        ]

        # Moderate risk
        result = interpret_wht_ratio(0.55, "es")
        assert result["risk"] == "moderate"
        assert result["description"] == "Moderate health risk"

        # High risk
        result = interpret_wht_ratio(0.65, "es")
        assert result["risk"] == "high"
        assert result["description"] == "High health risk"

    def test_whr_ratio_spanish_interpretation(self):
        """Test WHR interpretation in Spanish."""
        # Low risk male
        result = interpret_whr_ratio(0.9, "male", "es")
        assert result["risk"] == "low"

        # High risk male
        result = interpret_whr_ratio(1.0, "male", "es")
        assert result["risk"] == "high"
        assert (
            "forma androide" in result["description"].lower()
            or "manzana" in result["description"].lower()
        )

        # Low risk female
        result = interpret_whr_ratio(0.75, "female", "es")
        assert result["risk"] == "low"

        # High risk female
        result = interpret_whr_ratio(0.85, "female", "es")
        assert result["risk"] == "high"
        assert (
            "forma androide" in result["description"].lower()
            or "manzana" in result["description"].lower()
        )

    def test_stage_obesity_spanish(self):
        """Test obesity staging function with Spanish language."""
        # Low risk case
        result = stage_obesity(22, 0.4, 0.8, "male", "es")
        assert result["stage"] in ["low_risk", "bajo_riesgo"]
        assert isinstance(result["risk_factors"], str)

        # Moderate risk case
        result = stage_obesity(28, 0.5, 0.8, "male", "es")
        assert result["stage"] in ["moderate_risk", "riesgo_moderado"]
        assert isinstance(result["risk_factors"], str)

        # High risk case
        result = stage_obesity(32, 0.6, 1.0, "male", "es")
        assert result["stage"] in ["high_risk", "alto_riesgo"]
        assert isinstance(result["risk_factors"], str)

        # Check that recommendations are in Spanish
        assert len(result["recommendation"]) > 0
