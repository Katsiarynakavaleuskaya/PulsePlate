#!/usr/bin/env python3
"""Guard against deprecated httpx TestClient backend usage.

Starlette's TestClient now prefers the ``httpx2`` backend. Direct
``httpx.Client(app=...)`` and ``httpx.AsyncClient(app=...)`` calls are the old
HTTPX in-process app shortcut and should use explicit transports instead.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCAN_PATHS = (
    "app",
    "core",
    "providers",
    "scripts",
    "tests",
    "llm.py",
    "main.py",
    "mcp_pulseplate_server.py",
    "secure_config.py",
    "settings.py",
    "signed_links.py",
    # Compatibility seam is intentionally excluded below, but keep it in the
    # default path set so the exclusion is explicit and test-covered.
    "legacy_app.py",
)
HTTPX_CLIENT_NAMES = frozenset({"Client", "AsyncClient"})
EXCLUDED_DIR_PARTS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "artifacts",
        "build",
        "dist",
        "disabled_hypothesis",
        "generated",
        "htmlcov",
        "node_modules",
        "worktrees",
    }
)
EXCLUDED_FILES = frozenset(
    {
        Path("legacy_app.py"),
    }
)


@dataclass(frozen=True)
class Violation:
    """One deprecated httpx app shortcut call."""

    path: Path
    line: int
    column: int
    symbol: str

    def render(self, repo_root: Path) -> str:
        rel_path = self.path.relative_to(repo_root)
        return (
            f"{rel_path}:{self.line}:{self.column + 1}: "
            f"deprecated {self.symbol}(app=...) shortcut; use httpx.ASGITransport "
            "or FastAPI/Starlette TestClient instead"
        )


class HttpxAppShortcutVisitor(ast.NodeVisitor):
    """Find deprecated ``httpx.Client(app=...)`` calls in one Python module."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._httpx_module_alias_scopes: list[set[str]] = [set()]
        self._imported_httpx_client_scopes: list[dict[str, str]] = [{}]
        self.violations: list[Violation] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            bound_name = alias.asname or alias.name.split(".", maxsplit=1)[0]
            self._drop_shadowed_name(bound_name)
            if alias.name == "httpx":
                self.httpx_module_aliases.add(bound_name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == "*":
                self.httpx_module_aliases.clear()
                self.imported_httpx_clients.clear()
                continue

            bound_name = alias.asname or alias.name
            self._drop_shadowed_name(bound_name)
            if node.module == "httpx" and alias.name in HTTPX_CLIENT_NAMES:
                self.imported_httpx_clients[bound_name] = alias.name
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        for target in node.targets:
            self._drop_shadowed_names(target)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.annotation is not None:
            self.visit(node.annotation)
        if node.value is not None:
            self.visit(node.value)
        self._drop_shadowed_names(node.target)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit(node.value)
        self._drop_shadowed_names(node.target)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self.visit(node.value)
        self._drop_shadowed_names(node.target)

    def visit_For(self, node: ast.For) -> None:
        self._visit_for_like(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._visit_for_like(node)

    def visit_With(self, node: ast.With) -> None:
        self._visit_with_like(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._visit_with_like(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function_like(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function_like(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        for positional_default in node.args.defaults:
            self.visit(positional_default)
        for keyword_default in node.args.kw_defaults:
            if keyword_default is not None:
                self.visit(keyword_default)
        self._push_scope()
        self._drop_argument_names(node.args)
        self.visit(node.body)
        self._pop_scope()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        self._drop_shadowed_name(node.name)
        self._push_scope()
        for item in node.body:
            self.visit(item)
        self._pop_scope()

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is not None:
            self.visit(node.type)
        if node.name:
            self._drop_shadowed_name(node.name)
        for item in node.body:
            self.visit(item)

    def _visit_for_like(self, node: ast.For | ast.AsyncFor) -> None:
        self.visit(node.iter)
        self._drop_shadowed_names(node.target)
        for item in node.body:
            self.visit(item)
        for item in node.orelse:
            self.visit(item)

    def _visit_with_like(self, node: ast.With | ast.AsyncWith) -> None:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars is not None:
                self._drop_shadowed_names(item.optional_vars)
        for body_item in node.body:
            self.visit(body_item)

    def visit_Call(self, node: ast.Call) -> None:
        if self._call_passes_app_argument(node):
            symbol = self._deprecated_httpx_client_symbol(node.func)
            if symbol is not None:
                self.violations.append(
                    Violation(
                        path=self.path,
                        line=node.lineno,
                        column=node.col_offset,
                        symbol=symbol,
                    )
                )
        self.generic_visit(node)

    def _deprecated_httpx_client_symbol(self, func: ast.AST) -> str | None:
        if isinstance(func, ast.Attribute):
            if func.attr not in HTTPX_CLIENT_NAMES:
                return None
            if isinstance(func.value, ast.Name) and func.value.id in self.httpx_module_aliases:
                return f"{func.value.id}.{func.attr}"
            return None

        if isinstance(func, ast.Name) and func.id in self.imported_httpx_clients:
            return self.imported_httpx_clients[func.id]

        return None

    def _call_passes_app_argument(self, node: ast.Call) -> bool:
        return any(
            keyword.arg == "app"
            or (keyword.arg is None and self._literal_mapping_contains_app(keyword.value))
            for keyword in node.keywords
        )

    def _literal_mapping_contains_app(self, node: ast.AST) -> bool:
        if not isinstance(node, ast.Dict):
            return False
        return any(
            isinstance(key, ast.Constant) and key.value == "app"
            for key in node.keys
            if key is not None
        )

    @property
    def httpx_module_aliases(self) -> set[str]:
        return self._httpx_module_alias_scopes[-1]

    @property
    def imported_httpx_clients(self) -> dict[str, str]:
        return self._imported_httpx_client_scopes[-1]

    def _push_scope(self) -> None:
        self._httpx_module_alias_scopes.append(set(self.httpx_module_aliases))
        self._imported_httpx_client_scopes.append(dict(self.imported_httpx_clients))

    def _pop_scope(self) -> None:
        self._httpx_module_alias_scopes.pop()
        self._imported_httpx_client_scopes.pop()

    def _visit_function_like(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for positional_default in node.args.defaults:
            self.visit(positional_default)
        for keyword_default in node.args.kw_defaults:
            if keyword_default is not None:
                self.visit(keyword_default)
        if node.returns is not None:
            self.visit(node.returns)

        self._drop_shadowed_name(node.name)
        self._push_scope()
        self._drop_argument_names(node.args)
        for item in node.body:
            self.visit(item)
        self._pop_scope()

    def _drop_argument_names(self, args: ast.arguments) -> None:
        for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
            self._drop_shadowed_name(arg.arg)
        if args.vararg is not None:
            self._drop_shadowed_name(args.vararg.arg)
        if args.kwarg is not None:
            self._drop_shadowed_name(args.kwarg.arg)

    def _drop_shadowed_names(self, target: ast.AST) -> None:
        if isinstance(target, ast.Name):
            self._drop_shadowed_name(target.id)
            return
        if isinstance(target, ast.Starred):
            self._drop_shadowed_names(target.value)
            return
        if isinstance(target, ast.Tuple | ast.List):
            for element in target.elts:
                self._drop_shadowed_names(element)

    def _drop_shadowed_name(self, name: str) -> None:
        self.httpx_module_aliases.discard(name)
        self.imported_httpx_clients.pop(name, None)


def _is_excluded(path: Path, repo_root: Path) -> bool:
    rel_path = path.relative_to(repo_root)
    if rel_path in EXCLUDED_FILES:
        return True
    if path.suffix != ".py" or path.name.endswith(".py.broken"):
        return True
    return any(part in EXCLUDED_DIR_PARTS for part in rel_path.parts)


def iter_python_files(paths: list[Path], *, repo_root: Path) -> list[Path]:
    """Return Python files to scan, with generated/local/legacy noise excluded."""

    files: list[Path] = []
    for path in paths:
        resolved = path if path.is_absolute() else repo_root / path
        if not resolved.exists():
            raise FileNotFoundError(f"scan path does not exist: {resolved}")
        if resolved.is_file():
            candidates = [resolved]
        else:
            candidates = sorted(resolved.rglob("*.py"))
        for candidate in candidates:
            candidate = candidate.resolve()
            try:
                candidate.relative_to(repo_root)
            except ValueError:
                continue
            if not _is_excluded(candidate, repo_root):
                files.append(candidate)
    return files


def find_violations(paths: list[Path], *, repo_root: Path = REPO_ROOT) -> list[Violation]:
    """Return deprecated httpx app shortcut calls under ``paths``."""

    violations: list[Violation] = []
    for path in iter_python_files(paths, repo_root=repo_root):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = HttpxAppShortcutVisitor(path)
        visitor.visit(tree)
        violations.extend(visitor.violations)
    return sorted(violations, key=lambda item: (str(item.path), item.line, item.column))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root. Defaults to this checkout.",
    )
    parser.add_argument(
        "--path",
        action="append",
        type=Path,
        dest="paths",
        help="Path to scan. May be repeated. Defaults to production/test Python roots.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    paths = args.paths or [Path(path) for path in DEFAULT_SCAN_PATHS]
    violations = find_violations(paths, repo_root=repo_root)
    if violations:
        print("Deprecated httpx TestClient backend shortcuts found:")
        for violation in violations:
            print(f"- {violation.render(repo_root)}")
        return 1

    print("PASS: no deprecated httpx Client(app=...) shortcuts found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
