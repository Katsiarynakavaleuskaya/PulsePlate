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
    # NOTE: Scope stays intentionally narrow while legacy tests are cleaned up incrementally.
    "vip/**/*.py",
    "test_llm_extras.py",
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
        # Policy checks should stay non-blocking even if a file is temporarily invalid.
        return []

    violations: list[tuple[int, str]] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            super().__init__()
            self.sys_module_names: set[str] = {"sys"}
            self.modules_names: set[str] = set()

        def _is_sys_modules_attr(self, node: ast.AST) -> bool:
            # sys.modules  (also supports: import sys as s; s.modules)
            return (
                isinstance(node, ast.Attribute)
                and node.attr == "modules"
                and isinstance(node.value, ast.Name)
                and node.value.id in self.sys_module_names
            )

        def _is_modules_container(self, node: ast.AST) -> bool:
            # sys.modules OR (from sys import modules as m; m)
            return self._is_sys_modules_attr(node) or (
                isinstance(node, ast.Name) and node.id in self.modules_names
            )

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                if alias.name == "sys":
                    self.sys_module_names.add(alias.asname or alias.name)
            self.generic_visit(node)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            if node.module == "sys":
                for alias in node.names:
                    if alias.name == "modules":
                        self.modules_names.add(alias.asname or alias.name)
            self.generic_visit(node)

        def visit_Delete(self, node: ast.Delete) -> None:
            for target in node.targets:
                if isinstance(target, ast.Subscript) and self._is_modules_container(target.value):
                    violations.append((node.lineno, "Forbidden: `del sys.modules[...]` in tests."))
            self.generic_visit(node)

        def visit_Assign(self, node: ast.Assign) -> None:
            for target in node.targets:
                if isinstance(target, ast.Subscript) and self._is_modules_container(target.value):
                    violations.append(
                        (node.lineno, "Forbidden: `sys.modules[...] = ...` in tests.")
                    )
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Attribute) and self._is_modules_container(node.func.value):
                messages_by_method = {
                    "pop": "Forbidden: `sys.modules.pop(...)` in tests.",
                    "update": "Forbidden: `sys.modules.update(...)` in tests.",
                    "clear": "Forbidden: `sys.modules.clear()` in tests.",
                    "setdefault": "Forbidden: `sys.modules.setdefault(...)` in tests.",
                    "popitem": "Forbidden: `sys.modules.popitem()` in tests.",
                    "__setitem__": "Forbidden: `sys.modules.__setitem__(...)` in tests.",
                    "__delitem__": "Forbidden: `sys.modules.__delitem__(...)` in tests.",
                }
                msg = messages_by_method.get(node.func.attr)
                if msg is not None:
                    violations.append((node.lineno, msg))
            self.generic_visit(node)

    Visitor().visit(tree)
    return violations


def test_policy_does_not_flag_comments_or_strings() -> None:
    content = "# del sys.modules['x']\ns = \"sys.modules.pop('x')\"\n"
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
    assert _find_violations(content) == [
        (2, "Forbidden: `del sys.modules[...]` in tests."),
        (3, "Forbidden: `sys.modules[...] = ...` in tests."),
        (4, "Forbidden: `sys.modules.pop(...)` in tests."),
    ]


def test_policy_flags_sys_import_aliases() -> None:
    content = "\n".join(
        [
            "import sys as s",
            "del s.modules['x']",
            "s.modules['y'] = object()",
            "s.modules.pop('z', None)",
            "",
        ]
    )
    assert _find_violations(content) == [
        (2, "Forbidden: `del sys.modules[...]` in tests."),
        (3, "Forbidden: `sys.modules[...] = ...` in tests."),
        (4, "Forbidden: `sys.modules.pop(...)` in tests."),
    ]


def test_policy_flags_from_sys_import_modules_alias() -> None:
    content = "\n".join(
        [
            "from sys import modules as m",
            "del m['x']",
            "m['y'] = object()",
            "m.pop('z', None)",
            "",
        ]
    )
    assert _find_violations(content) == [
        (2, "Forbidden: `del sys.modules[...]` in tests."),
        (3, "Forbidden: `sys.modules[...] = ...` in tests."),
        (4, "Forbidden: `sys.modules.pop(...)` in tests."),
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
