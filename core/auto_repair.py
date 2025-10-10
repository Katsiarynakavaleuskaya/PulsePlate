"""
RU: Модуль для авто-ремонта недельных планов с UX-петлей.
EN: Module for auto-repair of weekly meal plans with UX loop.

Sprint 5: Auto-repair недели (UX-петля)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from core.menu_engine import repair_week_plan
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
    repaired_plan: dict
    original_plan: dict
    changes_made: list[dict]
    remaining_gaps: dict[str, float]
    strategy_used: RepairStrategy
    iterations: int
    message: str
    suggestions: list[str]


@dataclass
class RepairIteration:
    """Итерация ремонта"""

    iteration_number: int
    strategy: RepairStrategy
    gaps_before: dict[str, float]
    gaps_after: dict[str, float]
    changes_applied: list[dict]
    success: bool


class AutoRepairEngine:
    """Движок авто-ремонта с UX-петлей"""

    def __init__(self, max_iterations: int = 3):
        self.max_iterations = max_iterations
        self.repair_history: list[RepairIteration] = []

    def auto_repair_week_plan(
        self,
        week_plan: dict,
        targets: MicronutrientTargets,
        initial_strategy: RepairStrategy = RepairStrategy.BALANCED,
        user_preferences: dict | None = None,
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
        self, week_plan: dict, targets: MicronutrientTargets
    ) -> dict[str, float]:
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

    def _attempt_repair(
        self,
        week_plan: dict,
        targets: MicronutrientTargets,
        strategy: RepairStrategy,
        iteration: int,
    ) -> RepairIteration:
        """Пытается отремонтировать план с заданной стратегией"""
        gaps_before = self._analyze_nutrient_gaps(week_plan, targets)

        try:
            # Используем существующую функцию ремонта
            repaired_plan = repair_week_plan(week_plan, targets, strategy.value)  # type: ignore

            gaps_after = self._analyze_nutrient_gaps(repaired_plan, targets)  # type: ignore

            changes = [
                {
                    "type": "repair",
                    "strategy": strategy.value,
                    "iteration": iteration,
                    "repaired_plan": repaired_plan,
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

        except Exception:
            # Если ремонт не удался
            return RepairIteration(
                iteration_number=iteration,
                strategy=strategy,
                gaps_before=gaps_before,
                gaps_after=gaps_before,  # Дефициты не изменились
                changes_applied=[],
                success=False,
            )

    def _get_next_strategy(self, current_strategy: RepairStrategy) -> RepairStrategy:
        """Получает следующую стратегию ремонта"""
        if current_strategy == RepairStrategy.CONSERVATIVE:
            return RepairStrategy.BALANCED
        elif current_strategy == RepairStrategy.BALANCED:
            return RepairStrategy.AGGRESSIVE
        else:  # AGGRESSIVE
            return RepairStrategy.CONSERVATIVE

    def _get_all_changes(self) -> list[dict]:
        """Получает все изменения из истории ремонта"""
        all_changes = []
        for iteration in self.repair_history:
            all_changes.extend(iteration.changes_applied)
        return all_changes

    def _generate_success_suggestions(self) -> list[str]:
        """Генерирует предложения при успешном ремонте"""
        return [
            "План успешно оптимизирован!",
            "Рекомендуется сохранить изменения",
            "Можно экспортировать обновленный план",
            "Проверьте список покупок для новых ингредиентов",
        ]

    def _generate_manual_suggestions(self, remaining_gaps: dict[str, float]) -> list[str]:
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

        return suggestions

    def get_repair_history(self) -> list[RepairIteration]:
        """Возвращает историю ремонта"""
        return self.repair_history

    def suggest_manual_fixes(self, week_plan: dict, targets: MicronutrientTargets) -> list[dict]:
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
    week_plan: dict,
    targets: MicronutrientTargets,
    strategy: RepairStrategy = RepairStrategy.BALANCED,
    user_preferences: dict | None = None,
) -> RepairResult:
    """Авто-ремонт недельного плана"""
    engine = get_auto_repair_engine()
    return engine.auto_repair_week_plan(week_plan, targets, strategy, user_preferences)


def suggest_manual_fixes(week_plan: dict, targets: MicronutrientTargets) -> list[dict]:
    """Предлагает ручные исправления"""
    engine = get_auto_repair_engine()
    return engine.suggest_manual_fixes(week_plan, targets)
