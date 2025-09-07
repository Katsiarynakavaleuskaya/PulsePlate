"""
Tests for Life-Stage Nutrition module

Tests WHO/EFSA-based nutrition guidelines for children, pregnant women,
lactating mothers, and elderly populations.
"""

import pytest

from core.lifestage_nutrition import (
    LifeStage,
    LifeStageNutritionCalculator,
    get_lifestage_recommendations,
)
from core.targets import UserProfile


class TestLifeStageNutritionCalculator:
    """Test life-stage nutrition calculation system."""

    def test_child_2_5_nutrition(self):
        """Test nutrition requirements for children 2-5 years."""
        profile = UserProfile(
            sex="male",
            age=3,
            height_cm=95,
            weight_kg=14,
            activity="moderate",
            goal="maintain",
        )

        targets = LifeStageNutritionCalculator.calculate_lifestage_targets(
            profile, LifeStage.CHILD_2_5
        )

        assert targets["life_stage"] == "child_2_5"

        # Energy needs should be based on weight (90 kcal/kg)
        expected_energy = 90 * 14  # ~1260 kcal
        assert abs(targets["energy_needs"]["total_kcal"] - expected_energy) < 100

        # Protein should be 1.0 g/kg
        assert targets["macronutrients"]["protein_per_kg"] == 1.0

        # Key micronutrients
        micros = targets["key_micronutrients"]
        assert micros["iron_mg"] == 7  # EFSA recommendation
        assert micros["calcium_mg"] == 450  # EFSA recommendation
        assert micros["folate_ug"] == 150  # EFSA recommendation

        # Food guidance
        guidance = targets["food_guidance"]
        assert "honey" in guidance["avoid_foods"]
        assert "whole_nuts" in guidance["avoid_foods"]
        assert len(guidance["feeding_notes"]) > 0

        # Medical disclaimer
        assert "medical_disclaimer" in targets
        assert "WHO/EFSA" in targets["medical_disclaimer"]

    def test_child_6_11_nutrition(self):
        """Test nutrition requirements for school-age children."""
        profile = UserProfile(
            sex="female",
            age=8,
            height_cm=125,
            weight_kg=25,
            activity="active",
            goal="maintain",
        )

        targets = LifeStageNutritionCalculator.calculate_lifestage_targets(
            profile, LifeStage.CHILD_6_11
        )

        assert targets["life_stage"] == "child_6_11"

        # Energy needs should be 70 kcal/kg
        expected_energy = 70 * 25  # 1750 kcal
        assert abs(targets["energy_needs"]["total_kcal"] - expected_energy) < 100

        # Higher calcium needs for bone development
        micros = targets["key_micronutrients"]
        assert micros["calcium_mg"] == 800  # Critical for bone development
        assert micros["iron_mg"] == 9
        assert micros["iodine_ug"] == 120

    def test_adolescent_nutrition(self):
        """Test nutrition requirements for adolescents."""
        profile = UserProfile(
            sex="female",
            age=15,
            height_cm=160,
            weight_kg=50,
            activity="active",
            goal="maintain",
        )

        targets = LifeStageNutritionCalculator.calculate_lifestage_targets(
            profile, LifeStage.ADOLESCENT_12_18
        )

        assert targets["life_stage"] == "adolescent"

        # High iron needs for female adolescents
        micros = targets["key_micronutrients"]
        assert micros["iron_mg"] == 15  # High for females due to menstruation

        # Peak bone mass formation
        assert micros["calcium_mg"] == 1150  # Peak bone mass formation

        # Growth spurt considerations
        guidance = targets["food_guidance"]
        feeding_notes = " ".join(guidance["feeding_notes"])
        assert "growth spurt" in feeding_notes.lower()

    def test_pregnant_first_trimester(self):
        """Test nutrition requirements for first trimester pregnancy."""
        profile = UserProfile(
            sex="female",
            age=28,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
        )

        targets = LifeStageNutritionCalculator.calculate_lifestage_targets(
            profile, LifeStage.PREGNANT_T1
        )

        assert targets["life_stage"] == "pregnant_t1"

        # No additional calories in first trimester
        assert targets["energy_needs"]["additional_kcal"] == 0

        # Critical folate needs
        micros = targets["key_micronutrients"]
        assert micros["folate_ug"] == 600  # Critical for neural tube development
        assert micros["iron_mg"] == 27  # Significantly increased
        assert micros["iodine_ug"] == 220  # Increased for fetal brain development

        # Food safety
        guidance = targets["food_guidance"]
        assert "alcohol" in guidance["avoid_foods"]
        assert "raw_fish_meat" in guidance["avoid_foods"]
        assert "high_mercury_fish" in guidance["avoid_foods"]

    def test_pregnant_second_trimester(self):
        """Test nutrition requirements for second trimester pregnancy."""
        profile = UserProfile(
            sex="female",
            age=30,
            height_cm=168,
            weight_kg=65,
            activity="light",
            goal="maintain",
        )

        targets = LifeStageNutritionCalculator.calculate_lifestage_targets(
            profile, LifeStage.PREGNANT_T2
        )

        assert targets["life_stage"] == "pregnant_t2"

        # Additional 340 calories in second trimester
        assert targets["energy_needs"]["additional_kcal"] == 340

        # Increased protein needs
        assert targets["macronutrients"]["protein_per_kg"] == 1.1

    def test_pregnant_third_trimester(self):
        """Test nutrition requirements for third trimester pregnancy."""
        profile = UserProfile(
            sex="female",
            age=32,
            height_cm=170,
            weight_kg=70,
            activity="light",
            goal="maintain",
        )

        targets = LifeStageNutritionCalculator.calculate_lifestage_targets(
            profile, LifeStage.PREGNANT_T3
        )

        assert targets["life_stage"] == "pregnant_t3"

        # Additional 450 calories in third trimester
        assert targets["energy_needs"]["additional_kcal"] == 450

        # Feeding notes should address common third trimester issues
        guidance = targets["food_guidance"]
        feeding_notes = " ".join(guidance["feeding_notes"])
        assert "heartburn" in feeding_notes.lower()

    def test_lactating_nutrition(self):
        """Test nutrition requirements for lactating mothers."""
        profile = UserProfile(
            sex="female",
            age=29,
            height_cm=165,
            weight_kg=62,
            activity="moderate",
            goal="maintain",
        )

        targets = LifeStageNutritionCalculator.calculate_lifestage_targets(
            profile, LifeStage.LACTATING
        )

        assert targets["life_stage"] == "lactating"

        # Highest energy needs - additional 500 calories
        assert targets["energy_needs"]["additional_kcal"] == 500

        # Highest protein needs
        assert targets["macronutrients"]["protein_per_kg"] == 1.3

        # Highest iodine needs for milk production
        micros = targets["key_micronutrients"]
        assert micros["iodine_ug"] == 290  # Highest needs for milk production

        # Hydration emphasis
        guidance = targets["food_guidance"]
        feeding_notes = " ".join(guidance["feeding_notes"])
        assert "hydration" in feeding_notes.lower()
        assert "700ml" in feeding_notes  # Extra hydration needs

    def test_elderly_nutrition(self):
        """Test nutrition requirements for elderly adults."""
        profile = UserProfile(
            sex="male",
            age=70,
            height_cm=175,
            weight_kg=75,
            activity="light",
            goal="maintain",
        )

        targets = LifeStageNutritionCalculator.calculate_lifestage_targets(
            profile, LifeStage.ELDERLY
        )

        assert targets["life_stage"] == "elderly"

        # Lower energy needs (30 kcal/kg)
        expected_energy = 30 * 75  # 2250 kcal
        assert abs(targets["energy_needs"]["total_kcal"] - expected_energy) < 100

        # Higher protein to prevent sarcopenia
        assert targets["macronutrients"]["protein_per_kg"] == 1.2

        # Increased bone health nutrients
        micros = targets["key_micronutrients"]
        assert micros["calcium_mg"] == 1200  # Increased for bone health
        assert micros["vitamin_d_iu"] == 800  # Increased for bone health and immunity

        # Special considerations for elderly
        guidance = targets["food_guidance"]
        feeding_notes = " ".join(guidance["feeding_notes"])
        assert "nutrient-dense" in feeding_notes.lower()
        assert "medication" in feeding_notes.lower()


class TestLifeStageDetection:
    """Test automatic life stage detection."""

    def test_get_appropriate_lifestage(self):
        """Test automatic life stage detection based on age."""
        # Test child stages
        assert (
            LifeStageNutritionCalculator.get_appropriate_lifestage(3, "male")
            == LifeStage.CHILD_2_5
        )
        assert (
            LifeStageNutritionCalculator.get_appropriate_lifestage(8, "female")
            == LifeStage.CHILD_6_11
        )
        assert (
            LifeStageNutritionCalculator.get_appropriate_lifestage(15, "female")
            == LifeStage.ADOLESCENT_12_18
        )

        # Test adult
        assert (
            LifeStageNutritionCalculator.get_appropriate_lifestage(30, "male")
            == LifeStage.ADULT
        )

        # Test elderly
        assert (
            LifeStageNutritionCalculator.get_appropriate_lifestage(70, "female")
            == LifeStage.ELDERLY
        )

    def test_pregnancy_detection(self):
        """Test pregnancy stage detection."""
        # First trimester
        stage = LifeStageNutritionCalculator.get_appropriate_lifestage(
            25, "female", is_pregnant=True, trimester=1
        )
        assert stage == LifeStage.PREGNANT_T1

        # Second trimester
        stage = LifeStageNutritionCalculator.get_appropriate_lifestage(
            28, "female", is_pregnant=True, trimester=2
        )
        assert stage == LifeStage.PREGNANT_T2

        # Third trimester
        stage = LifeStageNutritionCalculator.get_appropriate_lifestage(
            30, "female", is_pregnant=True, trimester=3
        )
        assert stage == LifeStage.PREGNANT_T3

    def test_lactation_detection(self):
        """Test lactation detection."""
        stage = LifeStageNutritionCalculator.get_appropriate_lifestage(
            25, "female", is_lactating=True
        )
        assert stage == LifeStage.LACTATING

    def test_infant_age_error(self):
        """Test error handling for infants under 2 years."""
        with pytest.raises(ValueError) as excinfo:
            LifeStageNutritionCalculator.get_appropriate_lifestage(1, "male")

        assert "not suitable for infants under 2 years" in str(excinfo.value)
        assert "pediatrician" in str(excinfo.value)


class TestLifeStageIntegration:
    """Test integration with main nutrition system."""

    def test_get_lifestage_recommendations(self):
        """Test main life-stage recommendation function."""
        profile = UserProfile(
            sex="female",
            age=25,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
        )

        # Test pregnancy recommendations
        recommendations = get_lifestage_recommendations(
            profile, is_pregnant=True, trimester=2
        )

        assert recommendations["life_stage"] == "pregnant_t2"
        assert "energy_needs" in recommendations
        assert "macronutrients" in recommendations
        assert "key_micronutrients" in recommendations
        assert "food_guidance" in recommendations
        assert "medical_disclaimer" in recommendations
        assert "professional_referral_note" in recommendations

    def test_invalid_age_handling(self):
        """Test handling of invalid ages."""
        profile = UserProfile(
            sex="male",
            age=1,  # Too young
            height_cm=80,
            weight_kg=10,
            activity="light",
            goal="maintain",
        )

        recommendations = get_lifestage_recommendations(profile)

        assert "error" in recommendations
        assert (
            "pediatrician" in recommendations["recommendation"]
            or "healthcare professional" in recommendations["recommendation"]
        )
        assert recommendations["life_stage"] == "not_applicable"

    def test_elderly_recommendations(self):
        """Test elderly-specific recommendations."""
        profile = UserProfile(
            sex="female",
            age=75,
            height_cm=160,
            weight_kg=65,
            activity="light",
            goal="maintain",
        )

        recommendations = get_lifestage_recommendations(profile)

        assert recommendations["life_stage"] == "elderly"

        # Should emphasize nutrient density
        guidance = recommendations["food_guidance"]
        feeding_notes = " ".join(guidance["feeding_notes"])
        assert "nutrient-dense" in feeding_notes.lower()

        # Should address medication interactions
        assert "medication" in feeding_notes.lower()


class TestMedicalDisclaimers:
    """Test medical disclaimers and safety warnings."""

    def test_pregnancy_disclaimers(self):
        """Test pregnancy-specific medical disclaimers."""
        profile = UserProfile(
            sex="female",
            age=28,
            height_cm=165,
            weight_kg=60,
            activity="moderate",
            goal="maintain",
        )

        recommendations = get_lifestage_recommendations(
            profile, is_pregnant=True, trimester=1
        )

        disclaimer = recommendations["medical_disclaimer"]

        # Should emphasize medical supervision during pregnancy
        assert "pregnancy" in disclaimer.lower()
        assert "individual needs vary" in disclaimer.lower()  # More flexible matching
        assert "qualified healthcare professionals" in disclaimer

        # Professional referral note
        referral = recommendations["professional_referral_note"]
        assert "Obstetrician" in referral or "Midwife" in referral

    def test_pediatric_disclaimers(self):
        """Test pediatric-specific medical disclaimers."""
        profile = UserProfile(
            sex="male",
            age=5,
            height_cm=110,
            weight_kg=18,
            activity="active",
            goal="maintain",
        )

        recommendations = get_lifestage_recommendations(profile)

        disclaimer = recommendations["medical_disclaimer"]
        professional_referral = recommendations["professional_referral_note"]

        # Should emphasize pediatric care
        assert "childhood" in disclaimer.lower()
        assert "Pediatrician" in professional_referral

    def test_elderly_disclaimers(self):
        """Test elderly-specific medical disclaimers."""
        profile = UserProfile(
            sex="male",
            age=80,
            height_cm=170,
            weight_kg=70,
            activity="sedentary",
            goal="maintain",
        )

        recommendations = get_lifestage_recommendations(profile)

        disclaimer = recommendations["medical_disclaimer"]
        professional_referral = recommendations["professional_referral_note"]

        # Should emphasize geriatric care
        assert "elderly" in disclaimer.lower()
        assert "Geriatrician" in professional_referral


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
