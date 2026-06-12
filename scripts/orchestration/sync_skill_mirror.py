#!/usr/bin/env python3
"""Synchronize a PulsePlate Codex skill into the .agents mirror directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_ROOT = REPO_ROOT / "tools" / "codex_skills"
DEFAULT_MIRROR_ROOT = REPO_ROOT / ".agents" / "skills"
SOURCE_MARKER = ".pulseplate_codex_skill_source"


class SkillMirrorValidationError(ValueError):
    """Raised when sync input would escape the configured skill roots."""


def _validate_skill_name(skill_name: str) -> str:
    """Return a safe single-directory skill name."""

    skill_path = Path(skill_name)
    if (
        not skill_name
        or skill_path.is_absolute()
        or "/" in skill_name
        or "\\" in skill_name
        or skill_name != skill_path.name
        or skill_path.name in {".", ".."}
    ):
        raise SkillMirrorValidationError(
            "Skill name must be a single directory name without path separators: " f"{skill_name!r}"
        )
    return skill_name


def _resolve_source_child_path(root: Path, child_name: str) -> Path:
    child = (root / child_name).resolve()
    try:
        child.relative_to(root)
    except ValueError as exc:
        raise SkillMirrorValidationError(f"Path escapes configured root: {child}") from exc
    return child


def _destination_child_path(root: Path, child_name: str) -> Path:
    return root / child_name


def _ensure_skill_available(source_root: Path, skill_name: str) -> Path:
    skill_path = _resolve_source_child_path(source_root, skill_name)
    if not skill_path.is_dir():
        raise FileNotFoundError(f"Skill source folder not found: {skill_path}")
    if not (skill_path / "SKILL.md").is_file():
        raise FileNotFoundError("Skill source is invalid: missing SKILL.md at " f"{skill_path}")
    return skill_path


def _clear_existing_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    if path.is_dir():
        shutil.rmtree(path)


def _source_marker_value(source: Path, source_root: Path) -> str:
    """Return a portable marker path for the copied skill source."""

    if source_root.name == "codex_skills" and source_root.parent.name == "tools":
        repo_root = source_root.parent.parent
        return source.relative_to(repo_root).as_posix()
    return source.relative_to(source_root).as_posix()


def _copy_with_marker(source: Path, source_root: Path, destination: Path) -> None:
    shutil.copytree(source, destination)
    (destination / SOURCE_MARKER).write_text(
        f"{_source_marker_value(source, source_root)}\n",
        encoding="utf-8",
    )


def sync_skill_mirror(
    *,
    skill_name: str,
    source_root: Path,
    mirror_root: Path,
    force: bool,
) -> None:
    """Copy a skill from `source_root` into `mirror_root` and overwrite if `force`."""

    source_root = source_root.resolve()
    mirror_root = mirror_root.resolve()

    safe_skill_name = _validate_skill_name(skill_name)
    source = _ensure_skill_available(source_root, safe_skill_name)
    destination = _destination_child_path(mirror_root, safe_skill_name)

    if destination.exists() or destination.is_symlink():
        if not force:
            raise RuntimeError("Destination exists; use --force to replace: " f"{destination}")
        _clear_existing_path(destination)

    mirror_root.mkdir(parents=True, exist_ok=True)
    _copy_with_marker(source, source_root, destination)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync one skill from tools/codex_skills into .agents/skills."
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Skill directory name in tools/codex_skills, e.g. pulseplate-pr-review",
    )
    parser.add_argument(
        "--source-root",
        default=str(DEFAULT_SOURCE_ROOT),
        help="Path to skill source root (default: repo/tools/codex_skills)",
    )
    parser.add_argument(
        "--mirror-root",
        default=str(DEFAULT_MIRROR_ROOT),
        help="Path for discovered skill mirror (default: .agents/skills)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing destination before syncing",
    )

    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        sync_skill_mirror(
            skill_name=args.name,
            source_root=Path(args.source_root),
            mirror_root=Path(args.mirror_root),
            force=args.force,
        )
    except (
        FileNotFoundError,
        RuntimeError,
        PermissionError,
        SkillMirrorValidationError,
    ) as exc:
        print(f"ERROR: {exc}")
        return 1

    destination = Path(args.mirror_root) / args.name
    print(f"Synced {args.name} -> {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
