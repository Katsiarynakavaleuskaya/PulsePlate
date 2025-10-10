#!/usr/bin/env python3
"""
Тестовый скрипт для проверки окружения PulsePlate
"""

from __future__ import annotations

import os
from pathlib import Path
import sys


def check_python_version():
    """Проверить версию Python"""
    print(f"🐍 Python версия: {sys.version}")
    print(f"🐍 Python путь: {sys.executable}")
    return True


def check_imports():
    """Проверить основные импорты"""
    try:
        import fastapi

        print(f"✅ FastAPI: {fastapi.__version__}")
    except ImportError as e:
        print(f"❌ FastAPI: {e}")
        return False

    try:
        import pydantic

        print(f"✅ Pydantic: {pydantic.__version__}")
    except ImportError as e:
        print(f"❌ Pydantic: {e}")
        return False

    try:
        import pytest

        print(f"✅ Pytest: {pytest.__version__}")
    except ImportError as e:
        print(f"❌ Pytest: {e}")
        return False

    return True


def check_project_structure():
    """Проверить структуру проекта"""
    project_root = Path(__file__).parent

    required_dirs = ["app", "core", "tests", "data"]
    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f"✅ Директория {dir_name}: существует")
        else:
            print(f"❌ Директория {dir_name}: отсутствует")
            return False

    return True


def check_environment_variables():
    """Проверить переменные окружения"""
    # Store original environment values for restoration
    original_env = {}
    env_vars_to_set = {
        "VIP_MODULE_ENABLED": "true",
        "API_KEY": "test_key_development",
        "APP_ENV": "development",
    }

    # Store original sys.path for restoration
    original_sys_path = sys.path.copy()

    try:
        # Set environment variables and store originals
        for key, value in env_vars_to_set.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        # Build cross-platform project paths
        project_root = Path(__file__).parent.resolve()
        project_paths = [
            str(project_root),
            str(project_root / "core"),
            str(project_root / "app"),
            str(project_root / "tests"),
        ]

        # Modify sys.path directly (more effective than PYTHONPATH after interpreter start)
        for path in reversed(project_paths):  # Insert in reverse order to maintain priority
            if path not in sys.path:
                sys.path.insert(0, path)

        # Create PYTHONPATH string for display (cross-platform)
        pythonpath_display = os.pathsep.join(project_paths)

        # Print environment info (mask sensitive values)
        print(f"🔧 VIP_MODULE_ENABLED: {os.environ.get('VIP_MODULE_ENABLED')}")
        print(f"🔧 API_KEY: {'*' * 8}[MASKED]")  # Mask the API key for security
        print(f"🔧 APP_ENV: {os.environ.get('APP_ENV')}")
        print(f"🔧 Project paths added to sys.path: {len(project_paths)} entries")
        print(f"🔧 PYTHONPATH equivalent: {pythonpath_display}")

        return True

    finally:
        # Restore original environment variables
        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value

        # Restore original sys.path
        sys.path[:] = original_sys_path


def check_core_imports():
    """Проверить импорты из core"""
    try:
        from core.shoplist import ShoplistGenerator  # noqa: F401

        print("✅ core.shoplist: импорт успешен")
    except ImportError as e:
        print(f"❌ core.shoplist: {e}")
        return False

    try:
        from core.targets import NutritionTargets  # noqa: F401

        print("✅ core.targets: импорт успешен")
    except ImportError as e:
        print(f"❌ core.targets: {e}")
        return False

    return True


def check_app_imports():
    """Проверить импорты из app"""
    try:
        from app import app  # noqa: F401

        print("✅ app: импорт успешен")
    except ImportError as e:
        print(f"❌ app: {e}")
        return False

    return True


def main():
    """Основная функция"""
    print("🚀 Проверка окружения PulsePlate")
    print("=" * 50)

    checks = [
        ("Версия Python", check_python_version),
        ("Основные импорты", check_imports),
        ("Структура проекта", check_project_structure),
        ("Переменные окружения", check_environment_variables),
        ("Импорты core", check_core_imports),
        ("Импорты app", check_app_imports),
    ]

    results = []
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}:")
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ Ошибка в проверке {check_name}: {e}")
            results.append((check_name, False))

    print("\n📊 Результаты:")
    print("=" * 50)
    all_passed = True
    for check_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
        if not result:
            all_passed = False

    if all_passed:
        print("\n🎉 Все проверки прошли успешно!")
        print("📋 Окружение настроено правильно")
        print("📋 Можно запускать тесты и разработку")
    else:
        print("\n⚠️  Некоторые проверки не прошли")
        print("📋 Проверьте ошибки выше")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
