"""Deterministic tests for locked Python requirement installation helpers."""

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import re
import subprocess
from typing import Any

import pytest

import scripts.ci.install_locked_python_requirements as installer

APPROVED_PROXY_URL = "https://packages.example.internal/simple"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _repo_emergency_manifest() -> dict[str, Any]:
    return json.loads(
        (REPO_ROOT / "scripts/ci/emergency_python_wheels.json").read_text(encoding="utf-8")
    )


def _exact_requirement_pairs(contents: str) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for raw_line in contents.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or "==" not in line:
            continue
        package, version_and_markers = line.split("==", 1)
        version = version_and_markers.split(";", 1)[0].strip()
        pairs.add((package.strip(), version))
    return pairs


def _manifest_artifact_version(manifest: dict[str, Any], package: str) -> str:
    versions = [
        str(item["version"]).strip() for item in manifest["artifacts"] if item["package"] == package
    ]
    assert versions, f"Emergency wheel manifest must include {package!r}."
    assert (
        len(set(versions)) == 1
    ), f"Emergency wheel manifest must expose a single {package!r} version, found {versions!r}."
    return versions[0]


def _compatible_release_version(contents: str, package: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(package)}(?:\[[^]]+\])?\s*~=\s*([^\s;#]+)(?:\s*;.*)?$")
    matched_versions: list[str] = []
    for raw_line in contents.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        match = pattern.match(line)
        if match is None:
            continue
        matched_versions.append(match.group(1).strip())

    if not matched_versions:
        return None

    assert (
        len(set(matched_versions)) == 1
    ), f"Expected a single compatible-release pin for {package!r}, found {matched_versions!r}."
    return matched_versions[0]


def _resolver_miss_runtimeerror_like_run_command(package: str, version: str) -> RuntimeError:
    """Shape like :func:`run_command` on pip failure (``exit 1`` plus stderr text)."""
    requirement = f"{package}=={version}"
    return RuntimeError(
        "Command failed: python -m pip download stub: exit 1\n"
        f"No matching distribution found for {requirement}"
    )


def test_repo_emergency_manifest_tracks_current_active_fallback_set() -> None:
    manifest = _repo_emergency_manifest()
    artifacts = {(item["package"], item["version"]) for item in manifest["artifacts"]}
    requirements_ci_lite = (REPO_ROOT / "requirements-ci-lite.txt").read_text(encoding="utf-8")
    requirements_ci_lite_pins = _exact_requirement_pairs(requirements_ci_lite)
    ci_lite_emergency_pairs = {
        pair
        for pair in artifacts
        if pair[0] in {package for package, _version in requirements_ci_lite_pins}
    }

    assert artifacts, "Emergency wheel manifest should track at least one fallback artifact."
    assert {package for package, _version in ci_lite_emergency_pairs} >= {
        "mako",
        "pillow",
        "python-multipart",
    }
    assert ci_lite_emergency_pairs <= requirements_ci_lite_pins
    assert ("python-multipart", "0.0.26") in requirements_ci_lite_pins


def test_repo_ruff_emergency_fallback_matches_dev_requirement_surfaces() -> None:
    manifest = _repo_emergency_manifest()
    expected_version = _manifest_artifact_version(manifest, "ruff")

    requirements_dev_in = (REPO_ROOT / "requirements-dev.in").read_text(encoding="utf-8")
    requirements_dev_txt = (REPO_ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    requirements_lock_txt = (REPO_ROOT / "requirements-lock.txt").read_text(encoding="utf-8")

    assert _compatible_release_version(requirements_dev_in, "ruff") == expected_version
    assert ("ruff", expected_version) in _exact_requirement_pairs(requirements_dev_txt)
    assert ("ruff", expected_version) in _exact_requirement_pairs(requirements_lock_txt)


def test_repo_mypy_emergency_fallback_matches_dev_requirement_surfaces() -> None:
    manifest = _repo_emergency_manifest()
    expected_version = _manifest_artifact_version(manifest, "mypy")

    requirements_dev_in = (REPO_ROOT / "requirements-dev.in").read_text(encoding="utf-8")
    requirements_dev_txt = (REPO_ROOT / "requirements-dev.txt").read_text(encoding="utf-8")

    assert ("mypy", expected_version) in _exact_requirement_pairs(requirements_dev_in)
    assert ("mypy", expected_version) in _exact_requirement_pairs(requirements_dev_txt)


def test_compatible_release_version_accepts_environment_markers() -> None:
    contents = 'ruff~=0.15.11 ; python_version >= "3.13"\n'

    assert _compatible_release_version(contents, "ruff") == "0.15.11"


def test_exact_requirement_pairs_ignores_environment_markers() -> None:
    contents = 'ruff==0.15.11 ; python_version >= "3.13"\n'

    assert ("ruff", "0.15.11") in _exact_requirement_pairs(contents)


@pytest.fixture(autouse=True)
def isolate_proxy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(installer.APPROVED_INDEX_ENV_VAR, raising=False)
    monkeypatch.delenv(installer.TRUSTED_HOST_ENV_VAR, raising=False)
    monkeypatch.delenv(installer.DOCKER_SINGLE_PASS_LOCKED_INSTALL_ENV, raising=False)
    monkeypatch.delenv(installer.DOCKER_PIP_LAYER_CACHE_ENV, raising=False)
    for env_var in installer.AMBIENT_INDEX_OVERRIDE_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)


def test_resolve_requirement_files_prefers_dev_only_when_requested(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    requirements_dev = tmp_path / "requirements-dev.txt"
    requirements_dev.write_text("pytest==8.4.2\n", encoding="utf-8")
    requirements_test = tmp_path / "requirements-test.txt"
    requirements_test.write_text("pytest==8.4.2\n", encoding="utf-8")
    requirements_ci_lite = tmp_path / "requirements-ci-lite.txt"
    requirements_rag_vector = tmp_path / "requirements-rag-vector.txt"
    requirements_rag_vector.write_text("sentence-transformers==5.4.1\n", encoding="utf-8")

    files = installer.resolve_requirement_files(
        requirements_file=requirements,
        dev_requirements_file=requirements_dev,
        test_requirements_file=requirements_test,
        ci_lite_requirements_file=requirements_ci_lite,
        rag_vector_requirements_file=requirements_rag_vector,
        install_dev=True,
        install_test=False,
        requirements_profile=None,
    )

    assert files == [requirements, requirements_dev]


def test_resolve_requirement_files_includes_test_surface_when_requested(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    requirements_dev = tmp_path / "requirements-dev.txt"
    requirements_dev.write_text("bandit==1.9.4\n", encoding="utf-8")
    requirements_test = tmp_path / "requirements-test.txt"
    requirements_test.write_text("pytest==8.4.2\n", encoding="utf-8")
    requirements_ci_lite = tmp_path / "requirements-ci-lite.txt"
    requirements_rag_vector = tmp_path / "requirements-rag-vector.txt"
    requirements_rag_vector.write_text("sentence-transformers==5.4.1\n", encoding="utf-8")

    files = installer.resolve_requirement_files(
        requirements_file=requirements,
        dev_requirements_file=requirements_dev,
        test_requirements_file=requirements_test,
        ci_lite_requirements_file=requirements_ci_lite,
        rag_vector_requirements_file=requirements_rag_vector,
        install_dev=False,
        install_test=True,
        requirements_profile=None,
    )

    assert files == [requirements, requirements_test]


def test_resolve_requirement_files_supports_explicit_ci_lite_profile(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    requirements_dev = tmp_path / "requirements-dev.txt"
    requirements_dev.write_text("pre-commit==4.5.1\n", encoding="utf-8")
    requirements_test = tmp_path / "requirements-test.txt"
    requirements_test.write_text("pytest==8.4.2\n", encoding="utf-8")
    requirements_ci_lite = tmp_path / "requirements-ci-lite.txt"
    requirements_ci_lite.write_text("pre-commit==4.5.1\n", encoding="utf-8")
    requirements_rag_vector = tmp_path / "requirements-rag-vector.txt"
    requirements_rag_vector.write_text("sentence-transformers==5.4.1\n", encoding="utf-8")

    files = installer.resolve_requirement_files(
        requirements_file=requirements,
        dev_requirements_file=requirements_dev,
        test_requirements_file=requirements_test,
        ci_lite_requirements_file=requirements_ci_lite,
        rag_vector_requirements_file=requirements_rag_vector,
        install_dev=False,
        install_test=False,
        requirements_profile="ci-lite",
    )

    assert files == [requirements_ci_lite]


def test_resolve_requirement_files_supports_explicit_ci_test_profile(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    requirements_dev = tmp_path / "requirements-dev.txt"
    requirements_dev.write_text("pre-commit==4.5.1\n", encoding="utf-8")
    requirements_test = tmp_path / "requirements-test.txt"
    requirements_test.write_text("pytest==9.0.3\n", encoding="utf-8")
    requirements_ci_lite = tmp_path / "requirements-ci-lite.txt"
    requirements_ci_lite.write_text("pre-commit==4.5.1\n", encoding="utf-8")
    requirements_rag_vector = tmp_path / "requirements-rag-vector.txt"
    requirements_rag_vector.write_text("sentence-transformers==5.4.1\n", encoding="utf-8")

    files = installer.resolve_requirement_files(
        requirements_file=requirements,
        dev_requirements_file=requirements_dev,
        test_requirements_file=requirements_test,
        ci_lite_requirements_file=requirements_ci_lite,
        rag_vector_requirements_file=requirements_rag_vector,
        install_dev=False,
        install_test=False,
        requirements_profile="ci-test",
    )

    assert files == [requirements_ci_lite, requirements_test]


def test_resolve_requirement_files_supports_explicit_rag_vector_profile(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    requirements_dev = tmp_path / "requirements-dev.txt"
    requirements_dev.write_text("pre-commit==4.5.1\n", encoding="utf-8")
    requirements_test = tmp_path / "requirements-test.txt"
    requirements_test.write_text("pytest==9.0.3\n", encoding="utf-8")
    requirements_ci_lite = tmp_path / "requirements-ci-lite.txt"
    requirements_ci_lite.write_text("pre-commit==4.5.1\n", encoding="utf-8")
    requirements_rag_vector = tmp_path / "requirements-rag-vector.txt"
    requirements_rag_vector.write_text("sentence-transformers==5.4.1\n", encoding="utf-8")

    files = installer.resolve_requirement_files(
        requirements_file=requirements,
        dev_requirements_file=requirements_dev,
        test_requirements_file=requirements_test,
        ci_lite_requirements_file=requirements_ci_lite,
        rag_vector_requirements_file=requirements_rag_vector,
        install_dev=False,
        install_test=False,
        requirements_profile="rag-vector",
    )

    assert files == [requirements, requirements_rag_vector]


def test_resolve_requirement_files_fails_when_runtime_file_is_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Requirements file not found"):
        installer.resolve_requirement_files(
            requirements_file=tmp_path / "requirements.txt",
            dev_requirements_file=tmp_path / "requirements-dev.txt",
            test_requirements_file=tmp_path / "requirements-test.txt",
            ci_lite_requirements_file=tmp_path / "requirements-ci-lite.txt",
            rag_vector_requirements_file=tmp_path / "requirements-rag-vector.txt",
            install_dev=False,
            install_test=False,
            requirements_profile=None,
        )


def test_resolve_requirement_files_fails_when_dev_file_is_requested_but_missing(
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Dev requirements file not found"):
        installer.resolve_requirement_files(
            requirements_file=requirements,
            dev_requirements_file=tmp_path / "requirements-dev.txt",
            test_requirements_file=tmp_path / "requirements-test.txt",
            ci_lite_requirements_file=tmp_path / "requirements-ci-lite.txt",
            rag_vector_requirements_file=tmp_path / "requirements-rag-vector.txt",
            install_dev=True,
            install_test=False,
            requirements_profile=None,
        )


def test_resolve_requirement_files_fails_when_test_file_is_requested_but_missing(
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    requirements_dev = tmp_path / "requirements-dev.txt"
    requirements_dev.write_text("bandit==1.9.4\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Test requirements file not found"):
        installer.resolve_requirement_files(
            requirements_file=requirements,
            dev_requirements_file=requirements_dev,
            test_requirements_file=tmp_path / "requirements-test.txt",
            ci_lite_requirements_file=tmp_path / "requirements-ci-lite.txt",
            rag_vector_requirements_file=tmp_path / "requirements-rag-vector.txt",
            install_dev=False,
            install_test=True,
            requirements_profile=None,
        )


def test_resolve_requirement_files_fails_when_ci_lite_profile_is_requested_but_missing(
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    requirements_dev = tmp_path / "requirements-dev.txt"
    requirements_dev.write_text("pre-commit==4.5.1\n", encoding="utf-8")
    requirements_test = tmp_path / "requirements-test.txt"
    requirements_test.write_text("pytest==8.4.2\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="CI lite requirements file not found"):
        installer.resolve_requirement_files(
            requirements_file=requirements,
            dev_requirements_file=requirements_dev,
            test_requirements_file=requirements_test,
            ci_lite_requirements_file=tmp_path / "requirements-ci-lite.txt",
            rag_vector_requirements_file=tmp_path / "requirements-rag-vector.txt",
            install_dev=False,
            install_test=False,
            requirements_profile="ci-lite",
        )


def test_resolve_requirement_files_fails_when_ci_test_profile_is_requested_but_missing(
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    requirements_dev = tmp_path / "requirements-dev.txt"
    requirements_dev.write_text("pre-commit==4.5.1\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="CI lite requirements file not found"):
        installer.resolve_requirement_files(
            requirements_file=requirements,
            dev_requirements_file=requirements_dev,
            test_requirements_file=tmp_path / "requirements-test.txt",
            ci_lite_requirements_file=tmp_path / "requirements-ci-lite.txt",
            rag_vector_requirements_file=tmp_path / "requirements-rag-vector.txt",
            install_dev=False,
            install_test=False,
            requirements_profile="ci-test",
        )


def test_resolve_requirement_files_fails_when_ci_test_test_file_is_missing(
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    requirements_dev = tmp_path / "requirements-dev.txt"
    requirements_dev.write_text("pre-commit==4.5.1\n", encoding="utf-8")
    requirements_ci_lite = tmp_path / "requirements-ci-lite.txt"
    requirements_ci_lite.write_text("pre-commit==4.5.1\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="CI test requirements file not found"):
        installer.resolve_requirement_files(
            requirements_file=requirements,
            dev_requirements_file=requirements_dev,
            test_requirements_file=tmp_path / "requirements-test.txt",
            ci_lite_requirements_file=requirements_ci_lite,
            rag_vector_requirements_file=tmp_path / "requirements-rag-vector.txt",
            install_dev=False,
            install_test=False,
            requirements_profile="ci-test",
        )


def test_resolve_requirement_files_fails_when_rag_vector_profile_is_requested_but_missing(
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    requirements_dev = tmp_path / "requirements-dev.txt"
    requirements_dev.write_text("pre-commit==4.5.1\n", encoding="utf-8")
    requirements_test = tmp_path / "requirements-test.txt"
    requirements_test.write_text("pytest==9.0.3\n", encoding="utf-8")
    requirements_ci_lite = tmp_path / "requirements-ci-lite.txt"
    requirements_ci_lite.write_text("pre-commit==4.5.1\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="RAG vector requirements file not found"):
        installer.resolve_requirement_files(
            requirements_file=requirements,
            dev_requirements_file=requirements_dev,
            test_requirements_file=requirements_test,
            ci_lite_requirements_file=requirements_ci_lite,
            rag_vector_requirements_file=tmp_path / "requirements-rag-vector.txt",
            install_dev=False,
            install_test=False,
            requirements_profile="rag-vector",
        )


def test_build_pip_download_command_uses_constraint_when_present(tmp_path: Path) -> None:
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("openai>=2.29.0\n", encoding="utf-8")

    command = installer.build_pip_download_command(
        python_executable="python",
        requirement_file=tmp_path / "requirements.txt",
        wheelhouse_dir=tmp_path / "wheelhouse",
        constraints_file=constraints,
        index_url=APPROVED_PROXY_URL,
        trusted_host="packages.example.internal",
    )

    assert command[:4] == ["python", "-m", "pip", "download"]
    download_idx = command.index("download")
    assert command[download_idx + 1 : download_idx + 5] == [
        "--retries",
        str(installer.PIP_NETWORK_RETRIES),
        "--timeout",
        str(installer.PIP_NETWORK_TIMEOUT_SECONDS),
    ]
    assert "--only-binary" in command
    assert ":all:" in command
    assert "--find-links" in command
    assert str(tmp_path / "wheelhouse") in command
    assert "--dest" in command
    assert "--index-url" in command
    assert APPROVED_PROXY_URL in command
    assert "--trusted-host" in command
    assert "--constraint" in command


def test_build_pip_install_command_is_hermetic(tmp_path: Path) -> None:
    command = installer.build_pip_install_command(
        python_executable="python",
        requirement_file=tmp_path / "requirements.txt",
        wheelhouse_dir=tmp_path / "wheelhouse",
        constraints_file=None,
    )

    assert command[:4] == ["python", "-m", "pip", "install"]
    assert "--no-index" in command
    assert "--find-links" in command


def test_effective_constraints_file_for_requirement_filters_duplicate_exact_pin(
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pillow==12.2.0\nopenai==2.8.1\n", encoding="utf-8")
    constraints = tmp_path / "constraints.txt"
    constraints.write_text(
        "pillow==12.2.0  # Security floor\nhttpx>=0.28.1\n",
        encoding="utf-8",
    )

    with installer.effective_constraints_file_for_requirement(
        requirements,
        constraints,
    ) as effective_constraints:
        assert effective_constraints is not None
        assert effective_constraints != constraints
        assert effective_constraints.read_text(encoding="utf-8") == "httpx>=0.28.1\n"


def test_effective_constraints_file_for_requirement_keeps_relative_includes_resolvable(
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pillow==12.2.0\n", encoding="utf-8")
    constraints = tmp_path / "constraints.txt"
    nested_constraints = tmp_path / "nested.txt"
    nested_constraints.write_text("httpx>=0.28.1\n", encoding="utf-8")
    constraints.write_text("-c nested.txt\npillow==12.2.0\n", encoding="utf-8")

    with installer.effective_constraints_file_for_requirement(
        requirements,
        constraints,
    ) as effective_constraints:
        assert effective_constraints is not None
        assert effective_constraints != constraints
        assert effective_constraints.parent == constraints.parent
        assert (effective_constraints.parent / "nested.txt").exists()
        assert effective_constraints.read_text(encoding="utf-8") == "-c nested.txt\n"


def test_effective_constraints_file_for_requirement_drops_constraint_when_only_duplicate_pin(
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pillow==12.2.0\n", encoding="utf-8")
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("pillow==12.2.0\n", encoding="utf-8")

    with installer.effective_constraints_file_for_requirement(
        requirements,
        constraints,
    ) as effective_constraints:
        assert effective_constraints is None


def test_install_from_proxy_omits_duplicate_exact_constraint_for_same_requirement_surface(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pillow==12.2.0\n", encoding="utf-8")
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("pillow==12.2.0\n", encoding="utf-8")
    observed_commands: list[list[str]] = []

    def fake_run_command(command: list[str]) -> None:
        observed_commands.append(command)

    monkeypatch.setattr(installer, "run_command", fake_run_command)

    installer.install_from_proxy(
        python_executable="python",
        requirement_files=[requirements],
        constraints_file=constraints,
        index_url=APPROVED_PROXY_URL,
        trusted_host="packages.example.internal",
    )

    assert len(observed_commands) == 1
    assert "--constraint" not in observed_commands[0]


def test_build_wheelhouse_preserves_non_duplicate_constraints(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pillow==12.2.0\n", encoding="utf-8")
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("httpx>=0.28.1\n", encoding="utf-8")
    observed_commands: list[list[str]] = []

    def fake_run_command(command: list[str]) -> None:
        observed_commands.append(command)

    monkeypatch.setattr(installer, "run_command", fake_run_command)

    installer.build_wheelhouse(
        python_executable="python",
        requirement_files=[requirements],
        constraints_file=constraints,
        wheelhouse_dir=tmp_path / "wheelhouse",
        index_url=APPROVED_PROXY_URL,
        trusted_host="packages.example.internal",
    )

    assert len(observed_commands) == 1
    assert "--constraint" in observed_commands[0]
    constraint_path = Path(observed_commands[0][observed_commands[0].index("--constraint") + 1])
    assert constraint_path == constraints
    assert constraint_path.read_text(encoding="utf-8") == "httpx>=0.28.1\n"


def test_install_from_wheelhouse_omits_duplicate_exact_constraint_for_same_requirement_surface(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pillow==12.2.0\n", encoding="utf-8")
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("pillow==12.2.0\n", encoding="utf-8")
    observed_commands: list[list[str]] = []

    def fake_run_command(command: list[str]) -> None:
        observed_commands.append(command)

    monkeypatch.setattr(installer, "run_command", fake_run_command)

    installer.install_from_wheelhouse(
        python_executable="python",
        requirement_files=[requirements],
        constraints_file=constraints,
        wheelhouse_dir=tmp_path / "wheelhouse",
    )

    assert len(observed_commands) == 1
    assert "--constraint" not in observed_commands[0]


def test_install_from_wheelhouse_preserves_non_duplicate_constraints(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pillow==12.2.0\n", encoding="utf-8")
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("httpx>=0.28.1\n", encoding="utf-8")
    observed_commands: list[list[str]] = []

    def fake_run_command(command: list[str]) -> None:
        observed_commands.append(command)

    monkeypatch.setattr(installer, "run_command", fake_run_command)

    installer.install_from_wheelhouse(
        python_executable="python",
        requirement_files=[requirements],
        constraints_file=constraints,
        wheelhouse_dir=tmp_path / "wheelhouse",
    )

    assert len(observed_commands) == 1
    assert "--constraint" in observed_commands[0]
    constraint_path = Path(observed_commands[0][observed_commands[0].index("--constraint") + 1])
    assert constraint_path == constraints
    assert constraint_path.read_text(encoding="utf-8") == "httpx>=0.28.1\n"


def test_build_pip_proxy_install_command_uses_approved_proxy_without_cache(
    tmp_path: Path,
) -> None:
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("openai>=2.29.0\n", encoding="utf-8")

    command = installer.build_pip_proxy_install_command(
        python_executable="python",
        requirement_file=tmp_path / "requirements.txt",
        constraints_file=constraints,
        index_url=APPROVED_PROXY_URL,
        trusted_host="packages.example.internal",
    )

    assert command[:4] == ["python", "-m", "pip", "install"]
    install_idx = command.index("install")
    assert command[install_idx + 1 : install_idx + 5] == [
        "--no-cache-dir",
        "--retries",
        str(installer.PIP_NETWORK_RETRIES),
        "--timeout",
    ]
    assert command[install_idx + 5] == str(installer.PIP_NETWORK_TIMEOUT_SECONDS)
    assert "--only-binary" in command
    assert ":all:" in command
    assert "--index-url" in command
    assert APPROVED_PROXY_URL in command
    assert "--trusted-host" in command
    assert "--constraint" in command


def test_build_pip_proxy_install_command_omits_no_cache_dir_when_cache_allowed(
    tmp_path: Path,
) -> None:
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("openai>=2.29.0\n", encoding="utf-8")

    command = installer.build_pip_proxy_install_command(
        python_executable="python",
        requirement_file=tmp_path / "requirements.txt",
        constraints_file=constraints,
        index_url=APPROVED_PROXY_URL,
        trusted_host="packages.example.internal",
        allow_pip_download_cache=True,
    )

    assert "--no-cache-dir" not in command
    install_idx = command.index("install")
    assert command[install_idx + 1 : install_idx + 5] == [
        "--retries",
        str(installer.PIP_NETWORK_RETRIES),
        "--timeout",
        str(installer.PIP_NETWORK_TIMEOUT_SECONDS),
    ]


def test_build_pip_proxy_install_command_supports_find_links(tmp_path: Path) -> None:
    command = installer.build_pip_proxy_install_command(
        python_executable="python",
        requirement_file=tmp_path / "requirements.txt",
        constraints_file=None,
        index_url=APPROVED_PROXY_URL,
        trusted_host=None,
        find_links_dir=tmp_path / "wheelhouse",
    )

    assert "--find-links" in command
    assert str(tmp_path / "wheelhouse") in command


def test_validate_private_proxy_url_rejects_public_hosts() -> None:
    with pytest.raises(RuntimeError, match="must not point to public host"):
        installer.validate_private_proxy_url("https://pypi.org/simple")


def test_validate_private_proxy_url_strips_whitespace_and_trailing_dot() -> None:
    normalized = installer.validate_private_proxy_url(
        "  https://packages.example.internal/simple  "
    )

    assert normalized == "https://packages.example.internal/simple"

    with pytest.raises(RuntimeError, match="must not point to public host"):
        installer.validate_private_proxy_url("https://pypi.org./simple")


def test_resolve_private_proxy_settings_requires_explicit_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(RuntimeError, match="Approved Python package proxy is required"):
        installer.resolve_private_proxy_settings(index_url=None, trusted_host=None)


def test_resolve_private_proxy_settings_rejects_ambient_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PIP_EXTRA_INDEX_URL", "https://malicious.example/simple")

    with pytest.raises(RuntimeError, match="Ambient Python package index overrides are forbidden"):
        installer.resolve_private_proxy_settings(
            index_url=APPROVED_PROXY_URL,
            trusted_host=None,
        )


def test_load_emergency_wheel_manifest_rejects_expired_file(tmp_path: Path) -> None:
    manifest = tmp_path / "emergency.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "expires_at": "2026-04-01",
                "artifacts": [
                    {
                        "package": "cryptography",
                        "version": "46.0.7",
                        "filename": "cryptography.whl",
                        "url": "https://files.pythonhosted.org/packages/example/cryptography.whl",
                        "sha256": "a" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="expired"):
        installer.load_emergency_wheel_manifest(manifest)


def test_load_emergency_wheel_manifest_rejects_non_canonical_iso_date_format(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "emergency.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "expires_at": "20991231",
                "artifacts": [
                    {
                        "package": "cryptography",
                        "version": "46.0.7",
                        "filename": "cryptography.whl",
                        "url": "https://files.pythonhosted.org/packages/example/cryptography.whl",
                        "sha256": "a" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="must use YYYY-MM-DD"):
        installer.load_emergency_wheel_manifest(manifest)


def test_load_emergency_wheel_manifest_keeps_active_artifact_specific_override(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "emergency.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "expires_at": "2026-04-01",
                "artifacts": [
                    {
                        "package": "cryptography",
                        "version": "46.0.7",
                        "filename": "cryptography.whl",
                        "url": "https://files.pythonhosted.org/packages/example/cryptography.whl",
                        "sha256": "a" * 64,
                    },
                    {
                        "package": "mako",
                        "version": "1.3.11",
                        "expires_at": "2099-12-31",
                        "filename": "mako.whl",
                        "url": "https://files.pythonhosted.org/packages/example/mako.whl",
                        "sha256": "b" * 64,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    artifacts = installer.load_emergency_wheel_manifest(manifest)

    assert [(item["package"], item["version"]) for item in artifacts] == [("mako", "1.3.11")]


def test_load_emergency_wheel_manifest_rejects_invalid_artifact_specific_iso_date(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "emergency.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "expires_at": "2099-12-31",
                "artifacts": [
                    {
                        "package": "mako",
                        "version": "1.3.11",
                        "expires_at": "20991231",
                        "filename": "mako.whl",
                        "url": "https://files.pythonhosted.org/packages/example/mako.whl",
                        "sha256": "a" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match=r"artifacts\[0\]\.expires_at"):
        installer.load_emergency_wheel_manifest(manifest)


def test_load_emergency_wheel_manifest_filters_past_artifact_specific_expiries(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "emergency.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "expires_at": "2099-12-31",
                "artifacts": [
                    {
                        "package": "expired-pkg",
                        "version": "1.0.0",
                        "expires_at": "2000-01-01",
                        "filename": "expired.whl",
                        "url": "https://files.pythonhosted.org/packages/example/expired.whl",
                        "sha256": "a" * 64,
                    },
                    {
                        "package": "valid-pkg",
                        "version": "2.0.0",
                        "expires_at": "2099-12-31",
                        "filename": "valid.whl",
                        "url": "https://files.pythonhosted.org/packages/example/valid.whl",
                        "sha256": "b" * 64,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    artifacts = installer.load_emergency_wheel_manifest(manifest)

    assert [(item["package"], item["version"]) for item in artifacts] == [("valid-pkg", "2.0.0")]


def test_load_emergency_wheel_manifest_raises_when_all_artifacts_expire_individually(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "emergency.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "expires_at": "2099-12-31",
                "artifacts": [
                    {
                        "package": "expired-pkg-1",
                        "version": "1.0.0",
                        "expires_at": "2000-01-01",
                        "filename": "expired-1.whl",
                        "url": "https://files.pythonhosted.org/packages/example/expired-1.whl",
                        "sha256": "a" * 64,
                    },
                    {
                        "package": "expired-pkg-2",
                        "version": "2.0.0",
                        "expires_at": "2000-01-02",
                        "filename": "expired-2.whl",
                        "url": "https://files.pythonhosted.org/packages/example/expired-2.whl",
                        "sha256": "b" * 64,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="manifest is expired"):
        installer.load_emergency_wheel_manifest(manifest)


def test_stage_emergency_wheels_downloads_only_requested_exact_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("cryptography==46.0.7\nopenai==2.29.0\n", encoding="utf-8")
    manifest = tmp_path / "emergency.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "expires_at": "2099-12-31",
                "artifacts": [
                    {
                        "package": "cryptography",
                        "version": "46.0.7",
                        "filename": "cryptography-46.0.7.whl",
                        "url": "https://files.pythonhosted.org/packages/example/cryptography-46.0.7.whl",
                        "sha256": "b" * 64,
                    },
                    {
                        "package": "cryptography",
                        "version": "46.0.8",
                        "filename": "cryptography-46.0.8.whl",
                        "url": "https://files.pythonhosted.org/packages/example/cryptography-46.0.8.whl",
                        "sha256": "c" * 64,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    observed_downloads: list[tuple[str, Path, str]] = []

    def fake_download(*, url: str, destination: Path, expected_sha256: str) -> None:
        observed_downloads.append((url, destination, expected_sha256))
        destination.write_bytes(b"wheel-bytes")

    monkeypatch.setattr(installer, "_download_with_sha256", fake_download)

    staged = installer.stage_emergency_wheels(
        requirement_files=[requirements],
        constraints_file=None,
        wheelhouse_dir=tmp_path / "wheelhouse",
        manifest_path=manifest,
    )

    assert [path.name for path in staged] == ["cryptography-46.0.7.whl"]
    assert observed_downloads == [
        (
            "https://files.pythonhosted.org/packages/example/cryptography-46.0.7.whl",
            tmp_path / "wheelhouse" / "cryptography-46.0.7.whl",
            "b" * 64,
        )
    ]


def test_stage_emergency_wheels_downloads_requested_artifacts_across_multiple_packages(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements-dev.txt"
    requirements.write_text(
        "cryptography==46.0.7\nruff==0.15.11\ntypes-pyyaml==6.0.12.20260408\nopenai==2.29.0\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "emergency.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "expires_at": "2099-12-31",
                "artifacts": [
                    {
                        "package": "cryptography",
                        "version": "46.0.7",
                        "filename": "cryptography-46.0.7.whl",
                        "url": "https://files.pythonhosted.org/packages/example/cryptography-46.0.7.whl",
                        "sha256": "b" * 64,
                    },
                    {
                        "package": "ruff",
                        "version": "0.15.11",
                        "filename": "ruff-0.15.11-manylinux.whl",
                        "url": "https://files.pythonhosted.org/packages/example/ruff-0.15.11-manylinux.whl",
                        "sha256": "c" * 64,
                    },
                    {
                        "package": "types-pyyaml",
                        "version": "6.0.12.20260408",
                        "filename": "types_pyyaml-6.0.12.20260408-py3-none-any.whl",
                        "url": "https://files.pythonhosted.org/packages/example/types_pyyaml-6.0.12.20260408-py3-none-any.whl",
                        "sha256": "d" * 64,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    observed_downloads: list[tuple[str, Path, str]] = []

    def fake_download(*, url: str, destination: Path, expected_sha256: str) -> None:
        observed_downloads.append((url, destination, expected_sha256))
        destination.write_bytes(b"wheel-bytes")

    monkeypatch.setattr(installer, "_download_with_sha256", fake_download)

    staged = installer.stage_emergency_wheels(
        requirement_files=[requirements],
        constraints_file=None,
        wheelhouse_dir=tmp_path / "wheelhouse",
        manifest_path=manifest,
    )

    assert [path.name for path in staged] == [
        "cryptography-46.0.7.whl",
        "ruff-0.15.11-manylinux.whl",
        "types_pyyaml-6.0.12.20260408-py3-none-any.whl",
    ]
    assert observed_downloads == [
        (
            "https://files.pythonhosted.org/packages/example/cryptography-46.0.7.whl",
            tmp_path / "wheelhouse" / "cryptography-46.0.7.whl",
            "b" * 64,
        ),
        (
            "https://files.pythonhosted.org/packages/example/ruff-0.15.11-manylinux.whl",
            tmp_path / "wheelhouse" / "ruff-0.15.11-manylinux.whl",
            "c" * 64,
        ),
        (
            "https://files.pythonhosted.org/packages/example/types_pyyaml-6.0.12.20260408-py3-none-any.whl",
            tmp_path / "wheelhouse" / "types_pyyaml-6.0.12.20260408-py3-none-any.whl",
            "d" * 64,
        ),
    ]


def test_stage_emergency_wheels_downloads_artifacts_requested_via_constraints(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements-dev.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("types-pyyaml==6.0.12.20260408\n", encoding="utf-8")
    manifest = tmp_path / "emergency.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "expires_at": "2099-12-31",
                "artifacts": [
                    {
                        "package": "types-pyyaml",
                        "version": "6.0.12.20260408",
                        "filename": "types_pyyaml-6.0.12.20260408-py3-none-any.whl",
                        "url": "https://files.pythonhosted.org/packages/example/types_pyyaml-6.0.12.20260408-py3-none-any.whl",
                        "sha256": "d" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    observed_downloads: list[tuple[str, Path, str]] = []

    def fake_download(*, url: str, destination: Path, expected_sha256: str) -> None:
        observed_downloads.append((url, destination, expected_sha256))
        destination.write_bytes(b"wheel-bytes")

    monkeypatch.setattr(installer, "_download_with_sha256", fake_download)

    staged = installer.stage_emergency_wheels(
        requirement_files=[requirements],
        constraints_file=constraints,
        wheelhouse_dir=tmp_path / "wheelhouse",
        manifest_path=manifest,
    )

    assert [path.name for path in staged] == ["types_pyyaml-6.0.12.20260408-py3-none-any.whl"]
    assert observed_downloads == [
        (
            "https://files.pythonhosted.org/packages/example/types_pyyaml-6.0.12.20260408-py3-none-any.whl",
            tmp_path / "wheelhouse" / "types_pyyaml-6.0.12.20260408-py3-none-any.whl",
            "d" * 64,
        )
    ]


def test_stage_emergency_wheels_reads_constraints_surface_once_for_multiple_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements-dev.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    constraints = tmp_path / "constraints.txt"
    constraints.write_text(
        "ruff==0.15.11\ntypes-pyyaml==6.0.12.20260408\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "emergency.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "expires_at": "2099-12-31",
                "artifacts": [
                    {
                        "package": "ruff",
                        "version": "0.15.11",
                        "filename": "ruff-0.15.11-manylinux.whl",
                        "url": "https://files.pythonhosted.org/packages/example/ruff-0.15.11-manylinux.whl",
                        "sha256": "c" * 64,
                    },
                    {
                        "package": "types-pyyaml",
                        "version": "6.0.12.20260408",
                        "filename": "types_pyyaml-6.0.12.20260408-py3-none-any.whl",
                        "url": "https://files.pythonhosted.org/packages/example/types_pyyaml-6.0.12.20260408-py3-none-any.whl",
                        "sha256": "d" * 64,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    observed_downloads: list[tuple[str, Path, str]] = []
    constraint_reads = 0
    original_read_text = Path.read_text

    def fake_download(*, url: str, destination: Path, expected_sha256: str) -> None:
        observed_downloads.append((url, destination, expected_sha256))
        destination.write_bytes(b"wheel-bytes")

    def counting_read_text(self: Path, *args: object, **kwargs: object) -> str:
        nonlocal constraint_reads
        if self == constraints:
            constraint_reads += 1
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(installer, "_download_with_sha256", fake_download)
    monkeypatch.setattr(Path, "read_text", counting_read_text)

    staged = installer.stage_emergency_wheels(
        requirement_files=[requirements],
        constraints_file=constraints,
        wheelhouse_dir=tmp_path / "wheelhouse",
        manifest_path=manifest,
    )

    assert [path.name for path in staged] == [
        "ruff-0.15.11-manylinux.whl",
        "types_pyyaml-6.0.12.20260408-py3-none-any.whl",
    ]
    assert constraint_reads == 1


def test_download_with_sha256_cleans_partial_temp_files_on_stream_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class BrokenResponse:
        def __init__(self) -> None:
            self._read_count = 0

        def __enter__(self) -> BrokenResponse:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        def read(self, size: int) -> bytes:
            self._read_count += 1
            if self._read_count == 1:
                return b"partial-wheel"
            raise OSError("network dropped")

    monkeypatch.setattr(installer, "urlopen", lambda *args, **kwargs: BrokenResponse())

    destination = tmp_path / "wheelhouse" / "cryptography-46.0.7.whl"

    with pytest.raises(OSError, match="network dropped"):
        installer._download_with_sha256(
            url="https://files.pythonhosted.org/packages/example/cryptography-46.0.7.whl",
            destination=destination,
            expected_sha256="a" * 64,
        )

    assert destination.exists() is False
    assert list((tmp_path / "wheelhouse").iterdir()) == []


def test_download_with_sha256_closes_temp_fd_when_urlopen_fails_immediately(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observed_fdopen_calls: list[int] = []
    original_fdopen = installer.os.fdopen

    def tracking_fdopen(fd: int, mode: str, *args: object, **kwargs: object) -> object:
        observed_fdopen_calls.append(fd)
        return original_fdopen(fd, mode, *args, **kwargs)

    def raise_urlopen(*args: object, **kwargs: object) -> object:
        raise OSError("connect failed")

    monkeypatch.setattr(installer.os, "fdopen", tracking_fdopen)
    monkeypatch.setattr(installer, "urlopen", raise_urlopen)

    destination = tmp_path / "wheelhouse" / "cryptography-46.0.7.whl"

    with pytest.raises(OSError, match="connect failed"):
        installer._download_with_sha256(
            url="https://files.pythonhosted.org/packages/example/cryptography-46.0.7.whl",
            destination=destination,
            expected_sha256="a" * 64,
        )

    assert observed_fdopen_calls
    assert destination.exists() is False
    assert list((tmp_path / "wheelhouse").iterdir()) == []


def test_build_wheelhouse_with_emergency_fallback_retries_only_after_proxy_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("cryptography==46.0.7\n", encoding="utf-8")
    manifest = tmp_path / "emergency.json"
    manifest.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-09",
                "expires_at": "2099-12-31",
                "artifacts": [
                    {
                        "package": "cryptography",
                        "version": "46.0.7",
                        "filename": "cryptography-46.0.7.whl",
                        "url": "https://files.pythonhosted.org/packages/example/cryptography-46.0.7.whl",
                        "sha256": "b" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    observed_calls: list[Path] = []
    build_attempts = {"count": 0}

    def fake_build_wheelhouse(**kwargs: object) -> None:
        build_attempts["count"] += 1
        observed_calls.append(Path(kwargs["wheelhouse_dir"]))
        if build_attempts["count"] == 1:
            raise RuntimeError("proxy miss")

    def fake_stage_emergency_wheels(**kwargs: object) -> list[Path]:
        wheelhouse_dir = Path(kwargs["wheelhouse_dir"])
        destination = wheelhouse_dir / "cryptography-46.0.7.whl"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"wheel-bytes")
        return [destination]

    monkeypatch.setattr(installer, "build_wheelhouse", fake_build_wheelhouse)
    monkeypatch.setattr(installer, "stage_emergency_wheels", fake_stage_emergency_wheels)

    installer.build_wheelhouse_with_emergency_fallback(
        python_executable="python",
        requirement_files=[requirements],
        constraints_file=None,
        wheelhouse_dir=tmp_path / "wheelhouse",
        index_url=APPROVED_PROXY_URL,
        trusted_host=None,
        emergency_wheel_manifest=manifest,
    )

    assert observed_calls == [tmp_path / "wheelhouse", tmp_path / "wheelhouse"]
    assert build_attempts["count"] == 2


def test_install_from_proxy_with_emergency_fallback_retries_with_find_links_after_proxy_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("cryptography==46.0.7\n", encoding="utf-8")
    manifest = tmp_path / "emergency.json"
    manifest.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-09",
                "expires_at": "2099-12-31",
                "artifacts": [
                    {
                        "package": "cryptography",
                        "version": "46.0.7",
                        "filename": "cryptography-46.0.7.whl",
                        "url": "https://files.pythonhosted.org/packages/example/cryptography-46.0.7.whl",
                        "sha256": "b" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    observed_find_links: list[Path | None] = []

    def fake_install_from_proxy(**kwargs: object) -> None:
        find_links_dir = kwargs["find_links_dir"]
        observed_find_links.append(None if find_links_dir is None else Path(find_links_dir))
        if find_links_dir is None:
            raise RuntimeError("proxy miss")

    def fake_stage_emergency_wheels(**kwargs: object) -> list[Path]:
        wheelhouse_dir = Path(kwargs["wheelhouse_dir"])
        destination = wheelhouse_dir / "cryptography-46.0.7.whl"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"wheel-bytes")
        return [destination]

    monkeypatch.setattr(installer, "install_from_proxy", fake_install_from_proxy)
    monkeypatch.setattr(installer, "stage_emergency_wheels", fake_stage_emergency_wheels)

    installer.install_from_proxy_with_emergency_fallback(
        python_executable="python",
        requirement_files=[requirements],
        constraints_file=None,
        index_url=APPROVED_PROXY_URL,
        trusted_host=None,
        emergency_wheelhouse_dir=tmp_path / "wheelhouse",
        emergency_wheel_manifest=manifest,
    )

    assert observed_find_links == [None, tmp_path / "wheelhouse"]


def test_build_pip_download_command_fails_when_constraints_file_is_missing(
    tmp_path: Path,
) -> None:
    missing_constraints = tmp_path / "missing-constraints.txt"

    with pytest.raises(FileNotFoundError, match="Constraints file not found"):
        installer.build_pip_download_command(
            python_executable="python",
            requirement_file=tmp_path / "requirements.txt",
            wheelhouse_dir=tmp_path / "wheelhouse",
            constraints_file=missing_constraints,
            index_url=APPROVED_PROXY_URL,
            trusted_host=None,
        )


def test_is_virtualenv_python_detects_virtualenv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Result:
        stdout = json.dumps({"prefix": "/tmp/.venv", "base_prefix": "/usr/local"})

    monkeypatch.setattr(installer.subprocess, "run", lambda *a, **k: Result())

    assert installer.is_virtualenv_python("python") is True


def test_is_virtualenv_python_wraps_probe_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_called_process_error(*args: object, **kwargs: object) -> object:
        raise subprocess.CalledProcessError(returncode=1, cmd=["python", "-c", "probe"])

    monkeypatch.setattr(installer.subprocess, "run", raise_called_process_error)

    with pytest.raises(RuntimeError, match="Unable to probe virtualenv state"):
        installer.is_virtualenv_python("python")


def test_run_command_wraps_subprocess_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=list(args[0]) if args else [],
            returncode=1,
            stdout="",
            stderr="pip stderr here",
        )

    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="Command failed: python -m pip") as excinfo:
        installer.run_command(["python", "-m", "pip"])
    assert "pip stderr here" in str(excinfo.value)


def test_main_fails_when_virtualenv_is_required(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("openai==2.29.0\n", encoding="utf-8")
    monkeypatch.setattr(installer, "DEFAULT_REQUIREMENTS_FILE", requirements)
    monkeypatch.setattr(installer, "DEFAULT_DEV_REQUIREMENTS_FILE", tmp_path / "missing-dev.txt")
    monkeypatch.setattr(installer, "DEFAULT_TEST_REQUIREMENTS_FILE", tmp_path / "missing-test.txt")
    monkeypatch.setattr(installer, "DEFAULT_CONSTRAINTS_FILE", constraints)
    monkeypatch.setattr(installer, "is_virtualenv_python", lambda python_executable: False)
    monkeypatch.setenv(installer.APPROVED_INDEX_ENV_VAR, APPROVED_PROXY_URL)

    result = installer.main(
        [
            "--requirements-file",
            str(requirements),
            "--require-virtualenv",
        ]
    )

    assert result == 1
    assert (
        "refusing to install packages with a non-virtualenv interpreter" in capsys.readouterr().out
    )


def test_collect_startup_hook_failure_lines_uses_guard_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_command: list[str] = []

    class Result:
        returncode = 1
        stdout = "ERROR: unexpected executable Python startup hook (.pth) detected.\n- /tmp/hook.pth:1 :: import os\n"
        stderr = ""

    def fake_run(command: list[str], **kwargs: object) -> Result:
        observed_command[:] = command
        return Result()

    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    failure_lines = installer.collect_startup_hook_failure_lines(
        guard_script=Path("/tmp/check_python_startup_hooks.py"),
        python_executable="python",
    )

    assert observed_command == [
        "python",
        "-S",
        "/tmp/check_python_startup_hooks.py",
        "--python-executable",
        "python",
    ]
    assert failure_lines == [
        "ERROR: unexpected executable Python startup hook (.pth) detected.",
        "- /tmp/hook.pth:1 :: import os",
    ]


def test_main_runs_download_install_and_static_guard_without_pip_self_upgrade(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    wheelhouse_dir = tmp_path / "wheelhouse"
    guard_script = tmp_path / "check_python_startup_hooks.py"
    guard_script.write_text("# test guard\n", encoding="utf-8")
    observed_commands: list[list[str]] = []
    observed_guard_python: list[str] = []

    @contextmanager
    def fake_staging_environment(target_python: str) -> str:
        assert target_python == "python"
        yield "staging-python"

    monkeypatch.setattr(
        installer, "run_command", lambda command: observed_commands.append(list(command))
    )
    monkeypatch.setattr(
        installer,
        "collect_startup_hook_failure_lines",
        lambda **kwargs: observed_guard_python.append(kwargs["python_executable"]) or [],
    )
    monkeypatch.setattr(installer, "staged_python_environment", fake_staging_environment)
    monkeypatch.setenv(installer.APPROVED_INDEX_ENV_VAR, APPROVED_PROXY_URL)

    result = installer.main(
        [
            "--python-executable",
            "python",
            "--requirements-file",
            str(requirements),
            "--wheelhouse-dir",
            str(wheelhouse_dir),
            "--guard-script",
            str(guard_script),
        ]
    )

    assert result == 0
    download_command = observed_commands[0]
    assert download_command[:4] == ["python", "-m", "pip", "download"]
    assert "--only-binary" in download_command
    assert ":all:" in download_command
    assert "--dest" in download_command
    assert str(wheelhouse_dir) in download_command
    assert "--requirement" in download_command
    assert str(requirements) in download_command
    assert "--index-url" in download_command
    assert APPROVED_PROXY_URL in download_command
    assert "--constraint" in download_command
    assert str(installer.DEFAULT_CONSTRAINTS_FILE) in download_command

    staging_install_command = observed_commands[1]
    assert staging_install_command[:4] == ["staging-python", "-m", "pip", "install"]
    assert "--no-index" in staging_install_command
    assert "--find-links" in staging_install_command
    assert str(wheelhouse_dir) in staging_install_command
    assert "--constraint" in staging_install_command
    assert str(installer.DEFAULT_CONSTRAINTS_FILE) in staging_install_command

    install_command = observed_commands[2]
    assert install_command[:4] == ["python", "-m", "pip", "install"]
    assert "--no-index" in install_command
    assert "--find-links" in install_command
    assert str(wheelhouse_dir) in install_command
    assert "--constraint" in install_command
    assert str(installer.DEFAULT_CONSTRAINTS_FILE) in install_command
    assert observed_guard_python == ["staging-python"]


def test_main_runs_optional_pip_upgrade_only_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    wheelhouse_dir = tmp_path / "wheelhouse"
    observed_commands: list[list[str]] = []

    @contextmanager
    def fake_staging_environment(target_python: str) -> str:
        yield "staging-python"

    monkeypatch.setattr(
        installer, "run_command", lambda command: observed_commands.append(list(command))
    )
    monkeypatch.setattr(installer, "collect_startup_hook_failure_lines", lambda **kwargs: [])
    monkeypatch.setattr(installer, "staged_python_environment", fake_staging_environment)
    monkeypatch.setenv(installer.APPROVED_INDEX_ENV_VAR, APPROVED_PROXY_URL)

    result = installer.main(
        [
            "--python-executable",
            "python",
            "--requirements-file",
            str(requirements),
            "--wheelhouse-dir",
            str(wheelhouse_dir),
            "--upgrade-pip",
        ]
    )

    assert result == 0
    assert observed_commands[0] == [
        "python",
        "-m",
        "pip",
        "install",
        "--upgrade",
        "pip",
        "--index-url",
        APPROVED_PROXY_URL,
    ]


def test_main_fails_when_static_startup_hook_scan_finds_malicious_pth(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    wheelhouse_dir = tmp_path / "wheelhouse"
    guard_script = tmp_path / "check_python_startup_hooks.py"
    guard_script.write_text("# test guard\n", encoding="utf-8")
    observed_commands: list[list[str]] = []

    @contextmanager
    def fake_staging_environment(target_python: str) -> str:
        yield "staging-python"

    monkeypatch.setattr(
        installer, "run_command", lambda command: observed_commands.append(list(command))
    )
    monkeypatch.setattr(
        installer,
        "collect_startup_hook_failure_lines",
        lambda **kwargs: [
            "ERROR: unexpected executable Python startup hook (.pth) detected.",
            "- /tmp/litellm_init.pth:1 :: import os",
        ],
    )
    monkeypatch.setattr(installer, "staged_python_environment", fake_staging_environment)
    monkeypatch.setenv(installer.APPROVED_INDEX_ENV_VAR, APPROVED_PROXY_URL)

    result = installer.main(
        [
            "--python-executable",
            "python",
            "--requirements-file",
            str(requirements),
            "--wheelhouse-dir",
            str(wheelhouse_dir),
            "--guard-script",
            str(guard_script),
        ]
    )

    assert result == 1
    assert "litellm_init.pth:1 :: import os" in capsys.readouterr().out
    assert observed_commands[0][:4] == ["python", "-m", "pip", "download"]
    assert observed_commands[1][:4] == ["staging-python", "-m", "pip", "install"]
    assert not any(
        command[:4] == ["python", "-m", "pip", "install"] for command in observed_commands[2:]
    )


def test_main_reports_missing_requirements_file_cleanly(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing_requirements = tmp_path / "missing-requirements.txt"

    result = installer.main(
        [
            "--requirements-file",
            str(missing_requirements),
            "--index-url",
            APPROVED_PROXY_URL,
        ]
    )

    assert result == 1
    assert (
        f"ERROR: locked install failed: Requirements file not found: {missing_requirements}"
        in capsys.readouterr().out
    )


def test_main_reports_missing_constraints_file_cleanly(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    missing_constraints = tmp_path / "missing-constraints.txt"

    result = installer.main(
        [
            "--requirements-file",
            str(requirements),
            "--constraints-file",
            str(missing_constraints),
            "--index-url",
            APPROVED_PROXY_URL,
        ]
    )

    assert result == 1
    assert (
        f"ERROR: locked install failed: Constraints file not found: {missing_constraints}"
        in capsys.readouterr().out
    )


def test_main_reports_guard_runtime_error_cleanly(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    wheelhouse_dir = tmp_path / "wheelhouse"
    guard_script = tmp_path / "missing-guard.py"

    monkeypatch.setattr(installer, "run_command", lambda command: None)
    monkeypatch.setattr(
        installer,
        "collect_startup_hook_failure_lines",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("guard subprocess failed")),
    )
    monkeypatch.setenv(installer.APPROVED_INDEX_ENV_VAR, APPROVED_PROXY_URL)

    result = installer.main(
        [
            "--python-executable",
            "python",
            "--requirements-file",
            str(requirements),
            "--wheelhouse-dir",
            str(wheelhouse_dir),
            "--guard-script",
            str(guard_script),
        ]
    )

    assert result == 1
    assert "ERROR: locked install failed: guard subprocess failed" in capsys.readouterr().out


def test_main_runs_direct_proxy_install_and_static_guard(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    guard_script = tmp_path / "check_python_startup_hooks.py"
    guard_script.write_text("# test guard\n", encoding="utf-8")
    observed_commands: list[list[str]] = []
    observed_guard_python: list[str] = []

    @contextmanager
    def fake_staging_environment(target_python: str) -> str:
        assert target_python == "python"
        yield "staging-python"

    monkeypatch.setattr(
        installer, "run_command", lambda command: observed_commands.append(list(command))
    )
    monkeypatch.setattr(
        installer,
        "collect_startup_hook_failure_lines",
        lambda **kwargs: observed_guard_python.append(kwargs["python_executable"]) or [],
    )
    monkeypatch.setattr(installer, "staged_python_environment", fake_staging_environment)
    monkeypatch.setenv(installer.APPROVED_INDEX_ENV_VAR, APPROVED_PROXY_URL)

    result = installer.main(
        [
            "--python-executable",
            "python",
            "--requirements-file",
            str(requirements),
            "--guard-script",
            str(guard_script),
            "--install-mode",
            "direct-proxy",
        ]
    )

    assert result == 0
    assert len(observed_commands) == 2

    staging_install_command = observed_commands[0]
    assert staging_install_command[:4] == ["staging-python", "-m", "pip", "install"]
    assert "--no-cache-dir" in staging_install_command
    assert "--index-url" in staging_install_command
    assert APPROVED_PROXY_URL in staging_install_command
    assert str(requirements) in staging_install_command
    assert "--constraint" in staging_install_command
    assert str(installer.DEFAULT_CONSTRAINTS_FILE) in staging_install_command

    install_command = observed_commands[1]
    assert install_command[:4] == ["python", "-m", "pip", "install"]
    assert "--no-cache-dir" in install_command
    assert "--index-url" in install_command
    assert APPROVED_PROXY_URL in install_command
    assert str(requirements) in install_command
    assert observed_guard_python == ["staging-python"]


def test_main_direct_proxy_docker_layer_cache_skips_no_cache_dir_on_target_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    guard_script = tmp_path / "check_python_startup_hooks.py"
    guard_script.write_text("# test guard\n", encoding="utf-8")
    observed_commands: list[list[str]] = []

    @contextmanager
    def fake_staging_environment(target_python: str) -> str:
        yield "staging-python"

    monkeypatch.setattr(
        installer, "run_command", lambda command: observed_commands.append(list(command))
    )
    monkeypatch.setattr(
        installer,
        "collect_startup_hook_failure_lines",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(installer, "staged_python_environment", fake_staging_environment)
    monkeypatch.setenv(installer.APPROVED_INDEX_ENV_VAR, APPROVED_PROXY_URL)
    monkeypatch.setenv(installer.DOCKER_PIP_LAYER_CACHE_ENV, "1")

    result = installer.main(
        [
            "--python-executable",
            "python",
            "--requirements-file",
            str(requirements),
            "--guard-script",
            str(guard_script),
            "--install-mode",
            "direct-proxy",
        ]
    )

    assert result == 0
    assert len(observed_commands) == 2
    assert "--no-cache-dir" in observed_commands[0]
    assert "--no-cache-dir" not in observed_commands[1]


def test_main_direct_proxy_docker_single_pass_runs_one_target_install_and_guard(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    guard_script = tmp_path / "check_python_startup_hooks.py"
    guard_script.write_text("# test guard\n", encoding="utf-8")
    observed_commands: list[list[str]] = []
    observed_guard_python: list[str] = []

    monkeypatch.setattr(
        installer, "run_command", lambda command: observed_commands.append(list(command))
    )
    monkeypatch.setattr(
        installer,
        "collect_startup_hook_failure_lines",
        lambda **kwargs: observed_guard_python.append(kwargs["python_executable"]) or [],
    )
    monkeypatch.setenv(installer.APPROVED_INDEX_ENV_VAR, APPROVED_PROXY_URL)
    monkeypatch.setenv(installer.DOCKER_SINGLE_PASS_LOCKED_INSTALL_ENV, "1")
    monkeypatch.setenv(installer.DOCKER_PIP_LAYER_CACHE_ENV, "1")

    result = installer.main(
        [
            "--python-executable",
            "python",
            "--requirements-file",
            str(requirements),
            "--guard-script",
            str(guard_script),
            "--install-mode",
            "direct-proxy",
        ]
    )

    assert result == 0
    assert len(observed_commands) == 1
    assert observed_commands[0][:4] == ["python", "-m", "pip", "install"]
    assert "--no-cache-dir" not in observed_commands[0]
    assert observed_guard_python == ["python"]


def test_main_direct_proxy_docker_single_pass_rejects_multiple_requirement_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    dev_requirements = tmp_path / "requirements-dev.txt"
    dev_requirements.write_text("pytest\n", encoding="utf-8")
    guard_script = tmp_path / "check_python_startup_hooks.py"
    guard_script.write_text("# test guard\n", encoding="utf-8")

    def _fail_run_command(_command: list[str]) -> None:
        pytest.fail("run_command should not run when single-pass preflight rejects")

    monkeypatch.setattr(installer, "run_command", _fail_run_command)
    monkeypatch.setenv(installer.APPROVED_INDEX_ENV_VAR, APPROVED_PROXY_URL)
    monkeypatch.setenv(installer.DOCKER_SINGLE_PASS_LOCKED_INSTALL_ENV, "1")

    result = installer.main(
        [
            "--python-executable",
            "python",
            "--requirements-file",
            str(requirements),
            "--dev-requirements-file",
            str(dev_requirements),
            "--install-dev",
            "--guard-script",
            str(guard_script),
            "--install-mode",
            "direct-proxy",
        ]
    )

    assert result == 1
    assert "exactly one requirements file" in capsys.readouterr().err


def test_main_direct_proxy_mode_stops_before_target_install_when_guard_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")
    guard_script = tmp_path / "check_python_startup_hooks.py"
    guard_script.write_text("# test guard\n", encoding="utf-8")
    observed_commands: list[list[str]] = []

    @contextmanager
    def fake_staging_environment(target_python: str) -> str:
        yield "staging-python"

    monkeypatch.setattr(
        installer, "run_command", lambda command: observed_commands.append(list(command))
    )
    monkeypatch.setattr(
        installer,
        "collect_startup_hook_failure_lines",
        lambda **kwargs: [
            "ERROR: unexpected executable Python startup hook (.pth) detected.",
            "- /tmp/litellm_init.pth:1 :: import os",
        ],
    )
    monkeypatch.setattr(installer, "staged_python_environment", fake_staging_environment)
    monkeypatch.setenv(installer.APPROVED_INDEX_ENV_VAR, APPROVED_PROXY_URL)

    result = installer.main(
        [
            "--python-executable",
            "python",
            "--requirements-file",
            str(requirements),
            "--guard-script",
            str(guard_script),
            "--install-mode",
            "direct-proxy",
        ]
    )

    assert result == 1
    assert "litellm_init.pth:1 :: import os" in capsys.readouterr().out
    assert len(observed_commands) == 1
    assert observed_commands[0][:4] == ["staging-python", "-m", "pip", "install"]


def test_main_reports_missing_private_proxy_cleanly(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")

    result = installer.main(["--requirements-file", str(requirements)])

    assert result == 1
    assert "Approved Python package proxy is required" in capsys.readouterr().out


def test_main_rejects_mixing_explicit_profile_with_legacy_flags(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("openai==2.29.0\n", encoding="utf-8")

    result = installer.main(
        [
            "--requirements-file",
            str(requirements),
            "--requirements-profile",
            "runtime-test",
            "--install-test",
            "--index-url",
            APPROVED_PROXY_URL,
        ]
    )

    assert result == 1
    assert "requirements-profile cannot be combined" in capsys.readouterr().out


def test_run_dependency_floor_preflight_checks_each_floor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_commands: list[list[str]] = []
    monkeypatch.setattr(
        installer,
        "load_dependency_security_floors",
        lambda: {"cryptography": "46.0.7", "pillow": "12.2.0"},
    )
    monkeypatch.setattr(
        installer,
        "run_command",
        lambda command: observed_commands.append(list(command)),
    )

    installer.run_dependency_floor_preflight(
        python_executable="python",
        index_url=APPROVED_PROXY_URL,
        trusted_host="packages.example.internal",
        emergency_wheel_manifest=None,
    )

    assert len(observed_commands) == 2
    for command in observed_commands:
        assert command[:4] == ["python", "-m", "pip", "download"]
        assert "--no-deps" in command
        assert "--index-url" in command
        assert APPROVED_PROXY_URL in command
        assert "--trusted-host" in command
        assert "--dest" in command


def test_run_dependency_floor_preflight_allows_exact_emergency_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "emergency.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "expires_at": "2099-12-31",
                "artifacts": [
                    {
                        "package": "cryptography",
                        "version": "46.0.7",
                        "filename": "cryptography-46.0.7.whl",
                        "url": "https://files.pythonhosted.org/packages/example/cryptography-46.0.7.whl",
                        "sha256": "b" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        installer,
        "load_dependency_security_floors",
        lambda: {"cryptography": "46.0.7"},
    )
    monkeypatch.setattr(
        installer,
        "_download_with_sha256",
        lambda **kwargs: Path(kwargs["destination"]).write_bytes(b"wheel-bytes"),
    )

    def fail_run_command(_command: list[str]) -> None:
        raise _resolver_miss_runtimeerror_like_run_command("cryptography", "46.0.7")

    monkeypatch.setattr(installer, "run_command", fail_run_command)

    installer.run_dependency_floor_preflight(
        python_executable="python",
        index_url=APPROVED_PROXY_URL,
        trusted_host=None,
        emergency_wheel_manifest=manifest,
    )


def test_run_dependency_floor_preflight_rejects_non_resolver_failure_even_with_emergency(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "emergency.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "expires_at": "2099-12-31",
                "artifacts": [
                    {
                        "package": "cryptography",
                        "version": "46.0.7",
                        "filename": "cryptography-46.0.7.whl",
                        "url": "https://files.pythonhosted.org/packages/example/cryptography-46.0.7.whl",
                        "sha256": "b" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        installer,
        "load_dependency_security_floors",
        lambda: {"cryptography": "46.0.7"},
    )

    def non_resolver_failure(_command: list[str]) -> None:
        raise RuntimeError("Command failed: python -m pip download: SSL certificate verify failed")

    monkeypatch.setattr(installer, "run_command", non_resolver_failure)

    with pytest.raises(RuntimeError, match="Dependency floor preflight failed"):
        installer.run_dependency_floor_preflight(
            python_executable="python",
            index_url=APPROVED_PROXY_URL,
            trusted_host=None,
            emergency_wheel_manifest=manifest,
        )


def test_run_dependency_floor_preflight_verifies_emergency_artifact_download(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "emergency.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "expires_at": "2099-12-31",
                "artifacts": [
                    {
                        "package": "cryptography",
                        "version": "46.0.7",
                        "filename": "cryptography-46.0.7.whl",
                        "url": "https://files.pythonhosted.org/packages/example/cryptography-46.0.7.whl",
                        "sha256": "b" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        installer,
        "load_dependency_security_floors",
        lambda: {"cryptography": "46.0.7"},
    )
    observed_downloads: list[tuple[str, str]] = []

    def resolver_miss(_command: list[str]) -> None:
        raise _resolver_miss_runtimeerror_like_run_command("cryptography", "46.0.7")

    def fake_download(*, url: str, destination: Path, expected_sha256: str) -> None:
        observed_downloads.append((url, expected_sha256))
        destination.write_bytes(b"wheel-bytes")

    monkeypatch.setattr(installer, "run_command", resolver_miss)
    monkeypatch.setattr(installer, "_download_with_sha256", fake_download)

    installer.run_dependency_floor_preflight(
        python_executable="python",
        index_url=APPROVED_PROXY_URL,
        trusted_host=None,
        emergency_wheel_manifest=manifest,
    )

    assert observed_downloads == [
        ("https://files.pythonhosted.org/packages/example/cryptography-46.0.7.whl", "b" * 64)
    ]


def test_main_preflight_only_skips_requirements_file_resolution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing_requirements = tmp_path / "missing-requirements.txt"
    preflight_called = {"count": 0}

    def fake_preflight(**_kwargs: object) -> None:
        preflight_called["count"] += 1

    monkeypatch.setattr(installer, "run_dependency_floor_preflight", fake_preflight)

    result = installer.main(
        [
            "--requirements-file",
            str(missing_requirements),
            "--index-url",
            APPROVED_PROXY_URL,
            "--preflight-only",
        ]
    )

    assert result == 0
    assert preflight_called["count"] == 1
