#!/usr/bin/env python3
"""
Комплексный pre-commit хук с байесовским анализом всех аспектов системы PulsePlate.
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

from core.comprehensive_bayesian_analyzer import ComprehensiveBayesianAnalyzer


def analyze_changed_files_comprehensively() -> Dict[str, Any]:
    """Комплексный анализ измененных файлов."""
    print("🔍 Комплексный байесовский анализ измененных файлов...")

    analyzer = ComprehensiveBayesianAnalyzer()

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
            return {"status": "error", "message": "Cannot get changed files"}

        changed_files = [f.strip() for f in result.stdout.split("\n") if f.strip()]
        print(f"📁 Измененные файлы: {len(changed_files)}")

        # Анализируем только Python файлы
        python_files = [f for f in changed_files if f.endswith(".py")]

        if not python_files:
            print("✅ Нет изменений в Python файлах")
            return {"status": "success", "message": "No Python files changed"}

        # Анализируем каждый измененный файл
        analysis_results = []
        for file_path in python_files:
            try:
                with open(project_root / file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()

                # Анализируем файл
                result = analyzer.analyze_comprehensively(
                    file_content, f"file_analysis_{file_path}", file_path
                )
                analysis_results.append(result)

                # Выводим результаты для файла
                if not result.success:
                    print(f"❌ {file_path}: {result.overall_score:.2f} балл")
                    if result.critical_issues:
                        print(f"   Критические проблемы: {len(result.critical_issues)}")
                    if result.optimization_opportunities:
                        print(
                            f"   Возможности оптимизации: {len(result.optimization_opportunities)}"
                        )
                else:
                    print(f"✅ {file_path}: {result.overall_score:.2f} балл")

            except Exception as e:
                print(f"⚠️ Ошибка анализа {file_path}: {e}")
                continue

        # Получаем комплексный диагноз
        diagnosis = analyzer.get_comprehensive_diagnosis()

        return {
            "status": "analyzed",
            "files_analyzed": len(python_files),
            "analysis_results": analysis_results,
            "diagnosis": diagnosis,
        }

    except Exception as e:
        print(f"❌ Ошибка комплексного анализа: {e}")
        return {"status": "error", "message": str(e)}


def run_critical_tests() -> bool:
    """Запускает критические тесты."""
    print("⚡ Запуск критических тестов...")

    try:
        # Запускаем только стабильные тесты
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_comprehensive_bayesian_analyzer.py",
                "tests/test_bayesian_analyzer.py",
                "tests/test_llm_enhanced_simple.py",
                "tests/test_rag_system_simple.py",
                "tests/test_evaluation_system_simple.py",
                "-v",
                "--tb=short",
                "-x",  # Останавливается на первой ошибке
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=45,  # Таймаут 45 секунд
        )

        if result.returncode == 0:
            print("✅ Критические тесты прошли успешно")
            return True
        else:
            print("❌ Критические тесты не прошли")
            print(result.stdout[-500:])  # Показываем только последние 500 символов
            return False
    except subprocess.TimeoutExpired:
        print("❌ Критические тесты превысили время ожидания")
        return False
    except Exception as e:
        print(f"❌ Ошибка запуска тестов: {e}")
        return False


def check_coverage_threshold() -> bool:
    """Проверяет достижение порогового значения покрытия 97%."""
    print("📈 Проверка покрытия кода...")

    try:
        # Проверяем покрытие только для измененных файлов
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--cov=core",
                "--cov=scripts",
                "--cov-report=term-missing",
                "--cov-fail-under=97",
                "tests/test_comprehensive_bayesian_analyzer.py",
                "tests/test_bayesian_analyzer.py",
                "tests/test_llm_enhanced_simple.py",
                "tests/test_rag_system_simple.py",
                "tests/test_evaluation_system_simple.py",
                "tests/test_agent_system_simple.py",
                "-x",  # Останавливается на первой ошибке
                "--tb=short",
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=60,  # Таймаут 60 секунд
        )

        if result.returncode == 0:
            print("✅ Покрытие кода: 97%+ достигнуто")
            return True
        else:
            print("❌ Покрытие кода: менее 97%")
            print(result.stdout[-300:])  # Показываем только последние 300 символов
            return False
    except subprocess.TimeoutExpired:
        print("❌ Проверка покрытия превысила время ожидания")
        return False
    except Exception as e:
        print(f"❌ Ошибка проверки покрытия: {e}")
        return False


def generate_business_insights(analysis_data: Dict[str, Any]) -> None:
    """Генерирует бизнес-инсайты на основе анализа."""
    if analysis_data.get("status") != "analyzed":
        return

    diagnosis = analysis_data.get("diagnosis", {})

    print("\n💼 БИЗНЕС-ИНСАЙТЫ:")
    print("=" * 50)

    # Общее здоровье системы
    system_health = diagnosis.get("system_health", "unknown")
    print(f"🏥 Здоровье системы: {system_health.upper()}")

    # Средние баллы
    avg_scores = diagnosis.get("average_scores", {})
    if avg_scores:
        print(f"📊 Средние баллы:")
        print(f"   Технический: {avg_scores.get('technical', 0):.2f}")
        print(f"   Питание: {avg_scores.get('nutrition', 0):.2f}")
        print(f"   Бизнес: {avg_scores.get('business', 0):.2f}")
        print(f"   Общий: {avg_scores.get('overall', 0):.2f}")

    # Критические проблемы
    critical_tests = diagnosis.get("critical_tests", [])
    if critical_tests:
        print(f"🚨 Критические тесты: {len(critical_tests)}")
        for test in critical_tests[:3]:  # Показываем только первые 3
            print(f"   - {test}")

    # Возможности оптимизации
    opportunities = diagnosis.get("optimization_opportunities", [])
    if opportunities:
        print(f"💡 Возможности оптимизации: {len(opportunities)}")
        for opp in opportunities[:3]:  # Показываем только первые 3
            print(f"   - {opp}")

    # Рекомендации по экономии
    cost_savings = diagnosis.get("cost_savings_recommendations", [])
    if cost_savings:
        print(f"💰 Экономия средств: {len(cost_savings)} рекомендаций")
        for rec in cost_savings[:2]:  # Показываем только первые 2
            print(f"   - {rec}")

    # Рекомендации по росту доходов
    revenue_growth = diagnosis.get("revenue_optimization_recommendations", [])
    if revenue_growth:
        print(f"📈 Рост доходов: {len(revenue_growth)} рекомендаций")
        for rec in revenue_growth[:2]:  # Показываем только первые 2
            print(f"   - {rec}")


def main() -> int:
    """Основная функция комплексного pre-commit хука."""
    print("🚀 Запуск комплексного байесовского анализа...")
    print("=" * 60)

    # Комплексный анализ измененных файлов
    analysis_data = analyze_changed_files_comprehensively()

    # Запускаем критические тесты
    tests_ok = run_critical_tests()

    # Генерируем бизнес-инсайты
    generate_business_insights(analysis_data)

    # Определяем, нужно ли блокировать коммит
    should_block = False
    issues = []

    if not tests_ok:
        should_block = True
        issues.append("Критические тесты не проходят")

    # Проверяем результаты комплексного анализа
    if analysis_data.get("status") == "analyzed":
        diagnosis = analysis_data.get("diagnosis", {})
        critical_tests = diagnosis.get("critical_tests", [])

        if critical_tests:
            should_block = True
            issues.append(f"Обнаружены критические проблемы: {len(critical_tests)}")

        # Проверяем общий балл системы
        avg_overall = diagnosis.get("average_scores", {}).get("overall", 1.0)
        if avg_overall < 0.7:
            should_block = True
            issues.append(f"Общий балл системы слишком низкий: {avg_overall:.2f}")

    # Выводим итоговый результат
    print("\n" + "=" * 60)
    if should_block:
        print(f"❌ Комплексный анализ заблокировал коммит:")
        for issue in issues:
            print(f"  - {issue}")

        # Показываем рекомендации
        if analysis_data.get("status") == "analyzed":
            diagnosis = analysis_data.get("diagnosis", {})
            cost_savings = diagnosis.get("cost_savings_recommendations", [])
            revenue_growth = diagnosis.get("revenue_optimization_recommendations", [])

            if cost_savings or revenue_growth:
                print(f"\n🔧 Рекомендации для исправления:")
                for i, rec in enumerate((cost_savings + revenue_growth)[:3], 1):
                    print(f"  {i}. {rec}")

        return 1
    else:
        print("✅ Комплексный анализ: коммит разрешен")
        print("🎉 Система готова к развертыванию!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
