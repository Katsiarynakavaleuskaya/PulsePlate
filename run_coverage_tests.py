#!/usr/bin/env python3
"""
Скрипт для запуска тестов покрытия и проверки достижения 97%
"""

import os
import subprocess  # nosec B404: required for fixed local pytest subprocesses (remove-by: 2026-06-30, ref: PR-1113)
import sys


def run_command(cmd, description):
    """Запуск команды с выводом результата"""
    print(f"\n🚀 {description}")
    print(f"Команда: {' '.join(cmd)}")
    print("=" * 60)

    result = subprocess.run(  # nosec B603: argv uses sys.executable + fixed local pytest args only (remove-by: 2026-06-30, ref: PR-1113)
        cmd,
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
    )

    print("STDOUT:")
    print(result.stdout)

    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)

    print(f"\nReturn code: {result.returncode}")
    print("=" * 60)

    return result


def main():
    print("📊 Запуск проверки покрытия тестов для достижения 97%")

    # Сначала запустим быстрые точечные тесты новых файлов
    quick_tests = [
        (
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_food_db_new_missing_lines.py",
                "-v",
                "--tb=short",
            ],
            "Тестирование точечных кейсов для core/food_db_new.py",
        ),
        (
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_app_coverage_final.py",
                "-v",
                "--tb=short",
            ],
            "Тестирование новых файлов покрытия app.py",
        ),
        (
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_unified_db_coverage.py",
                "-v",
                "--tb=short",
            ],
            "Тестирование новых файлов покрытия unified_db.py",
        ),
    ]

    for cmd, description in quick_tests:
        result = run_command(cmd, description)
        if result.returncode != 0:
            print("❌ Один из быстрых тестов не прошёл, исправляем...")
            return 1

    # Теперь запустим полное покрытие
    print("\n🔍 Проверка общего покрытия с целью 97%...")

    cmd3 = [
        sys.executable,
        "-m",
        "pytest",
        "tests",
        "--cov=app",
        "--cov=core",
        "--cov-report=term-missing",
        "--cov-fail-under=97",
        "-x",  # Остановиться на первой ошибке
    ]

    result3 = run_command(cmd3, "Полная проверка покрытия (цель: 97%)")

    if result3.returncode == 0:
        print("🎉 ПОКРЫТИЕ 97%+ ДОСТИГНУТО! ✅")
        print("\nМожно переходить к pre-commit и push:")
        print("make lint")
        print("make safe-push")
        return 0
    else:
        print("❌ Покрытие еще не достигло 97%")
        print("\nНужно добавить еще тесты для недостающих строк")

        # Попробуем получить краткий отчет покрытия
        cmd4 = [
            sys.executable,
            "-m",
            "pytest",
            "tests",
            "--cov=app",
            "--cov=core",
            "--cov-report=term-missing",
            "--tb=no",
            "-q",
        ]

        run_command(cmd4, "Краткий отчет покрытия")

        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
