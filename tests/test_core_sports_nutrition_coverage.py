# !/usr/bin/env python3
"""
Тесты для модуля core/sports_nutrition.py
Покрытие системы спортивного питания на основе NASM/ACSM/IFPA рекомендаций
"""

import os

from core.sports_nutrition import (
    SportCategory,
    SportsNutritionCalculator,
    SportsNutritionTargets,
    TrainingPhase,
)


class TestSportCategory:
    """Тесты enum SportCategory"""

    def setup_method(self):
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def test_sport_category_values(self):
        """Тест правильности значений спортивных категорий"""
        assert SportCategory.ENDURANCE.value == "endurance"
        assert SportCategory.STRENGTH.value == "strength"
        assert SportCategory.POWER.value == "power"
        assert SportCategory.TEAM.value == "team"
        assert SportCategory.AESTHETIC.value == "aesthetic"
        assert SportCategory.COMBAT.value == "combat"
        assert SportCategory.RECREATIONAL.value == "recreational"

    def test_sport_category_completeness(self):
        """Тест что все основные спортивные категории покрыты"""
        categories = [cat.value for cat in SportCategory]
        assert len(categories) == 7
        assert "endurance" in categories
        assert "strength" in categories
        assert "recreational" in categories


class TestTrainingPhase:
    """Тесты enum TrainingPhase"""

    def setup_method(self):
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def test_training_phase_values(self):
        """Тест правильности значений фаз тренировки"""
        assert TrainingPhase.OFF_SEASON.value == "off_season"
        assert TrainingPhase.PRE_SEASON.value == "pre_season"
        assert TrainingPhase.IN_SEASON.value == "in_season"
        assert TrainingPhase.PEAK.value == "peak"
        assert TrainingPhase.RECOVERY.value == "recovery"

    def test_training_phase_completeness(self):
        """Тест полноты фаз тренировочного процесса"""
        phases = [phase.value for phase in TrainingPhase]
        assert len(phases) == 5
        assert "off_season" in phases
        assert "peak" in phases


class TestSportsNutritionTargets:
    """Тесты dataclass SportsNutritionTargets"""

    def setup_method(self):
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def test_create_basic_targets(self):
        """Тест создания базовых целей спортивного питания"""
        targets = SportsNutritionTargets(
            protein_g_per_kg=1.6,
            carbs_g_per_kg=5.0,
            fat_g_per_kg=1.0,
            fluid_ml_per_hour_training=500,
            electrolyte_replacement=True,
            pre_workout_carbs_g=30.0,
            post_workout_protein_g=25.0,
            post_workout_carbs_g=50.0,
            creatine_recommended=True,
            caffeine_timing="pre_workout",
            meal_frequency=5,
            carb_loading_recommended=False,
            weight_cutting_considerations=None,
        )

        assert targets.protein_g_per_kg == 1.6
        assert targets.carbs_g_per_kg == 5.0
        assert targets.electrolyte_replacement is True
        assert targets.caffeine_timing == "pre_workout"

    def test_targets_with_optional_none(self):
        """Тест создания targets с None значениями"""
        targets = SportsNutritionTargets(
            protein_g_per_kg=1.2,
            carbs_g_per_kg=3.0,
            fat_g_per_kg=0.8,
            fluid_ml_per_hour_training=300,
            electrolyte_replacement=False,
            pre_workout_carbs_g=None,
            post_workout_protein_g=None,
            post_workout_carbs_g=None,
            creatine_recommended=False,
            caffeine_timing=None,
            meal_frequency=3,
            carb_loading_recommended=False,
            weight_cutting_considerations=None,
        )

        assert targets.pre_workout_carbs_g is None
        assert targets.caffeine_timing is None
        assert targets.weight_cutting_considerations is None

    def test_targets_immutability(self):
        """Тест неизменяемости targets (frozen dataclass)"""
        targets = SportsNutritionTargets(
            protein_g_per_kg=1.5,
            carbs_g_per_kg=4.0,
            fat_g_per_kg=1.0,
            fluid_ml_per_hour_training=400,
            electrolyte_replacement=True,
            pre_workout_carbs_g=25.0,
            post_workout_protein_g=20.0,
            post_workout_carbs_g=40.0,
            creatine_recommended=False,
            caffeine_timing="morning",
            meal_frequency=4,
            carb_loading_recommended=True,
            weight_cutting_considerations="gradual",
        )

        # Попытка изменить поле должна вызвать ошибку
        try:
            targets.protein_g_per_kg = 2.0
            assert False, "Should not be able to modify frozen dataclass"
        except (AttributeError, TypeError):
            pass  # Ожидаемое поведение


class TestSportsNutritionCalculator:
    """Тесты SportsNutritionCalculator"""

    def setup_method(self):
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def test_calculator_constants_exist(self):
        """Тест наличия констант калькулятора"""
        # Проверяем что константы определены для всех спортивных категорий
        for sport in SportCategory:
            assert sport in SportsNutritionCalculator.SPORT_PROTEIN_REQUIREMENTS
            assert sport in SportsNutritionCalculator.SPORT_CARB_REQUIREMENTS
            assert sport in SportsNutritionCalculator.HYDRATION_GUIDELINES

    def test_protein_requirements_ranges(self):
        """Тест диапазонов белковых требований"""
        protein_reqs = SportsNutritionCalculator.SPORT_PROTEIN_REQUIREMENTS

        # Силовые виды спорта должны иметь больше белка
        assert protein_reqs[SportCategory.STRENGTH][1] > protein_reqs[SportCategory.ENDURANCE][1]
        assert protein_reqs[SportCategory.COMBAT][1] >= protein_reqs[SportCategory.RECREATIONAL][1]

        # Все значения должны быть в разумных пределах (1.0-3.0 г/кг)
        for sport, (min_protein, max_protein) in protein_reqs.items():
            assert 1.0 <= min_protein <= 3.0
            assert 1.0 <= max_protein <= 3.0
            assert min_protein <= max_protein

    def test_carb_requirements_ranges(self):
        """Тест диапазонов углеводных требований"""
        carb_reqs = SportsNutritionCalculator.SPORT_CARB_REQUIREMENTS

        # Выносливостные виды спорта должны иметь больше углеводов
        assert carb_reqs[SportCategory.ENDURANCE][1] > carb_reqs[SportCategory.STRENGTH][1]

        # Все значения должны быть в разумных пределах (3-12 г/кг)
        for sport, (min_carbs, max_carbs) in carb_reqs.items():
            assert 3 <= min_carbs <= 12
            assert 3 <= max_carbs <= 12
            assert min_carbs <= max_carbs

    def test_hydration_guidelines_reasonableness(self):
        """Тест разумности рекомендаций по гидратации"""
        hydration = SportsNutritionCalculator.HYDRATION_GUIDELINES

        # Выносливостные виды спорта должны иметь больше жидкости
        assert hydration[SportCategory.ENDURANCE] > hydration[SportCategory.STRENGTH]

        # Все значения должны быть в разумных пределах (200-1000 мл/час)
        for sport, fluid_ml in hydration.items():
            assert 200 <= fluid_ml <= 1000

    def test_calculator_instantiation(self):
        """Тест создания экземпляра калькулятора"""
        calc = SportsNutritionCalculator()
        assert calc is not None
        assert isinstance(calc, SportsNutritionCalculator)

        # Тестируем что у калькулятора есть необходимые атрибуты
        assert hasattr(calc, "SPORT_PROTEIN_REQUIREMENTS")
        assert hasattr(calc, "SPORT_CARB_REQUIREMENTS")
        assert hasattr(calc, "HYDRATION_GUIDELINES")

    def test_all_sports_covered_in_requirements(self):
        """Тест что все виды спорта покрыты в требованиях"""
        all_sports = set(SportCategory)
        protein_sports = set(SportsNutritionCalculator.SPORT_PROTEIN_REQUIREMENTS.keys())
        carb_sports = set(SportsNutritionCalculator.SPORT_CARB_REQUIREMENTS.keys())
        hydration_sports = set(SportsNutritionCalculator.HYDRATION_GUIDELINES.keys())

        assert all_sports == protein_sports
        assert all_sports == carb_sports
        assert all_sports == hydration_sports

    def test_evidence_based_values(self):
        """Тест что значения соответствуют научным рекомендациям"""
        # ACSM/AND/DC Position Statement values
        protein_reqs = SportsNutritionCalculator.SPORT_PROTEIN_REQUIREMENTS
        carb_reqs = SportsNutritionCalculator.SPORT_CARB_REQUIREMENTS

        # Endurance athletes: 1.2-1.4 g/kg protein, 6-10 g/kg carbs
        assert protein_reqs[SportCategory.ENDURANCE] == (1.2, 1.4)
        assert carb_reqs[SportCategory.ENDURANCE] == (6, 10)

        # Strength athletes: 1.6-2.2 g/kg protein
        assert protein_reqs[SportCategory.STRENGTH] == (1.6, 2.2)

        # Recreational: moderate requirements
        assert protein_reqs[SportCategory.RECREATIONAL] == (1.2, 1.6)
        assert carb_reqs[SportCategory.RECREATIONAL] == (3, 5)


class TestIntegrationScenarios:
    """Интеграционные тесты реальных сценариев"""

    def setup_method(self):
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def test_endurance_athlete_scenario(self):
        """Тест сценария выносливостного атлета"""
        # Марафонец, тренировки высокого объема
        sport = SportCategory.ENDURANCE

        protein_range = SportsNutritionCalculator.SPORT_PROTEIN_REQUIREMENTS[sport]
        carb_range = SportsNutritionCalculator.SPORT_CARB_REQUIREMENTS[sport]
        hydration = SportsNutritionCalculator.HYDRATION_GUIDELINES[sport]

        # Проверяем адекватность рекомендаций
        assert protein_range[0] >= 1.2  # Минимум для выносливости
        assert carb_range[1] >= 8  # Высокие углеводы для выносливости
        assert hydration >= 500  # Высокая потребность в жидкости

    def test_strength_athlete_scenario(self):
        """Тест сценария силового атлета"""
        # Пауэрлифтер, низкий объем высокоинтенсивных тренировок
        sport = SportCategory.STRENGTH

        protein_range = SportsNutritionCalculator.SPORT_PROTEIN_REQUIREMENTS[sport]
        carb_range = SportsNutritionCalculator.SPORT_CARB_REQUIREMENTS[sport]
        hydration = SportsNutritionCalculator.HYDRATION_GUIDELINES[sport]

        # Проверяем адекватность рекомендаций
        assert protein_range[1] >= 2.0  # Высокий белок для силы
        assert carb_range[1] <= 5  # Умеренные углеводы
        assert hydration <= 300  # Умеренная потребность в жидкости

    def test_team_sport_scenario(self):
        """Тест сценария командного спорта"""
        # Футболист, смешанные тренировки
        sport = SportCategory.TEAM

        protein_range = SportsNutritionCalculator.SPORT_PROTEIN_REQUIREMENTS[sport]
        carb_range = SportsNutritionCalculator.SPORT_CARB_REQUIREMENTS[sport]
        hydration = SportsNutritionCalculator.HYDRATION_GUIDELINES[sport]

        # Проверяем сбалансированные рекомендации
        assert 1.4 <= protein_range[0] <= protein_range[1] <= 1.7
        assert 5 <= carb_range[0] <= carb_range[1] <= 8
        assert 400 <= hydration <= 600

    def test_recreational_athlete_baseline(self):
        """Тест базовых рекомендаций для любителей"""
        sport = SportCategory.RECREATIONAL

        protein_range = SportsNutritionCalculator.SPORT_PROTEIN_REQUIREMENTS[sport]
        carb_range = SportsNutritionCalculator.SPORT_CARB_REQUIREMENTS[sport]
        hydration = SportsNutritionCalculator.HYDRATION_GUIDELINES[sport]

        # Умеренные, безопасные рекомендации
        assert protein_range[1] <= 1.6  # Не слишком высокий белок
        assert carb_range == (3, 5)  # Умеренные углеводы
        assert hydration == 300  # Базовая гидратация
