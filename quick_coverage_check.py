#!/usr/bin/env python3
"""
Быстрая проверка покрытия тестов
"""

import subprocess  # nosec B404
import sys


def main():
    print("🚀 Быстрая проверка покрытия")
    print("=" * 40)

    try:
        # Запуск тестов с покрытием
        result = subprocess.run(  # nosec B603
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_missing_coverage.py",
                "--cov-report=term-missing",
                "-v",
            ],
            capture_output=True,
            text=True,
        )

        print("📊 Результат:")
        print(result.stdout)

        if result.stderr:
            print("⚠️ Ошибки:")
            print(result.stderr)

        if result.returncode == 0:
            print("✅ Тесты прошли успешно!")
        else:
            print("❌ Есть ошибки в тестах")

    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    main()
