#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки покрытия тестов
"""

import subprocess  # nosec B404
import sys
from pathlib import Path


def run_coverage_check():
    """Запустить проверку покрытия"""
    print("🔍 Проверка покрытия тестов...")
    print("=" * 50)

    try:
        # Запуск тестов с покрытием
        result = subprocess.run(  # nosec B603
            [
                sys.executable,
                "-m",
                "pytest",
                "tests",
                "--cov=.",
                "--cov-report=term-missing",
                "--cov-fail-under=97",
                "-q",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )

        print("📊 Результат проверки покрытия:")
        print(result.stdout)

        if result.stderr:
            print("⚠️  Предупреждения:")
            print(result.stderr)

        if result.returncode == 0:
            print("✅ Покрытие достигнуто!")
        else:
            print("❌ Покрытие недостаточно")

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Ошибка при запуске проверки покрытия: {e}")
        return False


def run_detailed_coverage():
    """Запустить детальную проверку покрытия"""
    print("\n🔍 Детальная проверка покрытия...")
    print("=" * 50)

    try:
        # Запуск с детальным отчетом
        result = subprocess.run(  # nosec B603
            [
                sys.executable,
                "-m",
                "pytest",
                "tests",
                "--cov=.",
                "--cov-report=html:htmlcov",
                "--cov-report=xml:coverage.xml",
                "--cov-report=term-missing",
                "-q",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )

        print("📊 Детальный отчет создан:")
        print("- HTML отчет: htmlcov/index.html")
        print("- XML отчет: coverage.xml")

        if result.stdout:
            print("\n📈 Сводка покрытия:")
            print(result.stdout)

        return True

    except Exception as e:
        print(f"❌ Ошибка при создании детального отчета: {e}")
        return False


def main():
    """Основная функция"""
    print("🚀 Проверка покрытия тестов PulsePlate")
    print("=" * 50)

    # Проверка покрытия
    coverage_ok = run_coverage_check()

    # Детальный отчет
    if coverage_ok:
        run_detailed_coverage()

    print("\n📋 Рекомендации:")
    if not coverage_ok:
        print("1. Проверьте файлы с низким покрытием")
        print("2. Добавьте тесты для недостающих частей")
        print("3. Запустите: python check_coverage.py")
    else:
        print("✅ Покрытие в норме!")
        print("📁 Откройте htmlcov/index.html для детального просмотра")

    return coverage_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
