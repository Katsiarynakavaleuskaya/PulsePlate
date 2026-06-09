#!/usr/bin/env python3
"""Verify PulsePlate Codex skills install completeness.

Read-only verifier: compares repo source of truth (tools/codex_skills/)
against an install destination to detect missing, extra, or invalid skills.

No mutations, no network, no secrets, no shell profile access.
"""

from __future__ import annotations

import argparse
import errno
import filecmp
import json
import os
import stat
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PULSEPLATE_SKILLS_ROOT = REPO_ROOT / "tools" / "codex_skills"
CYBERSEC_SKILLS_ROOT = REPO_ROOT / "tools" / "cybersecurity_skills" / "skills"


def _discover_expected_skills(
    include_cybersec: bool = False,
) -> dict[str, Path]:
    """Return expected skill names mapped to repo source-of-truth paths."""
    skills: dict[str, Path] = {}
    if PULSEPLATE_SKILLS_ROOT.is_dir():
        for entry in sorted(PULSEPLATE_SKILLS_ROOT.iterdir()):
            if entry.is_dir() and (entry / "SKILL.md").exists():
                skills[entry.name] = entry
    if include_cybersec and CYBERSEC_SKILLS_ROOT.is_dir():
        for entry in sorted(CYBERSEC_SKILLS_ROOT.iterdir()):
            if entry.is_dir() and (entry / "SKILL.md").exists():
                skills[entry.name] = entry
    return dict(sorted(skills.items()))


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


COPY_MARKER_FILE = ".pulseplate_codex_skill_source"
COPY_MARKER_MAX_BYTES = 4096


def _canonical_path(path: Path) -> str | None:
    """Return the canonical path for an existing path, or None if unresolved."""
    try:
        return str(path.resolve(strict=True))
    except (OSError, RuntimeError):
        return None


def _relative_entries(root: Path) -> set[Path]:
    """Return all relative entries under a skill directory, excluding copy marker."""
    return {
        entry.relative_to(root)
        for entry in root.rglob("*")
        if entry.relative_to(root) != Path(COPY_MARKER_FILE)
    }


def _copied_skill_matches_source(skill_path: Path, source_skill: Path) -> bool:
    """Return whether a copied skill directory matches its repo source."""
    source_entries = _relative_entries(source_skill)
    copied_entries = _relative_entries(skill_path)
    if source_entries != copied_entries:
        return False
    for relative_entry in source_entries:
        source_entry = source_skill / relative_entry
        copied_entry = skill_path / relative_entry
        if source_entry.is_dir() or copied_entry.is_dir():
            if not (source_entry.is_dir() and copied_entry.is_dir()):
                return False
            continue
        if not (source_entry.is_file() and copied_entry.is_file()):
            return False
        if not filecmp.cmp(source_entry, copied_entry, shallow=False):
            return False
    return True


def _read_copy_marker(marker_path: Path) -> tuple[str, str | None]:
    """Read a trusted copy marker without following symlinks or large files."""
    try:
        marker_stat = marker_path.stat(follow_symlinks=False)
    except FileNotFoundError:
        return "", None
    except OSError:
        return "", "marker_unreadable"

    if not stat.S_ISREG(marker_stat.st_mode):
        return "", "marker_not_regular"
    if marker_stat.st_size > COPY_MARKER_MAX_BYTES:
        return "", "marker_too_large"

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(marker_path, flags)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            return "", "marker_symlink"
        return "", "marker_unreadable"

    try:
        with os.fdopen(fd, "rb") as marker_file:
            marker_fd_stat = os.fstat(marker_file.fileno())
            if not stat.S_ISREG(marker_fd_stat.st_mode):
                return "", "marker_not_regular"
            if marker_fd_stat.st_size > COPY_MARKER_MAX_BYTES:
                return "", "marker_too_large"
            marker_bytes = marker_file.read(COPY_MARKER_MAX_BYTES + 1)
    except OSError:
        return "", "marker_unreadable"

    if len(marker_bytes) > COPY_MARKER_MAX_BYTES:
        return "", "marker_too_large"
    try:
        return marker_bytes.decode("utf-8").strip(), None
    except UnicodeDecodeError:
        return "", "marker_invalid_utf8"


def _inspect_installed_skill(
    dest_dir: Path,
    skill_name: str,
    source_skill: Path,
) -> dict[str, str]:
    """Inspect a single skill entry at the destination."""
    skill_path = dest_dir / skill_name
    expected_resolved = _canonical_path(source_skill)
    if skill_path.is_symlink():
        link_target = os.readlink(str(skill_path))
        resolved_target = _canonical_path(skill_path) or link_target
        has_skill_md = (skill_path / "SKILL.md").exists()
        is_repo_managed = has_skill_md and resolved_target == expected_resolved
        return {
            "name": skill_name,
            "status": "linked" if is_repo_managed else "linked_invalid",
            "type": "symlink",
            "target": link_target,
            "resolved": resolved_target,
            "expected": expected_resolved or str(source_skill),
        }
    if skill_path.is_dir():
        marker_path = skill_path / COPY_MARKER_FILE
        marker_value, marker_error = _read_copy_marker(marker_path)
        marker_resolved = _canonical_path(Path(marker_value)) if marker_value else None
        has_skill_md = (skill_path / "SKILL.md").exists()
        is_repo_managed = (
            marker_error is None
            and has_skill_md
            and marker_resolved == expected_resolved
            and _copied_skill_matches_source(skill_path, source_skill)
        )
        info = {
            "name": skill_name,
            "status": "copied" if is_repo_managed else "copied_invalid",
            "type": "directory",
            "marker": marker_value if is_repo_managed else "",
            "expected": expected_resolved or str(source_skill),
        }
        if marker_error is not None:
            info["marker_error"] = marker_error
        return info
    return {
        "name": skill_name,
        "status": "missing",
        "type": "absent",
        "expected": expected_resolved or str(source_skill),
    }


def verify(
    target: str,
    dest: str | None,
    include_cybersec: bool,
    strict: bool,
    output_json: bool,
) -> int:
    """Run verification and return exit code."""
    expected_sources = _discover_expected_skills(include_cybersec=include_cybersec)
    expected = list(expected_sources)
    dest_dir = _resolve_destination(target, dest)

    missing: list[str] = []
    invalid: list[str] = []
    installed: list[str] = []
    details: list[dict[str, str]] = []

    for skill_name, source_skill in expected_sources.items():
        info = _inspect_installed_skill(dest_dir, skill_name, source_skill)
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
            install_cmd = "scripts/install_codex_skills.sh"
            if dest:
                install_cmd += f" --dest {dest_dir}"
            elif target == "compat":
                install_cmd += " --target compat"
            if not include_cybersec:
                install_cmd += " --no-cybersec"
            print(f"  Run the installer first: {install_cmd}")
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
            print(
                "\nInvalid skills (not repo-managed or content mismatch):\n  "
                + "\n  ".join(invalid)
            )
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
