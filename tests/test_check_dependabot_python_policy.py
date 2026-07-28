"""Tests for the production-governed Python Dependabot policy."""

from __future__ import annotations

from pathlib import Path
import shutil

import pytest
import yaml

from scripts.ci import check_dependabot_python_policy as policy
from scripts.ci.check_python_dependency_surfaces import DEPENDENCY_SURFACES

REPO_ROOT = Path(__file__).resolve().parents[1]


def _copy_policy_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / ".github").mkdir(parents=True)
    shutil.copy2(REPO_ROOT / policy.CONFIG_PATH, repo / policy.CONFIG_PATH)
    requirement_files = {
        relative_path
        for surface in DEPENDENCY_SURFACES
        for relative_path in (surface.source_file, surface.lockfile)
        if relative_path is not None
    }
    for relative_path in requirement_files:
        source = REPO_ROOT / relative_path
        if source.is_file():
            shutil.copy2(source, repo / relative_path)
    return repo


def _load_config(repo: Path) -> dict[str, object]:
    loaded = yaml.safe_load((repo / policy.CONFIG_PATH).read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _write_config(repo: Path, config: dict[str, object]) -> None:
    (repo / policy.CONFIG_PATH).write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )


def _pip_update(config: dict[str, object]) -> dict[str, object]:
    updates = config["updates"]
    assert isinstance(updates, list)
    update = updates[0]
    assert isinstance(update, dict)
    return update


def _groups(config: dict[str, object]) -> dict[str, object]:
    groups = _pip_update(config)["groups"]
    assert isinstance(groups, dict)
    return groups


def test_live_dependabot_policy_passes() -> None:
    assert policy.validate_repo(REPO_ROOT) == []


def test_shadow_yaml_fails_closed(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    (repo / policy.SHADOW_CONFIG_PATH).write_text("version: 2\n", encoding="utf-8")

    errors = policy.validate_repo(repo)

    assert ".github/dependabot.yaml:$:shadow Dependabot config is forbidden" in errors


def test_broken_shadow_yaml_symlink_fails_closed(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    (repo / policy.SHADOW_CONFIG_PATH).symlink_to("missing-dependabot-config")

    errors = policy.validate_repo(repo)

    assert ".github/dependabot.yaml:$:shadow Dependabot config is forbidden" in errors


def test_primary_config_symlink_fails_closed(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    config_path = repo / policy.CONFIG_PATH
    target_path = config_path.with_name("dependabot-target.yml")
    config_path.replace(target_path)
    config_path.symlink_to(target_path.name)

    errors = policy.validate_repo(repo)

    assert errors == [".github/dependabot.yml:$:required config must be a regular non-symlink file"]


def test_duplicate_yaml_key_fails_closed_with_cli_shape(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    config_path = repo / policy.CONFIG_PATH
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + "\nversion: 2\n",
        encoding="utf-8",
    )

    errors = policy.validate_repo(repo)

    assert len(errors) == 1
    assert errors[0].startswith(".github/dependabot.yml:$:invalid YAML:")
    assert "duplicate key" in errors[0]


def test_cyclic_yaml_alias_fails_closed_with_cli_shape(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _copy_policy_repo(tmp_path)
    (repo / policy.CONFIG_PATH).write_text(
        "version: 2\n"
        "registries: {}\n"
        "updates:\n"
        "  - package-ecosystem: pip\n"
        "    directory: /\n"
        "    groups: &cycle [*cycle]\n",
        encoding="utf-8",
    )

    errors = policy.validate_repo(repo)

    assert errors == [".github/dependabot.yml:$:cyclic YAML aliases are forbidden"]

    exit_code = policy.main(["--repo-root", str(repo)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == f"{errors[0]}\n"
    assert captured.err == ""
    assert "Traceback" not in captured.out


def test_mixed_scalar_yaml_keys_return_deterministic_errors(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    config_path = repo / policy.CONFIG_PATH
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + "\n1: extra\n",
        encoding="utf-8",
    )

    errors = policy.validate_repo(repo)

    assert any(
        error.startswith(".github/dependabot.yml:$:root keys must be exactly")
        and "got [1, 'registries', 'updates', 'version']" in error
        for error in errors
    )


@pytest.mark.parametrize(
    "complex_key",
    [
        "? [sequence-key-must-not-leak]\n: value",
        "? {mapping-key-must-not-leak: true}\n: value",
    ],
)
def test_unhashable_yaml_keys_return_sanitized_api_and_cli_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    complex_key: str,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config_path = repo / policy.CONFIG_PATH
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + f"\n{complex_key}\n",
        encoding="utf-8",
    )

    errors = policy.validate_repo(repo)

    assert errors == [
        ".github/dependabot.yml:$:invalid YAML: constructor error "
        f"at line {len(config_path.read_text(encoding='utf-8').splitlines()) - 1}, column 3"
    ]
    assert "must-not-leak" not in errors[0]

    exit_code = policy.main(["--repo-root", str(repo)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "must-not-leak" not in captured.out
    assert "must-not-leak" not in captured.err
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err


def test_registry_contract_rejects_public_fallback_and_wildcard_binding(
    tmp_path: Path,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    registries = config["registries"]
    assert isinstance(registries, dict)
    registry = registries[policy.REGISTRY_NAME]
    assert isinstance(registry, dict)
    registry["replaces-base"] = False
    _pip_update(config)["registries"] = "*"
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert any("registries.python-index.replaces-base:must be True" in error for error in errors)
    assert any("updates[0].registries:must be ['python-index']" in error for error in errors)


@pytest.mark.parametrize("credential_key", ["username", "password"])
def test_registry_credential_literals_are_redacted_from_errors_and_cli_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    credential_key: str,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    registries = config["registries"]
    assert isinstance(registries, dict)
    registry = registries[policy.REGISTRY_NAME]
    assert isinstance(registry, dict)
    sentinel = f"literal-{credential_key}-must-not-leak"
    registry[credential_key] = sentinel
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert sentinel not in "\n".join(errors)
    assert any(
        f"registries.{policy.REGISTRY_NAME}.{credential_key}:must be" in error
        and "got <redacted>" in error
        for error in errors
    )

    exit_code = policy.main(["--repo-root", str(repo)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert sentinel not in captured.out
    assert sentinel not in captured.err


def test_registry_url_userinfo_is_redacted_from_errors_and_cli_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    registries = config["registries"]
    assert isinstance(registries, dict)
    registry = registries[policy.REGISTRY_NAME]
    assert isinstance(registry, dict)
    userinfo_first = "userinfo-alpha-must-not-leak"
    userinfo_second = "userinfo-beta-must-not-leak"
    registry["url"] = (
        f"https://{userinfo_first}:{userinfo_second}"
        "@packages.pulseplate.app/root/pulseplate/+simple/"
    )
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert userinfo_first not in "\n".join(errors)
    assert userinfo_second not in "\n".join(errors)
    assert any(
        f"registries.{policy.REGISTRY_NAME}.url:must be" in error and "got <redacted>" in error
        for error in errors
    )

    exit_code = policy.main(["--repo-root", str(repo)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert f"registries.{policy.REGISTRY_NAME}.url:must be" in captured.out
    assert "got <redacted>" in captured.out
    assert userinfo_first not in captured.out
    assert userinfo_first not in captured.err
    assert userinfo_second not in captured.out
    assert userinfo_second not in captured.err


@pytest.mark.parametrize("credential_key", ["username", "password"])
@pytest.mark.parametrize("malformation", ["unterminated", "duplicate"])
def test_malformed_registry_credentials_are_redacted_from_yaml_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    credential_key: str,
    malformation: str,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config_path = repo / policy.CONFIG_PATH
    config_text = config_path.read_text(encoding="utf-8")
    original_line = next(
        line for line in config_text.splitlines() if line.lstrip().startswith(f"{credential_key}:")
    )
    sentinel = f"yaml-{malformation}-{credential_key}-must-not-leak"
    if malformation == "unterminated":
        replacement = f'    {credential_key}: "{sentinel}'
    else:
        replacement = f'{original_line}\n    {credential_key}: "{sentinel}"'
    config_path.write_text(
        config_text.replace(original_line, replacement, 1),
        encoding="utf-8",
    )

    errors = policy.validate_repo(repo)

    assert len(errors) == 1
    assert errors[0].startswith(".github/dependabot.yml:$:invalid YAML:")
    assert sentinel not in errors[0]

    exit_code = policy.main(["--repo-root", str(repo)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert sentinel not in captured.out
    assert sentinel not in captured.err


def test_mode_a_rejects_update_suppression_and_external_code_execution(
    tmp_path: Path,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    update = _pip_update(config)
    update["allow"] = [{"dependency-name": "fastapi"}]
    update["ignore"] = [{"dependency-name": "starlette"}]
    update["exclude-paths"] = ["requirements-test.in"]
    update["insecure-external-code-execution"] = "allow"
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert any("updates[0].allow:key is forbidden" in error for error in errors)
    assert any("updates[0].ignore:key is forbidden" in error for error in errors)
    assert any("updates[0].exclude-paths:key is forbidden" in error for error in errors)
    assert any(
        "updates[0].insecure-external-code-execution:key is forbidden" in error for error in errors
    )


@pytest.mark.parametrize(
    ("unexpected_key", "unexpected_value"),
    [
        ("directories", ["/", "/nested"]),
        ("versioning-strategy", "increase"),
        ("vendor", True),
    ],
)
def test_update_block_rejects_behavior_and_scope_keys_outside_policy(
    tmp_path: Path,
    unexpected_key: str,
    unexpected_value: object,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    _pip_update(config)[unexpected_key] = unexpected_value
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert any(
        error.startswith(".github/dependabot.yml:updates[0]:keys must be exactly")
        and unexpected_key in error
        for error in errors
    )


def test_multiple_root_pip_blocks_fail_closed(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    updates = config["updates"]
    assert isinstance(updates, list)
    updates.append(_pip_update(config).copy())
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert (
        ".github/dependabot.yml:updates:" "must contain exactly one governed update block; got 2"
    ) in errors
    assert (
        ".github/dependabot.yml:updates:must contain exactly one pip update block; got 2" in errors
    )


@pytest.mark.parametrize(
    "invalid_sibling",
    [
        {"package-ecosystem": "npm"},
        {"package-ecosystem": "not-a-real-ecosystem"},
    ],
)
def test_non_python_update_siblings_are_outside_the_governed_config(
    tmp_path: Path,
    invalid_sibling: dict[str, object],
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    updates = config["updates"]
    assert isinstance(updates, list)
    updates.append(invalid_sibling)
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert (
        ".github/dependabot.yml:updates:" "must contain exactly one governed update block; got 2"
    ) in errors


@pytest.mark.parametrize("invalid_update", [42, None, ["pip"]])
def test_non_mapping_update_siblings_fail_closed(
    tmp_path: Path,
    invalid_update: object,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    updates = config["updates"]
    assert isinstance(updates, list)
    updates.append(invalid_update)
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert ".github/dependabot.yml:updates[1]:must be a mapping" in errors


@pytest.mark.parametrize("package_ecosystem", [None, "", 42])
def test_update_siblings_require_a_non_empty_package_ecosystem(
    tmp_path: Path,
    package_ecosystem: object,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    updates = config["updates"]
    assert isinstance(updates, list)
    sibling: dict[str, object] = {"directory": "/"}
    if package_ecosystem is not None:
        sibling["package-ecosystem"] = package_ecosystem
    updates.append(sibling)
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert (
        ".github/dependabot.yml:updates[1].package-ecosystem:" "must be a non-empty string"
    ) in errors


def test_schedule_limit_and_cooldown_are_exact(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    update = _pip_update(config)
    update["schedule"] = {"interval": "weekly", "day": "monday"}
    update["open-pull-requests-limit"] = 5
    update["cooldown"] = {"default-days": 7}
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert any("updates[0].schedule:must be exactly" in error for error in errors)
    assert any("updates[0].open-pull-requests-limit:must be 4" in error for error in errors)
    assert any("updates[0].cooldown:keys must be exactly" in error for error in errors)


def test_direct_package_must_have_exactly_one_owner_group(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    runtime_web = _groups(config)["runtime-web"]
    assert isinstance(runtime_web, dict)
    patterns = runtime_web["patterns"]
    assert isinstance(patterns, list)
    patterns.remove("fastapi")
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert any(
        "groups.package-owner.fastapi:direct package must match exactly one group; got []" in error
        for error in errors
    )


def test_known_package_cannot_match_multiple_groups(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    security = _groups(config)["runtime-security-sensitive"]
    assert isinstance(security, dict)
    patterns = security["patterns"]
    assert isinstance(patterns, list)
    patterns.append("fastapi")
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert any(
        "groups.package-owner.fastapi:known package matches multiple groups" in error
        for error in errors
    )


def test_catch_all_and_zero_match_patterns_are_rejected(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    security = _groups(config)["runtime-security-sensitive"]
    assert isinstance(security, dict)
    patterns = security["patterns"]
    assert isinstance(patterns, list)
    patterns.extend(["*", "package-that-does-not-exist"])
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert any("catch-all patterns are forbidden" in error for error in errors)
    assert any("matches no known source or lock package" in error for error in errors)


def test_cli_returns_one_and_prints_file_key_path_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    _pip_update(config)["target-branch"] = "dependency-updates"
    _write_config(repo, config)

    exit_code = policy.main(["--repo-root", str(repo)])

    assert exit_code == 1
    assert (
        ".github/dependabot.yml:updates[0].target-branch:key is forbidden by Mode A intake policy"
    ) in capsys.readouterr().out
