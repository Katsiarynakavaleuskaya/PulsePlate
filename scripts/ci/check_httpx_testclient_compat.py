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
DEFAULT_SCAN_PATHS = ("app", "core", "providers", "scripts", "tests")
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
        self.httpx_module_aliases: set[str] = set()
        self.imported_httpx_clients: dict[str, str] = {}
        self.violations: list[Violation] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "httpx":
                self.httpx_module_aliases.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module != "httpx":
            self.generic_visit(node)
            return

        for alias in node.names:
            if alias.name in HTTPX_CLIENT_NAMES:
                self.imported_httpx_clients[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if any(keyword.arg == "app" for keyword in node.keywords):
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
