"""Fail when recognized external GitHub action refs lack full commit SHA pins."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

USES_RE = re.compile(r"^\s*-?\s*uses:\s*(?P<action>\S+?)(?:\s+#.*)?\s*$")
PINNED_SHA_RE = re.compile(r"^[^@]+@[0-9a-f]{40}$")


def _workflow_paths(workflows_dir: Path) -> list[Path]:
    return sorted([*workflows_dir.rglob("*.yml"), *workflows_dir.rglob("*.yaml")])


def _composite_action_paths(actions_dir: Path) -> list[Path]:
    return sorted([*actions_dir.rglob("action.yml"), *actions_dir.rglob("action.yaml")])


def find_unpinned_actions(root: Path) -> list[str]:
    """Return bounded workflow/composite violations for external action refs."""

    violations: list[str] = []
    workflows_dir = root / ".github" / "workflows"
    actions_dir = root / ".github" / "actions"
    action_source_paths = sorted(
        [
            *_workflow_paths(workflows_dir),
            *_composite_action_paths(actions_dir),
        ]
    )
    for action_source_path in action_source_paths:
        for line_number, line in enumerate(
            action_source_path.read_text(encoding="utf-8").splitlines(),
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
            if action.startswith("docker://"):
                continue
            if PINNED_SHA_RE.match(action):
                continue
            violations.append(
                f"{action_source_path.relative_to(root)}:{line_number}: action '{action}' must pin a 40-char commit SHA"
            )
    return violations


def main() -> int:
    """Run the guard as a CLI."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    violations = find_unpinned_actions(args.root.resolve())
    if not violations:
        print("OK: all recognized external GitHub action refs use full commit SHA pins")
        return 0

    print("ERROR: found unpinned GitHub Actions:")
    for violation in violations:
        print(violation)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
