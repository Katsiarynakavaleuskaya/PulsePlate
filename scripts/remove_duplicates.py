#!/usr/bin/env python3
"""
Find and optionally remove duplicate files safely.

Safety rules:
- Only consider files with backup-like suffixes as auto-removable when a base twin exists
  with identical content: .bak, .broken, .old, .orig, .copy, .tmp
- Never touch files under version control essentials: .git/, .venv/, __pycache__/,
  .pytest_cache/, htmlcov/, cache/, data/, external/
- Never delete inside tests/ by default (use --include-tests to allow)

Usage:
  python scripts/remove_duplicates.py                         # dry-run (prints plan)
  python scripts/remove_duplicates.py --execute               # remove safe backup twins
  python scripts/remove_duplicates.py --suggest               # suggest canonical file per identical group
  python scripts/remove_duplicates.py --apply-identical       # remove non-canonical files in identical groups
  python scripts/remove_duplicates.py --include-tests --apply-identical
  python scripts/remove_duplicates.py --prune-releases --apply-identical
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(".").resolve()
SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "htmlcov",
    "cache",
    "data",
    "external",
}
SAFE_SUFFIXES = [".bak", ".broken", ".old", ".orig", ".copy", ".tmp"]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def is_skipped_dir(p: Path) -> bool:
    parts = set(part for part in p.parts)
    return any(sd in parts for sd in SKIP_DIRS)


def collect_files(include_tests: bool) -> List[Path]:
    out: List[Path] = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if is_skipped_dir(p):
            continue
        if not include_tests and (ROOT / "tests") in p.parents:
            continue
        out.append(p)
    return out


def plan_removals(files: List[Path]) -> Tuple[List[Tuple[Path, Path]], List[List[Path]]]:
    """Return (backup_twins, full_duplicates).

    backup_twins: list of (backup_file, base_file) to remove backup_file when hash equal
    full_duplicates: list of groups (>=2) of identical files (different paths)
    """
    # Map base -> backups with safe suffixes
    backups: List[Tuple[Path, Path]] = []
    # Hash map for full duplicates
    by_hash: Dict[str, List[Path]] = {}

    # Prepare lookup for base twins
    for f in files:
        # Full duplicates hash collection
        try:
            h = sha256_of(f)
        except Exception:
            continue
        by_hash.setdefault(h, []).append(f)

        # Backup twin detection
        for suf in SAFE_SUFFIXES:
            if f.name.endswith(suf):
                base = f.with_name(f.name[: -len(suf)])
                if base.exists() and base.is_file():
                    backups.append((f, base))
                break

    # Full duplicate groups (same hash) > 1
    dup_groups = [paths for paths in by_hash.values() if len(paths) > 1]
    return backups, dup_groups


def path_score(p: Path) -> int:
    """Higher score = more canonical/preferred to keep for identical files.

    Heuristics:
    - Avoid backup suffixes (penalty)
    - Avoid releases artifacts (penalty)
    - Prefer non-coverage dirs (penalty for coverage_html/cov_html)
    - Prefer shorter path (slight bonus)
    - Prefer top-level project files (bonus for under ROOT and not in nested dist)
    """
    s = 0
    name = p.name
    # penalties
    if any(name.endswith(suf) for suf in SAFE_SUFFIXES):
        s -= 50
    parts = [str(x) for x in p.parts]
    if "releases" in parts:
        s -= 40
    if any(seg in ("coverage_html", "cov_html") for seg in parts):
        s -= 30
    if (ROOT / "tests") in p.parents:
        s -= 10  # do not prefer tests by default
    # bonuses
    s += max(0, 20 - len(parts))  # shorter paths preferred
    if p.parent == ROOT:
        s += 10
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="remove safe backup twins")
    ap.add_argument("--include-tests", action="store_true", help="allow touching tests/")
    ap.add_argument(
        "--suggest", action="store_true", help="suggest canonical file per identical group"
    )
    ap.add_argument(
        "--apply-identical", action="store_true", help="remove non-canonical in identical groups"
    )
    ap.add_argument("--prune-releases", action="store_true", help="allow deleting under releases/")
    args = ap.parse_args()

    files = collect_files(include_tests=args.include_tests)
    backups, dup_groups = plan_removals(files)

    print("Backup twins (candidate for removal if identical):")
    removed = []
    for backup, base in backups:
        try:
            if sha256_of(backup) == sha256_of(base):
                print("  ", backup, "<= IDENTICAL =>", base)
                if args.execute:
                    backup.unlink()
                    removed.append(str(backup))
            else:
                print("  ", backup, "!=", base)
        except Exception as e:
            print("   ! error:", backup, e)

    print("\nFull duplicate groups (identical content):")
    to_remove: List[Path] = []
    suggestions = []
    for grp in dup_groups:
        if len(grp) < 2:
            continue
        # Choose canonical by score
        canonical = max(grp, key=path_score)
        others = [p for p in grp if p != canonical]
        suggestions.append((canonical, others))
    # Print suggestions
    for can, others in suggestions[:50]:
        print("  keep:", can)
        for p in others:
            print("   rm:", p)
    if len(suggestions) > 50:
        print(f"  ... and {len(suggestions) - 50} more groups")

    if args.suggest and not (args.apply_identical or args.execute):
        return 0

    if args.apply_identical:
        for can, others in suggestions:
            for p in others:
                # Safety: skip tests unless included
                if not args.include_tests and (ROOT / "tests") in p.parents:
                    continue
                # Skip releases unless allowed
                if not args.prune_releases and "releases" in {str(x) for x in p.parts}:
                    continue
                try:
                    p.unlink()
                    to_remove.append(p)
                except Exception as e:
                    print("   ! error removing", p, e)

    if args.execute or args.apply_identical:
        print("\nRemoved:")
        for p in removed + [str(x) for x in to_remove]:
            print("  ", p)
    else:
        print(
            "\n(dry-run) pass --execute to apply backup removals; --apply-identical to prune identical duplicates; --suggest to only show canonical picks"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
