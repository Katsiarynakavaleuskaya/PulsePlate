import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEST_DIRS = [ROOT / "tests"]
FILES = [
    "tests/test_simple_coverage_fixed.py",
    "tests/test_specific_lines_coverage.py",
    "tests/test_targeted_coverage_boost.py",
    "tests/test_targets_realistic_coverage.py",
    "tests/test_zero_coverage_modules.py",
]

EXCEPT_PATTERNS = [
    # "except Exception: pass" -> "except Exception:\n    logging.exception(...)"
    re.compile(r"(\s*)except\s+Exception\s*:\s*pass\s*$", re.MULTILINE),
    # "except Exception:" (без pass) -> добавить logging.exception(...)
    re.compile(r"(\s*)except\s+Exception\s*:\s*$", re.MULTILINE),
]


def ensure_logging_import(text: str) -> str:
    """Гарантирует корректный top-level `import logging` (вне докстринга)."""
    lines = text.splitlines()
    # Уже импортирован?
    for _i, line in enumerate(lines[:50]):  # быстрый поиск в верхнем блоке файла
        s = line.strip()
        if s.startswith("import logging") or s.startswith("from logging"):
            return text

    insert_at = 0
    in_docstring = False
    doc_delim = None

    # Пропускаем shebang/encoding/__future__/первый модульный докстринг целиком
    while insert_at < len(lines):
        raw = lines[insert_at]
        s = raw.strip()
        if s.startswith("#!"):
            insert_at += 1
            continue
        if "coding:" in raw:
            insert_at += 1
            continue
        if s.startswith("from __future__"):
            insert_at += 1
            continue
        # вход в докстринг
        if not in_docstring and (s.startswith('"""') or s.startswith("'''")):
            delim = '"""' if s.startswith('"""') else "'''"
            # если одно-строчный докстринг (открытие/закрытие на одной строке)
            if s.count(delim) >= 2:
                insert_at += 1
                continue
            in_docstring = True
            doc_delim = delim
            insert_at += 1
            continue
        # выход из докстринга
        if in_docstring:
            if doc_delim and doc_delim in s:
                in_docstring = False
                doc_delim = None
            insert_at += 1
            continue
        break

    lines.insert(insert_at, "import logging")
    return "\n".join(lines) + ("\n" if not text.endswith("\n") else "")


def replace_bare_except(text: str, file_hint: str) -> str:
    updated = text
    # "except Exception: pass"
    updated = EXCEPT_PATTERNS[0].sub(
        lambda m: f"{m.group(1)}except Exception:\n{m.group(1)}    logging.exception('Suppressed exception in tests: {file_hint}')\n",
        updated,
    )
    # "except Exception:" без pass
    updated = EXCEPT_PATTERNS[1].sub(
        lambda m: f"{m.group(1)}except Exception:\n{m.group(1)}    logging.exception('Unexpected exception in tests: {file_hint}')\n",
        updated,
    )
    if updated != text:
        updated = ensure_logging_import(updated)
        # Дополнительно: если ранее кто-то вставил 'import logging' ВНУТРЬ докстринга — перенесём наверх
        updated = move_import_out_of_top_docstring(updated)
    return updated


def move_import_out_of_top_docstring(text: str) -> str:
    """Если 'import logging' оказался внутри первого модульного докстринга — вытащить его наружу."""
    lines = text.splitlines()
    # Найдём границы первого докстринга (если есть)
    start = None
    end = None
    delim = None
    for idx, line in enumerate(lines[:200]):
        s = line.strip()
        if start is None and (s.startswith('"""') or s.startswith("'''")):
            delim = '"""' if s.startswith('"""') else "'''"
            if s.count(delim) >= 2:
                # одно-строчный докстринг — нечего двигать
                return text
            start = idx
            continue
        if start is not None and delim and delim in s:
            end = idx
            break
    if start is None or end is None:
        return text
    # Проверим, нет ли import logging внутри [start, end]
    moved = False
    new_block = []
    for i in range(start + 1, end):
        if lines[i].strip().startswith("import logging"):
            # вырезаем из докстринга
            lines[i] = ""
            moved = True
    if not moved:
        return text
    # Теперь гарантируем корректный import сверху
    text2 = "\n".join(line for line in lines if line != "")
    return ensure_logging_import(text2)


def main() -> int:
    changed = 0
    errors = 0
    for rel in FILES:
        path = ROOT / rel
        if not path.exists():
            continue
        try:
            orig = path.read_text(encoding="utf-8")
            new = replace_bare_except(orig, path.name)
            if new != orig:
                path.write_text(new, encoding="utf-8")
                changed += 1
                print(f"[codemod] fixed bare except in {path}")
        except Exception as exc:  # noqa: BLE001 - сознательно логируем любые IO/parse ошибки
            errors += 1
            print(f"[codemod] ERROR processing {path}: {exc}")
    print(f"[codemod] total files changed: {changed}")
    if errors:
        print(f"[codemod] total errors: {errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
