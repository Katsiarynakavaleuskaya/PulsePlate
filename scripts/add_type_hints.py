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

    def _check_returns_in_body(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> tuple[bool, bool]:
        """Check for return/yield statements only in the function's own body, not nested functions."""
        has_return_value = False
        has_yield = False

        def visit_node(n: ast.AST) -> None:
            """Recursively visit nodes but skip nested function/class definitions."""
            nonlocal has_return_value, has_yield

            # Check for return statements with values
            if isinstance(n, ast.Return) and n.value is not None:
                has_return_value = True

            # Check for yield statements
            if isinstance(n, (ast.Yield, ast.YieldFrom)):
                has_yield = True

            # Continue traversal for child nodes, but skip nested definitions
            for child in ast.iter_child_nodes(n):
                # Skip nested function/class/lambda definitions entirely
                if isinstance(
                    child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
                ):
                    continue  # Don't traverse into nested definitions
                visit_node(child)

        # Visit only the function's body statements, skipping nested definitions
        for stmt in node.body:
            # Skip nested function/class definitions at top level
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue  # Skip nested definitions completely
            visit_node(stmt)

        return has_return_value, has_yield

    def _add_return_type_if_needed(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool = False
    ) -> None:
        """Add return type hint if missing and function doesn't return anything."""
        if node.returns is None:
            # Check only direct statements, not nested functions
            has_return_value, has_yield = self._check_returns_in_body(node)

            # Only add -> None if function doesn't return a value
            if not has_return_value and not has_yield:
                if not self.dry_run:
                    node.returns = ast.Constant(value=None)
                    self.modified = True
                func_type = "async " if is_async else ""
                self.changes.append(f"  Added -> None to {func_type}{node.name}()")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Add return type hint if missing and function doesn't return anything."""
        self._add_return_type_if_needed(node, is_async=False)
        return cast(ast.FunctionDef, self.generic_visit(node))

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        """Add return type hint if missing and async function doesn't return anything."""
        self._add_return_type_if_needed(node, is_async=True)
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
                    import shutil

                    new_content = astor.to_source(modified_tree)

                    # Create backup before writing
                    backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                    try:
                        shutil.copy2(file_path, backup_path)
                        print(f"  📦 Backup created: {backup_path}")
                    except Exception as backup_error:
                        print(f"  ⚠️  Failed to create backup: {backup_error}")
                        return False

                    # Write new content
                    try:
                        file_path.write_text(new_content, encoding="utf-8")
                        print(f"  ✅ Updated {file_path}")
                        # Remove backup only after successful write
                        try:
                            backup_path.unlink()
                        except Exception as cleanup_error:
                            # Backup removal is non-critical - log but don't fail
                            print(f"  ⚠️  Could not remove backup file: {cleanup_error}")
                        return True
                    except Exception as write_error:
                        # Restore from backup on write failure
                        try:
                            shutil.copy2(backup_path, file_path)
                            print(f"  ❌ Write failed, restored from backup: {write_error}")
                        except Exception as restore_error:
                            print(f"  ❌ CRITICAL: Failed to restore backup: {restore_error}")
                        return False
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
        default=["__pycache__", ".pytest_cache", "cache"],
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
