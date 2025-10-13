#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PulsePlate Development Environment Setup.

Скрипт для настройки среды разработки PulsePlate.
"""

import os
import shlex
import subprocess  # nosec B404
import sys
from pathlib import Path


def run_command(cmd: str, description: str) -> bool:
    """Запустить команду и вернуть результат."""
    print(f"🔄 {description}...")
    try:
        # Use shlex.split() for safe command parsing to avoid injection
        cmd_list = shlex.split(cmd)
        result = subprocess.run(cmd_list, capture_output=True, text=True)  # nosec B603
        if result.returncode == 0:
            print(f"✅ {description} - успешно")
            return True
        else:
            print(f"❌ {description} - ошибка: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - исключение: {e}")
        return False


def check_python_version():
    """Проверить версию Python."""
    version = sys.version_info
    print(f"🐍 Python версия: {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("⚠️  Рекомендуется Python 3.10+")
        return False
    return True


def check_dependencies():
    """Проверить зависимости."""
    required_packages = [
        "fastapi",
        "pydantic",
        "pytest",
        "black",
        "flake8",
        "hypothesis",
        "uvicorn",
        "httpx",
    ]

    print("📦 Проверка зависимостей...")
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - не установлен")
            return False
    return True


def setup_environment():
    """Настроить переменные окружения."""
    project_root = Path(__file__).parent
    pythonpath = ":".join(
        [
            str(project_root),
            str(project_root / "core"),
            str(project_root / "app"),
            str(project_root / "tests"),
        ]
    )

    os.environ["PYTHONPATH"] = pythonpath
    os.environ["VIP_MODULE_ENABLED"] = "true"

    print(f"🔧 PYTHONPATH: {pythonpath}")
    print(f"🔧 VIP_MODULE_ENABLED: {os.environ.get('VIP_MODULE_ENABLED')}")


def run_tests():
    """Запустить тесты."""
    return run_command("python -m pytest tests -q", "Запуск тестов")


def run_coverage():
    """Запустить проверку покрытия."""
    return run_command(
        "python -m pytest tests --cov=. --cov-report=term-missing --cov-fail-under=97 -q",
        "Проверка покрытия",
    )


def run_linting():
    """Запустить линтинг."""
    return run_command("python -m flake8 .", "Линтинг кода")


def format_code():
    """Форматировать код."""
    return run_command("python -m black . --line-length=100", "Форматирование кода")


def main():
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
