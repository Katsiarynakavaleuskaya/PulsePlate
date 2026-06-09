"""Tests for the Codex skills installer contract."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_PATH = REPO_ROOT / "scripts" / "install_codex_skills.sh"
BASH_PATH = shutil.which("bash")
CYBERSEC_FIXTURE_SKILL = "implementing-diamond-model-analysis"


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
    secret_path = tmp_path / "secret.txt"
    secret_value = "PULSEPLATE_VALIDATION_SECRET_DO_NOT_LOG"
    secret_path.write_text(secret_value, encoding="utf-8")
    marker = copied_skill / ".pulseplate_codex_skill_source"
    marker.unlink()
    marker.symlink_to(secret_path)

    result = _run_verifier(tmp_path, "--dest", str(agents_skills), "--json", "--strict")
    assert result.returncode == 1
    assert secret_value not in result.stdout

    report = json_mod.loads(result.stdout)
    detail = next(
        item for item in report["details"] if item["name"] == "pulseplate-workflow"
    )
    assert detail["status"] == "copied_invalid"
    assert detail["marker"] == ""
    assert detail["marker_error"] in {"marker_not_regular", "marker_symlink"}


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
    detail = next(
        item for item in report["details"] if item["name"] == "pulseplate-workflow"
    )
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
        "pulseplate-pr-review",
        "pulseplate-premortem-risk-review",
        "pulseplate-web-launch-site",
        "pulseplate-workflow",
    )

    for skill_name in expected_skills:
        mirrored_skill = REPO_ROOT / ".agents" / "skills" / skill_name
        source_skill = REPO_ROOT / "tools" / "codex_skills" / skill_name

        assert source_skill.is_dir(), f"{skill_name} source directory must exist"
        assert (source_skill / "SKILL.md").exists(), f"{skill_name} source must include SKILL.md"
        if skill_name == "pulseplate-pr-review":
            assert (
                mirrored_skill.is_dir()
            ), f"{skill_name} mirror is required for PR-review workflow"
            assert not mirrored_skill.is_symlink()
            marker = mirrored_skill / ".pulseplate_codex_skill_source"
            assert marker.exists(), f"{skill_name} mirror must carry source marker"
            marker_parts = tuple(Path(marker.read_text(encoding="utf-8").strip()).parts)
            expected_parts = source_skill.relative_to(REPO_ROOT).parts
            assert marker_parts[-len(expected_parts) :] == expected_parts
            assert (mirrored_skill / "SKILL.md").exists()
        else:
            assert mirrored_skill.is_symlink(), f"{skill_name} must be exposed via .agents/skills"
            assert mirrored_skill.resolve() == source_skill
