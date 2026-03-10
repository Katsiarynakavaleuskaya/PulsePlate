"""Fail when VS Code recommendations drift from the reviewed allowlist."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_allowlist(path: Path) -> set[str]:
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def find_extension_allowlist_violations(
    *,
    extensions_json_path: Path,
    allowlist_path: Path,
    repo_root: Path,
) -> list[str]:
    """Return recommendations not present in the reviewed allowlist."""

    if not extensions_json_path.exists():
        return [
            f"{extensions_json_path.relative_to(repo_root)}: tracked recommendations file is required"
        ]
    if not allowlist_path.exists():
        return [f"{allowlist_path.relative_to(repo_root)}: allowlist file is required"]

    payload = json.loads(extensions_json_path.read_text(encoding="utf-8"))
    recommendations = payload.get("recommendations", [])
    if not isinstance(recommendations, list):
        return [f"{extensions_json_path.relative_to(repo_root)}: recommendations must be a list"]

    allowlist = _load_allowlist(allowlist_path)
    violations: list[str] = []
    for recommendation in sorted(recommendations):
        if recommendation not in allowlist:
            violations.append(
                f"{extensions_json_path.relative_to(repo_root)}: recommendation '{recommendation}' is not in allowlist"
            )
    return violations


def main() -> int:
    """Run the guard as a CLI."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=Path("docs/security/vscode_extensions_allowlist.txt"),
    )
    args = parser.parse_args()

    root = args.root.resolve()
    violations = find_extension_allowlist_violations(
        extensions_json_path=root / ".vscode" / "extensions.json",
        allowlist_path=(root / args.allowlist).resolve(),
        repo_root=root,
    )
    if not violations:
        print("OK: VS Code recommendations match reviewed allowlist")
        return 0

    print("ERROR: found VS Code recommendation drift:")
    for violation in violations:
        print(violation)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
