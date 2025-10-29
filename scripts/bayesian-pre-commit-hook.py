#!/usr/bin/env python3
"""
Байесовский pre-commit хук для анализа тестов и диагностики проблем.
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import subprocess
import json
import tempfile

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.bayesian_test_analyzer import BayesianTestAnalyzer, ProblemCategory, ErrorType


def run_tests_and_collect_results() -> Dict[str, Any]:
    """Запускает тесты и собирает результаты для байесовского анализа."""
    print("🔍 Запуск тестов для байесовского анализа...")

    # Запускаем тесты с детальным выводом
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/",
                "-v",
                "--tb=short",
                "--json-report",
                "--json-report-file=test-results.json",
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        # Читаем JSON отчет если он существует
        json_file = project_root / "test-results.json"
        if json_file.exists():
            with open(json_file, "r") as f:
                report = json.load(f)
        else:
            report = {}

        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "json_report": report,
        }
    except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError, OSError) as e:
        print(f"❌ Ошибка выполнения тестов: {e}")
        return {"returncode": 1, "stdout": "", "stderr": str(e), "json_report": {}}


def analyze_test_results(results: Dict[str, Any]) -> List[str]:
    """Анализирует результаты тестов с помощью байесовской системы."""
    print("🧠 Байесовский анализ результатов тестов...")

    analyzer = BayesianTestAnalyzer()
    recommendations = []

    # Анализируем код возврата
    if results["returncode"] != 0:
        analyzer.add_test_result(
            test_name="overall_test_suite",
            success=False,
            error_type=ErrorType.TEST_FAILURE,
            error_message="Test suite failed",
            execution_time=0.0,
            file_path="tests/",
        )

        # Анализируем stderr для конкретных ошибок
        stderr = results["stderr"]
        if "AssertionError" in stderr:
            analyzer.add_test_result(
                test_name="assertion_errors",
                success=False,
                error_type=ErrorType.ASSERTION_ERROR,
                error_message="Assertion errors detected",
                execution_time=0.0,
                file_path="tests/",
            )

        if "ImportError" in stderr or "ModuleNotFoundError" in stderr:
            analyzer.add_test_result(
                test_name="import_errors",
                success=False,
                error_type=ErrorType.IMPORT_ERROR,
                error_message="Import errors detected",
                execution_time=0.0,
                file_path="tests/",
            )

        if "TypeError" in stderr:
            analyzer.add_test_result(
                test_name="type_errors",
                success=False,
                error_type=ErrorType.TYPE_ERROR,
                error_message="Type errors detected",
                execution_time=0.0,
                file_path="tests/",
            )

    # Анализируем JSON отчет если доступен
    json_report = results.get("json_report", {})
    if "summary" in json_report:
        summary = json_report["summary"]
        if summary.get("failed", 0) > 0:
            # Анализируем каждый упавший тест
            for test in json_report.get("tests", []):
                if test.get("outcome") == "failed":
                    analyzer.add_test_result(
                        test_name=test.get("nodeid", "unknown"),
                        success=False,
                        error_type=ErrorType.TEST_FAILURE,
                        error_message=test.get("call", {}).get("longrepr", "Test failed"),
                        execution_time=test.get("call", {}).get("duration", 0.0),
                        file_path=(
                            test.get("nodeid", "").split("::")[0]
                            if "::" in test.get("nodeid", "")
                            else "tests/"
                        ),
                    )

    # Получаем диагноз и рекомендации
    if analyzer.test_results:
        diagnosis = analyzer.diagnose_test_failure()
        recommendations = analyzer.generate_recommendations()

        print(f"📊 Байесовский диагноз:")
        for category, probability in diagnosis.items():
            print(f"  {category.value}: {probability:.2%}")

        print(f"\n💡 Рекомендации ({len(recommendations)}):")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")

    return recommendations


def check_coverage_threshold() -> bool:
    """Проверяет, достигнуто ли пороговое значение покрытия 97%."""
    print("📈 Проверка покрытия кода...")

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--cov=core",
                "--cov=scripts",
                "--cov-report=term-missing",
                "--cov-fail-under=97",
                "tests/",
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        if result.returncode == 0:
            print("✅ Покрытие кода: 97%+ достигнуто")
            return True
        else:
            print("❌ Покрытие кода: менее 97%")
            print(result.stdout)
            return False
    except Exception as e:
        print(f"❌ Ошибка проверки покрытия: {e}")
        return False


def main() -> int:
    """Основная функция байесовского pre-commit хука."""
    print("🚀 Запуск байесовского pre-commit анализа...")

    # Проверяем покрытие кода
    coverage_ok = check_coverage_threshold()

    # Запускаем тесты и анализируем результаты
    test_results = run_tests_and_collect_results()
    recommendations = analyze_test_results(test_results)

    # Определяем, нужно ли блокировать коммит
    should_block = False
    issues = []

    if not coverage_ok:
        should_block = True
        issues.append("Покрытие кода менее 96%")

    if test_results["returncode"] != 0:
        should_block = True
        issues.append("Тесты не проходят")

    # Выводим итоговый результат
    if should_block:
        print(f"\n❌ Байесовский анализ заблокировал коммит:")
        for issue in issues:
            print(f"  - {issue}")

        if recommendations:
            print(f"\n🔧 Рекомендации для исправления:")
            for i, rec in enumerate(recommendations[:5], 1):  # Показываем только первые 5
                print(f"  {i}. {rec}")

        return 1
    else:
        print("\n✅ Байесовский анализ: коммит разрешен")
        return 0


if __name__ == "__main__":
    sys.exit(main())
