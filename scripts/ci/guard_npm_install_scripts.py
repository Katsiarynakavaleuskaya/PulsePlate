"""Fail when tracked package manifests define unsafe install hooks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FORBIDDEN_SCRIPTS = ("preinstall", "install", "postinstall")


def find_install_hook_violations(root: Path) -> list[str]:
    """Return package.json violations for install-time hooks."""

    violations: list[str] = []
    for package_json in sorted(root.glob("**/package.json")):
        if "node_modules" in package_json.parts:
            continue
        try:
            payload = json.loads(package_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            violations.append(f"{package_json.relative_to(root)}: invalid JSON ({exc.msg})")
            continue
        if not isinstance(payload, dict):
            violations.append(
                f"{package_json.relative_to(root)}: package.json payload must be a JSON object"
            )
            continue
        scripts = payload.get("scripts")
        if scripts is None:
            continue
        if not isinstance(scripts, dict):
            violations.append(
                f"{package_json.relative_to(root)}: scripts must be a JSON object when present"
            )
            continue
        for script_name in FORBIDDEN_SCRIPTS:
            command = scripts.get(script_name)
            if isinstance(command, str) and command.strip():
                violations.append(
                    f"{package_json.relative_to(root)}: scripts.{script_name} is forbidden in tracked manifests"
                )
    return violations


def main() -> int:
    """Run the guard as a CLI."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    violations = find_install_hook_violations(args.root.resolve())
    if not violations:
        print("OK: no tracked package.json files define install hooks")
        return 0

    print("ERROR: found forbidden package install hooks:")
    for violation in violations:
        print(violation)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
