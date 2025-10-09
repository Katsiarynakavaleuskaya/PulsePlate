import re
import sys
from pathlib import Path
from typing import Match

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


def dedupe_match(match: Match[str]) -> str:
    """Keep only the first logging.exception line from duplicates"""
    lines = match.group(0).splitlines()
    # Find the first logging.exception line and preserve its formatting
    for line in lines:
        if "logging.exception(" in line:
            return line + "\n"
    return ""


def ensure_logging_import(text: str) -> str:
    lines = text.splitlines()
    for line in lines[:30]:  # search in first third for speed
        if line.strip().startswith("import logging") or line.strip().startswith("from logging"):
            return text
    # Insert after possible shebang/__future__/docstring/encoding line
    insert_at = 0
    in_docstring = False
    docstring_delim = None
    while insert_at < len(lines):
        raw = lines[insert_at]
        line = raw.strip()
        if line.startswith("#!") or "coding:" in line or line.startswith("from __future__"):
            insert_at += 1
        elif not in_docstring and (line.startswith('"""') or line.startswith("'''")):
            in_docstring = True
            docstring_delim = '"""' if line.startswith('"""') else "'''"
            if line.endswith(docstring_delim) and len(line) > 6:  # single-line docstring """..."""
                in_docstring = False
            insert_at += 1
        elif in_docstring and docstring_delim in line:
            in_docstring = False
            insert_at += 1
        else:
            break
    lines.insert(insert_at, "import logging")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


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
            base_indent = len(line) - len(stripped)
            look_ahead = 0
            while i + look_ahead + 1 < len(lines):
                next_line = lines[i + look_ahead + 1]
                stripped_next = next_line.strip()
                if "logging.exception(" in next_line:
                    has_logging = True
                    break
                if stripped_next.startswith(("except ", "finally")):
                    break
                # stop when dedent out of current block
                if stripped_next and (len(next_line) - len(next_line.lstrip())) <= base_indent:
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

    # Deduplicate consecutive logging.exception calls
    result = re.sub(
        r"(\s*logging\.exception\([^\n]+\)\s*\n){2,}",
        dedupe_match,
        result,
    )

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
