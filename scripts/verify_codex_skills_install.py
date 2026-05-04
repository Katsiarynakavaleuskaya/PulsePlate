#!/usr/bin/env python3
"""Verify PulsePlate Codex skills install completeness.

Read-only verifier: compares repo source of truth (tools/codex_skills/)
against an install destination to detect missing, extra, or invalid skills.

No mutations, no network, no secrets, no shell profile access.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PULSEPLATE_SKILLS_ROOT = REPO_ROOT / "tools" / "codex_skills"
CYBERSEC_SKILLS_ROOT = REPO_ROOT / "tools" / "cybersecurity_skills" / "skills"


def _discover_expected_skills(
    include_cybersec: bool = False,
) -> list[str]:
    """Return sorted list of expected skill names from repo source of truth."""
    skills: list[str] = []
    if PULSEPLATE_SKILLS_ROOT.is_dir():
        for entry in sorted(PULSEPLATE_SKILLS_ROOT.iterdir()):
            if entry.is_dir() and (entry / "SKILL.md").exists():
                skills.append(entry.name)
    if include_cybersec and CYBERSEC_SKILLS_ROOT.is_dir():
        for entry in sorted(CYBERSEC_SKILLS_ROOT.iterdir()):
            if entry.is_dir() and (entry / "SKILL.md").exists():
                skills.append(entry.name)
    return sorted(skills)


def _resolve_destination(
    target: str,
    dest: str | None,
) -> Path:
    """Resolve the install destination directory."""
    if dest:
        return Path(dest)
    if target == "compat":
        codex_home = os.environ.get("CODEX_HOME", "")
        if codex_home:
            return Path(codex_home) / "skills"
        return Path.home() / ".codex" / "skills"
    # official (default)
    agents_home = os.environ.get("AGENTS_HOME", "")
    if agents_home:
        return Path(agents_home) / "skills"
    return Path.home() / ".agents" / "skills"


def _inspect_installed_skill(dest_dir: Path, skill_name: str) -> dict[str, str]:
    """Inspect a single skill entry at the destination."""
    skill_path = dest_dir / skill_name
    if skill_path.is_symlink():
        link_target = os.readlink(str(skill_path))
        try:
            resolved_target = str(skill_path.resolve())
        except (OSError, RuntimeError):
            resolved_target = link_target
        has_skill_md = (skill_path / "SKILL.md").exists()
        return {
            "name": skill_name,
            "status": "linked" if has_skill_md else "linked_invalid",
            "type": "symlink",
            "target": link_target,
            "resolved": resolved_target,
        }
    if skill_path.is_dir():
        has_skill_md = (skill_path / "SKILL.md").exists()
        return {
            "name": skill_name,
            "status": "copied" if has_skill_md else "copied_invalid",
            "type": "directory",
        }
    return {
        "name": skill_name,
        "status": "missing",
        "type": "absent",
    }


def verify(
    target: str,
    dest: str | None,
    include_cybersec: bool,
    strict: bool,
    output_json: bool,
) -> int:
    """Run verification and return exit code."""
    expected = _discover_expected_skills(include_cybersec=include_cybersec)
    dest_dir = _resolve_destination(target, dest)

    missing: list[str] = []
    invalid: list[str] = []
    installed: list[str] = []
    details: list[dict[str, str]] = []

    for skill_name in expected:
        info = _inspect_installed_skill(dest_dir, skill_name)
        details.append(info)
        if info["status"] == "missing":
            missing.append(skill_name)
        elif info["status"] in ("linked_invalid", "copied_invalid"):
            invalid.append(skill_name)
        else:
            installed.append(skill_name)

    # Detect extra skills at destination (not in expected set)
    extra: list[str] = []
    if dest_dir.is_dir():
        expected_set = set(expected)
        for entry in sorted(dest_dir.iterdir()):
            if entry.name not in expected_set and (entry.is_dir() or entry.is_symlink()):
                extra.append(entry.name)

    report = {
        "destination": str(dest_dir),
        "target": target if not dest else "custom",
        "expected_count": len(expected),
        "installed_count": len(installed),
        "missing_count": len(missing),
        "invalid_count": len(invalid),
        "extra_count": len(extra),
        "missing": missing,
        "invalid": invalid,
        "extra": extra,
        "details": details,
    }

    if output_json:
        print(json.dumps(report, indent=2))
    else:
        if not dest_dir.is_dir():
            print(f"Destination does not exist: {dest_dir}")
            print("  Run the installer first: scripts/install_codex_skills.sh --no-cybersec")
        print(f"Destination: {dest_dir}")
        print(f"Target: {report['target']}")
        print(f"Expected: {report['expected_count']}")
        print(f"Installed: {report['installed_count']}")
        print(f"Missing: {report['missing_count']}")
        print(f"Invalid: {report['invalid_count']}")
        print(f"Extra: {report['extra_count']}")
        if missing:
            print("\nMissing skills:\n  " + "\n  ".join(missing))
        if invalid:
            print("\nInvalid skills (no SKILL.md):\n  " + "\n  ".join(invalid))
        if not missing and not invalid:
            print("\nAll expected skills are installed.")

    if strict and (missing or invalid):
        return 1
    return 0


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Verify PulsePlate Codex skills install completeness.",
        epilog=(
            "Examples:\n"
            "  python3 scripts/verify_codex_skills_install.py --strict\n"
            "  python3 scripts/verify_codex_skills_install.py --target compat --strict\n"
            "  python3 scripts/verify_codex_skills_install.py --dest /tmp/skills --json\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--target",
        choices=["official", "compat"],
        default="official",
        help="Install target to verify (default: official = $AGENTS_HOME/skills).",
    )
    parser.add_argument(
        "--dest",
        default=None,
        help="Explicit destination directory (overrides --target).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output JSON report.",
    )
    parser.add_argument(
        "--no-cybersec",
        action="store_true",
        default=False,
        help=(
            "Exclude cybersecurity skills from expected set. "
            "This is already the default; the flag exists for CLI "
            "consistency with install_codex_skills.sh."
        ),
    )
    parser.add_argument(
        "--include-cybersec",
        action="store_true",
        default=False,
        help="Include cybersecurity skills in expected set.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        default=False,
        help="Exit 1 if any expected skill is missing or invalid.",
    )
    args = parser.parse_args()

    # Default excludes cybersec; --include-cybersec explicitly opts in.
    include_cybersec = args.include_cybersec

    return verify(
        target=args.target,
        dest=args.dest,
        include_cybersec=include_cybersec,
        strict=args.strict,
        output_json=args.output_json,
    )


if __name__ == "__main__":
    sys.exit(main())
