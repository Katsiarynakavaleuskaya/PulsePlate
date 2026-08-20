"""Tests for the Codex skills installer contract."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

from scripts import verify_codex_skills_install

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_PATH = REPO_ROOT / "scripts" / "install_codex_skills.sh"
BASH_PATH = shutil.which("bash")
CYBERSEC_FIXTURE_SKILL = "implementing-diamond-model-analysis"
PR_CLOSEOUT_SKILL_PATH = (
    REPO_ROOT / "tools" / "codex_skills" / "pulseplate-pr-closeout" / "SKILL.md"
)
PR_CLOSEOUT_METADATA = {
    "interface": {
        "display_name": "PulsePlate PR Closeout",
        "short_description": "Govern PulsePlate PR closeout evidence",
        "default_prompt": (
            "Use $pulseplate-pr-closeout in audit-only mode by default. Treat every "
            "mutation and merge as blocked unless a mutating mode is explicitly "
            "selected and separate explicit human authorization binds each exact "
            "effect in a fresh closed bundle."
        ),
    }
}
PR_CLOSEOUT_EFFECTS = frozenset(
    {
        "draft_init",
        "draft_freeze",
        "disposition_write",
        "validation_write",
        "mapping_write",
        "pr_body_write",
        "mapping_commit",
        "push",
        "thread_reply",
        "thread_resolution",
        "base_sync",
        "merge",
        "main_sync",
        "branch_delete",
        "worktree_delete",
        "temporary_path_delete",
    }
)


def _mirrored_skill_files(mirrored_skill: Path) -> dict[Path, bytes]:
    """Collect mirror bytes while excluding only the root source marker."""

    root_marker = mirrored_skill / ".pulseplate_codex_skill_source"
    inventory: dict[Path, bytes] = {}
    for path in mirrored_skill.rglob("*"):
        if path == root_marker:
            continue
        assert not path.is_symlink(), f"mirror inventory rejects symlink: {path}"
        if path.is_file():
            inventory[path.relative_to(mirrored_skill)] = path.read_bytes()
    return inventory


def _run_installer(
    home_root: Path,
    *args: str,
    set_codex_home: bool = True,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the installer with an isolated HOME/CODEX_HOME."""

    assert BASH_PATH is not None, "bash is required for installer tests"
    env = {
        **os.environ,
        "HOME": str(home_root),
    }
    if set_codex_home:
        env["CODEX_HOME"] = str(home_root / ".codex")
    else:
        env.pop("CODEX_HOME", None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [BASH_PATH, str(INSTALLER_PATH), *args],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )


def _create_cybersec_skill_fixture(tmp_path: Path) -> Path:
    """Create a minimal cybersecurity skills source for installer contract tests."""

    cybersec_root = tmp_path / "cybersec-skills"
    skill_dir = cybersec_root / CYBERSEC_FIXTURE_SKILL
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n" f"name: {CYBERSEC_FIXTURE_SKILL}\n" "---\n\n" "# Fixture skill\n",
        encoding="utf-8",
    )
    return cybersec_root


def test_install_codex_skills_defaults_to_official_agents_target(tmp_path: Path) -> None:
    """Default list output should point to ~/.agents/skills, not ~/.codex/skills."""

    result = _run_installer(tmp_path, "--list", "--no-cybersec")

    assert "Target: official" in result.stdout
    assert f"Destination: {tmp_path / '.agents' / 'skills'}" in result.stdout


def test_install_codex_skills_installs_and_unlinks_official_target(tmp_path: Path) -> None:
    """Default install should write only to the official ~/.agents/skills target."""

    install_result = _run_installer(tmp_path, "--no-cybersec")
    agents_skills_root = tmp_path / ".agents" / "skills"
    codex_skills_root = tmp_path / ".codex" / "skills"
    installed_skill = agents_skills_root / "pulseplate-workflow"

    assert "Linked: pulseplate-workflow" in install_result.stdout
    assert installed_skill.is_symlink()
    assert installed_skill.resolve() == (
        REPO_ROOT / "tools" / "codex_skills" / "pulseplate-workflow"
    )
    assert not codex_skills_root.exists()

    unlink_result = _run_installer(tmp_path, "--unlink", "--no-cybersec")
    assert "Unlinked: pulseplate-workflow" in unlink_result.stdout
    assert not installed_skill.exists()


def test_install_codex_skills_honors_agents_home_override(tmp_path: Path) -> None:
    """Official installs should honor AGENTS_HOME when operators override the base path."""

    agents_home = tmp_path / "alt-agents-home"
    install_result = _run_installer(
        tmp_path,
        "--no-cybersec",
        extra_env={"AGENTS_HOME": str(agents_home)},
    )
    installed_skill = agents_home / "skills" / "pulseplate-workflow"

    assert "Linked: pulseplate-workflow" in install_result.stdout
    assert installed_skill.is_symlink()
    assert not (tmp_path / ".agents" / "skills").exists()

    list_result = _run_installer(
        tmp_path,
        "--list",
        "--no-cybersec",
        extra_env={"AGENTS_HOME": str(agents_home)},
    )
    assert "Target: official" in list_result.stdout
    assert f"Destination: {agents_home / 'skills'}" in list_result.stdout


def test_install_codex_skills_supports_explicit_compat_target(tmp_path: Path) -> None:
    """Compatibility installs should remain explicit and isolated to ~/.codex/skills."""

    install_result = _run_installer(tmp_path, "--target", "compat", "--no-cybersec")
    compat_skills_root = tmp_path / ".codex" / "skills"
    official_skills_root = tmp_path / ".agents" / "skills"
    installed_skill = compat_skills_root / "pulseplate-workflow"

    assert "Linked: pulseplate-workflow" in install_result.stdout
    assert installed_skill.is_symlink()
    assert not official_skills_root.exists()

    list_result = _run_installer(tmp_path, "--target", "compat", "--list", "--no-cybersec")
    assert "Target: compat" in list_result.stdout
    assert f"Destination: {compat_skills_root}" in list_result.stdout

    unlink_result = _run_installer(tmp_path, "--target", "compat", "--unlink", "--no-cybersec")
    assert "Unlinked: pulseplate-workflow" in unlink_result.stdout
    assert not installed_skill.exists()


def test_install_codex_skills_copy_cybersec_copies_only_cybersecurity_bundle(
    tmp_path: Path,
) -> None:
    """--copy-cybersec should copy cybersecurity skills while keeping PulsePlate skills linked."""

    cybersec_root = _create_cybersec_skill_fixture(tmp_path)
    install_result = _run_installer(
        tmp_path,
        "--copy-cybersec",
        extra_env={"PULSEPLATE_CYBERSEC_SKILLS_ROOT": str(cybersec_root)},
    )
    agents_skills_root = tmp_path / ".agents" / "skills"
    pulseplate_skill = agents_skills_root / "pulseplate-workflow"
    cyber_skill = agents_skills_root / CYBERSEC_FIXTURE_SKILL

    assert "Linked: pulseplate-workflow" in install_result.stdout
    assert f"Copied: {CYBERSEC_FIXTURE_SKILL}" in install_result.stdout
    assert pulseplate_skill.is_symlink()
    assert cyber_skill.is_dir()
    assert not cyber_skill.is_symlink()
    assert (cyber_skill / ".pulseplate_codex_skill_source").read_text().strip() == str(
        cybersec_root / CYBERSEC_FIXTURE_SKILL
    )


def test_install_codex_skills_copy_cybersec_accepts_trailing_slash_override(
    tmp_path: Path,
) -> None:
    """Cybersecurity source override should keep copy-mode with a trailing slash."""

    cybersec_root = _create_cybersec_skill_fixture(tmp_path)
    install_result = _run_installer(
        tmp_path,
        "--copy-cybersec",
        extra_env={"PULSEPLATE_CYBERSEC_SKILLS_ROOT": f"{cybersec_root}/"},
    )
    copied_skill = tmp_path / ".agents" / "skills" / CYBERSEC_FIXTURE_SKILL

    assert f"Copied: {CYBERSEC_FIXTURE_SKILL}" in install_result.stdout
    assert copied_skill.is_dir()
    assert not copied_skill.is_symlink()
    assert (copied_skill / ".pulseplate_codex_skill_source").read_text().strip() == str(
        cybersec_root / CYBERSEC_FIXTURE_SKILL
    )


def test_install_codex_skills_compat_target_falls_back_to_home_codex_when_unset(
    tmp_path: Path,
) -> None:
    """Compat target should fall back to HOME/.codex when CODEX_HOME is unset."""

    install_result = _run_installer(
        tmp_path,
        "--target",
        "compat",
        "--no-cybersec",
        set_codex_home=False,
    )
    compat_skills_root = tmp_path / ".codex" / "skills"
    installed_skill = compat_skills_root / "pulseplate-workflow"

    assert "Linked: pulseplate-workflow" in install_result.stdout
    assert installed_skill.is_symlink()


def test_install_codex_skills_help_clarifies_compat_fallback_when_codex_home_is_overridden(
    tmp_path: Path,
) -> None:
    """Help text should explain that ~/.codex is only the fallback when CODEX_HOME is unset."""

    result = _run_installer(tmp_path, "--help")

    assert (
        "compat -> $CODEX_HOME/skills (or $HOME/.codex/skills when CODEX_HOME is unset)."
        in result.stdout
    )
    assert "--copy-cybersec" in result.stdout


def test_install_codex_skills_only_cybersec_copy_mode_copies_skill_without_symlink_target(
    tmp_path: Path,
) -> None:
    """The dedicated cybersecurity copy path should produce copied skill folders."""

    cybersec_root = _create_cybersec_skill_fixture(tmp_path)
    install_result = _run_installer(
        tmp_path,
        "--only-cybersec",
        "--copy-cybersec",
        extra_env={"PULSEPLATE_CYBERSEC_SKILLS_ROOT": str(cybersec_root)},
    )
    copied_skill = tmp_path / ".agents" / "skills" / CYBERSEC_FIXTURE_SKILL

    assert f"Copied: {CYBERSEC_FIXTURE_SKILL}" in install_result.stdout
    assert copied_skill.is_dir()
    assert not copied_skill.is_symlink()


def test_install_codex_skills_explicit_dest_wins_over_target_regardless_of_order(
    tmp_path: Path,
) -> None:
    """Explicit --dest should remain authoritative even if --target is passed afterwards."""

    custom_skills_root = tmp_path / "custom-skills"
    install_result = _run_installer(
        tmp_path,
        "--dest",
        str(custom_skills_root),
        "--target",
        "compat",
        "--no-cybersec",
    )
    installed_skill = custom_skills_root / "pulseplate-workflow"

    assert "Linked: pulseplate-workflow" in install_result.stdout
    assert installed_skill.is_symlink()
    assert not (tmp_path / ".codex" / "skills").exists()

    list_result = _run_installer(
        tmp_path,
        "--dest",
        str(custom_skills_root),
        "--target",
        "compat",
        "--list",
        "--no-cybersec",
    )
    assert "Target: custom" in list_result.stdout
    assert f"Destination: {custom_skills_root}" in list_result.stdout


def test_install_codex_skills_explicit_dest_wins_when_target_comes_first(tmp_path: Path) -> None:
    """Explicit --dest should also win when it appears after --target compat."""

    custom_skills_root = tmp_path / "custom-skills"
    install_result = _run_installer(
        tmp_path,
        "--target",
        "compat",
        "--dest",
        str(custom_skills_root),
        "--no-cybersec",
    )
    installed_skill = custom_skills_root / "pulseplate-workflow"

    assert "Linked: pulseplate-workflow" in install_result.stdout
    assert installed_skill.is_symlink()
    assert not (tmp_path / ".codex" / "skills").exists()

    list_result = _run_installer(
        tmp_path,
        "--target",
        "compat",
        "--dest",
        str(custom_skills_root),
        "--list",
        "--no-cybersec",
    )
    assert "Target: custom" in list_result.stdout
    assert f"Destination: {custom_skills_root}" in list_result.stdout


def test_install_codex_skills_supports_explicit_custom_destination(tmp_path: Path) -> None:
    """Explicit --dest should use a custom target without touching default install roots."""

    custom_skills_root = tmp_path / "custom-skills"

    install_result = _run_installer(
        tmp_path,
        "--dest",
        str(custom_skills_root),
        "--no-cybersec",
    )
    installed_skill = custom_skills_root / "pulseplate-workflow"

    assert "Linked: pulseplate-workflow" in install_result.stdout
    assert installed_skill.is_symlink()
    assert not (tmp_path / ".agents" / "skills").exists()
    assert not (tmp_path / ".codex" / "skills").exists()

    list_result = _run_installer(
        tmp_path,
        "--dest",
        str(custom_skills_root),
        "--list",
        "--no-cybersec",
    )
    assert "Target: custom" in list_result.stdout
    assert f"Destination: {custom_skills_root}" in list_result.stdout

    unlink_result = _run_installer(
        tmp_path,
        "--dest",
        str(custom_skills_root),
        "--unlink",
        "--no-cybersec",
    )
    assert "Unlinked: pulseplate-workflow" in unlink_result.stdout
    assert not installed_skill.exists()


def test_install_codex_skills_unlink_is_side_effect_free_when_nothing_is_installed(
    tmp_path: Path,
) -> None:
    """Cleanup-only unlink should not create a destination directory on a clean HOME."""

    unlink_result = _run_installer(tmp_path, "--unlink", "--no-cybersec")

    assert "Not installed: pulseplate-workflow" in unlink_result.stdout
    assert not (tmp_path / ".agents" / "skills").exists()
    assert not (tmp_path / ".codex" / "skills").exists()


VERIFIER_PATH = REPO_ROOT / "scripts" / "verify_codex_skills_install.py"
PYTHON_PATH = shutil.which("python3") or shutil.which("python")


def _run_verifier(
    home_root: Path,
    *args: str,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the verifier with an isolated HOME."""

    assert PYTHON_PATH is not None, "python3 is required for verifier tests"
    env = {
        **os.environ,
        "HOME": str(home_root),
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [PYTHON_PATH, str(VERIFIER_PATH), *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )


def test_verify_codex_skills_install_passes_after_official_install(tmp_path: Path) -> None:
    """Verifier should pass when all expected skills are installed at destination."""

    _run_installer(tmp_path, "--no-cybersec")
    agents_skills = tmp_path / ".agents" / "skills"

    result = _run_verifier(tmp_path, "--dest", str(agents_skills))
    assert result.returncode == 0
    assert "All expected skills are installed" in result.stdout


def test_verify_codex_skills_install_passes_after_copy_install(tmp_path: Path) -> None:
    """Verifier should trust copied skills only when they match repo sources."""

    _run_installer(tmp_path, "--copy", "--no-cybersec")
    agents_skills = tmp_path / ".agents" / "skills"

    result = _run_verifier(tmp_path, "--dest", str(agents_skills), "--strict")
    assert result.returncode == 0
    assert "All expected skills are installed" in result.stdout


def test_verify_codex_skills_install_rejects_external_same_name_symlink(
    tmp_path: Path,
) -> None:
    """Strict verification must fail for same-name symlinks outside repo sources."""

    _run_installer(tmp_path, "--no-cybersec")
    agents_skills = tmp_path / ".agents" / "skills"
    installed_skill = agents_skills / "pulseplate-workflow"
    attacker_skill = tmp_path / "attacker-skills" / "pulseplate-workflow"
    attacker_skill.mkdir(parents=True)
    (attacker_skill / "SKILL.md").write_text("# attacker controlled\n", encoding="utf-8")
    installed_skill.unlink()
    installed_skill.symlink_to(attacker_skill)

    result = _run_verifier(tmp_path, "--dest", str(agents_skills), "--strict")
    assert result.returncode == 1
    assert "Invalid: 1" in result.stdout
    assert "pulseplate-workflow" in result.stdout


def test_verify_codex_skills_install_rejects_modified_same_name_copy(
    tmp_path: Path,
) -> None:
    """Strict verification must fail when a copied skill diverges from repo content."""

    _run_installer(tmp_path, "--copy", "--no-cybersec")
    agents_skills = tmp_path / ".agents" / "skills"
    copied_skill = agents_skills / "pulseplate-workflow"
    (copied_skill / "SKILL.md").write_text("# attacker controlled\n", encoding="utf-8")

    result = _run_verifier(tmp_path, "--dest", str(agents_skills), "--strict")
    assert result.returncode == 1
    assert "Invalid: 1" in result.stdout
    assert "pulseplate-workflow" in result.stdout


def test_verify_codex_skills_install_rejects_marker_symlink_without_leaking_target(
    tmp_path: Path,
) -> None:
    """Verifier JSON must not disclose marker symlink target contents."""

    import json as json_mod

    _run_installer(tmp_path, "--copy", "--no-cybersec")
    agents_skills = tmp_path / ".agents" / "skills"
    copied_skill = agents_skills / "pulseplate-workflow"
    payload_path = tmp_path / "marker-payload.txt"
    marker_payload = "PULSEPLATE_MARKER_PAYLOAD_DO_NOT_LOG"
    payload_path.write_text(marker_payload, encoding="utf-8")
    marker = copied_skill / ".pulseplate_codex_skill_source"
    marker.unlink()
    marker.symlink_to(payload_path)

    result = _run_verifier(tmp_path, "--dest", str(agents_skills), "--json", "--strict")
    assert result.returncode == 1
    assert marker_payload not in result.stdout

    report = json_mod.loads(result.stdout)
    detail = next(item for item in report["details"] if item["name"] == "pulseplate-workflow")
    assert detail["status"] == "copied_invalid"
    assert detail["marker"] == ""
    assert detail["marker_error"] in {"marker_not_regular", "marker_symlink"}


def test_read_copy_marker_fails_closed_without_no_follow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Existing marker files must fail closed if no no-follow open flag exists."""

    marker = tmp_path / ".pulseplate_codex_skill_source"
    marker.write_text(str(REPO_ROOT / "tools" / "codex_skills"), encoding="utf-8")

    monkeypatch.delattr(verify_codex_skills_install.os, "O_NOFOLLOW", raising=False)
    read_copy_marker = getattr(verify_codex_skills_install, "_read_copy_marker")
    marker_error = getattr(verify_codex_skills_install, "MARKER_ERROR_NO_NOFOLLOW")

    assert read_copy_marker(marker) == ("", marker_error)


def test_read_copy_marker_rejects_path_replacement_before_reading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A marker swapped after stat but before open must not be trusted."""

    marker = tmp_path / ".pulseplate_codex_skill_source"
    marker.write_text("original-marker", encoding="utf-8")
    replacement = tmp_path / "replacement-marker"
    replacement.write_text("replacement-marker", encoding="utf-8")
    real_open = verify_codex_skills_install.os.open

    def replacing_open(path: Path, flags: int) -> int:
        replacement.replace(marker)
        return real_open(path, flags)

    monkeypatch.setattr(verify_codex_skills_install.os, "open", replacing_open)
    read_copy_marker = getattr(verify_codex_skills_install, "_read_copy_marker")
    marker_error = getattr(verify_codex_skills_install, "MARKER_ERROR_REPLACED")

    assert read_copy_marker(marker) == ("", marker_error)


def test_verify_codex_skills_install_rejects_invalid_utf8_marker_without_crashing(
    tmp_path: Path,
) -> None:
    """Malformed copy markers should be reported as invalid instead of crashing."""

    import json as json_mod

    _run_installer(tmp_path, "--copy", "--no-cybersec")
    agents_skills = tmp_path / ".agents" / "skills"
    copied_skill = agents_skills / "pulseplate-workflow"
    marker = copied_skill / ".pulseplate_codex_skill_source"
    marker.write_bytes(b"\xff\xfe\xfd")

    result = _run_verifier(tmp_path, "--dest", str(agents_skills), "--json", "--strict")
    assert result.returncode == 1

    report = json_mod.loads(result.stdout)
    detail = next(item for item in report["details"] if item["name"] == "pulseplate-workflow")
    assert detail["status"] == "copied_invalid"
    assert detail["marker"] == ""
    assert detail["marker_error"] == "marker_invalid_utf8"


def test_verify_codex_skills_install_fails_when_skill_missing(tmp_path: Path) -> None:
    """Verifier with --strict should fail when a skill is missing from destination."""

    _run_installer(tmp_path, "--no-cybersec")
    agents_skills = tmp_path / ".agents" / "skills"

    # Remove one skill to create a gap
    missing_skill = agents_skills / "pulseplate-workflow"
    if missing_skill.is_symlink():
        missing_skill.unlink()
    else:
        shutil.rmtree(missing_skill)

    result = _run_verifier(tmp_path, "--dest", str(agents_skills), "--strict")
    assert result.returncode == 1
    assert "pulseplate-workflow" in result.stdout


def test_verify_codex_skills_install_supports_compat_target(tmp_path: Path) -> None:
    """Verifier should resolve compat target via CODEX_HOME."""

    codex_home = tmp_path / ".codex"
    _run_installer(tmp_path, "--target", "compat", "--no-cybersec")

    result = _run_verifier(
        tmp_path,
        "--target",
        "compat",
        extra_env={"CODEX_HOME": str(codex_home)},
    )
    assert result.returncode == 0
    assert "All expected skills are installed" in result.stdout


def test_verify_codex_skills_install_supports_custom_dest(tmp_path: Path) -> None:
    """Verifier should accept a custom --dest path."""

    custom_dest = tmp_path / "custom-skills"
    _run_installer(tmp_path, "--dest", str(custom_dest), "--no-cybersec")

    result = _run_verifier(tmp_path, "--dest", str(custom_dest))
    assert result.returncode == 0
    assert "All expected skills are installed" in result.stdout


def test_verify_codex_skills_install_reports_json(tmp_path: Path) -> None:
    """Verifier --json should produce valid JSON with expected fields."""

    import json as json_mod

    _run_installer(tmp_path, "--no-cybersec")
    agents_skills = tmp_path / ".agents" / "skills"

    result = _run_verifier(tmp_path, "--dest", str(agents_skills), "--json")
    assert result.returncode == 0

    report = json_mod.loads(result.stdout)
    # Derive expected count from repo source to avoid hardcoded fragility
    source_dir = REPO_ROOT / "tools" / "codex_skills"
    repo_skill_count = sum(
        1 for d in source_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
    )
    assert report["expected_count"] == repo_skill_count
    assert report["missing_count"] == 0
    assert report["missing"] == []


def test_verify_codex_skills_install_is_read_only(tmp_path: Path) -> None:
    """Verifier must not create or modify files at the destination."""

    empty_dest = tmp_path / "empty-dest"
    empty_dest.mkdir()

    before = set(empty_dest.iterdir())
    _run_verifier(tmp_path, "--dest", str(empty_dest))
    after = set(empty_dest.iterdir())

    assert before == after, "Verifier must not create files at destination"


def test_repo_agents_skills_mirror_points_to_codex_skill_sources() -> None:
    """Repo-local .agents/skills mirror must stay aligned to tools/codex_skills sources."""

    expected_skills = (
        "pulseplate-ai-reports",
        "pulseplate-agent-learning-loop",
        "pulseplate-agent-product",
        "pulseplate-app-store-release",
        "pulseplate-backend-endpoints",
        "pulseplate-design-launch-system",
        "pulseplate-frontend-ui",
        "pulseplate-gates",
        "pulseplate-graphmap",
        "pulseplate-guards",
        "pulseplate-ledger",
        "pulseplate-monetization-gtm",
        "pulseplate-openapi-sync",
        "pulseplate-playwright-e2e",
        "pulseplate-pr-closeout",
        "pulseplate-pr-review",
        "pulseplate-premortem-risk-review",
        "pulseplate-review-pattern-oracles",
        "pulseplate-web-launch-site",
        "pulseplate-workflow",
    )
    copied_skills = {
        "pulseplate-agent-learning-loop",
        "pulseplate-pr-closeout",
        "pulseplate-pr-review",
        "pulseplate-review-pattern-oracles",
    }
    discovered_skills = {
        path.name
        for path in (REPO_ROOT / "tools" / "codex_skills").iterdir()
        if path.is_dir() and path.joinpath("SKILL.md").is_file()
    }

    assert discovered_skills == set(expected_skills)

    for skill_name in expected_skills:
        mirrored_skill = REPO_ROOT / ".agents" / "skills" / skill_name
        source_skill = REPO_ROOT / "tools" / "codex_skills" / skill_name

        assert source_skill.is_dir(), f"{skill_name} source directory must exist"
        assert (source_skill / "SKILL.md").exists(), f"{skill_name} source must include SKILL.md"
        if skill_name in copied_skills:
            assert (
                mirrored_skill.is_dir()
            ), f"{skill_name} mirror is required for PR-review workflow"
            assert not mirrored_skill.is_symlink()
            marker = mirrored_skill / ".pulseplate_codex_skill_source"
            assert marker.exists(), f"{skill_name} mirror must carry source marker"
            marker_parts = tuple(Path(marker.read_text(encoding="utf-8").strip()).parts)
            expected_parts = source_skill.relative_to(REPO_ROOT).parts
            assert marker_parts[-len(expected_parts) :] == expected_parts
            source_files = {
                path.relative_to(source_skill): path.read_bytes()
                for path in source_skill.rglob("*")
                if path.is_file()
            }
            mirrored_files = _mirrored_skill_files(mirrored_skill)
            assert mirrored_files == source_files
            if skill_name == "pulseplate-pr-closeout":
                metadata = mirrored_skill / "agents" / "openai.yaml"
                assert metadata.is_file()
                assert yaml.safe_load(metadata.read_text(encoding="utf-8")) == (
                    PR_CLOSEOUT_METADATA
                )
        else:
            assert mirrored_skill.is_symlink(), f"{skill_name} must be exposed via .agents/skills"
            assert mirrored_skill.resolve() == source_skill


def test_pr_closeout_skill_has_one_closed_effect_vocabulary() -> None:
    """The passive closeout skill should enumerate one finite mutation vocabulary."""

    skill_text = PR_CLOSEOUT_SKILL_PATH.read_text(encoding="utf-8")
    authority_section = skill_text.split("## Require one closed effect bundle", 1)[1].split(
        "## Admit the lane", 1
    )[0]
    table_effects = {
        line.split("`")[1] for line in authority_section.splitlines() if line.startswith("| `")
    }

    assert table_effects == PR_CLOSEOUT_EFFECTS


def test_mirror_file_inventory_excludes_only_root_source_marker(tmp_path: Path) -> None:
    """A nested marker-named file must remain visible to mirror comparison."""

    mirrored_skill = tmp_path / "copied-skill"
    nested = mirrored_skill / "nested"
    nested.mkdir(parents=True)
    (mirrored_skill / ".pulseplate_codex_skill_source").write_text(
        "tools/codex_skills/copied-skill\n", encoding="utf-8"
    )
    (mirrored_skill / "SKILL.md").write_text("skill\n", encoding="utf-8")
    (nested / ".pulseplate_codex_skill_source").write_text(
        "unexpected nested marker\n", encoding="utf-8"
    )

    assert _mirrored_skill_files(mirrored_skill) == {
        Path("SKILL.md"): b"skill\n",
        Path("nested/.pulseplate_codex_skill_source"): b"unexpected nested marker\n",
    }


def test_mirror_file_inventory_rejects_nested_symlink(tmp_path: Path) -> None:
    """Mirror comparison must reject symlinks instead of following their targets."""

    mirrored_skill = tmp_path / "copied-skill"
    nested = mirrored_skill / "nested"
    nested.mkdir(parents=True)
    target = nested / "target.md"
    target.write_text("same bytes\n", encoding="utf-8")
    (nested / "SKILL.md").symlink_to(target.name)

    with pytest.raises(AssertionError, match="mirror inventory rejects symlink"):
        _mirrored_skill_files(mirrored_skill)


@pytest.mark.parametrize(
    "required_clause",
    (
        pytest.param(
            "`AUDIT` always has an empty effect-instance list and denies every "
            "effect in the table.",
            id="audit-denies-all-mutations",
        ),
        pytest.param(
            "Interpret a pre-closeout `PASS` as procedural admission evidence only. "
            "It is not user authorization for mapping write, mapping commit, push, "
            "thread mutation, or merge",
            id="pre-closeout-pass-is-not-authority",
        ),
        pytest.param(
            "Without a fresh, post-readiness `merge` effect instance from a separate "
            "human authority bundle, stop at `READY_FOR_AUTHORIZED_MERGE`.",
            id="readiness-requires-fresh-merge-authority",
        ),
        pytest.param(
            "A `merge` effect never implies `branch_delete`, `main_sync`, "
            "`worktree_delete`, or `temporary_path_delete`.",
            id="merge-does-not-authorize-deletion",
        ),
        pytest.param(
            "If an effect is omitted, stale, already consumed, replayed, retargeted, "
            "wildcarded, or not in the closed vocabulary, fail closed in every mode",
            id="invalid-bundle-effects-fail-closed",
        ),
    ),
)
def test_pr_closeout_skill_authority_contract_is_fail_closed(required_clause: str) -> None:
    """Static scenarios should retain the fail-closed human-authority boundary."""

    skill_text = PR_CLOSEOUT_SKILL_PATH.read_text(encoding="utf-8")
    normalized_skill = " ".join(skill_text.split())
    merge_command = skill_text.split("gh pr merge <N>", 1)[1].split("```", 1)[0]

    assert required_clause in normalized_skill
    assert "--delete-branch" not in merge_command
