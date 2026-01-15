"""
Comprehensive tests for core/bmi_extras.py (Pro tier) - Advanced BMI metrics.

Tests cover:
- Waist-to-Height Ratio (WHtR) calculation and interpretation
- Waist-to-Hip Ratio (WHR) calculation and interpretation
- Fat-Free Mass Index (FFMI) calculation
- Obesity staging based on multiple metrics
"""

import pytest
from core.bmi_extras import (
    wht_ratio,
    whr_ratio,
    ffmi,
    interpret_wht_ratio,
    interpret_whr_ratio,
    stage_obesity,
)


class TestWHTRatio:
    """Tests for Waist-to-Height Ratio calculation."""

    def test_wht_ratio_normal(self):
        """Test WHtR calculation for normal values."""
        # Waist 80cm, Height 170cm -> 0.47 (healthy)
        result = wht_ratio(80.0, 170.0)
        assert result == pytest.approx(0.47, abs=0.01)

    def test_wht_ratio_high_risk(self):
        """Test WHtR for high risk values."""
        # Waist 100cm, Height 170cm -> 0.59 (high risk)
        result = wht_ratio(100.0, 170.0)
        assert result == pytest.approx(0.588, abs=0.01)

    def test_wht_ratio_very_high_risk(self):
        """Test WHtR for very high risk values."""
        # Waist 110cm, Height 170cm -> 0.65 (very high risk)
        result = wht_ratio(110.0, 170.0)
        assert result == pytest.approx(0.647, abs=0.01)

    def test_wht_ratio_edge_cases(self):
        """Test WHtR edge cases."""
        # Very small waist
        assert wht_ratio(60.0, 180.0) == pytest.approx(0.333, abs=0.01)
        # Very tall person
        assert wht_ratio(90.0, 200.0) == pytest.approx(0.45, abs=0.01)


class TestWHRRatio:
    """Tests for Waist-to-Hip Ratio calculation."""

    def test_whr_male_normal(self):
        """Test WHR for male with normal values."""
        # Waist 85cm, Hip 95cm -> 0.89 (normal for male)
        result = whr_ratio(85.0, 95.0, "male")
        assert result == pytest.approx(0.895, abs=0.01)

    def test_whr_female_normal(self):
        """Test WHR for female with normal values."""
        # Waist 75cm, Hip 95cm -> 0.79 (normal for female)
        result = whr_ratio(75.0, 95.0, "female")
        assert result == pytest.approx(0.789, abs=0.01)

    def test_whr_male_high_risk(self):
        """Test WHR for male with high risk values."""
        # Waist 100cm, Hip 95cm -> 1.05 (high risk for male)
        result = whr_ratio(100.0, 95.0, "male")
        assert result == pytest.approx(1.053, abs=0.01)

    def test_whr_female_high_risk(self):
        """Test WHR for female with high risk values."""
        # Waist 90cm, Hip 95cm -> 0.95 (high risk for female)
        result = whr_ratio(90.0, 95.0, "female")
        assert result == pytest.approx(0.947, abs=0.01)

    def test_whr_edge_cases(self):
        """Test WHR edge cases."""
        # Equal waist and hip
        assert whr_ratio(90.0, 90.0, "male") == pytest.approx(1.0, abs=0.01)
        # Very small waist
        assert whr_ratio(60.0, 95.0, "female") == pytest.approx(0.632, abs=0.01)


class TestFFMI:
    """Tests for Fat-Free Mass Index calculation."""

    def test_ffmi_normal_male(self):
        """Test FFMI for normal male."""
        # Weight 75kg, Height 180cm, BF 15%
        result = ffmi(75.0, 180.0, 15.0)
        assert "ffmi" in result
        assert "ffm_kg" in result
        assert result["ffmi"] == pytest.approx(19.6, abs=0.5)
        assert result["ffm_kg"] == pytest.approx(63.75, abs=1.0)

    def test_ffmi_normal_female(self):
        """Test FFMI for normal female."""
        # Weight 60kg, Height 165cm, BF 25%
        result = ffmi(60.0, 165.0, 25.0)
        assert "ffmi" in result
        assert "ffm_kg" in result
        assert result["ffmi"] == pytest.approx(16.5, abs=0.5)
        assert result["ffm_kg"] == pytest.approx(45.0, abs=1.0)

    def test_ffmi_athlete_male(self):
        """Test FFMI for male athlete."""
        # Weight 85kg, Height 180cm, BF 10%
        result = ffmi(85.0, 180.0, 10.0)
        assert result["ffmi"] > 21  # Athletic range

    def test_ffmi_high_bodyfat(self):
        """Test FFMI with high body fat."""
        # Weight 90kg, Height 175cm, BF 30%
        result = ffmi(90.0, 175.0, 30.0)
        assert result["ffmi"] > 15  # Should still be reasonable

    def test_ffmi_no_bodyfat(self):
        """Test FFMI without body fat percentage (uses default)."""
        # Weight 75kg, Height 180cm, no BF provided
        result = ffmi(75.0, 180.0)
        assert "ffmi" in result
        assert "ffm_kg" in result
        # Should use default estimation (85% lean mass)
        assert result["ffmi"] > 15

    def test_ffmi_edge_cases(self):
        """Test FFMI edge cases."""
        # Very low body fat
        result = ffmi(70.0, 180.0, 5.0)
        assert result["ffmi"] > 18
        # Very high body fat
        result = ffmi(100.0, 180.0, 40.0)
        assert result["ffmi"] > 12

    def test_ffmi_validation_errors(self):
        """Test FFMI validation."""
        # Negative weight
        with pytest.raises(ValueError):
            ffmi(-75.0, 180.0, 15.0)
        # Negative height
        with pytest.raises(ValueError):
            ffmi(75.0, -180.0, 15.0)
        # Invalid body fat
        with pytest.raises(ValueError):
            ffmi(75.0, 180.0, 150.0)
        # Negative body fat
        with pytest.raises(ValueError):
            ffmi(75.0, 180.0, -5.0)


class TestInterpretWHTRatio:
    """Tests for WHtR interpretation."""

    def test_interpret_wht_healthy_en(self):
        """Test WHtR interpretation - healthy range in English."""
        result = interpret_wht_ratio(0.45, lang="en")
        assert "category" in result or "description" in result
        assert "risk" in result
        # Just verify it returns non-empty strings
        assert isinstance(result["category"], str)
        assert len(result["category"]) > 0

    def test_interpret_wht_increased_risk(self):
        """Test WHtR interpretation - increased risk."""
        result = interpret_wht_ratio(0.52, lang="en")
        assert "category" in result or "description" in result
        assert "risk" in result

    def test_interpret_wht_high_risk(self):
        """Test WHtR interpretation - high risk."""
        result = interpret_wht_ratio(0.60, lang="en")
        assert "category" in result or "description" in result
        assert "risk" in result

    def test_interpret_wht_russian(self):
        """Test WHtR interpretation in Russian."""
        result = interpret_wht_ratio(0.45, lang="ru")
        assert "category" in result or "description" in result
        assert "risk" in result
        # Should return Russian text
        assert isinstance(result["category"], str)

    def test_interpret_wht_spanish(self):
        """Test WHtR interpretation in Spanish."""
        result = interpret_wht_ratio(0.45, lang="es")
        assert "category" in result or "description" in result
        assert "risk" in result

    def test_interpret_wht_edge_values(self):
        """Test WHtR interpretation edge values."""
        # Very low
        result = interpret_wht_ratio(0.35, lang="en")
        assert result is not None
        # Very high
        result = interpret_wht_ratio(0.70, lang="en")
        assert result is not None


class TestInterpretWHRRatio:
    """Tests for WHR interpretation."""

    def test_interpret_whr_male_low_risk_en(self):
        """Test WHR interpretation for male - low risk in English."""
        result = interpret_whr_ratio(0.85, "male", lang="en")
        assert "category" in result or "description" in result
        assert "risk" in result
        # Just verify it returns non-empty strings
        assert isinstance(result["risk"], str)
        assert len(result["risk"]) > 0

    def test_interpret_whr_female_low_risk(self):
        """Test WHR interpretation for female - low risk."""
        result = interpret_whr_ratio(0.75, "female", lang="en")
        assert "category" in result or "description" in result
        assert "risk" in result

    def test_interpret_whr_male_high_risk(self):
        """Test WHR interpretation for male - high risk."""
        result = interpret_whr_ratio(1.0, "male", lang="en")
        assert "category" in result or "description" in result
        assert "risk" in result
        # Just verify it returns non-empty strings
        assert isinstance(result["risk"], str)
        assert len(result["risk"]) > 0

    def test_interpret_whr_female_high_risk(self):
        """Test WHR interpretation for female - high risk."""
        result = interpret_whr_ratio(0.90, "female", lang="en")
        assert "category" in result or "description" in result
        assert "risk" in result

    def test_interpret_whr_russian(self):
        """Test WHR interpretation in Russian."""
        result = interpret_whr_ratio(0.85, "male", lang="ru")
        assert "category" in result or "description" in result
        assert "risk" in result

    def test_interpret_whr_spanish(self):
        """Test WHR interpretation in Spanish."""
        result = interpret_whr_ratio(0.85, "male", lang="es")
        assert "category" in result or "description" in result
        assert "risk" in result


class TestStageObesity:
    """Tests for obesity staging."""

    def test_stage_obesity_normal_weight(self):
        """Test obesity staging for normal weight."""
        result = stage_obesity(bmi=22.0, wht=0.45, whr=0.85, sex="male", lang="en")
        assert "stage" in result
        assert result["stage"] is not None

    def test_stage_obesity_overweight(self):
        """Test obesity staging for overweight."""
        result = stage_obesity(bmi=27.0, wht=0.52, whr=0.90, sex="male", lang="en")
        assert "stage" in result

    def test_stage_obesity_class_1(self):
        """Test obesity staging - Class I."""
        result = stage_obesity(bmi=32.0, wht=0.58, whr=0.98, sex="male", lang="en")
        assert "stage" in result

    def test_stage_obesity_female(self):
        """Test obesity staging for female."""
        result = stage_obesity(bmi=28.0, wht=0.53, whr=0.82, sex="female", lang="en")
        assert "stage" in result

    def test_stage_obesity_underweight(self):
        """Test obesity staging for underweight BMI category."""
        result = stage_obesity(bmi=17.0, wht=0.4, whr=0.7, sex="male", lang="en")
        assert result["bmi_category"] == "underweight"

    def test_stage_obesity_multilingual(self):
        """Test obesity staging in different languages."""
        result_ru = stage_obesity(bmi=27.0, wht=0.52, whr=0.90, sex="male", lang="ru")
        assert "stage" in result_ru
        result_es = stage_obesity(bmi=27.0, wht=0.52, whr=0.90, sex="male", lang="es")
        assert "stage" in result_es

    def test_stage_obesity_optional_whr_with_whr_none(self):
        """Test stage_obesity_optional_whr with missing WHR (whr=None)."""
        from core.bmi_extras import stage_obesity_optional_whr

        # Missing WHR should result in whr_risk="unknown"
        result = stage_obesity_optional_whr(bmi=22.0, wht=0.45, whr=None, sex="male", lang="en")
        assert "stage" in result
        assert result["whr_risk"] == "unknown"
        assert "wht_risk" in result
        assert result["risk_factors"] in ["0", "1", "2"]  # WHR not counted when None

    def test_stage_obesity_optional_whr_with_whr_provided(self):
        """Test stage_obesity_optional_whr with WHR provided."""
        from core.bmi_extras import stage_obesity_optional_whr

        # With WHR, should calculate whr_risk normally
        result = stage_obesity_optional_whr(bmi=32.0, wht=0.55, whr=0.96, sex="male", lang="en")
        assert "stage" in result
        assert result["whr_risk"] != "unknown"
        assert result["whr_risk"] in ["low", "high"]
        assert "wht_risk" in result

    def test_stage_obesity_optional_whr_low_risk_path(self):
        """Test stage_obesity_optional_whr low_risk path (risk_factors=0)."""
        from core.bmi_extras import stage_obesity_optional_whr

        # Low risk: BMI < 30, WHtR < 0.5, no WHR risk
        result = stage_obesity_optional_whr(bmi=22.0, wht=0.4, whr=None, sex="male", lang="en")
        assert result["stage"] == "low_risk"
        assert result["risk_factors"] == "0"
        assert "recommendation" in result

    def test_stage_obesity_optional_whr_underweight_bmi_category(self):
        """Test stage_obesity_optional_whr with underweight BMI category."""
        from core.bmi_extras import stage_obesity_optional_whr

        # Underweight: BMI < 18.5
        result = stage_obesity_optional_whr(bmi=17.0, wht=0.4, whr=None, sex="male", lang="en")
        assert result["bmi_category"] == "underweight"
        assert "stage" in result
        assert "wht_risk" in result
        assert result["whr_risk"] == "unknown"  # WHR is None

    def test_stage_obesity_optional_whr_high_risk_localization(self):
        """Test that high-risk recommendation is localized (not hardcoded English).

        Verifies that recommendation matches i18n key 'recommendation_consult_healthcare'
        for all languages (RU/ES/EN), ensuring no hardcoded English text appears.
        """
        from core.bmi_extras import stage_obesity_optional_whr
        from core.i18n import t

        # High risk: BMI >= 30, WHtR >= 0.5 (risk_factors >= 2)
        for lang in ["ru", "es", "en"]:
            result = stage_obesity_optional_whr(bmi=32.0, wht=0.55, whr=None, sex="male", lang=lang)
            assert result["stage"] == "high_risk"
            assert "recommendation" in result

            # Compare directly with i18n key (not hardcoded text)
            expected = t(lang, "recommendation_consult_healthcare")
            assert (
                result["recommendation"] == expected
            ), f"Recommendation for lang={lang} should match i18n key 'recommendation_consult_healthcare'"

            # Additional safety check: RU/ES should NOT contain English text
            if lang in ["ru", "es"]:
                assert (
                    "Consider consulting" not in result["recommendation"]
                ), f"Language {lang} should not contain English text 'Consider consulting'"


class TestIntegration:
    """Integration tests combining multiple pro metrics."""

    def test_comprehensive_health_profile_healthy(self):
        """Test comprehensive health profile for healthy individual."""
        # Healthy male: 75kg, 180cm, 15% BF, waist 85cm, hip 95cm
        wht = wht_ratio(85.0, 180.0)
        whr = whr_ratio(85.0, 95.0, "male")
        ffmi_result = ffmi(75.0, 180.0, 15.0)

        assert wht < 0.5  # Healthy
        assert whr < 0.95  # Healthy for male
        assert 18 <= ffmi_result["ffmi"] <= 22  # Normal FFMI range

    def test_comprehensive_health_profile_at_risk(self):
        """Test comprehensive health profile for at-risk individual."""
        # At-risk male: 95kg, 175cm, 28% BF, waist 105cm, hip 100cm
        wht = wht_ratio(105.0, 175.0)
        whr = whr_ratio(105.0, 100.0, "male")

        assert wht > 0.5  # At risk
        assert whr > 0.95  # At risk for male

    def test_consistency_across_languages(self):
        """Test that interpretations are consistent across languages."""
        wht_value = 0.52

        result_en = interpret_wht_ratio(wht_value, lang="en")
        result_ru = interpret_wht_ratio(wht_value, lang="ru")
        result_es = interpret_wht_ratio(wht_value, lang="es")

        # All should have same structure
        assert set(result_en.keys()) == set(result_ru.keys()) == set(result_es.keys())

        # All should be non-empty
        assert all(result_en.values())
        assert all(result_ru.values())
        assert all(result_es.values())
