#!/usr/bin/env python3
"""
Verify that package versions are consistent across requirements files.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List


def parse_requirements(file_path: Path) -> Dict[str, str]:
    """Parse requirements file and return dict of package:version."""
    packages: Dict[str, str] = {}

    if not file_path.exists():
        return packages

    for line in file_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        # Skip comments, empty lines, and -r references
        if not line or line.startswith("#") or line.startswith("-r"):
            continue

        # Parse package==version or package>=version
        match = re.match(r"^([a-zA-Z0-9_\-\[\]]+)(==|>=)([0-9\.]+.*?)$", line)
        if match:
            package, operator, version = match.groups()
            packages[package.lower()] = f"{operator}{version}"

    return packages


def main() -> int:
    """Check consistency between requirements files."""
    repo_root = Path(__file__).parent

    # Parse all requirements files
    req_main = parse_requirements(repo_root / "requirements.txt")
    req_dev = parse_requirements(repo_root / "requirements-dev.txt")
    req_all = parse_requirements(repo_root / "requirements-all.txt")
    constraints = parse_requirements(repo_root / "constraints.txt")

    print("🔍 Verifying requirements consistency...\n")

    errors: List[str] = []

    # Check: requirements-dev.txt should not override requirements.txt versions
    print("✓ Checking requirements-dev.txt vs requirements.txt...")
    for pkg, version in req_dev.items():
        if pkg in req_main and req_main[pkg] != version:
            errors.append(
                f"  ❌ {pkg}: requirements.txt={req_main[pkg]}, requirements-dev.txt={version}"
            )

    # Check: requirements-all.txt should not have different versions
    print("✓ Checking requirements-all.txt vs requirements.txt...")
    for pkg, version in req_all.items():
        if pkg in req_main and req_main[pkg] != version:
            errors.append(
                f"  ❌ {pkg}: requirements.txt={req_main[pkg]}, requirements-all.txt={version}"
            )

    if errors:
        print("\n❌ Version mismatches found:\n")
        for error in errors:
            print(error)
        print("\n💡 Fix: Update requirements-all.txt to use '-r requirements.txt'")
        return 1

    print("\n✅ All requirements files are consistent!")
    print(f"\n📦 Production packages: {len(req_main)}")
    print(f"🛠️  Dev packages: {len(req_dev)}")
    print(f"📌 Constraints: {len(constraints)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
