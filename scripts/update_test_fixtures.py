#!/usr/bin/env python3
"""
Скрипт для обновления тестовых файлов для использования фикстуры test_client
"""

import re
from pathlib import Path


def update_test_file(file_path: Path) -> None:
    """Обновить тестовый файл для использования фикстуры test_client"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Паттерны для замены
    patterns = [
        # Заменить создание TestClient в тестах - добавить capture groups
        (
            r"def (test_\w+)\(self, test_environment\):",
            r"def \1(self, test_environment, test_client):",
        ),
        (
            r"def (test_\w+)\(self, production_environment\):",
            r"def \1(self, production_environment, test_client):",
        ),
        (
            r"def (test_\w+)\(self, premium_disabled_environment\):",
            r"def \1(self, premium_disabled_environment, test_client):",
        ),
        # Заменить создание TestClient - более гибкий паттерн
        (r"client = TestClient\(app\.app\)", r"client = test_client"),
    ]

    # Применить замены
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    # Убрать импорт TestClient если он больше не нужен
    if "client = test_client" in content and "TestClient(" not in content:
        content = re.sub(r"from fastapi\.testclient import TestClient\n", "", content)

    # Записать обновленный файл
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Updated: {file_path}")


def main() -> None:
    """Основная функция"""
    tests_dir = Path("tests")

    # Найти все тестовые файлы
    test_files = list(tests_dir.glob("test_*.py"))

    print(f"Found {len(test_files)} test files")

    for test_file in test_files:
        if test_file.name.startswith("test_vip_import_fallback_coverage"):
            continue  # Пропустить уже обновленный файл

        try:
            update_test_file(test_file)
        except Exception as e:
            print(f"Error updating {test_file}: {e}")


if __name__ == "__main__":
    main()
