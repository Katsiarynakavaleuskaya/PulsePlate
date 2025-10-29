#!/usr/bin/env python3
"""
Обновленный анализ текущих проблем PulsePlate с использованием теоремы Байеса.
"""

import json
from pathlib import Path
from typing import Any, Dict, List
from core.bayesian_test_analyzer import (
    BayesianTestAnalyzer,
    TestExecution,
    TestResult,
    ErrorType,
    TestCategory,
    diagnose_test_failure,
)


class CurrentIssuesAnalyzer:
    """Анализатор текущих проблем с использованием байесовской системы."""

    def __init__(self) -> None:
        """Инициализировать анализатор."""
        self.analyzer = BayesianTestAnalyzer()

        # Обновленные известные проблемы
        self.known_issues = [
            {
                "test_name": "test_agent_system_simple.py::TestAgentOrchestrator::test_execute_single_task_error",
                "category": "agent_system",
                "error_message": "assert True is False - AgentResult(success=True, data={'error': \"object Mock can't be used in 'await' expression\"})",
                "context": {
                    "is_async": True,
                    "has_mocks": True,
                    "coverage_related": False,
                    "recent_changes": True,
                    "mock_error": True,
                },
            },
            {
                "test_name": "test_agent_system_simple.py::TestAgentOrchestrator::test_execute_sequential_tasks",
                "category": "agent_system",
                "error_message": "assert 1 == 2 - len(results) == 1 instead of 2, critical task failed",
                "context": {
                    "is_async": True,
                    "has_mocks": True,
                    "coverage_related": False,
                    "recent_changes": True,
                    "workflow_error": True,
                },
            },
            {
                "test_name": "test_agent_system_simple.py::TestAgentOrchestrator::test_execute_parallel_tasks",
                "category": "agent_system",
                "error_message": "assert False - all(result.success for result in results) failed",
                "context": {
                    "is_async": True,
                    "has_mocks": True,
                    "coverage_related": False,
                    "recent_changes": True,
                    "parallel_execution_error": True,
                },
            },
        ]

    def analyze_all_issues(self) -> Dict[str, Any]:
        """Анализировать все известные проблемы."""
        print("🔍 Анализ текущих проблем PulsePlate с использованием теоремы Байеса...")

        analysis_results = []

        for issue in self.known_issues:
            print(f"\n📋 Анализ: {issue['test_name']}")

            # Диагностировать проблему
            diagnosis = diagnose_test_failure(
                issue["test_name"], issue["error_message"], issue["context"]
            )

            # Записать в историю для обучения
            self._record_issue_as_test_execution(issue)

            analysis_results.append(
                {
                    "issue": issue,
                    "diagnosis": {
                        "most_likely_cause": diagnosis.most_likely_cause,
                        "probability": diagnosis.probability,
                        "confidence": diagnosis.confidence,
                        "evidence": diagnosis.evidence,
                        "recommendations": diagnosis.recommendations,
                        "alternative_causes": diagnosis.alternative_causes,
                    },
                }
            )

        return {
            "total_issues": len(self.known_issues),
            "analysis_results": analysis_results,
            "summary": self._generate_summary(analysis_results),
        }

    def _record_issue_as_test_execution(self, issue: dict) -> None:
        """Записать проблему как выполнение теста для обучения."""
        # Определить тип ошибки
        error_type = self._classify_error_type(issue["error_message"])

        # Определить категорию теста
        category = self._map_category(issue["category"])

        execution = TestExecution(
            test_name=issue["test_name"],
            category=category,
            result=TestResult.FAILED,
            error_type=error_type,
            error_message=issue["error_message"],
            file_path=issue["test_name"].split("::")[0],
            execution_time=1.0,
        )

        self.analyzer.record_test_execution(execution)

    def _classify_error_type(self, error_message: str) -> ErrorType:
        """Классифицировать тип ошибки."""
        error_lower = error_message.lower()

        if "mock" in error_lower and "await" in error_lower:
            return ErrorType.ASYNC_ERROR
        elif "assert" in error_lower and "false" in error_lower:
            return ErrorType.ASSERTION_ERROR
        elif "attribute" in error_lower and "get" in error_lower:
            return ErrorType.ATTRIBUTE_ERROR
        elif "workflow" in error_lower or "sequential" in error_lower:
            return ErrorType.RUNTIME_ERROR
        elif "parallel" in error_lower:
            return ErrorType.RUNTIME_ERROR
        else:
            return ErrorType.ASSERTION_ERROR

    def _map_category(self, category: str) -> TestCategory:
        """Сопоставить категорию с TestCategory."""
        category_mapping = {
            "unit": TestCategory.UNIT,
            "integration": TestCategory.INTEGRATION,
            "e2e": TestCategory.E2E,
            "performance": TestCategory.PERFORMANCE,
            "coverage": TestCategory.COVERAGE,
            "agent_system": TestCategory.INTEGRATION,
        }
        return category_mapping.get(category, TestCategory.UNIT)

    def _generate_summary(self, analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Генерировать сводку анализа."""
        error_types = {}
        categories = {}
        avg_confidence = 0.0

        for result in analysis_results:
            diagnosis = result["diagnosis"]
            issue = result["issue"]

            # Типы ошибок
            error_type = diagnosis["most_likely_cause"]
            error_types[error_type] = error_types.get(error_type, 0) + 1

            # Категории
            category = issue["category"]
            categories[category] = categories.get(category, 0) + 1

            # Уверенность
            avg_confidence += diagnosis["confidence"]

        avg_confidence /= len(analysis_results) if analysis_results else 1

        # Найти наиболее проблемные области
        most_problematic_category = (
            max(categories.items(), key=lambda x: x[1]) if categories else ("none", 0)
        )
        most_common_error = (
            max(error_types.items(), key=lambda x: x[1]) if error_types else ("none", 0)
        )

        return {
            "error_types": error_types,
            "categories": categories,
            "most_problematic_category": most_problematic_category,
            "most_common_error": most_common_error,
            "average_confidence": avg_confidence,
            "total_issues": len(analysis_results),
        }

    def print_analysis_report(self, analysis: dict) -> None:
        """Вывести отчет об анализе."""
        print("\n" + "=" * 80)
        print("🧠 БАЙЕСОВСКИЙ АНАЛИЗ ТЕКУЩИХ ПРОБЛЕМ PULSEPLATE")
        print("=" * 80)

        summary = analysis["summary"]
        print(f"📊 Всего проблем: {summary['total_issues']}")
        print(f"🎯 Средняя уверенность: {summary['average_confidence']:.2%}")
        print(
            f"🔥 Наиболее проблемная область: {summary['most_problematic_category'][0]} ({summary['most_problematic_category'][1]} проблем)"
        )
        print(
            f"⚠️ Наиболее частый тип ошибки: {summary['most_common_error'][0]} ({summary['most_common_error'][1]} раз)"
        )

        print("\n" + "-" * 80)
        print("📋 ДЕТАЛЬНЫЙ АНАЛИЗ ПРОБЛЕМ")
        print("-" * 80)

        for i, result in enumerate(analysis["analysis_results"], 1):
            issue = result["issue"]
            diagnosis = result["diagnosis"]

            print(f"\n{i}. {issue['test_name']}")
            print(f"   Категория: {issue['category']}")
            print(f"   Ошибка: {issue['error_message'][:100]}...")
            print(f"   🎯 Наиболее вероятная причина: {diagnosis['most_likely_cause']}")
            print(f"   📊 Вероятность: {diagnosis['probability']:.2%}")
            print(f"   🎲 Уверенность: {diagnosis['confidence']:.2%}")

            print("   💡 Рекомендации:")
            for recommendation in diagnosis["recommendations"]:
                print(f"      • {recommendation}")

        print("\n" + "-" * 80)
        print("🎯 ОБЩИЕ РЕКОМЕНДАЦИИ")
        print("-" * 80)

        # Рекомендации на основе анализа
        recommendations = []

        if summary["most_common_error"][0] == "async_error":
            recommendations.append(
                "⚡ Проблемы с асинхронными моками - используйте AsyncMock правильно"
            )

        if summary["most_common_error"][0] == "assertion_error":
            recommendations.append(
                "🔍 Проблемы с утверждениями - проверьте логику тестов и ожидаемые значения"
            )

        if summary["most_problematic_category"][0] == "agent_system":
            recommendations.append(
                "🤖 Проблемы с агентной системой - проверьте моки и асинхронную логику"
            )

        if summary["average_confidence"] < 0.7:
            recommendations.append(
                "📚 Низкая уверенность - добавьте больше тестовых данных для улучшения диагностики"
            )

        for recommendation in recommendations:
            print(f"• {recommendation}")

        print("\n" + "=" * 80)

    def generate_fix_suggestions(self) -> List[Dict[str, Any]]:
        """Генерировать конкретные предложения по исправлению."""
        suggestions = []

        # Анализ паттернов ошибок
        for issue in self.known_issues:
            if "Mock can't be used in 'await' expression" in issue["error_message"]:
                suggestions.append(
                    {
                        "file": "tests/test_agent_system_simple.py",
                        "issue": "Неправильное использование Mock в асинхронном контексте",
                        "fix": "Заменить Mock на AsyncMock для асинхронных методов",
                        "code": "mock_llm.generate = AsyncMock(return_value='...')",
                    }
                )

            elif "assert 1 == 2" in issue["error_message"]:
                suggestions.append(
                    {
                        "file": "tests/test_agent_system_simple.py",
                        "issue": "Критический таск останавливает выполнение последовательных задач",
                        "fix": "Исправить логику критических задач или моки",
                        "code": "task.priority = 3  # Сделать таск некритическим",
                    }
                )

            elif "all(result.success" in issue["error_message"]:
                suggestions.append(
                    {
                        "file": "tests/test_agent_system_simple.py",
                        "issue": "Параллельные задачи падают из-за неправильных моков",
                        "fix": "Исправить моки для всех агентов в параллельном выполнении",
                        "code": "for agent in orchestrator.agents.values(): agent.llm_provider.generate = AsyncMock(...)",
                    }
                )

        return suggestions

    def print_fix_suggestions(self, suggestions: List[Dict[str, Any]]) -> None:
        """Вывести предложения по исправлению."""
        print("\n" + "=" * 80)
        print("🔧 КОНКРЕТНЫЕ ПРЕДЛОЖЕНИЯ ПО ИСПРАВЛЕНИЮ")
        print("=" * 80)

        for i, suggestion in enumerate(suggestions, 1):
            print(f"\n{i}. Файл: {suggestion['file']}")
            print(f"   Проблема: {suggestion['issue']}")
            print(f"   Решение: {suggestion['fix']}")
            print(f"   Код: {suggestion['code']}")

        print("\n" + "=" * 80)


def main() -> None:
    """Главная функция."""
    analyzer = CurrentIssuesAnalyzer()

    # Анализировать все проблемы
    analysis = analyzer.analyze_all_issues()

    # Вывести отчет
    analyzer.print_analysis_report(analysis)

    # Генерировать предложения по исправлению
    suggestions = analyzer.generate_fix_suggestions()
    analyzer.print_fix_suggestions(suggestions)

    # Сохранить результаты
    results_file = Path("bayesian_analysis_results_updated.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n💾 Результаты анализа сохранены в {results_file}")


if __name__ == "__main__":
    main()
