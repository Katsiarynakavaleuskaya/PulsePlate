#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Настройка среды разработки PulsePlate."""

import os
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Iterable, Sequence


def run_command(cmd: Iterable[str], description: str) -> bool:
    """Execute command and report success."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(  # nosec B603  # noqa: S603
            list(cmd), capture_output=True, text=True, check=False, timeout=300
        )
    except (OSError, subprocess.TimeoutExpired) as exc:  # pragma: no cover - safeguard
        print(f"❌ {description} - исключение: {exc}")
        return False

    if result.returncode == 0:
        print(f"✅ {description} - успешно")
        return True

    if result.stdout:
        print(f"ℹ️ stdout: {result.stdout}")
    print(f"❌ {description} - ошибка: {result.stderr}")
    return False


def check_python_version() -> bool:
    """Проверить версию Python."""
    version = sys.version_info
    print(f"🐍 Python версия: {version.major}.{version.minor}.{version.micro}")
    if (version.major, version.minor, version.micro) < (3, 13, 5):
        print("⚠️  Рекомендуется Python 3.13.6+")
        return False
    return True


def check_dependencies() -> bool:
    """Проверить зависимости."""
    required_packages: Sequence[str] = [
        "fastapi",
        "pydantic",
        "pytest",
        "ruff",
        "hypothesis",
        "uvicorn",
        "httpx",
    ]

    print("📦 Проверка зависимостей...")
    missing: list[str] = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing.append(package)
    if missing:
        print(f"❌ Не установлены: {', '.join(missing)}")
        return False
    return True


def setup_environment() -> None:
    """Настроить переменные окружения."""
    project_root = Path(__file__).parent
    pythonpath = os.pathsep.join(
        [
            str(project_root),
            str(project_root / "core"),
            str(project_root / "app"),
            str(project_root / "tests"),
        ]
    )

    existing = os.environ.get("PYTHONPATH")
    os.environ["PYTHONPATH"] = pythonpath + os.pathsep + existing if existing else pythonpath
    os.environ["VIP_MODULE_ENABLED"] = "true"

    print(f"🔧 PYTHONPATH: {pythonpath}")
    print(f"🔧 VIP_MODULE_ENABLED: {os.environ.get('VIP_MODULE_ENABLED')}")


def run_tests() -> bool:
    """Запустить тесты."""
    return run_command([sys.executable, "-m", "pytest", "tests", "-q"], "Запуск тестов")


def run_coverage() -> bool:
    """Запустить проверку покрытия."""
    return run_command(
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
        "Проверка покрытия",
    )


def run_linting() -> bool:
    """Запустить линтинг (ruff check)."""
    return run_command([sys.executable, "-m", "ruff", "check", "."], "Ruff linting")


def format_code() -> bool:
    """Форматировать код (ruff format)."""
    return run_command([sys.executable, "-m", "ruff", "format", "."], "Ruff форматирование")


def main() -> bool:
    """Основная функция."""
    print("🚀 Настройка среды разработки PulsePlate")
    print("=" * 50)

    # Проверки
    if not check_python_version():
        print("❌ Неподходящая версия Python")
        return False

    if not check_dependencies():
        print("❌ Отсутствуют необходимые зависимости")
        return False

    # Настройка окружения
    setup_environment()

    # Проверки качества кода
    print("\n🔍 Проверка качества кода...")
    tests_ok = run_tests()
    coverage_ok = run_coverage()
    linting_ok = run_linting()
    formatting_ok = format_code()

    # Результат
    print("\n📊 Результаты:")
    print(f"Тесты: {'✅' if tests_ok else '❌'}")
    print(f"Покрытие: {'✅' if coverage_ok else '❌'}")
    print(f"Линтинг: {'✅' if linting_ok else '❌'}")
    print(f"Форматирование: {'✅' if formatting_ok else '❌'}")

    if all([tests_ok, coverage_ok, linting_ok, formatting_ok]):
        print("\n🎉 Среда разработки настроена успешно!")
        print("📋 Доступные команды:")
        print("  - pptest - запустить тесты")
        print("  - ppcov - проверить покрытие")
        print("  - pplint - запустить линтинг")
        print("  - ppformat - форматировать код")
        print("  - ppcheck - полная проверка")
        print("  - ppserver - запустить сервер")
        print("  - pppython - запустить Python с настройками")
        return True
    else:
        print("\n⚠️  Некоторые проверки не прошли. Проверьте ошибки выше.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
