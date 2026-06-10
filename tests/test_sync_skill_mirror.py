"""Tests for the deterministic skill mirror sync helper."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.orchestration import sync_skill_mirror


def test_sync_skill_mirror_copies_source_and_writes_marker(tmp_path: Path) -> None:
    source_root = tmp_path / "tools" / "codex_skills"
    skill_name = "pulseplate-pr-review"
    source_skill = source_root / skill_name
    source_skill.mkdir(parents=True)
    source_skill.joinpath("SKILL.md").write_text(
        "---\nname: pulseplate-pr-review\n---\n", encoding="utf-8"
    )

    mirror_root = tmp_path / ".agents" / "skills"

    sync_skill_mirror.sync_skill_mirror(
        skill_name=skill_name,
        source_root=source_root,
        mirror_root=mirror_root,
        force=False,
    )

    mirrored_skill = mirror_root / skill_name
    assert mirrored_skill.is_dir()
    assert not mirrored_skill.is_symlink()
    assert mirrored_skill.joinpath("SKILL.md").exists()
    marker = mirrored_skill / ".pulseplate_codex_skill_source"
    assert marker.exists()
    assert marker.read_text(encoding="utf-8").strip() == "tools/codex_skills/pulseplate-pr-review"


def test_sync_skill_mirror_writes_source_root_relative_marker_for_custom_root(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "custom_tools"
    skill_name = "custom-review-skill"
    source_skill = source_root / skill_name
    source_skill.mkdir(parents=True)
    source_skill.joinpath("SKILL.md").write_text("# custom", encoding="utf-8")

    mirror_root = tmp_path / "custom_mirror"

    sync_skill_mirror.sync_skill_mirror(
        skill_name=skill_name,
        source_root=source_root,
        mirror_root=mirror_root,
        force=False,
    )

    marker = mirror_root / skill_name / ".pulseplate_codex_skill_source"
    assert marker.exists()
    assert marker.read_text(encoding="utf-8").strip() == skill_name


@pytest.mark.parametrize(
    "unsafe_skill_name",
    [
        "../pulseplate-pr-review",
        "custom_layout/pulseplate-pr-review",
        r"custom_layout\\pulseplate-pr-review",
        "/tmp/pulseplate-pr-review",
        "",
        ".",
        "..",
    ],
)
def test_sync_skill_mirror_rejects_path_like_skill_names(
    tmp_path: Path, unsafe_skill_name: str
) -> None:
    source_root = tmp_path / "tools" / "codex_skills"
    mirror_root = tmp_path / "mirror"

    with pytest.raises(ValueError, match="single directory name"):
        sync_skill_mirror.sync_skill_mirror(
            skill_name=unsafe_skill_name,
            source_root=source_root,
            mirror_root=mirror_root,
            force=True,
        )


def test_sync_skill_mirror_rejects_source_symlink_escape(tmp_path: Path) -> None:
    source_root = tmp_path / "tools" / "codex_skills"
    source_root.mkdir(parents=True)
    escaped_skill = tmp_path / "escaped-skill"
    escaped_skill.mkdir()
    escaped_skill.joinpath("SKILL.md").write_text("# escaped", encoding="utf-8")
    source_root.joinpath("pulseplate-pr-review").symlink_to(
        escaped_skill, target_is_directory=True
    )

    with pytest.raises(ValueError, match="escapes configured root"):
        sync_skill_mirror.sync_skill_mirror(
            skill_name="pulseplate-pr-review",
            source_root=source_root,
            mirror_root=tmp_path / "mirror",
            force=False,
        )


def test_sync_skill_mirror_force_does_not_clear_traversed_destination(tmp_path: Path) -> None:
    source_root = tmp_path / "source" / "deeper"
    payload_source = tmp_path / "source" / "payload"
    payload_source.mkdir(parents=True)
    payload_source.joinpath("SKILL.md").write_text("# payload", encoding="utf-8")
    outside_destination = tmp_path / "payload"
    outside_destination.mkdir()
    outside_destination.joinpath("stale.txt").write_text("stale", encoding="utf-8")

    with pytest.raises(ValueError, match="single directory name"):
        sync_skill_mirror.sync_skill_mirror(
            skill_name="../payload",
            source_root=source_root,
            mirror_root=tmp_path / "mirror",
            force=True,
        )

    assert outside_destination.joinpath("stale.txt").read_text(encoding="utf-8") == "stale"


def test_sync_skill_mirror_rejects_existing_without_force(tmp_path: Path) -> None:
    source_root = tmp_path / "tools" / "codex_skills" / "pulseplate-pr-review"
    source_root.mkdir(parents=True)
    source_root.joinpath("SKILL.md").write_text("# source", encoding="utf-8")

    mirror_root = tmp_path / "mirror"
    destination = mirror_root / "pulseplate-pr-review"
    mirror_root.mkdir()
    destination.mkdir()

    with pytest.raises(RuntimeError):
        sync_skill_mirror.sync_skill_mirror(
            skill_name="pulseplate-pr-review",
            source_root=source_root.parent,
            mirror_root=mirror_root,
            force=False,
        )


def test_sync_skill_mirror_force_replaces_existing_destination(tmp_path: Path) -> None:
    source_root = tmp_path / "tools" / "codex_skills" / "pulseplate-pr-review"
    source_root.mkdir(parents=True)
    source_root.joinpath("SKILL.md").write_text("# source", encoding="utf-8")

    mirror_root = tmp_path / "mirror"
    destination = mirror_root / "pulseplate-pr-review"
    mirror_root.mkdir()
    destination.mkdir()
    destination.joinpath("stale.txt").write_text("stale", encoding="utf-8")

    sync_skill_mirror.sync_skill_mirror(
        skill_name="pulseplate-pr-review",
        source_root=source_root.parent,
        mirror_root=mirror_root,
        force=True,
    )

    assert destination.is_dir()
    assert not destination.joinpath("stale.txt").exists()
    assert destination.joinpath("SKILL.md").exists()
    marker = destination / ".pulseplate_codex_skill_source"
    assert marker.read_text(encoding="utf-8").strip() == "tools/codex_skills/pulseplate-pr-review"
