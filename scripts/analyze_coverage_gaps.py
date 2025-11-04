#!/usr/bin/env python3
"""
Анализ непокрытых строк для достижения 97% покрытия тестами.
"""

import os
import re
import subprocess  # nosec B404
import sys
import warnings
from typing import List


def parse_timeout_env(env_var: str, default: int = 180) -> int:
    """Parse timeout value from environment variable with fallback.

    Args:
        env_var: Environment variable name to read.
        default: Default timeout value in seconds if parsing fails.

    Returns:
        int: Parsed timeout value or default if parsing fails.
    """
    value = os.environ.get(env_var)
    if value is None:
        return default

    # Strip whitespace before parsing
    value = value.strip()
    if not value:
        return default

    try:
        return int(value)
    except ValueError:
        warnings.warn(
            f"Invalid value '{value}' for {env_var}. "
            f"Expected integer, falling back to default {default} seconds.",
            UserWarning,
        )
        return default


def run_coverage_analysis() -> bool:
    """Запустить анализ покрытия и получить детальную информацию.

    Returns:
        bool: True если анализ и запуск тестов завершились успешно, иначе False.
    """
    print("🔍 Анализ покрытия тестами...")

    # Устанавливаем переменные окружения
    os.environ.update(
        {
            "PYTHONPATH": ".:core:app:tests",
            "VIP_MODULE_ENABLED": "true",
            "FEATURE_PREMIUM_NUTRITION": "true",
            "API_KEY": "test_key",  # nosec B105  # Coverage analysis only
            "APP_ENV": "test",
            "ALLOW_DEV_API_KEY": "true",
        }
    )

    # Запускаем pytest с детальным отчетом покрытия
    # Timeout configurable via COVERAGE_TEST_TIMEOUT env var, default 180 seconds
    test_timeout = parse_timeout_env("COVERAGE_TEST_TIMEOUT", default=180)

    try:
        result = subprocess.run(  # nosec B603
            [
                sys.executable,
                "-m",
                "pytest",
                "--cov=.",
                "--cov-report=term-missing",
                "--cov-report=html",
                "-q",
                "--maxfail=5",
            ],
            capture_output=True,
            text=True,
            timeout=test_timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"❌ pytest execution timed out after {test_timeout} seconds")
        return False

    if result.returncode != 0:
        print(f"❌ pytest execution failed with return code {result.returncode}")
        if result.stderr:
            print(f"Error output: {result.stderr}")
        return False

    print("📊 Результаты покрытия:")
    print(result.stdout)

    if result.stderr:
        print("⚠️ Предупреждения:")
        print(result.stderr)

    # Анализируем основные файлы с низким покрытием
    critical_files: List[str] = ["app.py", "app/routers/vip.py", "conftest.py"]

    print("\n🎯 Критические файлы для улучшения покрытия:")
    for file in critical_files:
        print(f"  - {file}")

    print("\n📈 Рекомендации:")
    print("1. Добавить тесты для непокрытых строк в app.py")
    print("2. Улучшить тестирование VIP endpoints")
    print("3. Добавить тесты для conftest.py")
    print("4. Проверить htmlcov/index.html для детального анализа")

    # Parse coverage percentage from output
    coverage_pct = None
    # Look for "TOTAL ... XX%" or "TOTAL ... XX.X%" pattern in the output
    # More robust regex that handles integer or decimal percentages
    coverage_pattern = r"TOTAL\s+\d+\s+\d+\s+(?:\d+\s+)?(\d+(?:\.\d+)?)%"
    match = re.search(coverage_pattern, result.stdout)
    if match:
        coverage_pct = float(match.group(1))
    else:
        # Try alternative pattern if the first one doesn't match
        alt_pattern = r"TOTAL\s+.*?(\d+(?:\.\d+)?)%"
        alt_match = re.search(alt_pattern, result.stdout)
        if alt_match:
            coverage_pct = float(alt_match.group(1))

    if coverage_pct is not None:
        if coverage_pct < 97:
            print(f"\n❌ Coverage is {coverage_pct}%, which is below the required 97% threshold.")
            return False
        else:
            print(f"\n✅ Coverage is {coverage_pct}%, meeting the required 97% threshold.")
            return True
    else:
        # If we can't parse coverage, fail to ensure coverage gate is not bypassed
        print("\n❌ Could not parse coverage percentage from pytest output.")
        print("Please check the output format or update the regex patterns.")
        return False


if __name__ == "__main__":
    success: bool = run_coverage_analysis()
    sys.exit(0 if success else 1)
