#!/usr/bin/env python3
"""Quick test coverage check. / Быстрая проверка покрытия тестов."""

import os
import subprocess  # nosec B404 - importing subprocess to invoke pytest for coverage checks; safe because we control the command and arguments
import sys

try:
    COVERAGE_CHECK_TIMEOUT = int(os.getenv("COVERAGE_CHECK_TIMEOUT", "300"))
    if COVERAGE_CHECK_TIMEOUT <= 0:
        raise ValueError("Timeout must be positive")
except ValueError as e:
    print(f"❌ Invalid COVERAGE_CHECK_TIMEOUT: {e}")
    sys.exit(1)


def main() -> None:
    """Run a quick single-file coverage check and print results."""
    print("🚀 Quick coverage check / Быстрая проверка покрытия")
    print("=" * 40)

    try:
        # Run tests with coverage / Запуск тестов с покрытием
        result = subprocess.run(  # nosec B603 - safe: args passed as list, shell=False
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_missing_coverage.py",
                "tests/test_food_store_additional_coverage.py",
                "tests/test_app_dependencies_additional.py",
                "tests/test_foods_router_additional.py",
                "tests/test_recipe_store_additional.py",
                "tests/test_weekly_plan_additional.py",
                "--cov=app",
                "--cov-report=term-missing",
                "-v",
            ],
            capture_output=True,
            text=True,
            timeout=COVERAGE_CHECK_TIMEOUT,
        )

        print("📊 Results / Результат:")
        print(result.stdout)

        if result.stderr:
            print("⚠️ Errors / Ошибки:")
            print(result.stderr)

        if result.returncode == 0:
            print("✅ Tests passed successfully! / Тесты прошли успешно!")
        else:
            print("❌ Tests have errors / Есть ошибки в тестах")
            sys.exit(result.returncode)

    except subprocess.TimeoutExpired:
        print(
            f"⏳ Coverage check timeout ({COVERAGE_CHECK_TIMEOUT}s). CI stopped. / "
            f"Таймаут при запуске проверки покрытия ({COVERAGE_CHECK_TIMEOUT}s). CI остановлен."
        )
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error / Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
