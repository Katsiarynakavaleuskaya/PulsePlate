#!/usr/bin/env python3
"""Script to automatically add missing return type hints to functions.

This script uses AST to analyze Python files and add `-> None` return type hints
to functions that are missing them and don't have explicit return statements.

Usage:
    python scripts/add_type_hints.py <file_or_directory>
    python scripts/add_type_hints.py app/ core/ --dry-run
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import cast


class TypeHintAdder(ast.NodeTransformer):
    """AST transformer that adds missing return type hints."""

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self.modified = False
        self.changes: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Add return type hint if missing and function doesn't return anything."""
        if node.returns is None:
            # Check if function has explicit return with value
            has_return_value = any(
                isinstance(stmt, ast.Return) and stmt.value is not None for stmt in ast.walk(node)
            )
            has_yield = any(isinstance(stmt, ast.Yield) for stmt in ast.walk(node))

            # Only add -> None if function doesn't return a value
            if not has_return_value and not has_yield:
                if not self.dry_run:
                    node.returns = ast.Constant(value=None)
                    self.modified = True
                self.changes.append(f"  Added -> None to {node.name}()")
        return cast(ast.FunctionDef, self.generic_visit(node))

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        """Add return type hint if missing and async function doesn't return anything."""
        if node.returns is None:
            has_return_value = any(
                isinstance(stmt, ast.Return) and stmt.value is not None for stmt in ast.walk(node)
            )
            has_yield = any(isinstance(stmt, ast.Yield) for stmt in ast.walk(node))

            if not has_return_value and not has_yield:
                if not self.dry_run:
                    node.returns = ast.Constant(value=None)
                    self.modified = True
                self.changes.append(f"  Added -> None to async {node.name}()")
        return cast(ast.AsyncFunctionDef, self.generic_visit(node))


def process_file(file_path: Path, dry_run: bool = False) -> bool:
    """Process a single Python file and add missing type hints."""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))

        adder = TypeHintAdder(dry_run=dry_run)
        modified_tree = adder.visit(tree)

        if adder.changes:
            print(f"\n{file_path}:")
            for change in adder.changes:
                print(change)

            if not dry_run and adder.modified:
                # Reconstruct code with type hints
                try:
                    import astor

                    new_content = astor.to_source(modified_tree)
                    file_path.write_text(new_content, encoding="utf-8")
                    print(f"  ✅ Updated {file_path}")
                    return True
                except ImportError:
                    print("  ⚠️  astor not installed, skipping write")
                    return False
        return False
    except SyntaxError as e:
        print(f"  ❌ Syntax error in {file_path}: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error processing {file_path}: {e}")
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Add missing return type hints to Python functions"
    )
    parser.add_argument("paths", nargs="+", help="Files or directories to process")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=["tests", "__pycache__", ".pytest_cache", "cache"],
        help="Directories to exclude",
    )

    args = parser.parse_args()

    files_to_process: list[Path] = []
    for path_str in args.paths:
        path = Path(path_str)
        if path.is_file() and path.suffix == ".py":
            files_to_process.append(path)
        elif path.is_dir():
            for py_file in path.rglob("*.py"):
                # Skip excluded directories
                if any(excluded in py_file.parts for excluded in args.exclude):
                    continue
                files_to_process.append(py_file)

    if not files_to_process:
        print("No Python files found to process")
        return 1

    print(f"Processing {len(files_to_process)} file(s)...")
    if args.dry_run:
        print("DRY RUN MODE - no files will be modified\n")

    modified_count = 0
    for file_path in sorted(files_to_process):
        if process_file(file_path, dry_run=args.dry_run):
            modified_count += 1

    print(f"\n{'Would modify' if args.dry_run else 'Modified'} {modified_count} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
