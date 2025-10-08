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
    in_docstring = False
    docstring_delim = None
    while insert_at < len(lines):
        line = lines[insert_at].strip()
        if (
            line.startswith("#!")
            or "coding:" in lines[insert_at]
            or line.startswith("from __future__")
        ):
            insert_at += 1
        elif not in_docstring and (line.startswith('"""') or line.startswith("'''")):
            in_docstring = True
            docstring_delim = '"""' if line.startswith('"""') else "'''"
            if line.count(docstring_delim) >= 2:  # single-line docstring
                in_docstring = False
            insert_at += 1
        elif in_docstring and docstring_delim in line:
            in_docstring = False
            insert_at += 1
        else:
            break
    lines.insert(insert_at, "import logging")
    return "\n".join(lines) + ("" if text.endswith("\n") else "\n")


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
            updated_lines.append(f"{indent}except Exception:")
            updated_lines.append(
                f"{indent}    logging.exception('Suppressed exception in tests: {file_hint}')"
            )
            updated_lines.append(f"{indent}    pass")
            changed = True
            i += 1
        elif stripped == "except Exception:":
            # Check if logging.exception is already present in this except block
            # Look ahead to see if there's already logging in the next few lines
            has_logging = False
            look_ahead = 0
            while i + look_ahead + 1 < len(lines) and look_ahead < 5:  # Look up to 5 lines ahead
                next_line = lines[i + look_ahead + 1]
                if "logging.exception(" in next_line:
                    has_logging = True
                    break
                # Stop if we hit another except or end of indented block
                if next_line.strip().startswith("except ") or (
                    next_line.strip() and not next_line.startswith(" ")
                ):
                    break
                look_ahead += 1

            if not has_logging:
                # Add logging if not present
                indent = line[: len(line) - len(stripped)]
                updated_lines.append(f"{indent}except Exception:")
                updated_lines.append(
                    f"{indent}    logging.exception('Unexpected exception in tests: {file_hint}')"
                )
                changed = True
                i += 1
            else:
                # Keep existing except block as is
                updated_lines.append(line)
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
