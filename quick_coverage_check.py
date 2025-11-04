#!/usr/bin/env python3
"""Quick test coverage check. / Быстрая проверка покрытия тестов."""

import subprocess  # nosec B404 - importing subprocess to invoke pytest for coverage checks; safe because we control the command and arguments
import sys


def main() -> None:
    """Run a quick single-file coverage check and print results."""
    print("🚀 Quick coverage check / Быстрая проверка покрытия")
    print("=" * 40)

    try:
        # Run tests with coverage / Запуск тестов с покрытием
        result = subprocess.run(  # nosec B603
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_missing_coverage.py",
                "--cov=app",
                "--cov-report=term-missing",
                "-v",
            ],
            capture_output=True,
            text=True,
            timeout=300,
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

    except subprocess.TimeoutExpired:
        print(
            "⏳ Coverage check timeout (300s). CI stopped. / "
            "Таймаут при запуске проверки покрытия (300s). CI остановлен."
        )
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error / Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
