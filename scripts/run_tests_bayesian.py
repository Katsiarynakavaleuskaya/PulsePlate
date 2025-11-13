#!/usr/bin/env python3
"""
Быстрый прогон тестов с байесовским анализом упавших тестов.
Исключает кеш-файлы из покрытия для ускорения.
"""

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# Package should be installed in editable mode (pip install -e .)
# or PYTHONPATH should be set in the environment
from core.comprehensive_bayesian_analyzer import ComprehensiveBayesianAnalyzer

project_root = Path(__file__).parent.parent


def clean_cache() -> None:
    """Очищает кеш-файлы перед запуском тестов."""
    print("🧹 Очистка кеш-файлов...")

    cache_patterns = [
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
        ".pytest_cache",
        ".coverage",
    ]

    for pattern in cache_patterns:
        try:
            for path in project_root.glob(pattern):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
        except (PermissionError, OSError) as e:
            # Log expected filesystem errors during cleanup
            logging.warning(f"Error cleaning cache pattern {pattern}: {e}", exc_info=False)

    print("✅ Кеш очищен")


def run_tests_fast() -> dict[str, Any]:
    """Запускает тесты быстро с исключением кеш-файлов."""
    print("⚡ Быстрый запуск тестов (без кеш-файлов)...")
    print("=" * 60)

    # Очищаем кеш перед запуском
    clean_cache()

    try:
        # Security: Using list form (not shell=True) with static strings only.
        # sys.executable is a Python built-in and not controllable by external actors.
        # This prevents command injection vulnerabilities.
        result = subprocess.run(  # nosec B603 - test args are controlled, not user input
            [
                sys.executable,  # Safe: Python built-in, returns interpreter path
                "-m",
                "pytest",
                "tests/",
                "-q",  # Тихий режим
                "--tb=short",  # Короткий traceback
                "--cov=core",  # Только core (исключаем кеш)
                "--cov=app",  # И app
                "--cov-report=term-missing",
                "--cache-clear",  # Очистка кеша pytest
                "--maxfail=10",  # Максимум 10 падений
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=600,  # 10 минут максимум
        )

        output = result.stdout + result.stderr

        # Извлекаем информацию об упавших/ошибочных тестах
        failed_tests = []
        if result.returncode != 0:
            lines = output.split("\n")
            for i, line in enumerate(lines):
                if ("FAILED" in line or "ERROR" in line) and "::" in line:
                    # Extract test name with proper error handling
                    extraction_error = False
                    try:
                        test_name = line.split("::")[-1].strip()
                        # Validate that we got a meaningful test name
                        if not test_name or test_name == line.strip():
                            # If extraction didn't produce a distinct name, mark as error
                            extraction_error = True
                            test_name = "<unknown_test_name>"
                    except (AttributeError, IndexError) as e:
                        # Mark extraction as failed and use placeholder
                        extraction_error = True
                        test_name = "<unknown_test_name>"
                        logging.warning(
                            f"Failed to extract test name from line {i}: {e}. "
                            f"Raw line: {line[:100] if line else '(empty)'}"
                        )

                    # Add entry with extraction error flag for callers to filter if needed
                    failed_tests.append(
                        {
                            "name": test_name,
                            "line": line,
                            "raw_line": line,  # Preserve original for debugging
                            "extraction_error": extraction_error,
                            "context": "\n".join(lines[max(0, i - 3) : i + 10]),
                        }
                    )

        return {
            "success": result.returncode == 0,
            "failed_tests": failed_tests,
            "output": output,
            "returncode": result.returncode,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "failed_tests": [],
            "output": "Тесты превысили время ожидания (10 минут)",
            "returncode": 1,
        }
    except Exception as e:
        return {
            "success": False,
            "failed_tests": [],
            "output": f"Ошибка запуска тестов: {e}",
            "returncode": 1,
        }


def analyze_failed_tests(failed_tests: list[dict[str, Any]]) -> None:
    """Анализирует упавшие тесты через байесовский метод."""
    if not failed_tests:
        return

    # Configurable limits via environment variables with error handling
    try:
        max_analysis = int(os.getenv("MAX_BAYESIAN_ANALYSIS", "5"))
    except (ValueError, TypeError):
        max_analysis = 5
        import warnings

        warnings.warn(f"Invalid MAX_BAYESIAN_ANALYSIS value, using default: {max_analysis}")

    summary_mode_str = os.getenv("SUMMARY_MODE", "").lower()
    summary_mode = summary_mode_str in ("1", "true", "yes")
    if summary_mode_str and summary_mode_str not in ("1", "true", "yes", "0", "false", "no", ""):
        import warnings

        warnings.warn(f"Invalid SUMMARY_MODE value '{summary_mode_str}', using default: False")

    try:
        score_threshold = float(os.getenv("BAYESIAN_SCORE_THRESHOLD", "0.7"))
    except (ValueError, TypeError):
        score_threshold = 0.7
        import warnings

        warnings.warn(f"Invalid BAYESIAN_SCORE_THRESHOLD value, using default: {score_threshold}")

    print("\n" + "=" * 60)
    print("🔍 Байесовский анализ упавших тестов...")
    print("=" * 60)

    analyzer = ComprehensiveBayesianAnalyzer()

    # Slice failed_tests to configurable limit
    tests_to_analyze = failed_tests[:max_analysis]

    if summary_mode:
        # Summary mode: only print counts
        print(f"\n📊 Анализ {len(tests_to_analyze)} из {len(failed_tests)} упавших тестов...")
        critical_count = 0
        optimization_count = 0
        low_score_count = 0

        for test_info in tests_to_analyze:
            test_context = test_info.get("context", "")
            try:
                result = analyzer.analyze_comprehensively(
                    test_context,
                    f"failed_test_{test_info['name']}",
                    f"tests/{test_info['name']}",
                )
                if result.critical_issues:
                    critical_count += len(result.critical_issues)
                if result.optimization_opportunities:
                    optimization_count += len(result.optimization_opportunities)
                if result.overall_score < score_threshold:
                    low_score_count += 1
            except Exception as e:
                # Log errors even in summary mode for visibility
                logging.error(
                    f"Error analyzing test {test_info.get('name', 'unknown')} in summary mode: {e}",
                    exc_info=True,
                )

        print(f"  ❌ Критические проблемы: {critical_count}")
        print(f"  💡 Возможности оптимизации: {optimization_count}")
        print(f"  ⚠️ Низкий балл (<{score_threshold:.2f}): {low_score_count}")
        return

    # Detailed mode: print limited details per test
    for test_info in tests_to_analyze:
        test_name = test_info["name"]
        test_context = test_info.get("context", "")

        print(f"\n📊 Анализ: {test_name}")

        try:
            # Анализируем контекст теста
            result = analyzer.analyze_comprehensively(
                test_context,
                f"failed_test_{test_name}",
                f"tests/{test_name}",
            )

            # Top 2 critical issues only
            if result.critical_issues:
                print(f"  ❌ Критические проблемы: {len(result.critical_issues)}")
                for issue in result.critical_issues[:2]:
                    print(f"     - {issue}")

            # Top 1 optimization only
            if result.optimization_opportunities:
                print("  💡 Возможности оптимизации:")
                for opt in result.optimization_opportunities[:1]:
                    print(f"     - {opt}")

            # Only print low score when below threshold
            if result.overall_score < score_threshold:
                print(f"  ⚠️ Низкий балл: {result.overall_score:.2f}")

        except Exception as e:
            print(f"  ⚠️ Ошибка анализа: {e}")

    # Получаем комплексный диагноз
    diagnosis = analyzer.get_comprehensive_diagnosis()
    if diagnosis.get("status") == "analyzed":
        print("\n📋 Комплексный диагноз:")
        avg_scores = diagnosis.get("average_scores", {})
        print(f"  Технический балл: {avg_scores.get('technical', 0):.2f}")
        print(f"  Бизнес балл: {avg_scores.get('business', 0):.2f}")

        recommendations = diagnosis.get("optimization_opportunities", [])
        if recommendations:
            print("\n🔧 Рекомендации:")
            for i, rec in enumerate(recommendations[:5], 1):
                print(f"  {i}. {rec}")


def main() -> int:
    """Основная функция быстрого прогона тестов."""
    print("🚀 Быстрый прогон тестов с байесовским анализом")
    print("=" * 60)

    # Запускаем тесты
    test_result = run_tests_fast()

    # Показываем результаты
    print("\n" + "=" * 60)
    if test_result["success"]:
        print("✅ Все тесты прошли успешно!")
        return 0
    else:
        print(f"❌ Упало тестов: {len(test_result['failed_tests'])}")

        # Анализируем упавшие тесты
        if test_result["failed_tests"]:
            analyze_failed_tests(test_result["failed_tests"])

        # Показываем краткую информацию о падениях
        print("\n" + "=" * 60)
        print("📋 Список упавших тестов:")
        for i, test_info in enumerate(test_result["failed_tests"][:10], 1):
            print(f"  {i}. {test_info['name']}")

        return 1


if __name__ == "__main__":
    sys.exit(main())
