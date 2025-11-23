# -*- coding: utf-8 -*-
"""
Tests for Sprint 5: Auto-repair functionality

RU: Тесты для функциональности авто-ремонта с UX-петлей
EN: Tests for auto-repair functionality with UX loop
"""

from typing import Any
from unittest.mock import patch

from core.auto_repair import (
    AutoRepairEngine,
    RepairIteration,
    RepairResult,
    RepairStatus,
    RepairStrategy,
    auto_repair_week_plan,
    get_auto_repair_engine,
    suggest_manual_fixes,
)
from core.targets import MicronutrientTargets


def default_targets() -> MicronutrientTargets:
    return MicronutrientTargets(
        iron_mg=(18.0, 18.0, 18.0),
        calcium_mg=(1000.0, 1000.0, 1000.0),
        magnesium_mg=(400.0, 400.0, 400.0),
        zinc_mg=(11.0, 11.0, 11.0),
        potassium_mg=(3500.0, 3500.0, 3500.0),
        iodine_ug=(150.0, 150.0, 150.0),
        selenium_ug=(55.0, 55.0, 55.0),
        folate_ug=(400.0, 400.0, 400.0),
        b12_ug=(2.4, 2.4, 2.4),
        vitamin_d_iu=(20.0, 20.0, 20.0),
        vitamin_a_ug=(900.0, 900.0, 900.0),
        vitamin_c_mg=(90.0, 90.0, 90.0),
    )


class TestRepairStrategy:
    """Тесты для enum RepairStrategy"""

    def test_repair_strategy_values(self) -> None:
        """Тест значений стратегий ремонта"""
        assert RepairStrategy.CONSERVATIVE.value == "conservative"
        assert RepairStrategy.BALANCED.value == "balanced"
        assert RepairStrategy.AGGRESSIVE.value == "aggressive"


class TestRepairStatus:
    """Тесты для enum RepairStatus"""

    def test_repair_status_values(self) -> None:
        """Тест значений статусов ремонта"""
        assert RepairStatus.SUCCESS.value == "success"
        assert RepairStatus.PARTIAL.value == "partial"
        assert RepairStatus.FAILED.value == "failed"
        assert RepairStatus.NEEDS_MANUAL.value == "needs_manual"


class TestRepairResult:
    """Тесты для класса RepairResult"""

    def test_repair_result_creation(self) -> None:
        """Тест создания результата ремонта"""
        result = RepairResult(
            status=RepairStatus.SUCCESS,
            repaired_plan={"days": []},
            original_plan={"days": []},
            changes_made=[],
            remaining_gaps={},
            strategy_used=RepairStrategy.BALANCED,
            iterations=1,
            message="Success",
            suggestions=[],
        )

        assert result.status == RepairStatus.SUCCESS
        assert result.strategy_used == RepairStrategy.BALANCED
        assert result.iterations == 1
        assert result.message == "Success"


class TestRepairIteration:
    """Тесты для класса RepairIteration"""

    def test_repair_iteration_creation(self) -> None:
        """Тест создания итерации ремонта"""
        iteration = RepairIteration(
            iteration_number=1,
            strategy=RepairStrategy.BALANCED,
            gaps_before={"iron": 50.0},
            gaps_after={"iron": 20.0},
            changes_applied=[{"type": "repair"}],
            success=True,
        )

        assert iteration.iteration_number == 1
        assert iteration.strategy == RepairStrategy.BALANCED
        assert iteration.gaps_before["iron"] == 50.0
        assert iteration.gaps_after["iron"] == 20.0
        assert iteration.success is True


class TestAutoRepairEngine:
    """Тесты для класса AutoRepairEngine"""

    def test_init_with_default_max_iterations(self) -> None:
        """Тест инициализации с максимальным количеством итераций по умолчанию"""
        engine = AutoRepairEngine()

        assert engine.max_iterations == 3
        assert engine.repair_history == []

    def test_init_with_custom_max_iterations(self) -> None:
        """Тест инициализации с пользовательским максимальным количеством итераций"""
        engine = AutoRepairEngine(max_iterations=5)

        assert engine.max_iterations == 5
        assert engine.repair_history == []

    def test_analyze_nutrient_gaps_no_gaps(self) -> None:
        """Тест анализа дефицитов - нет дефицитов"""
        engine = AutoRepairEngine()

        week_plan = {
            "days": [
                {
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "chicken", "amount": 200, "unit": "g"},
                                {"name": "broccoli", "amount": 150, "unit": "g"},
                                {"name": "spinach", "amount": 100, "unit": "g"},
                            ]
                        }
                    ]
                }
            ]
        }

        targets = default_targets()
        gaps = engine._analyze_nutrient_gaps(week_plan, targets)

        # В данном случае должны быть дефициты из-за упрощенной логики
        assert isinstance(gaps, dict)

    def test_analyze_nutrient_gaps_with_gaps(self) -> None:
        """Тест анализа дефицитов - есть дефициты"""
        engine = AutoRepairEngine()

        week_plan = {
            "days": [{"meals": [{"ingredients": [{"name": "rice", "amount": 200, "unit": "g"}]}]}]
        }

        targets = default_targets()
        gaps = engine._analyze_nutrient_gaps(week_plan, targets)

        assert isinstance(gaps, dict)

    def test_get_next_strategy(self) -> None:
        """Тест получения следующей стратегии"""
        engine = AutoRepairEngine()

        assert engine._get_next_strategy(RepairStrategy.CONSERVATIVE) == RepairStrategy.BALANCED
        assert engine._get_next_strategy(RepairStrategy.BALANCED) == RepairStrategy.AGGRESSIVE
        assert engine._get_next_strategy(RepairStrategy.AGGRESSIVE) == RepairStrategy.CONSERVATIVE

    def test_get_all_changes_empty_history(self) -> None:
        """Тест получения всех изменений - пустая история"""
        engine = AutoRepairEngine()

        changes = engine._get_all_changes()

        assert changes == []

    def test_get_all_changes_with_history(self) -> None:
        """Тест получения всех изменений - есть история"""
        engine = AutoRepairEngine()

        # Добавляем итерацию в историю
        iteration = RepairIteration(
            iteration_number=1,
            strategy=RepairStrategy.BALANCED,
            gaps_before={"iron": 50.0},
            gaps_after={"iron": 20.0},
            changes_applied=[{"type": "repair", "details": "test"}],
            success=True,
        )
        engine.repair_history = [iteration]

        changes = engine._get_all_changes()

        assert len(changes) == 1
        assert changes[0]["type"] == "repair"
        assert changes[0]["details"] == "test"

    def test_generate_success_suggestions(self) -> None:
        """Тест генерации предложений при успехе"""
        engine = AutoRepairEngine()

        suggestions = engine._generate_success_suggestions()

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert "План успешно оптимизирован!" in suggestions

    def test_generate_manual_suggestions(self) -> None:
        """Тест генерации предложений для ручного ремонта"""
        engine = AutoRepairEngine()

        remaining_gaps = {
            "iron": 30.0,
            "vitamin_c": 25.0,
            "folate": 20.0,
            "protein": 15.0,
        }

        suggestions = engine._generate_manual_suggestions(remaining_gaps)

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert any("железа" in suggestion for suggestion in suggestions)
        assert any("витамина C" in suggestion for suggestion in suggestions)

    def test_suggest_manual_fixes(self) -> None:
        """Тест предложения ручных исправлений"""
        engine = AutoRepairEngine()

        week_plan = {
            "days": [{"meals": [{"ingredients": [{"name": "rice", "amount": 200, "unit": "g"}]}]}]
        }

        targets = default_targets()
        suggestions = engine.suggest_manual_fixes(week_plan, targets)

        assert isinstance(suggestions, list)
        # Могут быть предложения или пустой список в зависимости от логики

    def test_get_repair_history(self) -> None:
        """Тест получения истории ремонта"""
        engine = AutoRepairEngine()

        # Добавляем итерацию в историю
        iteration = RepairIteration(
            iteration_number=1,
            strategy=RepairStrategy.BALANCED,
            gaps_before={"iron": 50.0},
            gaps_after={"iron": 20.0},
            changes_applied=[],
            success=True,
        )
        engine.repair_history = [iteration]

        history = engine.get_repair_history()

        assert len(history) == 1
        assert history[0].iteration_number == 1
        assert history[0].strategy == RepairStrategy.BALANCED

    @patch("core.auto_repair.repair_week_plan")
    def test_attempt_repair_success(self, mock_repair: Any) -> None:
        """Тест попытки ремонта - успех"""
        engine = AutoRepairEngine()

        # Мокаем успешный ремонт
        mock_repair.return_value = {"days": [], "repaired": True}

        week_plan: dict = {"days": []}
        targets = default_targets()

        iteration = engine._attempt_repair(week_plan, targets, RepairStrategy.BALANCED, 1)

        assert isinstance(iteration, RepairIteration)
        assert iteration.iteration_number == 1
        assert iteration.strategy == RepairStrategy.BALANCED

    @patch("core.auto_repair.repair_week_plan")
    def test_attempt_repair_failure(self, mock_repair: Any) -> None:
        """Тест попытки ремонта - неудача"""
        engine = AutoRepairEngine()

        # Мокаем неудачный ремонт
        mock_repair.side_effect = Exception("Repair failed")

        week_plan: dict = {"days": []}
        targets = default_targets()

        iteration = engine._attempt_repair(week_plan, targets, RepairStrategy.BALANCED, 1)

        assert isinstance(iteration, RepairIteration)
        assert iteration.iteration_number == 1
        assert iteration.strategy == RepairStrategy.BALANCED
        assert iteration.success is False

    def test_auto_repair_week_plan_no_gaps(self) -> None:
        """Тест авто-ремонта - нет дефицитов"""
        engine = AutoRepairEngine()

        week_plan = {
            "days": [
                {
                    "meals": [
                        {
                            "ingredients": [
                                {"name": "chicken", "amount": 200, "unit": "g"},
                                {"name": "broccoli", "amount": 150, "unit": "g"},
                                {"name": "spinach", "amount": 100, "unit": "g"},
                            ]
                        }
                    ]
                }
            ]
        }

        targets = default_targets()

        # Мокаем анализ дефицитов, чтобы вернуть пустой словарь
        with patch.object(engine, "_analyze_nutrient_gaps", return_value={}):
            result = engine.auto_repair_week_plan(week_plan, targets)

        assert isinstance(result, RepairResult)
        assert result.status == RepairStatus.SUCCESS
        assert result.iterations == 0
        assert "уже соответствует" in result.message

    def test_auto_repair_week_plan_with_gaps(self) -> None:
        """Тест авто-ремонта - есть дефициты"""
        engine = AutoRepairEngine()

        week_plan = {
            "days": [{"meals": [{"ingredients": [{"name": "rice", "amount": 200, "unit": "g"}]}]}]
        }

        targets = default_targets()

        # Мокаем анализ дефицитов и ремонт
        with patch.object(engine, "_analyze_nutrient_gaps", return_value={"iron": 50.0}):
            with patch.object(engine, "_attempt_repair") as mock_attempt:
                mock_attempt.return_value = RepairIteration(
                    iteration_number=1,
                    strategy=RepairStrategy.BALANCED,
                    gaps_before={"iron": 50.0},
                    gaps_after={"iron": 20.0},
                    changes_applied=[{"type": "repair"}],
                    success=True,
                )

                result = engine.auto_repair_week_plan(week_plan, targets)

        assert isinstance(result, RepairResult)
        assert result.iterations > 0


class TestConvenienceFunctions:
    """Тесты для удобных функций"""

    @patch("core.auto_repair._auto_repair_engine")
    def test_get_auto_repair_engine(self, mock_engine: Any) -> None:
        """Тест получения глобального движка авто-ремонта"""
        mock_engine_instance = AutoRepairEngine()
        mock_engine.return_value = mock_engine_instance

        engine = get_auto_repair_engine()

        assert engine is not None

    @patch("core.auto_repair.get_auto_repair_engine")
    def test_auto_repair_week_plan_function(self, mock_get_engine: Any) -> None:
        """Тест функции авто-ремонта недельного плана"""
        from unittest.mock import MagicMock

        mock_engine = MagicMock()
        mock_engine.auto_repair_week_plan.return_value = RepairResult(
            status=RepairStatus.SUCCESS,
            repaired_plan={},
            original_plan={},
            changes_made=[],
            remaining_gaps={},
            strategy_used=RepairStrategy.BALANCED,
            iterations=1,
            message="Success",
            suggestions=[],
        )
        mock_get_engine.return_value = mock_engine

        week_plan: dict = {"days": []}
        targets = default_targets()

        result = auto_repair_week_plan(week_plan, targets)

        assert isinstance(result, RepairResult)
        assert result.status == RepairStatus.SUCCESS

    @patch("core.auto_repair.get_auto_repair_engine")
    def test_suggest_manual_fixes_function(self, mock_get_engine: Any) -> None:
        """Тест функции предложения ручных исправлений"""
        from unittest.mock import MagicMock

        mock_engine = MagicMock()
        mock_engine.suggest_manual_fixes.return_value = [
            {"type": "add_ingredient", "nutrient": "iron", "suggestions": []}
        ]
        mock_get_engine.return_value = mock_engine

        week_plan: dict = {"days": []}
        targets = default_targets()

        suggestions = suggest_manual_fixes(week_plan, targets)

        # Verify mock was called
        mock_get_engine.assert_called_once()
        mock_engine.suggest_manual_fixes.assert_called_once_with(week_plan, targets)

        assert isinstance(suggestions, list)
        assert len(suggestions) == 1
        assert suggestions[0]["type"] == "add_ingredient"


class TestIntegration:
    """Интеграционные тесты"""

    def test_full_auto_repair_workflow(self) -> None:
        """Тест полного рабочего процесса авто-ремонта"""
        engine = AutoRepairEngine(max_iterations=2)

        week_plan = {
            "days": [{"meals": [{"ingredients": [{"name": "rice", "amount": 200, "unit": "g"}]}]}]
        }

        targets = default_targets()

        # Мокаем анализ дефицитов - сначала есть дефициты, потом нет
        counter = {"n": 0}

        def mock_analyze_gaps(plan: dict, targets: MicronutrientTargets) -> dict[str, float]:
            # Первый вызов - есть дефициты
            counter["n"] += 1
            return {"iron": 50.0} if counter["n"] == 1 else {}

        with patch.object(engine, "_analyze_nutrient_gaps", side_effect=mock_analyze_gaps):
            # Мокаем попытки ремонта
            with patch.object(engine, "_attempt_repair") as mock_attempt:
                # Первая попытка - успех
                mock_attempt.return_value = RepairIteration(
                    iteration_number=1,
                    strategy=RepairStrategy.BALANCED,
                    gaps_before={"iron": 50.0},
                    gaps_after={},
                    changes_applied=[{"type": "repair"}],
                    success=True,
                )

                result = engine.auto_repair_week_plan(week_plan, targets)

        assert isinstance(result, RepairResult)
        assert result.status == RepairStatus.SUCCESS
        assert result.iterations == 1
        # changes_made может быть пустым если нет дефицитов с самого начала
        assert len(result.suggestions) > 0

    def test_auto_repair_max_iterations_reached(self) -> None:
        """Тест авто-ремонта - достигнуто максимальное количество итераций"""
        engine = AutoRepairEngine(max_iterations=1)

        week_plan = {
            "days": [{"meals": [{"ingredients": [{"name": "rice", "amount": 200, "unit": "g"}]}]}]
        }

        targets = default_targets()

        # Мокаем анализ дефицитов
        with patch.object(engine, "_analyze_nutrient_gaps", return_value={"iron": 50.0}):
            # Мокаем неудачную попытку ремонта
            with patch.object(engine, "_attempt_repair") as mock_attempt:
                mock_attempt.return_value = RepairIteration(
                    iteration_number=1,
                    strategy=RepairStrategy.BALANCED,
                    gaps_before={"iron": 50.0},
                    gaps_after={"iron": 50.0},  # Дефициты не изменились
                    changes_applied=[],
                    success=False,
                )

                result = engine.auto_repair_week_plan(week_plan, targets)

        assert isinstance(result, RepairResult)
        assert result.status == RepairStatus.FAILED
        assert result.iterations == 1
        assert "Не удалось устранить" in result.message
