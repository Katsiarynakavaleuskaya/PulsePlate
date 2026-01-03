# -*- coding: utf-8 -*-
"""
RU: Repo policy guard — запрещает мутации sys.modules в тестах.
EN: Repo policy guard — forbids sys.modules mutations in tests.

Why:
- sys.modules mutations create dual-module state
- patch()/monkeypatch become unreliable
- tests become nondeterministic
"""

from __future__ import annotations

import re
from pathlib import Path


TESTS_DIR = Path("tests")

FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    # RU: Удаление из sys.modules приводит к двойным модулям и ломает patch().
    # EN: Deleting sys.modules entries can create dual-module state and break patch().
    (r"\bdel\s+sys\.modules\s*\[", "Forbidden: `del sys.modules[...]` in tests."),
    # RU: Переприсваивание sys.modules[...] = ... также опасно.
    # EN: Assigning sys.modules[...] = ... is also dangerous.
    (r"\bsys\.modules\s*\[[^\]]+\]\s*=", "Forbidden: `sys.modules[...] = ...` in tests."),
]


def _iter_test_py_files() -> list[Path]:
    if not TESTS_DIR.exists():
        return []
    return sorted(p for p in TESTS_DIR.rglob("*.py") if p.is_file())


def _find_violations(text: str) -> list[tuple[int, str]]:
    """
    Returns list of (line_number_1_based, message).
    """
    violations: list[tuple[int, str]] = []
    lines = text.splitlines()

    compiled = [(re.compile(pat), msg) for pat, msg in FORBIDDEN_PATTERNS]
    for i, line in enumerate(lines, start=1):
        for rx, msg in compiled:
            if rx.search(line):
                violations.append((i, msg))
    return violations


def test_repo_policy_forbid_sys_modules_mutations_in_tests() -> None:
    """
    RU: Запрещаем мутации sys.modules в tests/ — это ломает patch() и детерминизм.
    EN: Forbid sys.modules mutations in tests/ — breaks patch() and determinism.
    """
    offenders: list[str] = []

    for path in _iter_test_py_files():
        content = path.read_text(encoding="utf-8", errors="replace")
        violations = _find_violations(content)
        if not violations:
            continue

        snippet_lines = []
        for line_no, msg in violations:
            snippet_lines.append(f"  L{line_no}: {msg}")
        offenders.append(f"- {path}\n" + "\n".join(snippet_lines))

    if offenders:
        joined = "\n\n".join(offenders)
        raise AssertionError(
            "Repo policy violation: sys.modules mutations detected in tests.\n\n"
            f"{joined}\n\n"
            "Fix:\n"
            "- Use `patch()` / `monkeypatch.setattr()` instead of sys.modules edits.\n"
            "- If you need re-import behavior, refactor code to inject dependencies.\n"
            "- For FastAPI endpoints, use `tests/_route_patch.patch_route_dependency()`.\n"
        )
