#!/usr/bin/env python3
"""
Быстрый байесовский pre-commit хук для анализа измененных файлов.
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import ast
import subprocess

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.comprehensive_bayesian_analyzer import ComprehensiveBayesianAnalyzer


def analyze_changed_files() -> Dict[str, Any]:
    """Анализирует измененные файлы с помощью комплексной байесовской системы."""
    print("🔍 Комплексный байесовский анализ измененных файлов...")

    analyzer = ComprehensiveBayesianAnalyzer()
    recommendations = []

    # Получаем список измененных файлов
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        if result.returncode != 0:
            print("⚠️ Не удалось получить список измененных файлов")
            return {"recommendations": [], "has_issues": False}

        changed_files = [f.strip() for f in result.stdout.split("\n") if f.strip()]
        print(f"📁 Измененные файлы: {len(changed_files)}")

        # Анализируем только Python файлы
        python_files = [f for f in changed_files if f.endswith(".py")]

        if not python_files:
            print("✅ Нет изменений в Python файлах")
            return {"recommendations": [], "has_issues": False}

        # Анализируем каждый измененный файл
        has_issues = False
        for file_path in python_files:
            try:
                with open(project_root / file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()

                # Комплексный анализ файла
                analysis_result = analyzer.analyze_comprehensively(
                    file_content, f"file_analysis_{file_path}", file_path
                )

                if not analysis_result.success or analysis_result.critical_issues:
                    has_issues = True
                    print(f"❌ {file_path}: {analysis_result.overall_score:.2f} балл")
                    if analysis_result.critical_issues:
                        print(f"   Критические проблемы: {len(analysis_result.critical_issues)}")
                    if analysis_result.optimization_opportunities:
                        recommendations.extend(analysis_result.optimization_opportunities)
                else:
                    print(f"✅ {file_path}: {analysis_result.overall_score:.2f} балл")
            except Exception as e:
                print(f"⚠️ Ошибка анализа {file_path}: {e}")
                continue

        # Получаем комплексный диагноз
        diagnosis = analyzer.get_comprehensive_diagnosis()
        if diagnosis.get("status") == "analyzed":
            cost_savings = diagnosis.get("cost_savings_recommendations", [])
            revenue_growth = diagnosis.get("revenue_optimization_recommendations", [])
            recommendations.extend(cost_savings[:2])
            recommendations.extend(revenue_growth[:2])

    except Exception as e:
        print(f"❌ Ошибка анализа файлов: {e}")
        return {"recommendations": [], "has_issues": True}

    return {"recommendations": recommendations, "has_issues": has_issues}


def check_test_file_syntax(file_path: str) -> bool:
    """Проверяет синтаксис тестового файла."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", file_path],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        return result.returncode == 0
    except Exception:
        return False


def check_core_file_imports(file_path: str) -> bool:
    """Проверяет импорты и синтаксис в core файле с помощью ast.parse."""
    try:
        full_path = project_root / file_path
        with open(full_path, "r", encoding="utf-8") as f:
            source = f.read()
        ast.parse(source, filename=str(full_path))
        return True
    except (SyntaxError, FileNotFoundError):
        return False
    except Exception:
        return False


def run_fast_tests() -> bool:
    """Запускает быстрые тесты только для измененных модулей."""
    print("⚡ Запуск быстрых тестов...")

    try:
        # Запускаем только тесты, связанные с измененными файлами
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_llm_enhanced_simple.py",
                "tests/test_rag_system_simple.py",
                "tests/test_evaluation_system_simple.py",
                "tests/test_agent_system_simple.py",
                "-v",
                "--tb=short",
                "-x",  # -x останавливается на первой ошибке
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=45,  # 45 second timeout
        )

        if result.returncode == 0:
            print("✅ Быстрые тесты прошли успешно")
            return True
        else:
            print("❌ Быстрые тесты не прошли")
            print(result.stdout[-500:])  # Показываем только последние 500 символов
            return False
    except subprocess.TimeoutExpired:
        print("❌ Быстрые тесты превысили время ожидания")
        return False
    except Exception as e:
        print(f"❌ Ошибка запуска тестов: {e}")
        return False


def check_coverage() -> bool:
    """Проверяет покрытие кода - должно быть 97%+."""
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
                "-q",  # Тихий режим для скорости
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=120,  # Таймаут 2 минуты
        )

        if result.returncode == 0:
            print("✅ Покрытие кода: 97%+ достигнуто")
            return True
        else:
            print("❌ Покрытие кода: менее 97%")
            # Показываем только последние строки с информацией о покрытии
            output_lines = result.stdout.split("\n")
            coverage_lines = [
                line
                for line in output_lines
                if "TOTAL" in line or "Required" in line or "%" in line
            ]
            if coverage_lines:
                print("\n".join(coverage_lines[-5:]))
            return False
    except subprocess.TimeoutExpired:
        print("❌ Проверка покрытия превысила время ожидания")
        return False
    except Exception as e:
        print(f"❌ Ошибка проверки покрытия: {e}")
        return False


def main() -> int:
    """Основная функция быстрого байесовского pre-commit хука."""
    print("🚀 Запуск комплексного байесовского анализа...")
    print("=" * 60)

    # Анализируем измененные файлы
    analysis_result = analyze_changed_files()
    recommendations = analysis_result.get("recommendations", [])
    has_issues = analysis_result.get("has_issues", False)

    # Запускаем быстрые тесты
    tests_ok = run_fast_tests()

    # Проверяем покрытие кода
    coverage_ok = check_coverage()

    # Определяем, нужно ли блокировать коммит
    should_block = False
    issues = []

    if not tests_ok:
        should_block = True
        issues.append("Тесты не проходят")

    if not coverage_ok:
        should_block = True
        issues.append("Покрытие кода менее 96%")

    if has_issues:
        should_block = True
        issues.append("Обнаружены критические проблемы в коде")

    print("\n" + "=" * 60)
    if should_block:
        print(f"❌ Байесовский анализ заблокировал коммит:")
        for issue in issues:
            print(f"  - {issue}")

        if recommendations:
            print(f"\n🔧 Рекомендации для исправления:")
            for i, rec in enumerate(recommendations[:5], 1):  # Показываем первые 5
                print(f"  {i}. {rec}")

        return 1
    else:
        print("✅ Байесовский анализ: коммит разрешен")
        print("🎉 Все проверки пройдены успешно!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
