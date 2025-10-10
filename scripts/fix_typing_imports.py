#!/usr/bin/env python3
"""
Автоматически заменяет устаревшие typing imports на современные (PEP 585).

Заменяет:
- typing.Dict -> dict
- typing.List -> list
- typing.Set -> set
- typing.Tuple -> tuple
- typing.Type -> type

Использование:
    python scripts/fix_typing_imports.py
"""

from pathlib import Path
import re
import sys


def fix_file(filepath: Path) -> bool:
    """Исправить typing imports в файле."""
    try:
        content = filepath.read_text(encoding="utf-8")
        original = content

        # Паттерны для замены
        replacements = [
            # from typing import ... -> удаляем устаревшие
            (
                r"from typing import ((?:[A-Z]\w+(?:, )?)+)",
                lambda m: fix_import_line(m.group(0)),
            ),
            # Dict[str, int] -> dict[str, int]
            (r"dict[", "dict["),
            (r"list[", "list["),
            (r"set[", "set["),
            (r"tuple[", "tuple["),
            (r"type[", "type["),
            # Для случаев без скобок (редко, но бывает)
            (r": dict", ": dict"),
            (r": list", ": list"),
            (r": set", ": set"),
            (r": tuple", ": tuple"),
            (r": type", ": type"),
        ]

        for pattern, replacement in replacements:
            if callable(replacement):
                content = re.sub(pattern, replacement, content)
            else:
                content = content.replace(pattern, replacement)

        if content != original:
            filepath.write_text(content, encoding="utf-8")
            return True
        return False

    except Exception as e:
        print(f"❌ Ошибка в {filepath}: {e}", file=sys.stderr)
        return False


def fix_import_line(line: str) -> str:
    """
    Исправить строку импорта, удалив устаревшие типы.

    Примеры:
        'from typing import Any' -> 'from typing import Any'
        '' -> '' (удаляется полностью)
    """
    # Извлекаем список импортов
    match = re.match(r"from typing import (.+)", line)
    if not match:
        return line

    imports = [imp.strip() for imp in match.group(1).split(",")]

    # Устаревшие типы для удаления
    deprecated = {"Dict", "List", "Set", "Tuple", "Type"}

    # Оставляем только не-устаревшие
    kept = [imp for imp in imports if imp not in deprecated]

    if not kept:
        # Если все импорты устаревшие - удаляем строку
        return ""
    else:
        # Возвращаем обновлённый импорт
        return f"from typing import {', '.join(kept)}"


def main():
    """Главная функция."""
    project_root = Path.cwd()
    python_files = list(project_root.rglob("*.py"))

    # Исключаем директории
    exclude_dirs = {
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".git",
        "build",
        "dist",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
    }

    python_files = [
        f for f in python_files if not any(excluded in f.parts for excluded in exclude_dirs)
    ]

    print(f"🔍 Обработка {len(python_files)} Python файлов...")

    fixed = 0
    for filepath in python_files:
        if fix_file(filepath):
            print(f"✅ {filepath.relative_to(project_root)}")
            fixed += 1

    print(f"\n{'='*80}")
    print(f"✅ Исправлено файлов: {fixed}/{len(python_files)}")
    print(f"{'='*80}")

    return 0 if fixed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())

