#!/usr/bin/env python3
"""
Check and fix trailing newlines in Python and shell scripts.

POSIX Standard Requirement:
All text files must end with a newline character ('\n').
Files without trailing newlines cause issues with:
- POSIX text processing tools
- Git diff output
- Some editors and IDEs
- Shell script execution

This script checks all .py and .sh files in the scripts directory
and reports/fixes missing trailing newlines.
"""
import sys
from pathlib import Path
from typing import List


def check_trailing_newline(file_path: Path) -> bool:
    """Check if file ends with newline character.

    Args:
        file_path: Path to file to check

    Returns:
        True if file ends with newline or is empty, False otherwise
    """
    try:
        with open(file_path, "rb") as f:
            content = f.read()
            if not content:
                return True  # Empty files are OK
            return content[-1:] == b"\n"
    except (OSError, IOError) as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return True  # Assume OK on error


def fix_trailing_newline(file_path: Path) -> bool:
    """Add trailing newline if missing.

    Args:
        file_path: Path to file to fix

    Returns:
        True if file was fixed, False otherwise
    """
    try:
        with open(file_path, "rb") as f:
            content = f.read()
            if content and content[-1:] != b"\n":
                with open(file_path, "ab") as fw:
                    fw.write(b"\n")
                return True
    except (OSError, IOError) as e:
        print(f"Error fixing {file_path}: {e}", file=sys.stderr)
    return False


def find_files_without_newline(directory: Path) -> List[Path]:
    """Find all Python and shell scripts without trailing newline.

    Args:
        directory: Directory to search

    Returns:
        List of file paths without trailing newline
    """
    files_without_newline: List[Path] = []
    for ext in [".py", ".sh"]:
        for file in directory.rglob(f"*{ext}"):
            if file.is_file() and not check_trailing_newline(file):
                files_without_newline.append(file)
    return files_without_newline


def main() -> None:
    """Check and optionally fix trailing newlines in scripts directory."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check and fix trailing newlines in scripts (POSIX compliance)"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix files without trailing newline",
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path("scripts"),
        help="Directory to check (default: scripts)",
    )
    args = parser.parse_args()

    scripts_dir = args.directory
    if not scripts_dir.exists():
        print(f"Directory {scripts_dir} not found", file=sys.stderr)
        sys.exit(1)

    files_without_newline = find_files_without_newline(scripts_dir)

    if files_without_newline:
        print(f"❌ Found {len(files_without_newline)} files without trailing newline:")
        for f in files_without_newline:
            print(f"  {f}")
            if args.fix:
                if fix_trailing_newline(f):
                    print(f"  ✓ Fixed: {f}")
        if not args.fix:
            print("\n💡 Run with --fix to automatically add trailing newlines")
        sys.exit(1)
    else:
        print("✅ All files have trailing newline (POSIX compliant)")


if __name__ == "__main__":
    main()
