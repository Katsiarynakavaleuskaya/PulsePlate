"""Tests for the production-governed Python Dependabot policy."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict
import os
from pathlib import Path
import shutil

import pytest
import yaml

from scripts.ci import check_dependabot_python_policy as policy
from scripts.ci import dependabot_requirement_carriers as carriers
from scripts.ci.check_python_dependency_surfaces import DEPENDENCY_SURFACES

REPO_ROOT = Path(__file__).resolve().parents[1]


class _NoAliasSafeDumper(yaml.SafeDumper):
    """Materialize test mutations without introducing YAML graph indirection."""

    def ignore_aliases(self, data: object) -> bool:
        return True


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
    requirement_files.add(policy.CONSTRAINTS_PATH)
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
        yaml.dump(config, Dumper=_NoAliasSafeDumper, sort_keys=False),
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


@pytest.mark.parametrize(
    "relative_path",
    (
        "extra.txt",
        "nested/extra.in",
        ".claude/extra.txt",
        "nested/requirements-shadow.txt",
        "a\\b/extra.txt",
        "a\\b\\c.txt",
    ),
)
def test_every_novel_dependabot_carrier_path_fails_closed(
    tmp_path: Path,
    relative_path: str,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    carrier_path = repo / relative_path
    carrier_path.parent.mkdir(parents=True, exist_ok=True)
    carrier_path.write_text("novel-unowned-carrier>=1\n", encoding="utf-8")

    errors = policy.validate_repo(repo)

    assert (
        "dependabot.requirement-carriers:$:"
        f"unregistered candidate carriers are forbidden: [{relative_path!r}]"
    ) in errors


@pytest.mark.parametrize(
    ("relative_path", "content"),
    (
        ("diagnostics.txt", "./tests/example.py:1:1: E001 issue\n"),
        ("notes.txt", "hello world\n"),
        ("links.txt", "https://example.invalid/pkg\n"),
        ("direct-url.txt", "pkg @ https://example.invalid/pkg\n"),
        ("control-separator.txt", "package\vsecond\n"),
        ("unicode-whitespace.txt", "package\u00a0>=1\n"),
    ),
)
def test_non_requirement_text_file_is_not_misclassified_as_carrier(
    tmp_path: Path,
    relative_path: str,
    content: str,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    (repo / relative_path).write_text(content, encoding="utf-8")

    assert policy.validate_repo(repo) == []


@pytest.mark.parametrize(
    "content",
    (
        "package\n",
        "package>=1\n",
        'package[extra]>=1; python_version < "3.13"\n',
        "package==1 --hash=sha256:abc\n",
    ),
)
def test_frozen_upstream_requirement_grammar_accepts_valid_lines(content: str) -> None:
    assert carriers.is_dependabot_requirement_carrier_text("extra.txt", content)


def test_requirement_carrier_upstream_snapshot_is_immutable_and_documented() -> None:
    snapshot = carriers.DEPENDABOT_REQUIREMENT_CARRIER_UPSTREAM_SNAPSHOT
    assert asdict(snapshot) == {
        "contract_version": "dependabot-python-requirement-carriers/v1",
        "upstream_repository_url": "https://github.com/dependabot/dependabot-core",
        "upstream_commit_sha": "7936a8ab913935a937365279b3f44a1740117929",  # pragma: allowlist secret
        "shared_file_fetcher_source_path": ("python/lib/dependabot/python/shared_file_fetcher.rb"),
        "requirement_parser_source_path": ("python/lib/dependabot/python/requirement_parser.rb"),
    }
    assert not hasattr(type(snapshot), "__slots__")
    with pytest.raises(FrozenInstanceError):
        setattr(snapshot, "upstream_commit_sha", "different")

    documentation = (REPO_ROOT / "docs/DEPENDENCY_MANAGEMENT.md").read_text(encoding="utf-8")
    projection = "\n".join(
        (
            "contract_version=dependabot-python-requirement-carriers/v1",
            "upstream_repository_url=https://github.com/dependabot/dependabot-core",
            "upstream_commit_sha=7936a8ab913935a937365279b3f44a1740117929",
            (
                "shared_file_fetcher_source_path="
                "python/lib/dependabot/python/shared_file_fetcher.rb"
            ),
            (
                "requirement_parser_source_path="
                "python/lib/dependabot/python/requirement_parser.rb"
            ),
        )
    )
    assert documentation.count(projection) == 1
    for source_url in (
        (
            "https://github.com/dependabot/dependabot-core/blob/"
            "7936a8ab913935a937365279b3f44a1740117929/"
            "python/lib/dependabot/python/shared_file_fetcher.rb"
        ),
        (
            "https://github.com/dependabot/dependabot-core/blob/"
            "7936a8ab913935a937365279b3f44a1740117929/"
            "python/lib/dependabot/python/requirement_parser.rb"
        ),
    ):
        assert source_url in documentation
    assert "Newer upstream revisions are outside this pinned snapshot claim" in documentation
    assert "separate reviewed revalidation plus a contract-version bump" in documentation


def test_unclassifiable_novel_candidate_fails_closed(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    (repo / "extra.txt").symlink_to("missing-carrier-target")

    errors = policy.validate_repo(repo)

    assert (
        "dependabot.requirement-carriers:$:"
        "unregistered candidate carriers are forbidden: ['extra.txt']"
    ) in errors


def test_unreadable_candidate_directory_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    blocked_directory = repo / "blocked"
    blocked_directory.mkdir()
    (blocked_directory / "extra.txt").write_text(
        "novel-unowned-carrier>=1\n",
        encoding="utf-8",
    )
    real_open = carriers.os.open

    def deny_blocked_directory(
        path: str | bytes | Path,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if path == "blocked" and dir_fd is not None:
            raise PermissionError("deterministic unreadable-directory fixture")
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(carriers.os, "open", deny_blocked_directory)

    errors = policy.validate_repo(repo)

    assert (
        "dependabot.requirement-carriers:$:"
        "candidate discovery could not inspect the repository tree"
    ) in errors


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


def test_primary_config_invalid_utf8_fails_closed(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    (repo / policy.CONFIG_PATH).write_bytes(b"\xff")

    errors = policy.validate_repo(repo)

    assert errors == [".github/dependabot.yml:$:invalid YAML: config must be UTF-8"]


def test_primary_config_identity_swap_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config_path = repo / policy.CONFIG_PATH
    target_path = config_path.with_name("dependabot-swap-target.yml")
    real_open = policy.os.open
    swapped = False

    def _swap_before_open(path: str | bytes | Path, flags: int) -> int:
        nonlocal swapped
        if Path(path) == config_path and not swapped:
            config_path.replace(target_path)
            config_path.symlink_to(target_path.name)
            swapped = True
        return real_open(path, flags)

    monkeypatch.setattr(policy.os, "open", _swap_before_open)

    errors = policy.validate_repo(repo)

    assert swapped is True
    assert errors
    assert errors[0].startswith(".github/dependabot.yml:$:required config")


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

    assert errors == [".github/dependabot.yml:$:YAML anchors and aliases are forbidden"]

    exit_code = policy.main(["--repo-root", str(repo)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == f"{errors[0]}\n"
    assert captured.err == ""
    assert "Traceback" not in captured.out


@pytest.mark.parametrize(
    "alias_yaml",
    [
        "version: &version 2\nregistries: {}\nupdates: []\n",
        (
            "version: 2\n"
            "registries: {}\n"
            "updates: []\n"
            "leaf: &leaf {}\n"
            "level1: &level1 [*leaf, *leaf, *leaf, *leaf]\n"
            "level2: [*level1, *level1, *level1, *level1]\n"
        ),
    ],
)
def test_every_yaml_graph_indirection_is_rejected_before_construction(
    tmp_path: Path,
    alias_yaml: str,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    (repo / policy.CONFIG_PATH).write_text(alias_yaml, encoding="utf-8")

    errors = policy.validate_repo(repo)

    assert errors == [".github/dependabot.yml:$:YAML anchors and aliases are forbidden"]


def test_yaml_nesting_budget_rejects_deep_input_without_recursion(
    tmp_path: Path,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    depth = policy.MAX_YAML_NESTING + 1
    nested_value = "[" * depth + "0" + "]" * depth
    (repo / policy.CONFIG_PATH).write_text(
        "version: 2\nregistries: {}\nupdates: []\nextra: " + nested_value + "\n",
        encoding="utf-8",
    )

    errors = policy.validate_repo(repo)

    assert errors == [
        f".github/dependabot.yml:$:YAML nesting exceeds limit {policy.MAX_YAML_NESTING}"
    ]


def test_yaml_token_budget_rejects_wide_input(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    wide_value = ", ".join("0" for _ in range(policy.MAX_YAML_TOKENS))
    (repo / policy.CONFIG_PATH).write_text(
        "version: 2\nregistries: {}\nupdates: []\nextra: [" + wide_value + "]\n",
        encoding="utf-8",
    )

    errors = policy.validate_repo(repo)

    assert errors == [
        f".github/dependabot.yml:$:YAML token count exceeds limit {policy.MAX_YAML_TOKENS}"
    ]


def test_yaml_file_size_budget_rejects_oversized_input(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    (repo / policy.CONFIG_PATH).write_text(
        "#" * (policy.MAX_CONFIG_BYTES + 1),
        encoding="utf-8",
    )

    errors = policy.validate_repo(repo)

    assert errors == [
        f".github/dependabot.yml:$:config size exceeds limit {policy.MAX_CONFIG_BYTES} bytes"
    ]


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
        and "got key_count=4" in error
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
    assert any(
        "updates[0].registries:must be exactly ['python-index']" in error for error in errors
    )


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
        and "got string" in error
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
        f"registries.{policy.REGISTRY_NAME}.url:must be" in error and "got string" in error
        for error in errors
    )

    exit_code = policy.main(["--repo-root", str(repo)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert f"registries.{policy.REGISTRY_NAME}.url:must be" in captured.out
    assert "got string" in captured.out
    assert userinfo_first not in captured.out
    assert userinfo_first not in captured.err
    assert userinfo_second not in captured.out
    assert userinfo_second not in captured.err


def test_all_untrusted_yaml_keys_and_values_are_structurally_redacted(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    root_key_sentinel = "root-key-must-not-leak"
    value_sentinel = "value-must-not-leak"
    pattern_sentinel = "pattern-must-not-leak"
    config[root_key_sentinel] = value_sentinel
    update = _pip_update(config)
    update["directory"] = value_sentinel
    groups = _groups(config)
    runtime_web = groups["runtime-web"]
    assert isinstance(runtime_web, dict)
    runtime_web["patterns"] = [pattern_sentinel]
    _write_config(repo, config)

    errors = policy.validate_repo(repo)
    rendered = "\n".join(errors)

    assert root_key_sentinel not in rendered
    assert value_sentinel not in rendered
    assert pattern_sentinel not in rendered
    assert "got key_count=" in rendered
    assert "got string" in rendered
    assert "got list(len=1)" in rendered

    exit_code = policy.main(["--repo-root", str(repo)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert root_key_sentinel not in captured.out
    assert value_sentinel not in captured.out
    assert pattern_sentinel not in captured.out
    assert captured.err == ""


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
        and "got key_count=9" in error
        for error in errors
    )
    assert unexpected_key not in "\n".join(errors)


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
def test_single_governed_update_must_be_a_mapping(
    tmp_path: Path,
    invalid_update: object,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    config["updates"] = [invalid_update]
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert errors == [".github/dependabot.yml:updates[0]:must be a mapping"]


@pytest.mark.parametrize("package_ecosystem", [None, "", 42, "npm", "not-a-real-ecosystem"])
def test_single_governed_update_requires_exact_pip_ecosystem(
    tmp_path: Path,
    package_ecosystem: object,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    _pip_update(config)["package-ecosystem"] = package_ecosystem
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert (
        ".github/dependabot.yml:updates[0].package-ecosystem:must be exactly 'pip'"
    ) in "\n".join(errors)


@pytest.mark.parametrize(
    ("key", "invalid_value"),
    [
        ("directory", "/nested"),
        ("registries", "*"),
        ("schedule", {"interval": "daily"}),
        ("open-pull-requests-limit", 5),
        ("commit-message", []),
        ("commit-message", {"prefix": "deps"}),
        ("commit-message", {"prefix": "deps", "include": "scope", "extra": True}),
        ("commit-message", {"prefix": "other", "include": "scope"}),
    ],
)
def test_every_exact_update_field_is_value_validated(
    tmp_path: Path,
    key: str,
    invalid_value: object,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    _pip_update(config)[key] = invalid_value
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert any(f"updates[0].{key}:must be exactly" in error for error in errors)


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
    assert any("updates[0].open-pull-requests-limit:must be exactly 4" in error for error in errors)
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


def test_constraint_only_direct_package_must_have_one_owner_group(
    tmp_path: Path,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    constraints_path = repo / policy.CONSTRAINTS_PATH
    constraints_path.write_text(
        constraints_path.read_text(encoding="utf-8") + "novel-constraint-only>=1.0\n",
        encoding="utf-8",
    )

    errors = policy.validate_repo(repo)

    assert any(
        "groups.package-owner.novel-constraint-only:"
        "direct package must match exactly one group; got []" in error
        for error in errors
    )


def test_existing_constraint_only_tool_has_an_explicit_owner(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)

    direct, known, errors = policy._known_packages(repo)

    assert errors == []
    assert "sourcery" in direct
    assert "sourcery" in known
    owners: list[str] = []
    for group_name, group in policy.EXPECTED_GROUPS.items():
        patterns = group["patterns"]
        assert isinstance(patterns, tuple)
        if any(policy._matches("sourcery", pattern) for pattern in patterns):
            owners.append(group_name)
    assert owners == ["test-quality"]


def test_multiline_direct_requirement_fails_closed_before_ownership(
    tmp_path: Path,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    source_path = repo / "requirements.in"
    source_path.write_text(
        source_path.read_text(encoding="utf-8") + "novel-direct \\\n    ==1.0\n",
        encoding="utf-8",
    )
    lock_path = repo / "requirements.txt"
    lock_path.write_text(
        lock_path.read_text(encoding="utf-8") + "novel-direct==1.0\n",
        encoding="utf-8",
    )

    errors = policy.validate_repo(repo)

    assert any(
        error.startswith("requirements.in:")
        and "line continuations are forbidden; use one PEP 508 declaration per line" in error
        for error in errors
    )


@pytest.mark.parametrize(
    "directive",
    [
        "-r nested-requirements.in",
        "-e git+https://example.invalid/project.git#egg=novel-direct",
        "--index-url https://example.invalid/simple/",
    ],
)
def test_noncanonical_requirement_directive_class_fails_closed(
    tmp_path: Path,
    directive: str,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    source_path = repo / "requirements.in"
    source_path.write_text(
        source_path.read_text(encoding="utf-8") + f"{directive}\n",
        encoding="utf-8",
    )

    errors = policy.validate_repo(repo)

    assert any(
        error.startswith("requirements.in:")
        and "unsupported requirement directive; only the canonical constraint is allowed" in error
        for error in errors
    )


def test_direct_url_requirement_class_fails_closed(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    source_path = repo / "requirements.in"
    source_path.write_text(
        source_path.read_text(encoding="utf-8")
        + "novel-direct @ https://example.invalid/novel-direct.whl\n",
        encoding="utf-8",
    )

    errors = policy.validate_repo(repo)

    assert any(
        error.startswith("requirements.in:") and "direct URL requirements are forbidden" in error
        for error in errors
    )


def test_direct_requirement_source_symlink_fails_closed(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    source_path = repo / "requirements.in"
    target_path = repo / "requirements-source-target.in"
    source_path.replace(target_path)
    source_path.symlink_to(target_path.name)

    errors = policy.validate_repo(repo)

    assert "requirements.in:$:policy input must be a regular non-symlink file" in errors


@pytest.mark.parametrize("target_kind", ["missing", "directory"])
def test_every_direct_requirement_source_symlink_shape_fails_closed(
    tmp_path: Path,
    target_kind: str,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    source_path = repo / "requirements.in"
    source_path.unlink()
    target_path = repo / "requirements-source-target"
    if target_kind == "directory":
        target_path.mkdir()
    source_path.symlink_to(target_path.name)

    errors = policy.validate_repo(repo)

    assert "requirements.in:$:policy input must be a regular non-symlink file" in errors


def test_non_regular_direct_requirement_source_fails_closed_without_blocking(
    tmp_path: Path,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    source_path = repo / "requirements.in"
    source_path.unlink()
    os.mkfifo(source_path)

    errors = policy.validate_repo(repo)

    assert "requirements.in:$:policy input must be a regular non-symlink file" in errors


@pytest.mark.parametrize(
    "mutation",
    ["symlink", "fifo", "invalid-utf8", "oversized"],
)
def test_lock_policy_input_class_fails_closed(
    tmp_path: Path,
    mutation: str,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    lock_path = repo / "requirements.txt"
    if mutation == "symlink":
        target_path = repo / "requirements-lock-target.txt"
        lock_path.replace(target_path)
        lock_path.symlink_to(target_path.name)
        expected = "policy input must be a regular non-symlink file"
    elif mutation == "fifo":
        lock_path.unlink()
        os.mkfifo(lock_path)
        expected = "policy input must be a regular non-symlink file"
    elif mutation == "invalid-utf8":
        lock_path.write_bytes(b"\xff")
        expected = "policy input must be UTF-8"
    else:
        lock_path.write_bytes(b"a" * (policy.MAX_REQUIREMENT_SOURCE_BYTES + 1))
        expected = f"policy input size exceeds limit {policy.MAX_REQUIREMENT_SOURCE_BYTES} bytes"

    errors = policy.validate_repo(repo)

    assert any(error.startswith("requirements.txt:$:") and expected in error for error in errors)


@pytest.mark.parametrize(
    "lock_line",
    [
        "-r nested-lock.txt",
        "locked-package @ https://example.invalid/locked-package.whl",
        "not a valid PEP 508 declaration @",
    ],
)
def test_lock_grammar_never_silently_skips_unknown_carriers(
    tmp_path: Path,
    lock_line: str,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    lock_path = repo / "requirements.txt"
    lock_path.write_text(
        lock_path.read_text(encoding="utf-8") + f"{lock_line}\n",
        encoding="utf-8",
    )

    errors = policy.validate_repo(repo)

    assert any(error.startswith("requirements.txt:") for error in errors)


def test_direct_requirement_source_resource_budgets_fail_closed(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    source_path = repo / "requirements.in"
    source_path.write_text(
        "a" * (policy.MAX_REQUIREMENT_LINE_CHARS + 1),
        encoding="utf-8",
    )

    errors = policy.validate_repo(repo)

    assert errors == [
        "requirements.in:1:" f"line length exceeds limit {policy.MAX_REQUIREMENT_LINE_CHARS}"
    ]


def test_known_package_cannot_match_multiple_groups(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_groups = {
        name: dict(group_contract) for name, group_contract in policy.EXPECTED_GROUPS.items()
    }
    expected_security = expected_groups["runtime-security-sensitive"]
    expected_patterns = expected_security["patterns"]
    assert isinstance(expected_patterns, tuple)
    expected_security["patterns"] = (*expected_patterns, "fastapi")
    monkeypatch.setattr(policy, "EXPECTED_GROUPS", expected_groups)

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


def test_catch_all_and_zero_match_patterns_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_groups = {
        name: dict(group_contract) for name, group_contract in policy.EXPECTED_GROUPS.items()
    }
    expected_security = expected_groups["runtime-security-sensitive"]
    expected_patterns = expected_security["patterns"]
    assert isinstance(expected_patterns, tuple)
    expected_security["patterns"] = (
        *expected_patterns,
        "*",
        "package-that-does-not-exist",
    )
    monkeypatch.setattr(policy, "EXPECTED_GROUPS", expected_groups)

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
