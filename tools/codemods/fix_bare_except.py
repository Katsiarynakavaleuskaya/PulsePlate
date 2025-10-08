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
    # "except Exception: pass" - replace with proper exception handling
    re.compile(r"(\s*)except\s+Exception\s*:\s*pass\s*$", re.MULTILINE),
    # "except Exception:" followed by indented content - replace with proper exception handling
    re.compile(r"(\s*)except\s+Exception\s*:\s*$", re.MULTILINE),
]


def ensure_logging_import(text: str) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines[:30]):  # ищем в первой трети для скорости
        if line.strip().startswith("import logging") or line.strip().startswith("from logging"):
            return text
    # Вставим после возможной строки с будущим __future__/docstring/encoding
    insert_at = 0
    # пропустим шебанг / кодировку / __future__ / docstring блок
    while insert_at < len(lines) and (
        lines[insert_at].startswith("#!")
        or "coding:" in lines[insert_at]
        or lines[insert_at].strip().startswith("from __future__")
        or lines[insert_at].strip().startswith('"""')
        or lines[insert_at].strip().startswith("'''")
    ):
        insert_at += 1
    lines.insert(insert_at, "import logging")
    return "\n".join(lines) + ("\n" if not text.endswith("\n") else "")


def replace_bare_except(text: str, file_hint: str) -> str:
    lines = text.splitlines()
    updated_lines = []
    i = 0
    changed = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped == "except Exception: pass":
            # Replace "except Exception: pass" with proper logging
            indent = line[: len(line) - len(stripped)]
            updated_lines.append(f"{indent}except Exception as e:")
            updated_lines.append(
                f"{indent}    logging.exception('Suppressed exception in tests: {file_hint}')"
            )
            changed = True
            i += 1
        elif stripped == "except Exception:":
            # Replace "except Exception:" with proper logging
            indent = line[: len(line) - len(stripped)]
            updated_lines.append(f"{indent}except Exception as e:")
            updated_lines.append(
                f"{indent}    logging.exception('Unexpected exception in tests: {file_hint}')"
            )
            changed = True
            i += 1
        else:
            updated_lines.append(line)
            i += 1

    result = "\n".join(updated_lines)
    if changed:
        result = ensure_logging_import(result)
    return result


def main() -> int:
    changed = 0
    for rel in FILES:
        path = ROOT / rel
        if not path.exists():
            continue
        orig = path.read_text(encoding="utf-8")
        new = replace_bare_except(orig, path.name)
        if new != orig:
            path.write_text(new, encoding="utf-8")
            changed += 1
            print(f"[codemod] fixed bare except in {path}")
    print(f"[codemod] total files changed: {changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
