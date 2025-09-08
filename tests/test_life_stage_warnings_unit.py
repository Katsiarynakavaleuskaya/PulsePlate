"""
Unit tests for _life_stage_warnings function

Tests all life stage warning codes and localized messages for RU/EN/ES languages.
"""

from core.targets import _life_stage_warnings


class TestLifeStageWarningsUnit:
    """Unit tests for _life_stage_warnings function"""

    def test_teen_warning_ru(self):
        """Test teen warning in Russian"""
        warnings = _life_stage_warnings(age=15, life_stage="teen", lang="ru")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "teen"
        assert "Подростковая группа" in warnings[0]["message"]
        assert "специализированные нормы" in warnings[0]["message"]

    def test_teen_warning_en(self):
        """Test teen warning in English"""
        warnings = _life_stage_warnings(age=16, life_stage="teen", lang="en")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "teen"
        assert "Teen life stage" in warnings[0]["message"]
        assert "age-appropriate references" in warnings[0]["message"]

    def test_teen_warning_es(self):
        """Test teen warning in Spanish"""
        warnings = _life_stage_warnings(age=17, life_stage="teen", lang="es")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "teen"
        assert "Etapa adolescente" in warnings[0]["message"]
        assert "apropiadas para la edad" in warnings[0]["message"]

    def test_pregnant_warning_ru(self):
        """Test pregnant warning in Russian"""
        warnings = _life_stage_warnings(age=25, life_stage="pregnant", lang="ru")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "pregnant"
        assert "Беременность" in warnings[0]["message"]
        assert "нормы отличаются" in warnings[0]["message"]

    def test_pregnant_warning_en(self):
        """Test pregnant warning in English"""
        warnings = _life_stage_warnings(age=30, life_stage="pregnant", lang="en")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "pregnant"
        assert "Pregnancy" in warnings[0]["message"]
        assert "requirements differ" in warnings[0]["message"]

    def test_pregnant_warning_es(self):
        """Test pregnant warning in Spanish"""
        warnings = _life_stage_warnings(age=28, life_stage="pregnant", lang="es")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "pregnant"
        assert "Embarazo" in warnings[0]["message"]
        assert "requisitos difieren" in warnings[0]["message"]

    def test_lactating_warning_ru(self):
        """Test lactating warning in Russian"""
        warnings = _life_stage_warnings(age=26, life_stage="lactating", lang="ru")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "lactating"
        assert "Лактация" in warnings[0]["message"]
        assert "повышенные потребности" in warnings[0]["message"]

    def test_lactating_warning_en(self):
        """Test lactating warning in English"""
        warnings = _life_stage_warnings(age=29, life_stage="lactating", lang="en")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "lactating"
        assert "Lactation" in warnings[0]["message"]
        assert "increased nutrient requirements" in warnings[0]["message"]

    def test_lactating_warning_es(self):
        """Test lactating warning in Spanish"""
        warnings = _life_stage_warnings(age=27, life_stage="lactating", lang="es")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "lactating"
        assert "Lactancia" in warnings[0]["message"]
        assert "requisitos de nutrientes aumentados" in warnings[0]["message"]

    def test_elderly_warning_ru(self):
        """Test elderly warning in Russian"""
        warnings = _life_stage_warnings(age=55, life_stage="elderly", lang="ru")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "elderly"
        assert "51+" in warnings[0]["message"]
        assert "микронутриентах" in warnings[0]["message"]

    def test_elderly_warning_en(self):
        """Test elderly warning in English"""
        warnings = _life_stage_warnings(age=60, life_stage="elderly", lang="en")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "elderly"
        assert "Age 51+" in warnings[0]["message"]
        assert "micronutrient needs may differ" in warnings[0]["message"]

    def test_elderly_warning_es(self):
        """Test elderly warning in Spanish"""
        warnings = _life_stage_warnings(age=65, life_stage="elderly", lang="es")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "elderly"
        assert "51+" in warnings[0]["message"]
        assert "micronutrientes pueden diferir" in warnings[0]["message"]

    def test_child_warning_ru(self):
        """Test child warning in Russian"""
        warnings = _life_stage_warnings(age=8, life_stage="child", lang="ru")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "child"
        assert "Детский возраст" in warnings[0]["message"]
        assert "педиатрические нормы" in warnings[0]["message"]

    def test_child_warning_en(self):
        """Test child warning in English"""
        warnings = _life_stage_warnings(age=10, life_stage="child", lang="en")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "child"
        assert "Child age" in warnings[0]["message"]
        assert "pediatric references" in warnings[0]["message"]

    def test_child_warning_es(self):
        """Test child warning in Spanish"""
        warnings = _life_stage_warnings(age=9, life_stage="child", lang="es")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "child"
        assert "Edad infantil" in warnings[0]["message"]
        assert "pediátricas" in warnings[0]["message"]

    def test_no_warnings_adult(self):
        """Test no warnings for adult life stage"""
        warnings = _life_stage_warnings(age=35, life_stage="adult", lang="en")
        assert len(warnings) == 0

    def test_no_warnings_teen_wrong_age(self):
        """Test no teen warning for wrong age range"""
        # Too young
        warnings = _life_stage_warnings(age=10, life_stage="teen", lang="en")
        assert len(warnings) == 0

        # Too old
        warnings = _life_stage_warnings(age=20, life_stage="teen", lang="en")
        assert len(warnings) == 0

    def test_no_warnings_elderly_wrong_age(self):
        """Test no elderly warning for wrong age"""
        warnings = _life_stage_warnings(age=45, life_stage="elderly", lang="en")
        assert len(warnings) == 0

    def test_no_warnings_child_wrong_age(self):
        """Test no child warning for wrong age"""
        warnings = _life_stage_warnings(age=15, life_stage="child", lang="en")
        assert len(warnings) == 0

    def test_fallback_to_english(self):
        """Test fallback to English for unknown language"""
        warnings = _life_stage_warnings(age=15, life_stage="teen", lang="unknown")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "teen"
        assert "Teen life stage" in warnings[0]["message"]  # English fallback

    def test_multiple_warnings_elderly_pregnant(self):
        """Test multiple warnings for elderly pregnant woman"""
        warnings = _life_stage_warnings(age=55, life_stage="pregnant", lang="en")

        # Only pregnant warning should be present (life_stage takes precedence)
        assert len(warnings) == 1
        assert warnings[0]["code"] == "pregnant"

    def test_edge_case_teen_min_age(self):
        """Test teen warning at minimum age"""
        warnings = _life_stage_warnings(age=12, life_stage="teen", lang="en")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "teen"

    def test_edge_case_teen_max_age(self):
        """Test teen warning at maximum age"""
        warnings = _life_stage_warnings(age=18, life_stage="teen", lang="en")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "teen"

    def test_edge_case_elderly_min_age(self):
        """Test elderly warning at minimum age"""
        warnings = _life_stage_warnings(age=51, life_stage="elderly", lang="en")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "elderly"

    def test_edge_case_child_max_age(self):
        """Test child warning at maximum age"""
        warnings = _life_stage_warnings(age=11, life_stage="child", lang="en")

        assert len(warnings) == 1
        assert warnings[0]["code"] == "child"

    def test_all_warning_codes_present(self):
        """Test that all expected warning codes are present"""
        expected_codes = ["teen", "pregnant", "lactating", "elderly", "child"]

        # Test each code individually
        test_cases = [
            (15, "teen"),
            (25, "pregnant"),
            (26, "lactating"),
            (55, "elderly"),
            (8, "child"),
        ]

        for age, life_stage in test_cases:
            warnings = _life_stage_warnings(age=age, life_stage=life_stage, lang="en")
            assert len(warnings) == 1
            assert warnings[0]["code"] in expected_codes

    def test_message_structure(self):
        """Test that all messages have correct structure"""
        warnings = _life_stage_warnings(age=15, life_stage="teen", lang="en")

        assert len(warnings) == 1
        warning = warnings[0]

        # Check structure
        assert "code" in warning
        assert "message" in warning
        assert isinstance(warning["code"], str)
        assert isinstance(warning["message"], str)
        assert len(warning["code"]) > 0
        assert len(warning["message"]) > 0
