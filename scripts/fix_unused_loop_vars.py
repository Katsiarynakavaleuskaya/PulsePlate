#!/usr/bin/env python3
"""
Автоматически исправляет B007 - переименовывает неиспользуемые loop переменные с _ префиксом.

Использование:
    python scripts/fix_unused_loop_vars.py
"""

from pathlib import Path
import re
import subprocess  # nosec B404
import sys


def get_b007_errors() -> list[tuple[str, int, str]]:
    """Получить список B007 ошибок из Ruff."""
    result = subprocess.run(  # nosec B607, B603
        ["ruff", "check", "--select", "B007", ".", "--output-format", "json"],
        capture_output=True,
        text=True,
    )

    if result.returncode not in (0, 1):
        print(f"❌ Ошибка Ruff: {result.stderr}", file=sys.stderr)
        return []

    import json

    errors = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            data = json.loads(line)
            filepath = data["filename"]
            line_num = data["location"]["row"]
            message = data["message"]

            # Extract variable name from message
            # "Loop control variable `sport` not used within loop body"
            match = re.search(r"Loop control variable `(\w+)`", message)
            if match:
                var_name = match.group(1)
                errors.append((filepath, line_num, var_name))
        except (json.JSONDecodeError, KeyError):
            continue

    return errors


def fix_file(filepath: str, line_num: int, var_name: str) -> bool:
    """Исправить неиспользуемую loop переменную в файле."""
    try:
        path = Path(filepath)
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

        if line_num < 1 or line_num > len(lines):
            return False

        # Строка с индексом line_num-1 (нумерация с 1)
        line = lines[line_num - 1]

        # Заменяем только первое вхождение переменной в for loop
        # Паттерн: for var_name, ... in ...
        escaped_var = re.escape(var_name)
        new_line = re.sub(
            rf"\bfor\s+{escaped_var}\b",
            f"for _{var_name}",
            line,
            count=1,
        )

        if new_line != line:
            lines[line_num - 1] = new_line
            path.write_text("".join(lines), encoding="utf-8")
            return True

        return False

    except (OSError, UnicodeDecodeError, ValueError) as e:
        print(f"❌ Ошибка в {filepath}:{line_num}: {e}", file=sys.stderr)
        return False


def main():
    """Главная функция."""
    print("🔍 Поиск B007 ошибок...")
    errors = get_b007_errors()

    if not errors:
        print("✅ B007 ошибок не найдено!")
        return 0

    print(f"📋 Найдено {len(errors)} ошибок B007")

    fixed = 0
    for filepath, line_num, var_name in errors:
        if fix_file(filepath, line_num, var_name):
            print(f"✅ {filepath}:{line_num} - {var_name} → _{var_name}")
            fixed += 1

    print(f"\n{'=' * 80}")
    print(f"✅ Исправлено: {fixed}/{len(errors)}")
    print(f"{'=' * 80}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
