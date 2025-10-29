#!/usr/bin/env python3
"""
Bayesian diagnostic helper for PulsePlate issues.

Uses Bayes' theorem to analyze failing tests and provide
intelligent recommendations for fixing them.
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse
from datetime import datetime

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.bayesian_test_analyzer import (
    BayesianTestAnalyzer,
    TestResult,
    ErrorType,
    TestCategory,
    diagnose_test_failure,
    record_test_execution,
)


class BayesianDebugHelper:
    """Помощник для байесовской диагностики."""

    def __init__(self, project_root: Path = None):
        """Инициализация помощника."""
        self.project_root = project_root or Path(__file__).parent.parent
        self.analyzer = BayesianTestAnalyzer()
        self.test_results = {}

    def run_tests_with_diagnosis(
        self, test_pattern: str = None, verbose: bool = True
    ) -> Dict[str, Any]:
        """Запустить тесты с байесовской диагностикой."""
        print("🔍 Запуск тестов с байесовской диагностикой...")

        # Запустить pytest
        cmd = ["python", "-m", "pytest"]
        if test_pattern:
            cmd.append(test_pattern)
        if verbose:
            cmd.append("-v")
        cmd.extend(["--tb=short", "-x"])  # Остановиться на первой ошибке

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 минут таймаут
            )

            # Анализировать результаты
            return self._analyze_test_output(result.stdout, result.stderr, result.returncode)

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "message": "Тесты превысили лимит времени выполнения",
                "recommendations": [
                    "Проверьте, нет ли бесконечных циклов в тестах",
                    "Увеличьте таймауты для медленных тестов",
                    "Рассмотрите возможность параллельного выполнения тестов",
                ],
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка запуска тестов: {e}",
                "recommendations": [
                    "Проверьте установку pytest",
                    "Убедитесь, что все зависимости установлены",
                    "Проверьте синтаксис тестов",
                ],
            }

    def _analyze_test_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """Анализировать вывод тестов."""
        analysis = {
            "status": "success" if returncode == 0 else "failed",
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
            "diagnoses": [],
            "recommendations": [],
            "summary": {},
        }

        if returncode != 0:
            # Парсить падающие тесты
            failed_tests = self._parse_failed_tests(stdout, stderr)

            for test_name, error_info in failed_tests.items():
                diagnosis = self._diagnose_test(test_name, error_info)
                analysis["diagnoses"].append(diagnosis)

            # Общие рекомендации
            analysis["recommendations"] = self._generate_general_recommendations(failed_tests)

            # Сводка
            analysis["summary"] = {
                "total_failed": len(failed_tests),
                "most_common_error": self._get_most_common_error(failed_tests),
                "confidence_avg": (
                    sum(d["confidence"] for d in analysis["diagnoses"]) / len(analysis["diagnoses"])
                    if analysis["diagnoses"]
                    else 0
                ),
            }

        return analysis

    def _parse_failed_tests(self, stdout: str, stderr: str) -> Dict[str, Dict[str, Any]]:
        """Парсить информацию о падающих тестах."""
        failed_tests = {}

        # Простой парсинг вывода pytest
        lines = stdout.split("\n")
        current_test = None
        error_message = []

        for line in lines:
            if ("FAILED" in line or "ERROR" in line) and "::" in line:
                # Сохранить предыдущий тест
                if current_test and error_message:
                    failed_tests[current_test] = {
                        "error_message": "\n".join(error_message),
                        "error_type": self._classify_error("\n".join(error_message)),
                    }

                # Начать новый тест
                current_test = line.split("::")[-1].strip()
                error_message = []
            elif current_test and line.strip():
                error_message.append(line.strip())

        # Сохранить последний тест
        if current_test and error_message:
            failed_tests[current_test] = {
                "error_message": "\n".join(error_message),
                "error_type": self._classify_error("\n".join(error_message)),
            }

        return failed_tests

    def _classify_error(self, error_message: str) -> str:
        """Классифицировать тип ошибки."""
        error_lower = error_message.lower()

        if "assertionerror" in error_lower:
            return "assertion_error"
        elif "importerror" in error_lower or "modulenotfounderror" in error_lower:
            return "import_error"
        elif "typeerror" in error_lower:
            return "type_error"
        elif "attributeerror" in error_lower:
            return "attribute_error"
        elif "valueerror" in error_lower:
            return "value_error"
        elif "runtimeerror" in error_lower:
            return "runtime_error"
        elif "timeouterror" in error_lower:
            return "timeout_error"
        elif "coverage" in error_lower and "below" in error_lower:
            return "coverage_error"
        elif "mock" in error_lower:
            return "mock_error"
        elif "asyncio" in error_lower or "await" in error_lower:
            return "async_error"
        else:
            return "unknown_error"

    def _diagnose_test(self, test_name: str, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Диагностировать конкретный тест."""
        context = {
            "is_async": "async" in test_name.lower()
            or "asyncio" in error_info["error_message"].lower(),
            "has_mocks": "mock" in error_info["error_message"].lower(),
            "coverage_related": "coverage" in test_name.lower(),
        }

        diagnosis = diagnose_test_failure(test_name, error_info["error_message"], context)

        return {
            "test_name": test_name,
            "error_type": error_info["error_type"],
            "most_likely_cause": diagnosis.most_likely_cause,
            "probability": diagnosis.probability,
            "confidence": diagnosis.confidence,
            "evidence": diagnosis.evidence,
            "recommendations": diagnosis.recommendations,
            "alternative_causes": diagnosis.alternative_causes,
        }

    def _generate_general_recommendations(
        self, failed_tests: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """Генерировать общие рекомендации."""
        recommendations = []

        # Анализ типов ошибок
        error_types = [info["error_type"] for info in failed_tests.values()]
        error_counts = {}
        for error_type in error_types:
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        # Рекомендации на основе частоты ошибок
        if error_counts.get("assertion_error", 0) > 1:
            recommendations.append(
                "🔍 Множественные ошибки утверждений - проверьте логику тестов и моки"
            )

        if error_counts.get("import_error", 0) > 0:
            recommendations.append("📦 Ошибки импорта - проверьте зависимости и PYTHONPATH")

        if error_counts.get("type_error", 0) > 0:
            recommendations.append("🏷️ Ошибки типов - проверьте аннотации типов и сигнатуры функций")

        if error_counts.get("async_error", 0) > 0:
            recommendations.append(
                "⚡ Асинхронные ошибки - используйте AsyncMock и @pytest.mark.asyncio"
            )

        if error_counts.get("mock_error", 0) > 0:
            recommendations.append("🎭 Ошибки моков - проверьте настройку патчей и моков")

        # Общие рекомендации
        if len(failed_tests) > 3:
            recommendations.append(
                "🚨 Много падающих тестов - рассмотрите рефакторинг тестовой стратегии"
            )

        return recommendations

    def _get_most_common_error(self, failed_tests: Dict[str, Dict[str, Any]]) -> str:
        """Получить наиболее частый тип ошибки."""
        error_types = [info["error_type"] for info in failed_tests.values()]
        if not error_types:
            return "none"

        from collections import Counter

        return Counter(error_types).most_common(1)[0][0]

    def print_diagnosis_report(self, analysis: Dict[str, Any]) -> None:
        """Вывести отчет о диагностике."""
        print("\n" + "=" * 80)
        print("🔍 БАЙЕСОВСКИЙ ОТЧЕТ О ДИАГНОСТИКЕ ТЕСТОВ")
        print("=" * 80)

        if analysis["status"] == "success":
            print("✅ Все тесты прошли успешно!")
            return

        print(f"❌ Статус: {analysis['status'].upper()}")
        print(f"📊 Код возврата: {analysis['returncode']}")

        if "summary" in analysis:
            summary = analysis["summary"]
            print(f"📈 Падающих тестов: {summary.get('total_failed', 0)}")
            print(
                f"🎯 Наиболее частый тип ошибки: {summary.get('most_common_error', 'неизвестно')}"
            )
            print(f"🎲 Средняя уверенность: {summary.get('confidence_avg', 0):.2%}")

        print("\n" + "-" * 80)
        print("🔬 ДЕТАЛЬНАЯ ДИАГНОСТИКА")
        print("-" * 80)

        for i, diagnosis in enumerate(analysis.get("diagnoses", []), 1):
            print(f"\n{i}. Тест: {diagnosis['test_name']}")
            print(f"   Тип ошибки: {diagnosis['error_type']}")
            print(f"   Наиболее вероятная причина: {diagnosis['most_likely_cause']}")
            print(f"   Вероятность: {diagnosis['probability']:.2%}")
            print(f"   Уверенность: {diagnosis['confidence']:.2%}")

            print(f"   📋 Доказательства:")
            for evidence in diagnosis["evidence"]:
                print(f"      • {evidence}")

            print(f"   💡 Рекомендации:")
            for recommendation in diagnosis["recommendations"]:
                print(f"      • {recommendation}")

            if diagnosis["alternative_causes"]:
                print(f"   🔄 Альтернативные причины:")
                for cause, prob in diagnosis["alternative_causes"]:
                    print(f"      • {cause}: {prob:.2%}")

        print("\n" + "-" * 80)
        print("🎯 ОБЩИЕ РЕКОМЕНДАЦИИ")
        print("-" * 80)

        for recommendation in analysis.get("recommendations", []):
            print(f"• {recommendation}")

        print("\n" + "=" * 80)

    def suggest_test_improvements(self, test_file: str) -> List[str]:
        """Предложить улучшения для конкретного файла тестов."""
        suggestions = []

        # Анализировать файл тестов
        test_path = self.project_root / test_file
        if not test_path.exists():
            return [f"Файл {test_file} не найден"]

        try:
            with open(test_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Простые эвристики для улучшения тестов
            if "import" in content.lower() and "pytest" not in content:
                suggestions.append("Добавьте импорт pytest для лучшей совместимости")

            if "async" in content and "@pytest.mark.asyncio" not in content:
                suggestions.append("Добавьте @pytest.mark.asyncio для асинхронных тестов")

            if "mock" in content.lower() and "unittest.mock" not in content:
                suggestions.append("Добавьте импорт unittest.mock для работы с моками")

            if "assert" in content and "pytest.raises" not in content:
                suggestions.append(
                    "Рассмотрите использование pytest.raises для тестирования исключений"
                )

            if "time.sleep" in content:
                suggestions.append(
                    "Замените time.sleep на pytest-asyncio или моки для ускорения тестов"
                )

        except Exception as e:
            suggestions.append(f"Ошибка анализа файла: {e}")

        return suggestions


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(description="Байесовский помощник диагностики тестов")
    parser.add_argument("--test-pattern", "-p", help="Паттерн тестов для запуска")
    parser.add_argument("--test-file", "-f", help="Файл тестов для анализа")
    parser.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")
    parser.add_argument(
        "--suggestions", "-s", action="store_true", help="Показать предложения по улучшению"
    )

    args = parser.parse_args()

    helper = BayesianDebugHelper()

    if args.test_file and args.suggestions:
        # Анализ файла тестов
        suggestions = helper.suggest_test_improvements(args.test_file)
        print(f"\n💡 Предложения по улучшению {args.test_file}:")
        for suggestion in suggestions:
            print(f"• {suggestion}")
    else:
        # Запуск тестов с диагностикой
        analysis = helper.run_tests_with_diagnosis(
            test_pattern=args.test_pattern, verbose=args.verbose
        )
        helper.print_diagnosis_report(analysis)


if __name__ == "__main__":
    main()
