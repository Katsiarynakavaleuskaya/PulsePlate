# -*- coding: utf-8 -*-
"""
RU: Модуль для авто-ремонта недельных планов с UX-петлей.
EN: Module for auto-repair of weekly meal plans with UX loop.

Sprint 5: Auto-repair недели (UX-петля)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from core.menu_engine import repair_week_plan
from core.menu_types import DayMenu, WeekMenu
from core.targets import MicronutrientTargets


class RepairStrategy(Enum):
    """Стратегии ремонта"""

    CONSERVATIVE = "conservative"  # Минимальные изменения
    BALANCED = "balanced"  # Сбалансированный подход
    AGGRESSIVE = "aggressive"  # Максимальные изменения


class RepairStatus(Enum):
    """Статусы ремонта"""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    NEEDS_MANUAL = "needs_manual"


@dataclass
class RepairResult:
    """Результат ремонта"""

    status: RepairStatus
    repaired_plan: Dict
    original_plan: Dict
    changes_made: List[Dict]
    remaining_gaps: Dict[str, float]
    strategy_used: RepairStrategy
    iterations: int
    message: str
    suggestions: List[str]


@dataclass
class RepairIteration:
    """Итерация ремонта"""

    iteration_number: int
    strategy: RepairStrategy
    gaps_before: Dict[str, float]
    gaps_after: Dict[str, float]
    changes_applied: List[Dict]
    success: bool


class AutoRepairEngine:
    """Движок авто-ремонта с UX-петлей"""

    def __init__(self, max_iterations: int = 3) -> None:
        self.max_iterations = max_iterations
        self.repair_history: List[RepairIteration] = []

    def auto_repair_week_plan(
        self,
        week_plan: Dict,
        targets: MicronutrientTargets,
        initial_strategy: RepairStrategy = RepairStrategy.BALANCED,
        user_preferences: Optional[Dict] = None,
    ) -> RepairResult:
        """
        Авто-ремонт недельного плана с UX-петлей

        Args:
            week_plan: Недельный план питания
            targets: Цели по микронутриентам
            initial_strategy: Начальная стратегия ремонта
            user_preferences: Предпочтения пользователя

        Returns:
            Результат ремонта с историей итераций
        """
        self.repair_history = []
        original_plan = week_plan.copy()

        # Анализируем начальные дефициты
        initial_gaps = self._analyze_nutrient_gaps(week_plan, targets)

        if not initial_gaps:
            return RepairResult(
                status=RepairStatus.SUCCESS,
                repaired_plan=week_plan,
                original_plan=original_plan,
                changes_made=[],
                remaining_gaps={},
                strategy_used=initial_strategy,
                iterations=0,
                message="План уже соответствует целям",
                suggestions=[],
            )

        # Начинаем итеративный процесс ремонта
        current_plan = week_plan.copy()
        current_strategy = initial_strategy
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1

            # Анализируем текущие дефициты
            current_gaps = self._analyze_nutrient_gaps(current_plan, targets)

            if not current_gaps:
                # Успех! Все дефициты устранены
                return RepairResult(
                    status=RepairStatus.SUCCESS,
                    repaired_plan=current_plan,
                    original_plan=original_plan,
                    changes_made=self._get_all_changes(),
                    remaining_gaps={},
                    strategy_used=current_strategy,
                    iterations=iteration,
                    message=f"План успешно отремонтирован за {iteration} итераций",
                    suggestions=self._generate_success_suggestions(),
                )

            # Пытаемся отремонтировать с текущей стратегией
            repair_iteration = self._attempt_repair(
                current_plan, targets, current_strategy, iteration
            )

            self.repair_history.append(repair_iteration)

            if repair_iteration.success:
                current_plan = repair_iteration.changes_applied[0].get(
                    "repaired_plan", current_plan
                )

                # Проверяем, нужно ли изменить стратегию
                new_gaps = self._analyze_nutrient_gaps(current_plan, targets)
                if len(new_gaps) < len(current_gaps):
                    # Прогресс есть, продолжаем с той же стратегией
                    continue
                else:
                    # Прогресса нет, меняем стратегию
                    current_strategy = self._get_next_strategy(current_strategy)
            else:
                # Ремонт не удался, пробуем другую стратегию
                current_strategy = self._get_next_strategy(current_strategy)

        # Достигли максимального количества итераций
        final_gaps = self._analyze_nutrient_gaps(current_plan, targets)

        if len(final_gaps) < len(initial_gaps):
            status = RepairStatus.PARTIAL
            fixed = len(initial_gaps) - len(final_gaps)
            total = len(initial_gaps)
            message = f"Частичный ремонт: устранено {fixed} из {total} дефицитов"
        else:
            status = RepairStatus.FAILED
            message = "Не удалось устранить дефициты автоматически"

        return RepairResult(
            status=status,
            repaired_plan=current_plan,
            original_plan=original_plan,
            changes_made=self._get_all_changes(),
            remaining_gaps=final_gaps,
            strategy_used=current_strategy,
            iterations=iteration,
            message=message,
            suggestions=self._generate_manual_suggestions(final_gaps),
        )

    def _analyze_nutrient_gaps(
        self, week_plan: Dict, targets: MicronutrientTargets
    ) -> Dict[str, float]:
        """Анализирует дефициты микронутриентов"""
        # Упрощенная логика анализа дефицитов
        # В реальном приложении здесь был бы полный анализ плана

        gaps = {}

        # Примерные дефициты для демонстрации
        if "days" in week_plan:
            # Анализируем каждый день
            for day in week_plan["days"]:
                if "meals" in day:
                    for meal in day["meals"]:
                        # Простая логика: если мало овощей, то дефицит витаминов
                        if "ingredients" in meal:
                            vegetables_count = sum(
                                1
                                for ing in meal["ingredients"]
                                if "vegetable" in ing.get("name", "").lower()
                            )
                            if vegetables_count < 2:
                                gaps["vitamin_c"] = 50.0
                                gaps["folate"] = 30.0

                        # Если мало мяса/рыбы, то дефицит белка и железа
                        protein_count = sum(
                            1
                            for ing in meal["ingredients"]
                            if any(
                                word in ing.get("name", "").lower()
                                for word in ["meat", "chicken", "fish", "beef"]
                            )
                        )
                        if protein_count == 0:
                            gaps["iron"] = 40.0
                            gaps["protein"] = 20.0

        return gaps

    def _dict_to_week_menu(self, plan_dict: Dict[str, Any]) -> WeekMenu:
        """Convert dict representation to WeekMenu dataclass."""
        # Convert daily_menus from dict to DayMenu objects
        daily_menus: List[DayMenu] = []
        for day_dict in plan_dict.get("daily_menus", []):
            # DayMenu requires: date, meals, total_nutrients, targets, coverage, recommendations, estimated_cost
            # Use targets from day_dict if present
            targets = day_dict.get("targets")
            # If targets is None, we'll use type: ignore since DayMenu requires it
            # In practice, day_dict should always have targets from the original plan

            day_menu = DayMenu(
                date=day_dict.get("date", ""),
                meals=day_dict.get("meals", []),
                total_nutrients=day_dict.get("total_nutrients", {}),
                targets=targets,
                coverage=day_dict.get("coverage", {}),
                recommendations=day_dict.get("recommendations", []),
                estimated_cost=day_dict.get("estimated_cost", 0.0),
            )
            daily_menus.append(day_menu)

        return WeekMenu(
            week_start=plan_dict.get("week_start", ""),
            daily_menus=daily_menus,
            weekly_coverage=plan_dict.get("weekly_coverage", {}),
            shopping_list=plan_dict.get("shopping_list", {}),
            total_cost=plan_dict.get("total_cost", 0.0),
            adherence_score=plan_dict.get("adherence_score", 0.0),
        )

    def _attempt_repair(
        self,
        week_plan: Union[Dict[str, Any], WeekMenu],
        targets: MicronutrientTargets,
        strategy: RepairStrategy,
        iteration: int,
    ) -> RepairIteration:
        """Пытается отремонтировать план с заданной стратегией"""
        # Convert WeekMenu to dict for gap analysis
        plan_dict: Dict[str, Any] = (
            vars(week_plan) if isinstance(week_plan, WeekMenu) else week_plan
        )
        try:
            gaps_before = self._analyze_nutrient_gaps(plan_dict, targets)
        except Exception as exc:
            # Log for diagnostics - gap analysis failure before repair
            import logging

            logging.getLogger(__name__).warning(
                "Gap analysis failed before repair attempt %d: %s", iteration, exc
            )
            return RepairIteration(
                iteration_number=iteration,
                strategy=strategy,
                gaps_before={},
                gaps_after={},
                changes_applied=[
                    {
                        "type": "error",
                        "strategy": strategy.value,
                        "iteration": iteration,
                        "error": f"Pre-repair gap analysis failed: {exc}",
                    }
                ],
                success=False,
            )

        # Attempt repair and treat any errors as hard failure
        try:
            # Convert dict to WeekMenu if needed
            week_menu: WeekMenu
            if isinstance(week_plan, dict):
                week_menu = self._dict_to_week_menu(week_plan)
            else:
                week_menu = week_plan
            repaired_plan = repair_week_plan(week_menu, targets, strategy.value)
        except Exception as exc:
            return RepairIteration(
                iteration_number=iteration,
                strategy=strategy,
                gaps_before=gaps_before,
                gaps_after=gaps_before,
                changes_applied=[
                    {
                        "type": "error",
                        "strategy": strategy.value,
                        "iteration": iteration,
                        "error": f"Repair failed: {exc}",
                    }
                ],
                success=False,
            )

        try:
            # repaired_plan is always WeekMenu from repair_week_plan
            # Convert to dict for gap analysis
            repaired_dict: Dict[str, Any] = vars(repaired_plan)
            gaps_after = self._analyze_nutrient_gaps(repaired_dict, targets)
        except Exception as exc:
            # Gap analysis failed after repair - treat as failure, not success
            return RepairIteration(
                iteration_number=iteration,
                strategy=strategy,
                gaps_before=gaps_before,
                gaps_after=gaps_before,  # Keep original gaps to show no improvement
                changes_applied=[
                    {
                        "type": "error",
                        "strategy": strategy.value,
                        "iteration": iteration,
                        "error": f"Failed to analyze gaps after repair: {str(exc)}",
                        "fallback": "gap_analysis_error",
                    }
                ],
                success=False,
            )

        # Serialize repaired plan for changes log
        # repaired_plan is always WeekMenu from repair_week_plan
        from dataclasses import asdict

        repaired_serialized: Dict[str, Any] = asdict(repaired_plan)

        changes = [
            {
                "type": "repair",
                "strategy": strategy.value,
                "iteration": iteration,
                "repaired_plan": repaired_serialized,
                "gaps_before": gaps_before,
                "gaps_after": gaps_after,
            }
        ]

        success = len(gaps_after) < len(gaps_before)

        return RepairIteration(
            iteration_number=iteration,
            strategy=strategy,
            gaps_before=gaps_before,
            gaps_after=gaps_after,
            changes_applied=changes,
            success=success,
        )

    def _get_next_strategy(self, current_strategy: RepairStrategy) -> RepairStrategy:
        """Получает следующую стратегию ремонта"""
        if current_strategy == RepairStrategy.CONSERVATIVE:
            return RepairStrategy.BALANCED
        elif current_strategy == RepairStrategy.BALANCED:
            return RepairStrategy.AGGRESSIVE
        else:  # AGGRESSIVE
            return RepairStrategy.CONSERVATIVE

    def _get_all_changes(self) -> List[Dict]:
        """Получает все изменения из истории ремонта"""
        all_changes = []
        for iteration in self.repair_history:
            all_changes.extend(iteration.changes_applied)
        return all_changes

    def _generate_success_suggestions(self) -> List[str]:
        """Генерирует предложения при успешном ремонте"""
        return [
            "План успешно оптимизирован!",
            "Рекомендуется сохранить изменения",
            "Можно экспортировать обновленный план",
            "Проверьте список покупок для новых ингредиентов",
        ]

    def _generate_manual_suggestions(self, remaining_gaps: Dict[str, float]) -> List[str]:
        """Генерирует предложения для ручного ремонта"""
        suggestions = [
            "Автоматический ремонт не смог устранить все дефициты",
            "Рекомендуется ручная корректировка плана",
        ]

        if "iron" in remaining_gaps:
            suggestions.append("Добавьте больше мяса, рыбы или бобовых для железа")

        if "vitamin_c" in remaining_gaps:
            suggestions.append("Увеличьте количество овощей и фруктов для витамина C")

        if "folate" in remaining_gaps:
            suggestions.append("Добавьте листовые овощи для фолиевой кислоты")

        if "protein" in remaining_gaps:
            suggestions.append("Увеличьте порции белковых продуктов")

        # Если нет специфических предложений, добавляем общее на основе реальных дефицитов
        if len(suggestions) == 2:  # Только базовые сообщения
            missing = ", ".join(sorted(remaining_gaps.keys()))
            if missing:
                suggestions.append(
                    f"Обнаружены дефициты: {missing}. "
                    "Подберите продукты или проконсультируйтесь с диетологом."
                )
            else:
                suggestions.append(
                    "Недостаточно данных для точного анализа — поддерживайте разнообразный рацион."
                )

        return suggestions

    def get_repair_history(self) -> List[RepairIteration]:
        """Возвращает историю ремонта"""
        return self.repair_history

    def suggest_manual_fixes(self, week_plan: Dict, targets: MicronutrientTargets) -> List[Dict]:
        """Предлагает ручные исправления для плана"""
        gaps = self._analyze_nutrient_gaps(week_plan, targets)
        suggestions = []

        for nutrient, deficit in gaps.items():
            if nutrient == "iron":
                suggestions.append(
                    {
                        "type": "add_ingredient",
                        "nutrient": nutrient,
                        "suggestions": [
                            {"name": "beef", "amount": 150, "unit": "g"},
                            {"name": "salmon", "amount": 200, "unit": "g"},
                            {"name": "lentils", "amount": 100, "unit": "g"},
                        ],
                        "reason": f"Дефицит {nutrient}: {deficit}%",
                    }
                )
            elif nutrient == "vitamin_c":
                suggestions.append(
                    {
                        "type": "add_ingredient",
                        "nutrient": nutrient,
                        "suggestions": [
                            {"name": "bell peppers", "amount": 100, "unit": "g"},
                            {"name": "broccoli", "amount": 150, "unit": "g"},
                            {"name": "oranges", "amount": 200, "unit": "g"},
                        ],
                        "reason": f"Дефицит {nutrient}: {deficit}%",
                    }
                )
            elif nutrient == "folate":
                suggestions.append(
                    {
                        "type": "add_ingredient",
                        "nutrient": nutrient,
                        "suggestions": [
                            {"name": "spinach", "amount": 100, "unit": "g"},
                            {"name": "asparagus", "amount": 150, "unit": "g"},
                            {"name": "avocado", "amount": 100, "unit": "g"},
                        ],
                        "reason": f"Дефицит {nutrient}: {deficit}%",
                    }
                )

        if not suggestions:
            suggestions.append(
                {
                    "type": "info",
                    "nutrient": "general_balance",
                    "suggestions": [],
                    "reason": (
                        "Явных дефицитов не обнаружено. Поддерживайте разнообразный рацион "
                        "и при необходимости консультируйтесь со специалистом."
                    ),
                }
            )

        return suggestions


# Глобальный экземпляр движка ремонта
_auto_repair_engine = None


def get_auto_repair_engine() -> AutoRepairEngine:
    """Получает глобальный экземпляр движка авто-ремонта"""
    global _auto_repair_engine
    if _auto_repair_engine is None:
        _auto_repair_engine = AutoRepairEngine()
    return _auto_repair_engine


# Удобные функции для быстрого доступа
def auto_repair_week_plan(
    week_plan: Dict,
    targets: MicronutrientTargets,
    strategy: RepairStrategy = RepairStrategy.BALANCED,
    user_preferences: Optional[Dict] = None,
) -> RepairResult:
    """Авто-ремонт недельного плана"""
    engine = get_auto_repair_engine()
    return engine.auto_repair_week_plan(week_plan, targets, strategy, user_preferences)


def suggest_manual_fixes(week_plan: Dict, targets: MicronutrientTargets) -> List[Dict]:
    """Предлагает ручные исправления"""
    engine = get_auto_repair_engine()
    return engine.suggest_manual_fixes(week_plan, targets)
