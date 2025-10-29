#!/usr/bin/env python3
"""
Анализ текущих проблем в PulsePlate с использованием байесовской диагностики.

Этот скрипт анализирует известные проблемы и предоставляет
интеллектуальные рекомендации по их решению.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any
import json

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.bayesian_test_analyzer import (
    BayesianTestAnalyzer,
    TestExecution,
    TestResult,
    ErrorType,
    TestCategory,
    diagnose_test_failure,
)


class CurrentIssuesAnalyzer:
    """Анализатор текущих проблем PulsePlate."""

    def __init__(self) -> None:
        """Инициализация анализатора."""
        self.analyzer = BayesianTestAnalyzer()
        self.known_issues = self._load_known_issues()

    def _load_known_issues(self) -> List[Dict[str, Any]]:
        """Загрузить известные проблемы из истории."""
        return [
            {
                "test_name": "test_llm_enhanced_simple.py::TestEnhancedLLMProvider::test_generate_structured_success",
                "error_message": "AttributeError: 'EnhancedLLMProvider' object has no attribute 'generate_text'",
                "category": "llm_enhanced",
                "context": {
                    "is_async": True,
                    "has_mocks": True,
                    "coverage_related": False,
                    "recent_changes": True,
                },
            },
            {
                "test_name": "test_rag_system_simple.py::TestFoodRAGSystem::test_init",
                "error_message": "TypeError: FoodRAGSystem.__init__() missing 1 required positional argument: 'vector_store'",
                "category": "rag_system",
                "context": {
                    "is_async": False,
                    "has_mocks": True,
                    "coverage_related": False,
                    "recent_changes": True,
                },
            },
            {
                "test_name": "test_evaluation_system_simple.py::TestEvaluationCriteria::test_init",
                "error_message": "TypeError: EvaluationCriteria.__init__() missing 3 required positional arguments: 'metric', 'weight', and 'description'",
                "category": "evaluation_system",
                "context": {
                    "is_async": False,
                    "has_mocks": False,
                    "coverage_related": False,
                    "recent_changes": True,
                },
            },
            {
                "test_name": "test_agent_system_simple.py::TestAgentTask::test_init_defaults",
                "error_message": "AssertionError: assert 1 == 0",
                "category": "agent_system",
                "context": {
                    "is_async": False,
                    "has_mocks": False,
                    "coverage_related": False,
                    "recent_changes": True,
                },
            },
            {
                "test_name": "test_llm_enhanced_simple.py::TestEnhancedLLMProvider::test_generate_structured_json_success",
                "error_message": "AssertionError: assert '' == '{\"key\": \"value\"}'",
                "category": "llm_enhanced",
                "context": {
                    "is_async": True,
                    "has_mocks": True,
                    "coverage_related": False,
                    "recent_changes": True,
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

    def _record_issue_as_test_execution(self, issue: Dict[str, Any]) -> None:
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

        if "attributeerror" in error_lower:
            return ErrorType.ATTRIBUTE_ERROR
        elif "typeerror" in error_lower:
            return ErrorType.TYPE_ERROR
        elif "assertionerror" in error_lower:
            return ErrorType.ASSERTION_ERROR
        elif "importerror" in error_lower:
            return ErrorType.IMPORT_ERROR
        elif "valueerror" in error_lower:
            return ErrorType.VALUE_ERROR
        elif "runtimeerror" in error_lower:
            return ErrorType.RUNTIME_ERROR
        elif "mock" in error_lower:
            return ErrorType.MOCK_ERROR
        elif "async" in error_lower or "await" in error_lower:
            return ErrorType.ASYNC_ERROR
        else:
            return ErrorType.RUNTIME_ERROR

    def _map_category(self, category: str) -> TestCategory:
        """Сопоставить категорию с TestCategory."""
        category_mapping = {
            "llm_enhanced": TestCategory.UNIT,
            "rag_system": TestCategory.UNIT,
            "evaluation_system": TestCategory.UNIT,
            "agent_system": TestCategory.UNIT,
            "integration": TestCategory.INTEGRATION,
            "e2e": TestCategory.E2E,
            "performance": TestCategory.PERFORMANCE,
            "coverage": TestCategory.COVERAGE,
        }
        return category_mapping.get(category, TestCategory.UNIT)

    def _generate_summary(self, analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Генерировать сводку анализа."""
        # Статистика по типам ошибок
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

    def print_analysis_report(self, analysis: Dict[str, Any]) -> None:
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

        if summary["most_common_error"][0] == "attribute_error":
            recommendations.append(
                "🔧 Проблемы с атрибутами - проверьте инициализацию классов и моки"
            )

        if summary["most_common_error"][0] == "type_error":
            recommendations.append(
                "🏷️ Проблемы с типами - проверьте сигнатуры методов и конструкторов"
            )

        if summary["most_common_error"][0] == "assertion_error":
            recommendations.append(
                "🔍 Проблемы с утверждениями - проверьте логику тестов и ожидаемые значения"
            )

        if summary["most_problematic_category"][0] in [
            "llm_enhanced",
            "rag_system",
            "evaluation_system",
            "agent_system",
        ]:
            recommendations.append(
                "🤖 Проблемы с AI-компонентами - проверьте асинхронные методы и моки"
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
            if (
                "EnhancedLLMProvider" in issue["test_name"]
                and "generate_text" in issue["error_message"]
            ):
                suggestions.append(
                    {
                        "file": "tests/test_llm_enhanced_simple.py",
                        "issue": "Неправильный метод в моке",
                        "fix": "Заменить mock_provider.generate_text на mock_provider.generate",
                        "code": "mock_provider.generate = AsyncMock(return_value='...')",
                    }
                )

            elif "FoodRAGSystem.__init__" in issue["error_message"]:
                suggestions.append(
                    {
                        "file": "tests/test_rag_system_simple.py",
                        "issue": "Отсутствует обязательный аргумент vector_store",
                        "fix": "Добавить vector_store при создании FoodRAGSystem",
                        "code": "rag = FoodRAGSystem(vector_store=mock_vector_store, llm_provider=mock_llm)",
                    }
                )

            elif "EvaluationCriteria.__init__" in issue["error_message"]:
                suggestions.append(
                    {
                        "file": "tests/test_evaluation_system_simple.py",
                        "issue": "Неправильные аргументы конструктора",
                        "fix": "Использовать правильные аргументы: metric, weight, description",
                        "code": "criteria = EvaluationCriteria(metric=EvaluationMetric.ACCURACY, weight=0.5, description='Test')",
                    }
                )

            elif "assert 1 == 0" in issue["error_message"]:
                suggestions.append(
                    {
                        "file": "tests/test_agent_system_simple.py",
                        "issue": "Неправильное ожидаемое значение",
                        "fix": "Исправить ожидаемое значение с 0 на 1",
                        "code": "assert result.priority == 1  # Вместо assert result.priority == 0",
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
    results_file = Path("bayesian_analysis_results.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n💾 Результаты анализа сохранены в {results_file}")


if __name__ == "__main__":
    main()
