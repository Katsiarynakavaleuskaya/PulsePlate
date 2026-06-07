"""Guard: all symlinks in .agents/skills/ must resolve to valid SKILL.md files.

Broken symlinks cause silent skill loading failures in all runtimes
(Kimi CLI, Codex, Qoder) because .agents/skills/ is the canonical Project-scope
discovery path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"


def test_all_skill_symlinks_resolve() -> None:
    """Every entry in .agents/skills/ must either be a real directory with
    SKILL.md or a symlink that resolves to a directory with SKILL.md.

    If the canonical skill source submodule is missing, skip rather than fail
    so that CI environments without submodules initialized degrade gracefully.
    """
    if not SKILLS_DIR.exists():
        pytest.skip(f"Skills directory missing: {SKILLS_DIR}")

    # Detect missing submodule early and skip gracefully
    codex_skills_source = REPO_ROOT / "tools" / "codex_skills"
    if not codex_skills_source.exists():
        pytest.skip("tools/codex_skills/ missing — run: git submodule update --init --recursive")

    broken: list[str] = []
    for entry in sorted(SKILLS_DIR.iterdir()):
        if entry.is_symlink():
            try:
                resolved = entry.resolve()
            except OSError as exc:
                broken.append(f"{entry.name} -> unreadable symlink ({exc})")
                continue
            skill_md = resolved / "SKILL.md"
            if not skill_md.exists():
                broken.append(
                    f"{entry.name} -> {entry.readlink()} (resolved: {resolved}; "
                    f"SKILL.md missing)"
                )
        elif entry.is_dir():
            skill_md = entry / "SKILL.md"
            if not skill_md.exists():
                broken.append(f"{entry.name}/ missing SKILL.md")
        else:
            broken.append(f"{entry.name} is not a directory or symlink")

    assert (
        not broken
    ), f"Broken skill entries in {SKILLS_DIR.relative_to(REPO_ROOT)}:\n" + "\n".join(
        f"  - {b}" for b in broken
    )
