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

import ast
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent

ENFORCED_GLOBS: tuple[str, ...] = (
    # VIP tests were explicitly stabilized for import hygiene in PR-8c/8b.
    # Keep these files free of sys.modules mutation to avoid regressions.
    # NOTE: Scope is intentionally limited to `tests/vip/**` to avoid breaking legacy tests that
    # still contain sys.modules mutations. Expand scope only as legacy tests are cleaned up.
    "vip/**/*.py",
)


def _is_sys_modules_attr(node: ast.AST) -> bool:
    # sys.modules
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "modules"
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
    )


def _is_sys_modules_subscript(node: ast.AST) -> bool:
    # sys.modules[...]
    return isinstance(node, ast.Subscript) and _is_sys_modules_attr(node.value)


def _is_sys_modules_pop_call(node: ast.AST) -> bool:
    # sys.modules.pop(...)
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "pop"
        and _is_sys_modules_attr(node.func.value)
    )


def _iter_test_py_files() -> list[Path]:
    if not TESTS_DIR.exists():
        return []
    files: list[Path] = []
    for glob in ENFORCED_GLOBS:
        files.extend([p for p in TESTS_DIR.glob(glob) if p.is_file() and p.suffix == ".py"])
    return sorted(set(files))


def _find_violations(text: str) -> list[tuple[int, str]]:
    """
    Returns list of (line_number_1_based, message).
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        # Ignore syntactically invalid files (shouldn't happen for committed tests).
        return []

    violations: list[tuple[int, str]] = []

    class Visitor(ast.NodeVisitor):
        def visit_Delete(self, node: ast.Delete) -> None:
            for target in node.targets:
                if _is_sys_modules_subscript(target):
                    violations.append((node.lineno, "Forbidden: `del sys.modules[...]` in tests."))
            self.generic_visit(node)

        def visit_Assign(self, node: ast.Assign) -> None:
            for target in node.targets:
                if _is_sys_modules_subscript(target):
                    violations.append(
                        (node.lineno, "Forbidden: `sys.modules[...] = ...` in tests.")
                    )
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            if _is_sys_modules_pop_call(node):
                violations.append((node.lineno, "Forbidden: `sys.modules.pop(...)` in tests."))
            self.generic_visit(node)

    Visitor().visit(tree)
    return violations


def test_policy_does_not_flag_comments_or_strings() -> None:
    content = "# del sys.modules['x']\n" "s = \"sys.modules.pop('x')\"\n"
    assert _find_violations(content) == []


def test_policy_flags_runtime_mutations() -> None:
    content = "\n".join(
        [
            "import sys",
            "del sys.modules['x']",
            "sys.modules['y'] = object()",
            "sys.modules.pop('z', None)",
            "",
        ]
    )
    violations = _find_violations(content)
    assert [msg for _, msg in violations] == [
        "Forbidden: `del sys.modules[...]` in tests.",
        "Forbidden: `sys.modules[...] = ...` in tests.",
        "Forbidden: `sys.modules.pop(...)` in tests.",
    ]


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
