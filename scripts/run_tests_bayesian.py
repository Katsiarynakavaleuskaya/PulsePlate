#!/usr/bin/env python3
"""
Быстрый прогон тестов с байесовским анализом упавших тестов.
Исключает кеш-файлы из покрытия для ускорения.
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Any

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.comprehensive_bayesian_analyzer import ComprehensiveBayesianAnalyzer


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
                    import shutil

                    shutil.rmtree(path, ignore_errors=True)
        except Exception as e:
            print(f"⚠️ Ошибка очистки {pattern}: {e}")

    print("✅ Кеш очищен")


def run_tests_fast() -> Dict[str, Any]:
    """Запускает тесты быстро с исключением кеш-файлов."""
    print("⚡ Быстрый запуск тестов (без кеш-файлов)...")
    print("=" * 60)

    # Очищаем кеш перед запуском
    clean_cache()

    try:
        result = subprocess.run(
            [
                sys.executable,
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
                    try:
                        test_name = line.split("::")[-1].strip()
                    except Exception:
                        test_name = line.strip()
                    failed_tests.append(
                        {
                            "name": test_name,
                            "line": line,
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


def analyze_failed_tests(failed_tests: List[Dict[str, Any]]) -> None:
    """Анализирует упавшие тесты через байесовский метод."""
    if not failed_tests:
        return

    print("\n" + "=" * 60)
    print("🔍 Байесовский анализ упавших тестов...")
    print("=" * 60)

    analyzer = ComprehensiveBayesianAnalyzer()

    for test_info in failed_tests[:10]:  # Анализируем первые 10
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

            if result.critical_issues:
                print(f"  ❌ Критические проблемы: {len(result.critical_issues)}")
                for issue in result.critical_issues[:3]:
                    print(f"     - {issue}")

            if result.optimization_opportunities:
                print(f"  💡 Возможности оптимизации:")
                for opt in result.optimization_opportunities[:2]:
                    print(f"     - {opt}")

            if result.overall_score < 0.7:
                print(f"  ⚠️ Низкий балл: {result.overall_score:.2f}")

        except Exception as e:
            print(f"  ⚠️ Ошибка анализа: {e}")

    # Получаем комплексный диагноз
    diagnosis = analyzer.get_comprehensive_diagnosis()
    if diagnosis.get("status") == "analyzed":
        print("\n📋 Комплексный диагноз:")
        print(f"  Технический балл: {diagnosis.get('technical_score', 0):.2f}")
        print(f"  Бизнес балл: {diagnosis.get('business_score', 0):.2f}")

        recommendations = diagnosis.get("recommendations", [])
        if recommendations:
            print(f"\n🔧 Рекомендации:")
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
