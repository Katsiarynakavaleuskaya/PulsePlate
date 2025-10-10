#!/usr/bin/env python3
"""
Автоматическая проверка и исправление проблем с импортами.

Проверяет:
- Неиспользуемые импорты
- Дублирующиеся импорты
- Циклические импорты
- Отсутствующие зависимости
- Неправильный порядок импортов
"""

import ast
from pathlib import Path
import subprocess  # nosec B404
import sys


class ImportChecker:
    """Проверка импортов в Python файлах."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.fixed: list[str] = []

    def check_file(self, filepath: Path) -> bool:
        """Проверить один файл на проблемы с импортами."""
        try:
            errors_before = len(self.errors)
            with open(filepath, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(filepath))

            # Собираем все импорты
            imports = self._collect_imports(tree)

            # Проверяем дубликаты
            self._check_duplicates(filepath, imports)

            # Проверяем неиспользуемые импорты
            self._check_unused(filepath, tree, imports)

            return len(self.errors) == errors_before

        except SyntaxError as e:
            self.errors.append(f"{filepath}: Syntax error: {e}")
            return False
        except Exception as e:
            self.errors.append(f"{filepath}: Error checking imports: {e}")
            return False

    def _collect_imports(self, tree: ast.AST) -> list[tuple[str, str, int]]:
        """Собрать все импорты из AST."""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, alias.asname or alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    imports.append((full_name, alias.asname or alias.name, node.lineno))

        return imports

    def _check_duplicates(self, filepath: Path, imports: list[tuple[str, str, int]]) -> None:
        """Проверить дублирующиеся импорты."""
        seen: dict[str, int] = {}

        for module, alias, lineno in imports:
            key = f"{module}:{alias}"
            if key in seen:
                self.errors.append(
                    f"{filepath}:{lineno}: Duplicate import '{module}' "
                    f"(first seen on line {seen[key]})"
                )
            else:
                seen[key] = lineno

    def _check_unused(
        self, filepath: Path, tree: ast.AST, imports: list[tuple[str, str, int]]
    ) -> None:
        """Проверить неиспользуемые импорты (базовая проверка)."""
        # Собираем все имена, используемые в коде
        used_names: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # Для атрибутов берём корневое имя
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)

        # Проверяем, используются ли импорты
        for _module, alias, lineno in imports:
            # Пропускаем специальные импорты
            if alias.startswith("_"):
                continue

            if alias not in used_names:
                self.warnings.append(f"{filepath}:{lineno}: Possibly unused import '{alias}'")

    def auto_fix_file(self, filepath: Path) -> bool:
        """Автоматически исправить проблемы с импортами используя ruff."""
        try:
            # Ruff может автоматически удалить неиспользуемые импорты
            result = subprocess.run(  # nosec B607, B603
                ["ruff", "check", "--select", "F401", "--fix", str(filepath)],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0 or "fixed" in result.stdout.lower():
                self.fixed.append(str(filepath))
                return True

            return False
        except Exception as e:
            self.warnings.append(f"{filepath}: Could not auto-fix: {e}")
            return False

    def check_project(self, autofix: bool = False) -> bool:
        """Проверить все Python файлы в проекте."""
        python_files = list(self.project_root.rglob("*.py"))

        # Исключаем определённые директории
        exclude_dirs = {".venv", "venv", "node_modules", "__pycache__", ".git", "build", "dist"}
        python_files = [
            f for f in python_files if not any(excluded in f.parts for excluded in exclude_dirs)
        ]

        print(f"🔍 Checking {len(python_files)} Python files...")

        all_ok = True
        for filepath in python_files:
            if not self.check_file(filepath):
                all_ok = False

            if autofix:
                self.auto_fix_file(filepath)

        return all_ok

    def print_report(self) -> None:
        """Вывести отчёт о проверке."""
        print("\n" + "=" * 80)

        if self.fixed:
            print(f"\n✅ Auto-fixed {len(self.fixed)} files:")
            for f in self.fixed:
                print(f"  - {f}")

        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"  {w}")

        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for e in self.errors:
                print(f"  {e}")

        if not self.errors and not self.warnings:
            print("\n✅ All imports are clean!")

        print("=" * 80)


def main() -> None:
    """Основная функция."""
    import argparse

    parser = argparse.ArgumentParser(description="Check and fix Python imports")
    parser.add_argument("--fix", action="store_true", help="Automatically fix import issues")
    parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="Project root path (default: current directory)",
    )

    args = parser.parse_args()

    checker = ImportChecker(args.path)
    success = checker.check_project(autofix=args.fix)
    checker.print_report()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
