"""Focused contracts for the governed private-proxy lock compiler."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts.ci import check_python_dependency_surfaces as surfaces
from scripts.ci import compile_locked_python_requirements as compiler

REPO_ROOT = Path(__file__).resolve().parents[1]
APPROVED_INDEX = "https://packages.pulseplate.app/root/pulseplate/+simple/"


def _surface(profile: str) -> surfaces.DependencySurface:
    return next(
        surface
        for surface in surfaces.compiled_dependency_surfaces()
        if surface.compile_profile == profile
    )


def _write_test_profile(root: Path) -> surfaces.DependencySurface:
    surface = _surface("test")
    (root / "requirements.txt").write_text("fastapi==0.138.1\n", encoding="utf-8")
    (root / "requirements-test.in").write_text(
        "-c requirements.txt\ncoverage~=7.15.1\nfaker~=40.31.0\npytest==9.1.3\n",
        encoding="utf-8",
    )
    (root / "requirements-test.txt").write_text(
        surfaces.render_governed_lock_header(surface)
        + "coverage[toml]==7.15.0\nfaker==40.28.1\npytest==9.1.3\n",
        encoding="utf-8",
    )
    return surface


def _candidate_output_path(command: list[str]) -> Path:
    output_arg = next(item for item in command if item.startswith("--output-file="))
    return Path(output_arg.split("=", 1)[1])


def _successful_resolver(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
    _candidate_output_path(command).write_text(
        "coverage[toml]==7.15.1\nfaker==40.31.0\npytest==9.1.3\n",
        encoding="utf-8",
    )
    return subprocess.CompletedProcess(command, 0, "", "")


def test_compile_registry_is_single_authority_for_every_compiled_surface() -> None:
    registry = compiler._profile_registry()

    assert set(registry) == {
        "runtime",
        "docker-runtime",
        "ci-lite",
        "test",
        "dev",
        "rag-vector",
        "rag-vector-cpu",
        "data",
        "evals",
        "aggregate",
    }
    assert set(registry.values()) == set(surfaces.compiled_dependency_surfaces())
    surfaces.validate_compile_registry()
    for surface in surfaces.compiled_dependency_surfaces():
        if surface.compile_profile != "aggregate":
            assert surface.compile_sources == (surface.source_file,)

    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "requirements-locks: ensure-python-proxy" in makefile
    assert "PULSEPLATE_LOCK_COMPILE_VIA_MAKE=1" in makefile
    assert "$(value LOCK_PROFILES)" in makefile
    assert "$(value UPGRADE_PACKAGES)" in makefile
    assert "$(value GRAPH_CHANGE_PACKAGES)" in makefile
    assert "$(LOCK_PROFILES)" not in makefile
    assert "$(UPGRADE_PACKAGES)" not in makefile
    assert "$(GRAPH_CHANGE_PACKAGES)" not in makefile


def test_governed_header_is_stable_make_only_provenance() -> None:
    surface = _surface("aggregate")

    header = surfaces.render_governed_lock_header(surface)

    assert "# Profile: aggregate" in header
    assert "# Sources: requirements-dev.in, requirements.in" in header
    assert 'LOCK_PROFILES="aggregate" make requirements-locks' in header
    assert "piptools" not in header
    assert "pip-compile" not in header
    assert "PULSEPLATE_PYTHON_INDEX_URL" not in header


def test_make_preserves_lock_request_values_without_evaluating_them(tmp_path: Path) -> None:
    make = shutil.which("make")
    assert make is not None
    marker = tmp_path / "make-expanded-untrusted-input"
    makefile = tmp_path / "Makefile"
    makefile.write_text(
        "override RAW := $(value LOCK_PROFILES)\n"
        "export RAW\n"
        "unexport LOCK_PROFILES\n"
        "show:\n"
        '\t@printf "RAW=<%s>\\n" "$$RAW"\n',
        encoding="utf-8",
    )
    raw_value = f"$(shell touch {marker})"

    result = subprocess.run(  # nosec B603: resolved Make binary and inert temporary fixture (remove-by: 2027-01-31, ref: PR-2134)
        [make, "-s", "-f", str(makefile), "show", f"LOCK_PROFILES={raw_value}"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"RAW=<{raw_value}>\n"
    assert not marker.exists()


def test_profile_and_upgrade_selection_rejects_untrusted_values() -> None:
    assert compiler._parse_profiles("test dev aggregate") == ("test", "dev", "aggregate")
    assert compiler._parse_upgrades("coverage==7.15.1 faker==40.31.0") == {
        "coverage": "7.15.1",
        "faker": "40.31.0",
    }
    assert compiler._parse_graph_changes("Example_Pkg transitive.pkg") == frozenset(
        {"example-pkg", "transitive-pkg"}
    )

    for raw_profiles in (None, "", "test test", "test;touch-pwned"):
        with pytest.raises(RuntimeError):
            compiler._parse_profiles(raw_profiles)
    for raw_upgrade in (
        "pip==26.1.2",
        "coverage[toml]==7.15.1",
        "coverage>=7.15.1",
        "coverage==7.15.1;python_version>'3.11'",
        "coverage@https://example.invalid/coverage.whl",
        "coverage==7.15.1;touch-pwned",
    ):
        with pytest.raises(RuntimeError):
            compiler._parse_upgrades(raw_upgrade)
    for raw_graph_change in ("pip", "name;touch-pwned", "name name"):
        with pytest.raises(RuntimeError):
            compiler._parse_graph_changes(raw_graph_change)


def test_private_proxy_environment_is_canonical_and_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in compiler.AMBIENT_RESOLVER_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("PULSEPLATE_PYTHON_TRUSTED_HOST", raising=False)
    inspected_netrc_paths: list[Path | None] = []

    def inspect_netrc(_host: str, *, netrc_file: Path | None = None) -> None:
        inspected_netrc_paths.append(netrc_file)

    monkeypatch.setattr(
        compiler,
        "basic_auth_from_netrc",
        inspect_netrc,
    )

    child_env = compiler._private_proxy_child_env(
        {"HOME": "/tmp/home", compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX}
    )

    assert child_env["PIP_INDEX_URL"] == APPROVED_INDEX
    assert child_env["PIP_CONFIG_FILE"] == os.devnull
    assert child_env["PIP_NO_INPUT"] == "1"
    assert "PIP_EXTRA_INDEX_URL" not in child_env
    assert inspected_netrc_paths == [Path("/tmp/home/.netrc")]

    with pytest.raises((RuntimeError, ValueError)):
        compiler._private_proxy_child_env(
            {compiler.APPROVED_INDEX_ENV_VAR: "https://pypi.org/simple/"}
        )
    with pytest.raises((RuntimeError, ValueError)):
        credentialed_index = (
            "https://"
            + ":".join(("user", "placeholder"))
            + "@packages.pulseplate.app/root/pulseplate/+simple/"
        )
        compiler._private_proxy_child_env({compiler.APPROVED_INDEX_ENV_VAR: credentialed_index})
    with pytest.raises(RuntimeError, match="PIP_FIND_LINKS"):
        compiler._private_proxy_child_env(
            {
                compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX,
                "PIP_FIND_LINKS": "/tmp/wheels",
            }
        )
    with pytest.raises(RuntimeError, match="does not consume it"):
        compiler._private_proxy_child_env(
            {
                compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX,
                "PULSEPLATE_PYTHON_NETRC": "/tmp/custom.netrc",
            }
        )


def test_private_proxy_environment_rejects_root_netrc_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in compiler.AMBIENT_RESOLVER_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("PULSEPLATE_PYTHON_TRUSTED_HOST", raising=False)

    def reject_root(_host: str, *, netrc_file: Path | None = None) -> None:
        raise ValueError("root_devpi_credentials: root devpi credentials are forbidden")

    monkeypatch.setattr(compiler, "basic_auth_from_netrc", reject_root)

    with pytest.raises(ValueError, match="root_devpi_credentials"):
        compiler._private_proxy_child_env({compiler.APPROVED_INDEX_ENV_VAR: APPROVED_INDEX})


def test_compile_command_uses_module_argv_and_excludes_pip() -> None:
    command = compiler._build_compile_command(
        surface=_surface("test"),
        output_path=Path("requirements-test.txt.candidate"),
        upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
    )

    assert command[:4] == [sys.executable, "-m", "piptools", "compile"]
    assert "--no-allow-unsafe" in command
    assert "--allow-unsafe" not in command
    assert command[command.index("--unsafe-package") + 1] == "pip"
    assert "--no-config" in command
    assert "--no-emit-index-url" in command
    assert "--no-strip-extras" in command
    assert command[-1] == "requirements-test.in"


def test_prepare_lock_is_seeded_validated_and_atomic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _write_test_profile(tmp_path)
    original = (tmp_path / surface.lockfile).read_bytes()
    monkeypatch.setattr(compiler.subprocess, "run", _successful_resolver)

    prepared = compiler._prepare_lock(
        repo_root=tmp_path,
        surface=surface,
        upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
        graph_changes=frozenset(),
        child_env={},
    )

    assert (tmp_path / surface.lockfile).read_bytes() == original
    candidate = prepared.candidate_path.read_text(encoding="utf-8")
    assert candidate.startswith(surfaces.render_governed_lock_header(surface))
    assert "coverage[toml]==7.15.1" in candidate
    assert "faker==40.31.0" in candidate
    prepared.candidate_path.unlink()


def test_candidate_delta_allows_only_exact_reviewed_graph_changes(tmp_path: Path) -> None:
    surface = _write_test_profile(tmp_path)
    baseline = (tmp_path / surface.lockfile).read_text(encoding="utf-8")
    candidate = baseline + "new-direct-package==1.0\n"

    compiler._validate_candidate_delta(
        surface=surface,
        baseline_text=baseline,
        candidate_text=candidate,
        upgrades={},
        graph_changes=frozenset({"new-direct-package"}),
        repo_root=tmp_path,
    )
    with pytest.raises(RuntimeError, match="unused=.*other-package"):
        compiler._validate_candidate_delta(
            surface=surface,
            baseline_text=baseline,
            candidate_text=candidate,
            upgrades={},
            graph_changes=frozenset({"new-direct-package", "other-package"}),
            repo_root=tmp_path,
        )


@pytest.mark.parametrize(
    "candidate_body,match",
    (
        (
            "coverage[toml]==7.15.1\nfaker==40.31.0\npytest==9.2.0\n",
            "unrelated package versions changed",
        ),
        (
            "coverage[toml]==7.15.1\nfaker==40.31.0\npytest==9.1.3\npip==26.1.2\n",
            "must not pin pip",
        ),
        (
            "coverage[toml]==7.15.1\nfaker==40.31.0\n",
            "dependency graph change is not exactly authorized",
        ),
    ),
)
def test_prepare_lock_rejects_unsafe_candidate_without_mutating_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    candidate_body: str,
    match: str,
) -> None:
    surface = _write_test_profile(tmp_path)
    output_path = tmp_path / surface.lockfile
    original = output_path.read_bytes()

    def write_candidate(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        _candidate_output_path(command).write_text(candidate_body, encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(compiler.subprocess, "run", write_candidate)

    with pytest.raises(RuntimeError, match=match):
        compiler._prepare_lock(
            repo_root=tmp_path,
            surface=surface,
            upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
            graph_changes=frozenset(),
            child_env={},
        )
    assert output_path.read_bytes() == original
    assert not tuple(tmp_path.glob(f".{surface.lockfile}.*.candidate"))


def test_failed_resolver_and_source_mutation_leave_output_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _write_test_profile(tmp_path)
    output_path = tmp_path / surface.lockfile
    source_path = tmp_path / surface.compile_sources[0]
    original = output_path.read_bytes()

    def fail(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, "", "resolver failed")

    monkeypatch.setattr(compiler.subprocess, "run", fail)
    with pytest.raises(RuntimeError, match="resolver failed"):
        compiler._prepare_lock(
            repo_root=tmp_path,
            surface=surface,
            upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
            graph_changes=frozenset(),
            child_env={},
        )
    assert output_path.read_bytes() == original

    def mutate_source(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        source_path.write_text(source_path.read_text(encoding="utf-8") + "# changed\n")
        return _successful_resolver(command)

    monkeypatch.setattr(compiler.subprocess, "run", mutate_source)
    with pytest.raises(RuntimeError, match="file changed"):
        compiler._prepare_lock(
            repo_root=tmp_path,
            surface=surface,
            upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
            graph_changes=frozenset(),
            child_env={},
        )
    assert output_path.read_bytes() == original


def test_constraint_identity_change_is_detected_even_when_content_is_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = _write_test_profile(tmp_path)
    constraint_path = tmp_path / "requirements.txt"
    original_constraint = constraint_path.read_bytes()

    def replace_constraint(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        replacement = tmp_path / "replacement.txt"
        replacement.write_bytes(original_constraint)
        replacement.replace(constraint_path)
        return _successful_resolver(command)

    monkeypatch.setattr(compiler.subprocess, "run", replace_constraint)

    with pytest.raises(RuntimeError, match="requirements.txt"):
        compiler._prepare_lock(
            repo_root=tmp_path,
            surface=surface,
            upgrades={"coverage": "7.15.1", "faker": "40.31.0"},
            graph_changes=frozenset(),
            child_env={},
        )


def test_runtime_and_dependent_profiles_require_separate_transactions() -> None:
    with pytest.raises(RuntimeError, match="compiled and committed before"):
        compiler._validate_profile_transaction(
            repo_root=REPO_ROOT,
            profiles=("runtime", "dev", "test"),
            graph_changes=frozenset(),
        )

    compiler._validate_profile_transaction(
        repo_root=REPO_ROOT,
        profiles=("runtime",),
        graph_changes=frozenset(),
    )
    with pytest.raises(RuntimeError, match="exactly one"):
        compiler._validate_profile_transaction(
            repo_root=REPO_ROOT,
            profiles=("dev", "test"),
            graph_changes=frozenset({"example"}),
        )


def test_multi_lock_replacement_rolls_back_on_partial_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected_surfaces = (_surface("test"), _surface("dev"))
    prepared_by_profile: dict[str, compiler.PreparedLock] = {}
    for index, surface in enumerate(selected_surfaces):
        output_path = tmp_path / surface.lockfile
        output_path.write_text(f"baseline-{index}\n", encoding="utf-8")
        candidate_path = tmp_path / f".{surface.lockfile}.candidate"
        candidate_path.write_text(f"candidate-{index}\n", encoding="utf-8")
        prepared_by_profile[str(surface.compile_profile)] = compiler.PreparedLock(
            surface=surface,
            output_path=output_path,
            candidate_path=candidate_path,
            source_snapshots=(),
            output_snapshot=compiler._snapshot(output_path),
            candidate_snapshot=compiler._snapshot(candidate_path),
            baseline_bytes=output_path.read_bytes(),
        )

    monkeypatch.setattr(
        compiler,
        "_profile_registry",
        lambda: {str(surface.compile_profile): surface for surface in selected_surfaces},
    )
    monkeypatch.setattr(compiler, "_private_proxy_child_env", lambda _environment: {})
    monkeypatch.setattr(
        compiler,
        "_prepare_lock",
        lambda **kwargs: prepared_by_profile[str(kwargs["surface"].compile_profile)],
    )
    monkeypatch.setattr(compiler, "_fsync_directory", lambda _path: None)
    real_replace = os.replace
    replacement_count = 0

    def fail_second_replace(source: Path, destination: Path) -> None:
        nonlocal replacement_count
        replacement_count += 1
        if replacement_count == 2:
            raise OSError("simulated second replacement failure")
        real_replace(source, destination)

    monkeypatch.setattr(compiler.os, "replace", fail_second_replace)

    with pytest.raises(RuntimeError, match="rolled back"):
        compiler.compile_selected_profiles(
            repo_root=tmp_path,
            profiles=("test", "dev"),
            upgrades={},
            graph_changes=frozenset(),
            environment={},
        )

    assert (tmp_path / "requirements-test.txt").read_text(encoding="utf-8") == "baseline-0\n"
    assert (tmp_path / "requirements-dev.txt").read_text(encoding="utf-8") == "baseline-1\n"


def test_registry_paths_must_be_regular_non_symlink_files(tmp_path: Path) -> None:
    real_file = tmp_path / "real.in"
    real_file.write_text("example==1.0\n", encoding="utf-8")
    symlink = tmp_path / "requirements-test.in"
    symlink.symlink_to(real_file)

    with pytest.raises(RuntimeError, match="non-symlink"):
        compiler._validated_repo_file(tmp_path, "requirements-test.in")
    with pytest.raises(RuntimeError, match="repo-relative"):
        compiler._validated_repo_file(tmp_path, "../requirements-test.in")


def test_source_manifest_rejects_direct_urls_and_unowned_directives(tmp_path: Path) -> None:
    source = tmp_path / "requirements-test.in"
    source.write_text(
        "example @ https://example.invalid/example.whl\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="Direct URL requirements are forbidden"):
        compiler._validate_source_manifest(tmp_path, source)

    source.write_text("--find-links /tmp/wheels\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Unsupported resolver directive"):
        compiler._validate_source_manifest(tmp_path, source)

    cpu_index = "--extra-index-url https://download.pytorch.org/whl/cpu"
    source.write_text(f"{cpu_index}\n", encoding="utf-8")
    assert (
        compiler._validate_source_manifest(
            tmp_path,
            source,
            allow_directives=(cpu_index,),
        )
        == ()
    )


def test_direct_helper_invocation_requires_make_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(compiler.MAKE_AUTHORITY_ENV, raising=False)

    with pytest.raises(RuntimeError, match="make requirements-locks"):
        compiler.main()
