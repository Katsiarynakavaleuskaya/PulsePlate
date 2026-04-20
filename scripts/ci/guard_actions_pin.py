"""Fail when GitHub Actions workflow steps are not pinned to full commit SHAs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

USES_RE = re.compile(r"^\s*-?\s*uses:\s*(?P<action>\S+?)(?:\s+#.*)?\s*$")
PINNED_SHA_RE = re.compile(r"^[^@]+@[0-9a-f]{40}$")


def _workflow_paths(workflows_dir: Path) -> list[Path]:
    return sorted([*workflows_dir.rglob("*.yml"), *workflows_dir.rglob("*.yaml")])


def find_unpinned_actions(root: Path) -> list[str]:
    """Return workflow violations for non-local, non-SHA-pinned actions."""

    violations: list[str] = []
    workflows_dir = root / ".github" / "workflows"
    for workflow_path in _workflow_paths(workflows_dir):
        for line_number, line in enumerate(
            workflow_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            match = USES_RE.match(line)
            if not match:
                continue
            action = match.group("action")
            if action.startswith("./"):
                continue
            if PINNED_SHA_RE.match(action):
                continue
            violations.append(
                f"{workflow_path.relative_to(root)}:{line_number}: action '{action}' must pin a 40-char commit SHA"
            )
    return violations


def main() -> int:
    """Run the guard as a CLI."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    violations = find_unpinned_actions(args.root.resolve())
    if not violations:
        print("OK: all workflow actions are pinned to full commit SHAs")
        return 0

    print("ERROR: found unpinned GitHub Actions:")
    for violation in violations:
        print(violation)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
