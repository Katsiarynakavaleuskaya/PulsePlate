"""Tests for the production-governed Dependabot policy."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import FrozenInstanceError, asdict
from itertools import product
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest
import yaml

from scripts.ci import check_dependabot_python_policy as policy
from scripts.ci import dependabot_requirement_carriers as carriers
from scripts.ci.check_python_dependency_surfaces import DEPENDENCY_SURFACES

REPO_ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_CODE_EXECUTION_FORBIDDEN_ERROR_SUFFIX = (
    ".insecure-external-code-execution:key is forbidden because external code "
    "must not receive private registry credentials"
)


def _run_fixture_git(repo: Path, *args: str) -> None:
    git_binary = shutil.which("git")
    assert git_binary is not None
    fixture_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    subprocess.run(  # nosec B603: resolved Git binary with test-owned argv (remove-by: 2026-10-31, ref: PR-2181)
        [git_binary, "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env=fixture_env,
        timeout=10,
    )


def _stage_fixture_paths(repo: Path, *paths: str, force: bool = False) -> None:
    force_arg = ("--force",) if force else ()
    _run_fixture_git(repo, "add", *force_arg, "--", *paths)


class _NoAliasSafeDumper(yaml.SafeDumper):
    """Materialize test mutations without introducing YAML graph indirection."""

    def ignore_aliases(self, data: object) -> bool:
        return True


def _copy_policy_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / ".github").mkdir(parents=True)
    shutil.copy2(REPO_ROOT / ".gitignore", repo / ".gitignore")
    shutil.copy2(REPO_ROOT / policy.CONFIG_PATH, repo / policy.CONFIG_PATH)
    business_package = repo / policy.BUSINESS_COLLATERAL_PACKAGE_PATH
    business_package.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO_ROOT / policy.BUSINESS_COLLATERAL_PACKAGE_PATH, business_package)
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
    _run_fixture_git(repo, "init", "--quiet")
    _stage_fixture_paths(repo, ".")
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
    return _update_by_ecosystem(config, "pip")


def _update_by_ecosystem(
    config: dict[str, object],
    ecosystem: str,
) -> dict[str, object]:
    updates = config["updates"]
    assert isinstance(updates, list)
    matching = [
        update
        for update in updates
        if isinstance(update, dict) and update.get("package-ecosystem") == ecosystem
    ]
    assert len(matching) == 1
    return matching[0]


def _update_index(config: dict[str, object], ecosystem: str) -> int:
    updates = config["updates"]
    assert isinstance(updates, list)
    return updates.index(_update_by_ecosystem(config, ecosystem))


def _groups(config: dict[str, object]) -> dict[str, object]:
    groups = _pip_update(config)["groups"]
    assert isinstance(groups, dict)
    return groups


MappingSelector = tuple[str | int, ...]


def _iter_mapping_selectors(
    value: object,
    selector: MappingSelector = (),
) -> Iterator[MappingSelector]:
    if isinstance(value, dict):
        yield selector
        for key, child in value.items():
            assert isinstance(key, str)
            yield from _iter_mapping_selectors(child, (*selector, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_mapping_selectors(child, (*selector, index))


def _mapping_at_selector(
    value: object,
    selector: MappingSelector,
) -> dict[str, object]:
    selected = value
    for component in selector:
        if isinstance(component, int):
            assert isinstance(selected, list)
        else:
            assert isinstance(selected, dict)
        selected = selected[component]
    assert isinstance(selected, dict)
    return selected


def _selector_path(selector: MappingSelector) -> str:
    path = "$"
    for component in selector:
        if isinstance(component, int):
            path = f"{path}[{component}]"
        else:
            path = f"{path}.{component}"
    return path


def test_live_dependabot_policy_passes() -> None:
    assert policy.validate_repo(REPO_ROOT) == []


def test_closed_updater_registry_is_order_independent(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    updates = config["updates"]
    assert isinstance(updates, list)
    updates.reverse()
    npm_directories = _update_by_ecosystem(config, "npm")["directories"]
    actions_directories = _update_by_ecosystem(config, "github-actions")["directories"]
    assert isinstance(npm_directories, list)
    assert isinstance(actions_directories, list)
    npm_directories.reverse()
    actions_directories.reverse()
    _write_config(repo, config)

    assert policy.validate_repo(repo) == []


def test_closed_updater_registry_has_exact_core_v1_contract() -> None:
    config = _load_config(REPO_ROOT)

    assert {
        ecosystem: {
            key: value
            for key, value in _update_by_ecosystem(config, ecosystem).items()
            if key != "groups"
        }
        for ecosystem in policy.EXPECTED_UPDATER_ECOSYSTEMS
    } == {
        "pip": {
            key: value
            for key, value in policy.EXPECTED_UPDATE_EXACT_VALUES.items()
            if key != "groups"
        }
        | {"cooldown": policy.EXPECTED_COOLDOWN},
        "npm": {
            "package-ecosystem": "npm",
            "directories": ["/", "/frontend"],
            **policy.EXPECTED_COMMON_UPDATE_EXACT_VALUES,
            "cooldown": policy.EXPECTED_COOLDOWN,
        },
        "bundler": {
            "package-ecosystem": "bundler",
            "directory": "/ios",
            **policy.EXPECTED_COMMON_UPDATE_EXACT_VALUES,
            "cooldown": policy.EXPECTED_COOLDOWN,
        },
        "github-actions": {
            "package-ecosystem": "github-actions",
            "directories": ["/", "/.github/actions/*"],
            **policy.EXPECTED_COMMON_UPDATE_EXACT_VALUES,
            "cooldown": policy.EXPECTED_COOLDOWN,
        },
    }


@pytest.mark.parametrize("ecosystem", sorted(policy.EXPECTED_UPDATER_ECOSYSTEMS))
def test_every_required_updater_identity_fails_closed_when_missing(
    tmp_path: Path,
    ecosystem: str,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    updates = config["updates"]
    assert isinstance(updates, list)
    updates.remove(_update_by_ecosystem(config, ecosystem))
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert (
        f".github/dependabot.yml:updates:missing required {ecosystem!r} updater identity" in errors
    )


def test_duplicate_and_overlapping_updater_identity_fails_closed(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    updates = config["updates"]
    assert isinstance(updates, list)
    updates.append(_update_by_ecosystem(config, "npm").copy())
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert ".github/dependabot.yml:updates:duplicate 'npm' updater identity is forbidden" in errors
    assert ".github/dependabot.yml:updates:overlapping 'npm' updater scopes are forbidden" in errors


def test_unknown_updater_identity_fails_closed_without_rendering_value(
    tmp_path: Path,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    npm = _update_by_ecosystem(config, "npm")
    sentinel = "unknown-ecosystem-must-not-leak"
    npm["package-ecosystem"] = sentinel
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    rendered = "\n".join(errors)
    assert "must be one of the four exact governed ecosystems; got string" in rendered
    assert sentinel not in rendered
    assert "missing required 'npm' updater identity" in rendered


@pytest.mark.parametrize(
    ("ecosystem", "scope_key", "invalid_scope"),
    [
        ("npm", "directories", ["/"]),
        ("npm", "directories", ["/", "/nested"]),
        ("bundler", "directory", "/"),
        ("github-actions", "directories", ["/"]),
        ("github-actions", "directories", ["/", "/.github/actions/other"]),
    ],
)
def test_every_bounded_updater_requires_exact_scope(
    tmp_path: Path,
    ecosystem: str,
    scope_key: str,
    invalid_scope: object,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    update = _update_by_ecosystem(config, ecosystem)
    update[scope_key] = invalid_scope
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    update_index = _update_index(config, ecosystem)
    assert any(
        f"updates[{update_index}].{scope_key}:scope must be exactly" in error for error in errors
    )


@pytest.mark.parametrize(
    "invalid_scope",
    [
        [],
        ["/", "/"],
        ["/", 1],
        ["/", "frontend"],
        ["/", "/frontend/"],
        ["/", "/frontend//nested"],
        ["/", "/frontend/../nested"],
        ["/", "/front\\end"],
        ["/", "/front end"],
        ["/", "/front*"],
    ],
)
def test_directory_scope_grammar_fails_closed(
    tmp_path: Path,
    invalid_scope: object,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    _update_by_ecosystem(config, "npm")["directories"] = invalid_scope
    _write_config(repo, config)

    assert policy.validate_repo(repo)


def test_directory_and_directories_cannot_coexist(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    _update_by_ecosystem(config, "npm")["directory"] = "/"
    update_index = _update_index(config, "npm")
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    expected_keys = policy.EXPECTED_UPDATE_CONTRACTS["npm"].keys
    expected_errors = [
        f".github/dependabot.yml:updates[{update_index}]:keys must be exactly "
        f"{policy._sorted_keys(expected_keys)!r}; got key_count={len(expected_keys) + 1}",
        f".github/dependabot.yml:updates[{update_index}]:"
        "must define exactly one of 'directory' or 'directories'",
        f".github/dependabot.yml:updates[{update_index}]:"
        "scope key must be exactly 'directories'",
    ]
    assert errors == expected_errors

    probe = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "from scripts.ci.check_dependabot_python_policy import validate_repo\n"
        "print(json.dumps(validate_repo(Path(sys.argv[1]))))\n"
    )
    for hash_seed in ("1", "2", "3", "random"):
        result = subprocess.run(
            [sys.executable, "-O", "-c", probe, str(repo)],
            check=True,
            capture_output=True,
            cwd=REPO_ROOT,
            env={**os.environ, "PYTHONHASHSEED": hash_seed},
            text=True,
            timeout=10,
        )
        assert json.loads(result.stdout) == expected_errors


@pytest.mark.parametrize("ecosystem", ["npm", "bundler", "github-actions"])
@pytest.mark.parametrize(
    "forbidden_key",
    sorted(policy.NON_PYTHON_FORBIDDEN_AUTHORITY_KEYS - policy.FORBIDDEN_UPDATE_KEYS),
)
def test_non_python_authority_keys_are_recursively_forbidden(
    tmp_path: Path,
    ecosystem: str,
    forbidden_key: str,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    update = _update_by_ecosystem(config, ecosystem)
    schedule = update["schedule"]
    assert isinstance(schedule, dict)
    schedule[forbidden_key] = {"nested": True}
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert any(
        error.endswith(
            f".{forbidden_key}:key is forbidden for bounded non-Python updater authority"
        )
        for error in errors
    )


def test_multi_ecosystem_grouping_is_forbidden_at_root_and_update(
    tmp_path: Path,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    config["multi-ecosystem-groups"] = {"all": {"schedule": {"interval": "weekly"}}}
    _update_by_ecosystem(config, "npm")["multi-ecosystem-group"] = "all"
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert any("root keys must be exactly" in error for error in errors)
    assert any(
        ".multi-ecosystem-group:key is forbidden by Mode A intake policy" in error
        for error in errors
    )


@pytest.mark.parametrize("ecosystem", ["npm", "bundler", "github-actions"])
@pytest.mark.parametrize(
    ("key", "invalid_value"),
    [
        ("schedule", {"interval": "daily"}),
        ("open-pull-requests-limit", 0),
        ("open-pull-requests-limit", -1),
        ("open-pull-requests-limit", False),
        ("open-pull-requests-limit", 1.0),
        ("cooldown", {"default-days": 7}),
        ("commit-message", {"prefix": "deps"}),
    ],
)
def test_non_python_schedule_limit_cooldown_and_commit_policy_are_exact(
    tmp_path: Path,
    ecosystem: str,
    key: str,
    invalid_value: object,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    _update_by_ecosystem(config, ecosystem)[key] = invalid_value
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    update_index = _update_index(config, ecosystem)
    assert any(f"updates[{update_index}].{key}:" in error for error in errors)


@pytest.mark.parametrize("dependency_key", sorted(policy.BUSINESS_COLLATERAL_DEPENDENCY_KEYS))
def test_business_collateral_dependency_key_requires_new_ownership_decision(
    tmp_path: Path,
    dependency_key: str,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    package_path = repo / policy.BUSINESS_COLLATERAL_PACKAGE_PATH
    package_path.write_text(
        json.dumps({"type": "commonjs", dependency_key: {}}),
        encoding="utf-8",
    )

    errors = policy.validate_repo(repo)

    assert (
        f"{policy.BUSINESS_COLLATERAL_PACKAGE_PATH.as_posix()}:{dependency_key}:"
        "dependency ownership is not admitted for this marker"
    ) in errors


@pytest.mark.parametrize("lock_path", policy.BUSINESS_COLLATERAL_LOCK_PATHS)
def test_business_collateral_adjacent_lock_requires_new_ownership_decision(
    tmp_path: Path,
    lock_path: Path,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    (repo / lock_path).write_text("{}\n", encoding="utf-8")

    errors = policy.validate_repo(repo)

    assert (
        f"{lock_path.as_posix()}:$:"
        "adjacent lock requires a separate explicit updater ownership decision"
    ) in errors


def test_business_collateral_marker_requires_commonjs_and_bounded_json(
    tmp_path: Path,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    package_path = repo / policy.BUSINESS_COLLATERAL_PACKAGE_PATH
    package_path.write_text('{"type": "module"}', encoding="utf-8")

    errors = policy.validate_repo(repo)

    assert any(
        "dependency-free marker must declare exact string 'commonjs'" in error for error in errors
    )


@pytest.mark.parametrize(
    ("mutation", "expected_message"),
    (
        ("missing", "policy input could not be read"),
        ("symlink", "policy input must be a regular non-symlink file"),
        ("fifo", "policy input must be a regular non-symlink file"),
    ),
)
def test_business_collateral_marker_input_shape_fails_closed(
    tmp_path: Path,
    mutation: str,
    expected_message: str,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    package_path = repo / policy.BUSINESS_COLLATERAL_PACKAGE_PATH
    if mutation == "missing":
        package_path.unlink()
    elif mutation == "symlink":
        target_path = package_path.with_name("package-target.json")
        package_path.replace(target_path)
        package_path.symlink_to(target_path.name)
    else:
        package_path.unlink()
        os.mkfifo(package_path)

    errors = policy.validate_repo(repo)

    assert (
        f"{policy.BUSINESS_COLLATERAL_PACKAGE_PATH.as_posix()}:$:" f"{expected_message}"
    ) in errors


def test_business_collateral_marker_size_budget_fails_closed(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    package_path = repo / policy.BUSINESS_COLLATERAL_PACKAGE_PATH
    package_path.write_bytes(b"x" * (policy.MAX_BUSINESS_PACKAGE_BYTES + 1))

    errors = policy.validate_repo(repo)

    assert (
        f"{policy.BUSINESS_COLLATERAL_PACKAGE_PATH.as_posix()}:$:policy input size "
        f"exceeds limit {policy.MAX_BUSINESS_PACKAGE_BYTES} bytes"
    ) in errors


def test_business_collateral_marker_invalid_utf8_fails_closed(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    package_path = repo / policy.BUSINESS_COLLATERAL_PACKAGE_PATH
    package_path.write_bytes(b'\xff{"type":"commonjs"}')

    errors = policy.validate_repo(repo)

    assert (
        f"{policy.BUSINESS_COLLATERAL_PACKAGE_PATH.as_posix()}:$:" "policy input must be UTF-8"
    ) in errors


def test_business_collateral_marker_invalid_json_is_structurally_redacted(
    tmp_path: Path,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    package_path = repo / policy.BUSINESS_COLLATERAL_PACKAGE_PATH
    sentinel = "invalid-json-value-must-not-leak"
    package_path.write_text(f'{{"type":"commonjs","value":"{sentinel}"', encoding="utf-8")

    errors = policy.validate_repo(repo)

    assert (
        f"{policy.BUSINESS_COLLATERAL_PACKAGE_PATH.as_posix()}:$:" "must be valid bounded JSON"
    ) in errors
    assert sentinel not in "\n".join(errors)


@pytest.mark.parametrize(
    ("invalid_document", "untrusted_fragment"),
    (
        pytest.param('{"type":"commonjs","value":NaN}', "NaN", id="nan"),
        pytest.param(
            '{"type":"commonjs","value":Infinity}',
            "Infinity",
            id="positive-infinity",
        ),
        pytest.param(
            '{"type":"commonjs","value":-Infinity}',
            "-Infinity",
            id="negative-infinity",
        ),
        pytest.param(
            '{"type":"commonjs","value":' + "9" * 5000 + "}",
            "9" * 64,
            id="oversized-integer",
        ),
    ),
)
def test_business_collateral_marker_rejects_nonstandard_or_oversized_numbers(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    invalid_document: str,
    untrusted_fragment: str,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    package_path = repo / policy.BUSINESS_COLLATERAL_PACKAGE_PATH
    package_path.write_text(invalid_document, encoding="utf-8")
    expected_error = (
        f"{policy.BUSINESS_COLLATERAL_PACKAGE_PATH.as_posix()}:$:" "must be valid bounded JSON"
    )

    errors = policy.validate_repo(repo)

    assert errors == [expected_error]
    assert untrusted_fragment not in "\n".join(errors)

    exit_code = policy.main(["--repo-root", str(repo)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == f"{expected_error}\n"
    assert captured.err == ""
    assert untrusted_fragment not in captured.out
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("non_mapping", [[], "commonjs", 42, None])
def test_business_collateral_marker_non_mapping_json_fails_closed(
    tmp_path: Path,
    non_mapping: object,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    package_path = repo / policy.BUSINESS_COLLATERAL_PACKAGE_PATH
    package_path.write_text(json.dumps(non_mapping), encoding="utf-8")

    errors = policy.validate_repo(repo)

    assert (
        f"{policy.BUSINESS_COLLATERAL_PACKAGE_PATH.as_posix()}:$:"
        "dependency-free marker must be a mapping"
    ) in errors


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
    _stage_fixture_paths(repo, relative_path, force=True)

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
    _stage_fixture_paths(repo, relative_path)

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


def test_hardened_marker_language_preserves_raw_positive_ambiguities() -> None:
    raw_pattern = re.compile(
        carriers._UPSTREAM_VALID_REQUIREMENT_LINE_PATTERN,
        flags=re.ASCII,
    )
    marker_lines = (
        "package; (  and ",
        "package; (  or ",
        'package; python_version == "3" and  or ',
        'package; python_version == "3" or  and ',
        "package; ((  and ",
        'package; python_version == "3" and (  or python_version == "3"',
        "package; and ",
        'package; (  and python_version == "3"',
        'package; python_version == "3" and  or python_version == "3"',
        "package[extra]==1; ((  and --hash=sha256:abc # retained",
        'package[extra]>=1,<2; python_version == "3" and  or '
        'python_version == "3" --hash=sha256:abc # retained',
    )

    for marker_line in marker_lines:
        assert raw_pattern.fullmatch(marker_line) is not None
        assert carriers._UPSTREAM_VALID_REQUIREMENT_LINE_RE.fullmatch(marker_line) is None
        assert carriers.is_dependabot_requirement_carrier_text("extra.txt", marker_line)


def test_hardened_classifier_matches_frozen_raw_marker_boundary_matrix() -> None:
    raw_pattern = re.compile(
        carriers._UPSTREAM_VALID_REQUIREMENT_LINE_PATTERN,
        flags=re.ASCII,
    )
    atoms = ("(", ")", "and", "or", 'python_version == "3"')
    whitespace_boundaries = ("", " ", "  ")
    matrix_counter = 0

    for atom_count in (1, 2, 3):
        for selected_atoms in product(atoms, repeat=atom_count):
            for boundaries in product(whitespace_boundaries, repeat=atom_count + 1):
                marker_parts = [boundaries[0]]
                for index, atom in enumerate(selected_atoms):
                    marker_parts.extend((atom, boundaries[index + 1]))
                candidate = "package;" + "".join(marker_parts)

                raw_accepts = raw_pattern.fullmatch(candidate) is not None
                public_accepts = carriers.is_dependabot_requirement_carrier_text(
                    "extra.txt", candidate
                )

                assert public_accepts is raw_accepts, candidate
                matrix_counter += 1

    assert matrix_counter == 10_845


@pytest.mark.parametrize(
    ("pattern", "expected_sha256", "expected_counts", "compiled_pattern"),
    (
        (
            carriers._UPSTREAM_VALID_REQUIREMENT_LINE_PATTERN,
            carriers._UPSTREAM_VALID_REQUIREMENT_LINE_PATTERN_SHA256,
            carriers._UPSTREAM_VALID_REQUIREMENT_LINE_HARDENING_COUNTS,
            carriers._UPSTREAM_VALID_REQUIREMENT_LINE_RE.pattern,
        ),
        (
            carriers._UPSTREAM_REQUIREMENT_BEFORE_MARKER_PATTERN,
            carriers._UPSTREAM_REQUIREMENT_BEFORE_MARKER_PATTERN_SHA256,
            carriers._UPSTREAM_REQUIREMENT_BEFORE_MARKER_HARDENING_COUNTS,
            carriers._UPSTREAM_REQUIREMENT_BEFORE_MARKER_RE.pattern,
        ),
    ),
)
def test_hardening_helper_output_is_the_compiled_pattern(
    pattern: str,
    expected_sha256: str,
    expected_counts: tuple[int, int, int],
    compiled_pattern: str,
) -> None:
    assert (
        carriers._harden_upstream_requirement_pattern(
            pattern,
            expected_sha256=expected_sha256,
            expected_counts=expected_counts,
        )
        == compiled_pattern
    )


@pytest.mark.parametrize(
    ("pattern", "expected_sha256", "expected_counts"),
    (
        (
            carriers._UPSTREAM_VALID_REQUIREMENT_LINE_PATTERN,
            carriers._UPSTREAM_VALID_REQUIREMENT_LINE_PATTERN_SHA256,
            carriers._UPSTREAM_VALID_REQUIREMENT_LINE_HARDENING_COUNTS,
        ),
        (
            carriers._UPSTREAM_REQUIREMENT_BEFORE_MARKER_PATTERN,
            carriers._UPSTREAM_REQUIREMENT_BEFORE_MARKER_PATTERN_SHA256,
            carriers._UPSTREAM_REQUIREMENT_BEFORE_MARKER_HARDENING_COUNTS,
        ),
    ),
)
def test_hardening_helper_rejects_wrong_counts_before_digest(
    pattern: str,
    expected_sha256: str,
    expected_counts: tuple[int, int, int],
) -> None:
    wrong_counts = (expected_counts[0] + 1, *expected_counts[1:])
    with pytest.raises(RuntimeError, match="hardening locations drifted"):
        carriers._harden_upstream_requirement_pattern(
            pattern,
            expected_sha256="wrong-digest-must-not-be-reached",
            expected_counts=wrong_counts,
        )


@pytest.mark.parametrize(
    ("pattern", "expected_sha256", "expected_counts"),
    (
        (
            carriers._UPSTREAM_VALID_REQUIREMENT_LINE_PATTERN,
            carriers._UPSTREAM_VALID_REQUIREMENT_LINE_PATTERN_SHA256,
            carriers._UPSTREAM_VALID_REQUIREMENT_LINE_HARDENING_COUNTS,
        ),
        (
            carriers._UPSTREAM_REQUIREMENT_BEFORE_MARKER_PATTERN,
            carriers._UPSTREAM_REQUIREMENT_BEFORE_MARKER_PATTERN_SHA256,
            carriers._UPSTREAM_REQUIREMENT_BEFORE_MARKER_HARDENING_COUNTS,
        ),
    ),
)
def test_hardening_helper_rejects_same_count_relocated_identity(
    pattern: str,
    expected_sha256: str,
    expected_counts: tuple[int, int, int],
) -> None:
    relocated = pattern.replace(r"^\s*", "^", 1) + r"\s*"
    assert relocated.count(r"\s*") == pattern.count(r"\s*")
    with pytest.raises(RuntimeError, match="grammar identity drifted"):
        carriers._harden_upstream_requirement_pattern(
            relocated,
            expected_sha256=expected_sha256,
            expected_counts=expected_counts,
        )


def test_raw_positive_marker_ambiguity_is_forbidden_as_novel_carrier(
    tmp_path: Path,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    (repo / "ambiguous.txt").write_text("package; (  and \n", encoding="utf-8")
    _stage_fixture_paths(repo, "ambiguous.txt")

    errors = policy.validate_repo(repo)

    assert (
        "dependabot.requirement-carriers:$:"
        "unregistered candidate carriers are forbidden: ['ambiguous.txt']"
    ) in errors


@pytest.mark.parametrize(
    "content",
    (
        "package; (and ",
        "package and  or ",
        'package; python_version == "3" andor ',
        'package; python_version == "3" and  ! ',
    ),
)
def test_malformed_marker_boundaries_remain_non_carriers(content: str) -> None:
    assert not carriers.is_dependabot_requirement_carrier_text("extra.txt", content)


def test_frozen_hash_expansion_with_semicolon_remains_a_carrier() -> None:
    content = "package --hash=sha256:abc; and  or "
    raw_pattern = re.compile(
        carriers._UPSTREAM_VALID_REQUIREMENT_LINE_PATTERN,
        flags=re.ASCII,
    )
    assert raw_pattern.fullmatch(content) is not None
    assert carriers.is_dependabot_requirement_carrier_text("extra.txt", content)


@pytest.mark.parametrize(
    "content",
    (
        "package; )  (",
        'package; python_version == "3"  (',
    ),
)
def test_whitespace_before_open_parenthesis_does_not_widen_raw_language(
    content: str,
) -> None:
    raw_pattern = re.compile(
        carriers._UPSTREAM_VALID_REQUIREMENT_LINE_PATTERN,
        flags=re.ASCII,
    )
    assert raw_pattern.fullmatch(content) is None
    assert not carriers.is_dependabot_requirement_carrier_text("extra.txt", content)


@pytest.mark.parametrize(
    "content",
    (
        "package; (  (",
        "package; and  (",
    ),
)
def test_frozen_atoms_that_own_trailing_whitespace_allow_open_parenthesis(
    content: str,
) -> None:
    raw_pattern = re.compile(
        carriers._UPSTREAM_VALID_REQUIREMENT_LINE_PATTERN,
        flags=re.ASCII,
    )
    assert raw_pattern.fullmatch(content) is not None
    assert carriers.is_dependabot_requirement_carrier_text("extra.txt", content)


def test_consecutive_boolean_atoms_cannot_reuse_one_whitespace_character() -> None:
    content = "package; and or "
    raw_pattern = re.compile(
        carriers._UPSTREAM_VALID_REQUIREMENT_LINE_PATTERN,
        flags=re.ASCII,
    )
    assert raw_pattern.fullmatch(content) is None
    assert not carriers.is_dependabot_requirement_carrier_text("extra.txt", content)


def test_raw_positive_marker_ambiguity_respects_exact_line_budget() -> None:
    limit = carriers.DEPENDABOT_REQUIREMENT_MAX_LINE_CHARS
    prefix = 'package[extra]>=1,<2; python_version == "3" and  or '
    suffix = 'python_version == "3" --hash=sha256:abc # retained'
    admitted = prefix + " " * (limit - len(prefix) - len(suffix)) + suffix
    assert len(admitted) == limit
    assert (
        re.fullmatch(
            carriers._UPSTREAM_VALID_REQUIREMENT_LINE_PATTERN,
            admitted,
            flags=re.ASCII,
        )
        is not None
    )
    assert carriers.is_dependabot_requirement_carrier_text("extra.txt", admitted)

    with pytest.raises(carriers.DependabotRequirementDiscoveryError):
        carriers.is_dependabot_requirement_carrier_text("extra.txt", admitted + " ")


def test_hardened_marker_language_rejects_long_invalid_near_match() -> None:
    probe = (
        "from scripts.ci.dependabot_requirement_carriers import "
        "is_dependabot_requirement_carrier_text\n"
        "content = 'package; ' + '(  and ' * 500 + '!\\n'\n"
        "assert not is_dependabot_requirement_carrier_text('extra.txt', content)\n"
    )

    subprocess.run(
        [sys.executable, "-c", probe],
        check=True,
        cwd=REPO_ROOT,
        shell=False,
        timeout=5,
    )


def test_frozen_upstream_requirement_grammar_rejects_long_invalid_near_matches() -> None:
    probe = (
        "from scripts.ci.dependabot_requirement_carriers import "
        "is_dependabot_requirement_carrier_text\n"
        "for suffix in ('!', '@', '='):\n"
        "    content = f\"package{' ' * 1000}{suffix}\\n\"\n"
        "    assert not is_dependabot_requirement_carrier_text('extra.txt', content)\n"
    )

    subprocess.run(
        [sys.executable, "-c", probe],
        check=True,
        cwd=REPO_ROOT,
        shell=False,
        timeout=5,
    )


def test_frozen_upstream_requirement_grammar_rejects_long_invalid_version_near_match() -> None:
    probe = (
        "from scripts.ci.dependabot_requirement_carriers import "
        "DEPENDABOT_REQUIREMENT_MAX_LINE_CHARS, "
        "is_dependabot_requirement_carrier_text\n"
        "digit_count = DEPENDABOT_REQUIREMENT_MAX_LINE_CHARS - len('package==!')\n"
        "content = f\"package=={'1' * digit_count}!\\n\"\n"
        "assert not is_dependabot_requirement_carrier_text('extra.txt', content)\n"
    )

    subprocess.run(
        [sys.executable, "-c", probe],
        check=True,
        cwd=REPO_ROOT,
        shell=False,
        timeout=5,
    )


def test_requirement_carrier_line_budget_precedes_all_classification() -> None:
    limit = carriers.DEPENDABOT_REQUIREMENT_MAX_LINE_CHARS
    assert limit == 4096
    assert policy.MAX_REQUIREMENT_LINE_CHARS == limit
    assert carriers.is_dependabot_requirement_carrier_text("extra.txt", "a" * limit)

    overlong_cases = (
        ("extra.txt", "a" * (limit + 1)),
        ("requirements.txt", "package" + " " * limit),
        ("extra.txt", " " * (limit + 1)),
        ("extra.txt", "#" + " " * limit),
        ("extra.txt", "--" + " " * limit),
        ("extra.txt", "not a requirement @\n" + " " * (limit + 1)),
    )
    for relative_path, content in overlong_cases:
        with pytest.raises(carriers.DependabotRequirementDiscoveryError):
            carriers.is_dependabot_requirement_carrier_text(relative_path, content)


def test_marker_near_match_over_line_budget_fails_closed_in_child_process() -> None:
    probe = (
        "from scripts.ci.dependabot_requirement_carriers import "
        "DEPENDABOT_REQUIREMENT_MAX_LINE_CHARS, DependabotRequirementDiscoveryError, "
        "is_dependabot_requirement_carrier_text\n"
        "space_count = DEPENDABOT_REQUIREMENT_MAX_LINE_CHARS - len('package;!')\n"
        "admitted = f\"package;{' ' * space_count}!\\n\"\n"
        "assert not is_dependabot_requirement_carrier_text('extra.txt', admitted)\n"
        "content = f\"package;{' ' * 20000}!\\n\"\n"
        "try:\n"
        "    is_dependabot_requirement_carrier_text('extra.txt', content)\n"
        "except DependabotRequirementDiscoveryError:\n"
        "    pass\n"
        "else:\n"
        "    raise AssertionError('overlong carrier input did not fail closed')\n"
    )

    subprocess.run(
        [sys.executable, "-c", probe],
        check=True,
        cwd=REPO_ROOT,
        shell=False,
        timeout=5,
    )


def test_overlong_carrier_discovery_error_is_sanitized(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    sentinel = "carrier-content-must-not-leak"
    (repo / "extra.txt").write_text(
        "package;" + " " * 4097 + sentinel,
        encoding="utf-8",
    )
    _stage_fixture_paths(repo, "extra.txt")

    errors = policy.validate_repo(repo)

    assert errors == [
        "dependabot.requirement-carriers:$:"
        "candidate discovery could not inspect the repository tree"
    ]
    assert sentinel not in "\n".join(errors)


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
    _stage_fixture_paths(repo, "extra.txt")

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
    _stage_fixture_paths(repo, "blocked/extra.txt")
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


def test_ignored_untracked_runtime_salt_is_not_a_source_carrier(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    salt_path = repo / "cache" / "fingerprint_salt.txt"
    salt_path.parent.mkdir()
    salt_path.write_text("0123456789abcdef\n", encoding="utf-8")

    assert policy.validate_repo(repo) == []


def test_force_tracked_ignored_carrier_still_fails_closed(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    salt_path = repo / "cache" / "fingerprint_salt.txt"
    salt_path.parent.mkdir()
    salt_path.write_text("0123456789abcdef\n", encoding="utf-8")
    _stage_fixture_paths(repo, "cache/fingerprint_salt.txt", force=True)

    errors = policy.validate_repo(repo)

    assert (
        "dependabot.requirement-carriers:$:"
        "unregistered candidate carriers are forbidden: "
        "['cache/fingerprint_salt.txt']"
    ) in errors


def test_tracked_missing_carrier_fails_closed(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    carrier_path = repo / "missing.txt"
    carrier_path.write_text("package>=1\n", encoding="utf-8")
    _stage_fixture_paths(repo, "missing.txt")
    carrier_path.unlink()

    errors = policy.validate_repo(repo)

    assert (
        "dependabot.requirement-carriers:$:"
        "candidate discovery could not inspect the repository tree"
    ) in errors


def test_git_index_paths_are_nul_safe(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    relative_path = "line\nbreak.txt"
    (repo / relative_path).write_text("package>=1\n", encoding="utf-8")
    _stage_fixture_paths(repo, relative_path)

    errors = policy.validate_repo(repo)

    assert (
        "dependabot.requirement-carriers:$:"
        f"unregistered candidate carriers are forbidden: [{relative_path!r}]"
    ) in errors


def test_git_index_discovery_requires_exact_repo_top_level(tmp_path: Path) -> None:
    repo = _copy_policy_repo(tmp_path)
    nested = repo / "nested"
    nested.mkdir()

    with pytest.raises(carriers.DependabotRequirementDiscoveryError):
        carriers.discover_dependabot_requirement_carriers(nested)


def test_git_index_discovery_ignores_outer_git_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    outer_repo = tmp_path / "outer"
    outer_repo.mkdir()
    _run_fixture_git(outer_repo, "init", "--quiet")
    monkeypatch.setenv("GIT_DIR", os.fspath(outer_repo / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", os.fspath(outer_repo))
    monkeypatch.setenv("GIT_INDEX_FILE", os.fspath(outer_repo / ".git" / "index"))

    assert policy.validate_repo(repo) == []


def test_malformed_git_index_payload_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    real_run_git_bytes = carriers._run_git_bytes

    def malformed_ls_files(repo_root: Path, *args: str) -> bytes:
        if args and args[0] == "ls-files":
            return b"requirements.txt"
        return real_run_git_bytes(repo_root, *args)

    monkeypatch.setattr(carriers, "_run_git_bytes", malformed_ls_files)

    assert (
        "dependabot.requirement-carriers:$:"
        "candidate discovery could not inspect the repository tree"
    ) in policy.validate_repo(repo)


def test_missing_git_binary_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    monkeypatch.setattr(carriers, "GIT_BINARY", None)

    assert (
        "dependabot.requirement-carriers:$:"
        "candidate discovery could not inspect the repository tree"
    ) in policy.validate_repo(repo)


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


@pytest.mark.parametrize(
    ("selector", "key", "invalid_value", "expected_error"),
    [
        ((), "version", 2.0, ".github/dependabot.yml:version:must be 2; got number"),
        (
            ("registries", policy.REGISTRY_NAME),
            "replaces-base",
            1,
            ".github/dependabot.yml:registries.python-index.replaces-base:"
            "must be True; got integer",
        ),
        (
            ("registries", policy.REGISTRY_NAME),
            "replaces-base",
            1.0,
            ".github/dependabot.yml:registries.python-index.replaces-base:"
            "must be True; got number",
        ),
        (
            ("updates", 0),
            "open-pull-requests-limit",
            4.0,
            ".github/dependabot.yml:updates[0].open-pull-requests-limit:"
            "must be exactly 4; got number",
        ),
        (
            ("updates", 0, "cooldown"),
            "default-days",
            7.0,
            ".github/dependabot.yml:updates[0].cooldown.default-days:" "must be 7; got number",
        ),
        (
            ("updates", 0, "cooldown"),
            "semver-major-days",
            30.0,
            ".github/dependabot.yml:updates[0].cooldown.semver-major-days:"
            "must be 30; got number",
        ),
        (
            ("updates", 0, "cooldown"),
            "semver-minor-days",
            7.0,
            ".github/dependabot.yml:updates[0].cooldown.semver-minor-days:" "must be 7; got number",
        ),
        (
            ("updates", 0, "cooldown"),
            "semver-patch-days",
            3.0,
            ".github/dependabot.yml:updates[0].cooldown.semver-patch-days:" "must be 3; got number",
        ),
    ],
)
def test_exact_policy_values_reject_cross_type_equality(
    tmp_path: Path,
    selector: MappingSelector,
    key: str,
    invalid_value: object,
    expected_error: str,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    _mapping_at_selector(config, selector)[key] = invalid_value
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert expected_error in errors


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


@pytest.mark.parametrize("credential_key", ["username", "password"])
def test_registry_credential_mapping_diagnostics_are_redacted(
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
    sentinel = f"mapping-{credential_key}-must-not-leak"
    registry[credential_key] = {
        policy.EXTERNAL_CODE_EXECUTION_KEY: sentinel,
    }
    _write_config(repo, config)

    errors = policy.validate_repo(repo)
    forbidden_error = (
        f".github/dependabot.yml:$.registries.{policy.REGISTRY_NAME}.{credential_key}."
        f"{policy.EXTERNAL_CODE_EXECUTION_KEY}:key is forbidden because external code "
        "must not receive private registry credentials"
    )
    exact_mapping_error = (
        f".github/dependabot.yml:registries.{policy.REGISTRY_NAME}.{credential_key}:"
        "must be configured secret reference; got mapping(len=1)"
    )
    rendered_errors = "\n".join(errors)

    assert errors.count(forbidden_error) == 1
    assert exact_mapping_error in errors
    assert sentinel not in rendered_errors
    assert "${{secrets." not in rendered_errors

    exit_code = policy.main(["--repo-root", str(repo)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out.count(forbidden_error) == 1
    assert sentinel not in captured.out
    assert sentinel not in captured.err
    assert "${{secrets." not in captured.out
    assert "${{secrets." not in captured.err


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
    assert "must be a canonical absolute repository directory" in rendered
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


def test_mode_a_rejects_update_suppression(
    tmp_path: Path,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    update = _pip_update(config)
    update["allow"] = [{"dependency-name": "fastapi"}]
    update["ignore"] = [{"dependency-name": "starlette"}]
    update["exclude-paths"] = ["requirements-test.in"]
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert any("updates[0].allow:key is forbidden" in error for error in errors)
    assert any("updates[0].ignore:key is forbidden" in error for error in errors)
    assert any("updates[0].exclude-paths:key is forbidden" in error for error in errors)


def test_external_code_execution_is_absent_from_private_pip_updater() -> None:
    config = _load_config(REPO_ROOT)
    update = _pip_update(config)
    registries = config["registries"]

    assert policy.EXTERNAL_CODE_EXECUTION_KEY not in update
    assert update["package-ecosystem"] == "pip"
    assert update["directory"] == "/"
    assert update["registries"] == [policy.REGISTRY_NAME]
    assert registries == {policy.REGISTRY_NAME: policy.REGISTRY_CONFIG}
    assert policy.validate_repo(REPO_ROOT) == []


@pytest.mark.parametrize(
    "present_value",
    ["allow", "deny", False, None, {}],
)
def test_external_code_execution_is_forbidden_independent_of_value(
    tmp_path: Path,
    present_value: object,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    _pip_update(config)[policy.EXTERNAL_CODE_EXECUTION_KEY] = present_value
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    expected_error = (
        ".github/dependabot.yml:$.updates[0]" f"{EXTERNAL_CODE_EXECUTION_FORBIDDEN_ERROR_SUFFIX}"
    )
    assert errors.count(expected_error) == 1


def test_external_code_execution_is_rejected_at_every_mapping_position(
    tmp_path: Path,
) -> None:
    canonical_config = _load_config(REPO_ROOT)
    forbidden_selectors = list(_iter_mapping_selectors(canonical_config))

    assert {
        (),
        ("registries",),
        ("registries", policy.REGISTRY_NAME),
        ("updates", 0, "schedule"),
        ("updates", 0, "commit-message"),
        ("updates", 0, "cooldown"),
        ("updates", 0, "groups"),
    }.issubset(forbidden_selectors)
    assert {("updates", 0, "groups", group_name) for group_name in policy.EXPECTED_GROUPS}.issubset(
        forbidden_selectors
    )

    for index, selector in enumerate(forbidden_selectors):
        repo = _copy_policy_repo(tmp_path / f"position-{index}")
        config = _load_config(repo)
        target = _mapping_at_selector(config, selector)
        target[policy.EXTERNAL_CODE_EXECUTION_KEY] = "allow"
        _write_config(repo, config)

        errors = policy.validate_repo(repo)

        expected_error = (
            f".github/dependabot.yml:{_selector_path(selector)}"
            f"{EXTERNAL_CODE_EXECUTION_FORBIDDEN_ERROR_SUFFIX}"
        )
        assert errors.count(expected_error) == 1


@pytest.mark.parametrize(
    "untrusted_container",
    [
        {"nested": {policy.EXTERNAL_CODE_EXECUTION_KEY: "allow"}},
        [{"nested": {policy.EXTERNAL_CODE_EXECUTION_KEY: "allow"}}],
    ],
)
def test_external_code_execution_rejects_recursively_nested_unknown_container(
    tmp_path: Path,
    untrusted_container: object,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    schedule = _pip_update(config)["schedule"]
    assert isinstance(schedule, dict)
    schedule["untrusted"] = untrusted_container
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    matching_errors = [
        error for error in errors if error.endswith(EXTERNAL_CODE_EXECUTION_FORBIDDEN_ERROR_SUFFIX)
    ]
    assert len(matching_errors) == 1


@pytest.mark.parametrize("invalid_updates", [None, [], ["not-a-mapping"]])
def test_external_code_execution_is_reported_before_invalid_update_shape_returns(
    tmp_path: Path,
    invalid_updates: object,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    sentinel = "DO_NOT_RENDER_THIS_VALUE"
    config[policy.EXTERNAL_CODE_EXECUTION_KEY] = sentinel
    config["updates"] = invalid_updates
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    expected_error = ".github/dependabot.yml:$" f"{EXTERNAL_CODE_EXECUTION_FORBIDDEN_ERROR_SUFFIX}"
    assert errors.count(expected_error) == 1
    assert sentinel not in "\n".join(errors)


@pytest.mark.parametrize(
    ("unexpected_key", "unexpected_value"),
    [
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
        and f"got key_count={len(policy.EXPECTED_UPDATE_KEYS) + 1}" in error
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
        ".github/dependabot.yml:updates:must contain exactly four governed update blocks; got 5"
    ) in errors
    assert ".github/dependabot.yml:updates:duplicate 'pip' updater identity is forbidden" in errors
    assert ".github/dependabot.yml:updates:overlapping 'pip' updater scopes are forbidden" in errors


@pytest.mark.parametrize(
    "invalid_sibling",
    [
        {"package-ecosystem": "npm"},
        {"package-ecosystem": "not-a-real-ecosystem"},
    ],
)
def test_extra_update_siblings_fail_the_closed_registry(
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
        ".github/dependabot.yml:updates:must contain exactly four governed update blocks; got 5"
    ) in errors
    if invalid_sibling["package-ecosystem"] == "npm":
        assert (
            ".github/dependabot.yml:updates:duplicate 'npm' updater identity is forbidden" in errors
        )
    else:
        assert any(
            "updates[4].package-ecosystem:must be one of the four exact governed ecosystems"
            in error
            for error in errors
        )


@pytest.mark.parametrize("invalid_update", [42, None, ["pip"]])
def test_update_entry_must_be_a_mapping(
    tmp_path: Path,
    invalid_update: object,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    config["updates"] = [invalid_update]
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    assert ".github/dependabot.yml:updates[0]:must be a mapping" in errors
    assert (
        ".github/dependabot.yml:updates:must contain exactly four governed update blocks; got 1"
    ) in errors


@pytest.mark.parametrize("package_ecosystem", [None, "", 42, "not-a-real-ecosystem"])
def test_pip_update_rejects_unrecognized_ecosystem(
    tmp_path: Path,
    package_ecosystem: object,
) -> None:
    repo = _copy_policy_repo(tmp_path)
    config = _load_config(repo)
    _pip_update(config)["package-ecosystem"] = package_ecosystem
    _write_config(repo, config)

    errors = policy.validate_repo(repo)

    rendered = "\n".join(errors)
    assert (
        ".github/dependabot.yml:updates[0].package-ecosystem:"
        "must be one of the four exact governed ecosystems"
    ) in rendered
    assert "missing required 'pip' updater identity" in rendered


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

    if key == "directory":
        assert any("updates[0].directory:scope must be exactly ['/']" in error for error in errors)
    else:
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
        "dependabot.requirement-carriers:$:"
        "candidate discovery could not inspect the repository tree",
        "requirements.in:1:" f"line length exceeds limit {policy.MAX_REQUIREMENT_LINE_CHARS}",
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
