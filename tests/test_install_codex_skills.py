"""Tests for the Codex skills installer contract."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_PATH = REPO_ROOT / "scripts" / "install_codex_skills.sh"
BASH_PATH = shutil.which("bash")


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


def test_repo_agents_skills_mirror_points_to_codex_skill_sources() -> None:
    """Repo-local .agents/skills mirror must stay aligned to tools/codex_skills sources."""

    expected_skills = (
        "pulseplate-ai-reports",
        "pulseplate-backend-endpoints",
        "pulseplate-frontend-ui",
        "pulseplate-gates",
        "pulseplate-graphmap",
        "pulseplate-guards",
        "pulseplate-ledger",
        "pulseplate-openapi-sync",
        "pulseplate-playwright-e2e",
        "pulseplate-workflow",
    )

    for skill_name in expected_skills:
        mirrored_skill = REPO_ROOT / ".agents" / "skills" / skill_name
        source_skill = REPO_ROOT / "tools" / "codex_skills" / skill_name

        assert source_skill.is_dir(), f"{skill_name} source directory must exist"
        assert (source_skill / "SKILL.md").exists(), f"{skill_name} source must include SKILL.md"
        assert mirrored_skill.is_symlink(), f"{skill_name} must be exposed via .agents/skills"
        assert mirrored_skill.resolve() == source_skill
