"""Deterministic security and compatibility tests for strict runner dispatch."""

from __future__ import annotations

from contextlib import nullcontext
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
from typing import Any

import pytest

from scripts.orchestration import experiment_contract
from scripts.orchestration import experiment_runner_dispatch as dispatch

_DIGEST = "sha256:" + "a" * 64
_OTHER_DIGEST = "sha256:" + "b" * 64


def _run_isolated_git(
    git: str,
    *args: str,
    cwd: Path,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_PREFIX", "GIT_COMMON_DIR"):
        env.pop(key, None)
    return subprocess.run(
        [git, *args],
        cwd=cwd,
        check=True,
        capture_output=capture_output,
        text=True,
        env=env,
    )


def _image() -> dispatch.ImageReference:
    return dispatch.ImageReference(name="pulseplate/experiment-runner:local", digest=_DIGEST)


def _results(backend: str, value: bool = True) -> dict[str, bool | None]:
    results = dispatch._base_probe_results(backend)
    for key in dispatch.REQUIRED_PROBE_KEYS[backend]:
        results[key] = value
    return results


def _probe(
    backend: str,
    *,
    strict: bool,
    reason: str = "runtime_cli_missing",
) -> dispatch.BackendProbe:
    return dispatch.BackendProbe(
        backend=backend,
        host_platform="macos_arm64",
        guest_platform="linux_arm64",
        runtime_version="1.1.0" if backend == "apple-container" else "29.6.1",
        image_digest=_DIGEST,
        isolation_method=dispatch._isolation_method(backend),
        probe_results=_results(backend, strict),
        blocking_reasons=() if strict else (reason,),
    )


def _packet(*, network_budget: int = 0) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "experiment_id": "strict-mac-test",
        "runner_mode": "oracle_only_governance_reviewer",
        "decision_question": "Verify strict Mac execution",
        "task_class": "Infrastructure",
        "mutable_candidate_surface": ["scripts/orchestration/experiment_runner.py"],
        "immutable_oracles": [{"command": "git --version", "expected_signal": "pass"}],
        "budgets": {
            "wall_clock_seconds": 30,
            "retry_budget": 1,
            "max_changed_files": 1,
            "network_budget": network_budget,
            "benchmark_budget": 1,
            "test_budget": 1,
            "stop_condition": "Stop on any failure.",
        },
        "metrics": {
            "primary": "strict_isolation",
            "secondary": [],
            "baseline_reference": "current-main",
            "acceptance_threshold": "strict_improvement",
        },
        "negative_controls": [
            "network remains unavailable",
            "shared worktree remains unchanged",
        ],
        "promotion_target": "audit_artifact",
    }


def _legacy_result() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "experiment_id": "legacy-result",
        "runner_mode": "candidate_patch",
        "candidate_patch": "candidate.patch",
        "status": "accepted",
        "failure_class": None,
        "mutated_paths": ["core/rag/allowed.py"],
        "oracle_results": [],
        "budget_observations": {},
        "shared_tree_untouched": True,
        "promotion_ready": False,
        "contribution_kind": "none",
        "coauthor_required": False,
        "coauthor_reason": "",
    }


def _accepted_oracle_result() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "experiment_id": "strict-mac-test",
        "runner_mode": "oracle_only_governance_reviewer",
        "candidate_patch": "oracle_only_governance_reviewer",
        "status": "accepted",
        "failure_class": None,
        "mutated_paths": [],
        "oracle_results": [],
        "budget_observations": {},
        "shared_tree_untouched": True,
        "promotion_ready": False,
        "contribution_kind": "oracle_review",
        "coauthor_required": True,
        "coauthor_reason": "Material oracle review shaped the commit decision.",
    }


def test_image_reference_requires_immutable_digest() -> None:
    assert dispatch.parse_image_reference(f"runner:local@{_DIGEST}").digest == _DIGEST

    with pytest.raises(ValueError, match="immutable"):
        dispatch.parse_image_reference("runner:latest")
    with pytest.raises(ValueError, match="immutable"):
        dispatch.parse_image_reference(f"runner:local@sha256:{'A' * 64}")


def test_auto_prefers_strict_apple_without_probing_docker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(dispatch.platform, "system", lambda: "Darwin")

    def fake_probe(backend: str, _image: dispatch.ImageReference) -> dispatch.BackendProbe:
        calls.append(backend)
        return _probe(backend, strict=True)

    monkeypatch.setattr(dispatch, "probe_backend", fake_probe)

    selected, attempts = dispatch.select_backend("auto", _image())

    assert selected is not None and selected.backend == "apple-container"
    assert [attempt.backend for attempt in attempts] == ["apple-container"]
    assert calls == ["apple-container"]


def test_auto_uses_docker_only_after_apple_preflight_rejects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(dispatch.platform, "system", lambda: "Darwin")

    def fake_probe(backend: str, _image: dispatch.ImageReference) -> dispatch.BackendProbe:
        calls.append(backend)
        return _probe(backend, strict=backend == "docker")

    monkeypatch.setattr(dispatch, "probe_backend", fake_probe)

    selected, _attempts = dispatch.select_backend("auto", _image())

    assert selected is not None and selected.backend == "docker"
    assert calls == ["apple-container", "docker"]


def test_explicit_backend_never_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_probe(backend: str, _image: dispatch.ImageReference) -> dispatch.BackendProbe:
        calls.append(backend)
        return _probe(backend, strict=False)

    monkeypatch.setattr(dispatch, "probe_backend", fake_probe)

    selected, attempts = dispatch.select_backend("apple-container", _image())

    assert selected is None
    assert [probe.backend for probe in attempts] == ["apple-container"]
    assert calls == ["apple-container"]


def test_native_linux_is_not_strict_without_filesystem_containment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dispatch.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        dispatch,
        "probe_backend",
        lambda backend, _image: _probe(
            backend,
            strict=False,
            reason="filesystem_isolation_unavailable",
        ),
    )

    selected, attempts = dispatch.select_backend("auto", _image())

    assert selected is None
    assert [probe.backend for probe in attempts] == ["native-linux"]
    assert attempts[0].blocking_reasons == ("filesystem_isolation_unavailable",)


@pytest.mark.parametrize("backend", ["apple-container", "docker"])
def test_container_argv_enforces_exact_mount_and_network_contract(
    tmp_path: Path,
    backend: str,
) -> None:
    cli = "/usr/local/bin/container" if backend == "apple-container" else "/usr/local/bin/docker"
    argv = dispatch._container_run_argv(
        cli=cli,
        backend=backend,
        image_ref=_DIGEST,
        container_name="pp-er-test",
        result_volume="pp-er-result-test",
        repository=tmp_path / "repo",
        input_dir=tmp_path / "input",
        apple_network="strict-network" if backend == "apple-container" else None,
        command=[dispatch.CONTAINER_PYTHON, "--version"],
    )
    joined = " ".join(argv)

    assert "--read-only" in argv
    assert "65532:65532" in argv
    assert dispatch.CONTAINER_REPO in joined
    assert dispatch.CONTAINER_INPUT in joined
    assert "pp-er-result-test" in joined
    assert dispatch.CONTAINER_RESULT_DIR in joined
    assert "$HOME" not in joined
    assert "SSH_AUTH_SOCK" not in joined
    assert "docker.sock" not in joined
    assert "--cap-add" not in argv
    assert "SYS_ADMIN" not in argv
    if backend == "docker":
        assert argv[argv.index("--network") + 1] == "none"
        assert argv[argv.index("--pull") + 1] == "never"
        assert any(value.startswith("/tmp:rw,noexec,nosuid,size=") for value in argv)
    else:
        assert "--no-dns" in argv
        assert "type=tmpfs,destination=/tmp,size=1G,mode=1777" in argv
        assert "--tmpfs" not in argv


def test_subprocess_rejects_non_absolute_binary(tmp_path: Path) -> None:
    with pytest.raises(dispatch.DispatchError, match="runtime_cli_missing"):
        dispatch._run(["docker", "info"], cwd=tmp_path)


def test_apple_probe_rejects_unsupported_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dispatch.platform, "system", lambda: "Linux")

    probe = dispatch.probe_backend("apple-container", _image())

    assert probe.blocking_reasons == ("unsupported_host",)
    assert probe.strict is False


def test_probe_missing_cli_is_capability_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dispatch.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(dispatch.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(dispatch, "_resolve_cli", lambda _name: None)

    probe = dispatch.probe_backend("apple-container", _image())

    assert probe.blocking_reasons == ("runtime_cli_missing",)


def test_probe_distinguishes_apple_kernel_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dispatch.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(dispatch.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(dispatch, "_resolve_cli", lambda _name: "/usr/local/bin/container")
    monkeypatch.setattr(dispatch, "_runtime_version", lambda _cli: "1.1.0")
    monkeypatch.setattr(
        dispatch,
        "_runtime_readiness_reason",
        lambda _cli, _backend: "apple_kernel_not_configured",
    )

    probe = dispatch.probe_backend("apple-container", _image())

    assert probe.blocking_reasons == ("apple_kernel_not_configured",)


def test_image_digest_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dispatch,
        "_run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps([{"Id": _OTHER_DIGEST}]), stderr=""
        ),
    )

    with pytest.raises(dispatch.DispatchError, match="image_digest_drift"):
        dispatch._inspect_image("/usr/local/bin/docker", "docker", _image())


def test_capability_artifact_is_strict_and_sanitized() -> None:
    artifact = _probe("apple-container", strict=True).to_artifact()
    serialized = json.dumps(artifact)

    assert artifact["authority"] == "evidence_only"
    assert artifact["sanitized"] is True
    assert artifact["strict_isolation"] is True
    assert "username" not in serialized
    assert "hostname" not in serialized
    assert "/Users/" not in serialized
    assert "TOKEN" not in serialized
    assert "stdout" not in serialized
    assert "stderr" not in serialized


def test_capability_artifact_rejects_extra_fields() -> None:
    artifact = _probe("docker", strict=True).to_artifact()
    artifact["raw_output"] = "secret"

    with pytest.raises(ValueError, match="unexpected"):
        dispatch.validate_capability_artifact(artifact)


def test_capability_artifact_rejects_unknown_blocker() -> None:
    artifact = _probe(
        "apple-container",
        strict=False,
        reason="host_listener_unavailable",
    ).to_artifact()
    artifact["blocking_reasons"] = ["unknown_listener_failure"]

    with pytest.raises(ValueError, match="blocker code"):
        dispatch.validate_capability_artifact(artifact)


def test_existing_v1_capability_artifact_remains_valid() -> None:
    artifact = _probe(
        "apple-container",
        strict=False,
        reason="network_gateway_unavailable",
    ).to_artifact()

    assert dispatch.validate_capability_artifact(artifact) == artifact


def test_snapshot_applies_tracked_diff_and_leaves_source_unchanged(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    git = dispatch._resolve_cli("git")
    assert git is not None
    _run_isolated_git(git, "init", "--quiet", cwd=source)
    _run_isolated_git(git, "config", "user.email", "test@example.invalid", cwd=source)
    _run_isolated_git(git, "config", "user.name", "Test", cwd=source)
    tracked = source / "tracked.txt"
    tracked.write_text("before\n", encoding="utf-8")
    _run_isolated_git(git, "add", "tracked.txt", cwd=source)
    _run_isolated_git(git, "commit", "--quiet", "-m", "init", cwd=source)
    tracked.write_text("after\n", encoding="utf-8")
    before_status = _run_isolated_git(
        git, "status", "--short", cwd=source, capture_output=True
    ).stdout

    snapshot = tmp_path / "snapshot"
    tracked_diff = dispatch._create_snapshot(source, snapshot)

    assert tracked_diff
    assert (snapshot / "tracked.txt").read_text(encoding="utf-8") == "after\n"
    assert (snapshot / ".git").is_dir()
    assert "gitdir:" not in (snapshot / ".git" / "HEAD").read_text(encoding="utf-8")
    after_status = _run_isolated_git(
        git, "status", "--short", cwd=source, capture_output=True
    ).stdout
    assert after_status == before_status


def test_snapshot_preserves_staged_new_file_as_tracked(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    git = dispatch._resolve_cli("git")
    assert git is not None
    _run_isolated_git(git, "init", "--quiet", cwd=source)
    _run_isolated_git(git, "config", "user.email", "test@example.invalid", cwd=source)
    _run_isolated_git(git, "config", "user.name", "Test", cwd=source)
    (source / "base.txt").write_text("base\n", encoding="utf-8")
    _run_isolated_git(git, "add", "base.txt", cwd=source)
    _run_isolated_git(git, "commit", "--quiet", "-m", "init", cwd=source)
    added = source / "added.txt"
    added.write_text("new\n", encoding="utf-8")
    _run_isolated_git(git, "add", "added.txt", cwd=source)
    before_status = _run_isolated_git(
        git, "status", "--short", cwd=source, capture_output=True
    ).stdout

    snapshot = tmp_path / "snapshot"
    dispatch._create_snapshot(source, snapshot)

    tracked = _run_isolated_git(
        git, "ls-files", "--error-unmatch", "added.txt", cwd=snapshot, capture_output=True
    ).stdout
    assert tracked.strip() == "added.txt"
    assert added.read_text(encoding="utf-8") == "new\n"
    after_status = _run_isolated_git(
        git, "status", "--short", cwd=source, capture_output=True
    ).stdout
    assert after_status == before_status


def test_repo_local_input_rejects_absolute_and_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="repository-relative"):
        dispatch._require_repo_local_file(str(tmp_path / "packet.json"), suffix=".json")
    with pytest.raises((FileNotFoundError, ValueError)):
        dispatch._require_repo_local_file("../packet.json", suffix=".json")


def test_legacy_result_v1_remains_valid_without_backend_provenance() -> None:
    validated = experiment_contract.validate_experiment_result(_legacy_result())

    assert "execution_backend" not in validated


def test_result_v1_accepts_strict_backend_provenance() -> None:
    result = _legacy_result()
    result["execution_backend"] = dispatch._execution_backend_payload(
        _probe("docker", strict=True), passed=True
    )

    validated = experiment_contract.validate_experiment_result(result)

    assert validated["execution_backend"]["network_isolation"] == (
        "docker_network_none_plus_linux_unshare"
    )


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        (
            {"network_isolation": "linux_unshare"},
            "network_isolation is inconsistent",
        ),
        ({"preflight_status": "failed"}, "Accepted experiment results require"),
        ({"guest_platform": "linux_unsupported"}, "Accepted experiment results require"),
    ],
)
def test_result_v1_rejects_impossible_backend_provenance(
    updates: dict[str, str],
    message: str,
) -> None:
    result = _legacy_result()
    provenance = dispatch._execution_backend_payload(_probe("docker", strict=True), passed=True)
    result["execution_backend"] = {**provenance, **updates}

    with pytest.raises(ValueError, match=message):
        experiment_contract.validate_experiment_result(result)


def test_capability_mismatch_requires_failed_preflight() -> None:
    result = _legacy_result()
    result["status"] = "rejected"
    result["failure_class"] = "capability_mismatch"
    result["execution_backend"] = dispatch._execution_backend_payload(
        _probe("docker", strict=True), passed=True
    )

    with pytest.raises(ValueError, match="failed backend preflight"):
        experiment_contract.validate_experiment_result(result)


def test_capability_mismatch_is_non_retryable_and_preserves_zero_network() -> None:
    packet = _packet(network_budget=0)
    probe = _probe("apple-container", strict=False)

    result = dispatch._capability_mismatch_result(packet, _image(), probe)

    assert result["failure_class"] == "capability_mismatch"
    assert result["budget_observations"]["attempts"] == 0
    assert result["budget_observations"]["retries_consumed"] == 0
    assert result["budget_observations"]["configured_budgets"]["network_budget"] == 0
    assert result["execution_backend"]["preflight_status"] == "failed"
    assert result["contribution_kind"] == "none"
    assert result["coauthor_required"] is False
    assert result["coauthor_reason"] == ""


def test_result_backend_rejects_mutable_or_invalid_digest() -> None:
    result = _legacy_result()
    result["execution_backend"] = {
        **dispatch._execution_backend_payload(_probe("docker", strict=True), passed=True),
        "image_digest": "runner:latest",
    }

    with pytest.raises(ValueError, match="sha256"):
        experiment_contract.validate_experiment_result(result)


def test_backend_specific_runtime_refs_prevent_apple_digest_pull() -> None:
    image = _image()

    assert image.runtime_ref("apple-container") == f"{image.name}@{image.digest}"
    assert image.runtime_ref("docker") == image.digest


def test_apple_build_registers_exact_local_digest_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    digest = "sha256:" + "a" * 64
    tag = "pulseplate/experiment-runner:test"
    immutable_ref = f"{tag}@{digest}"
    inspect_payload = json.dumps([{"configuration": {"descriptor": {"digest": digest}}}])
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        stdout = inspect_payload if argv[1:3] == ["image", "inspect"] else ""
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    for name in (
        "PULSEPLATE_PYTHON_INDEX_URL",
        "PULSEPLATE_PYTHON_TRUSTED_HOST",
        "PULSEPLATE_PYTHON_NETRC",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(dispatch, "_resolve_cli", lambda _name: "/usr/local/bin/container")
    monkeypatch.setattr(dispatch, "_runtime_readiness_reason", lambda _cli, _backend: None)
    monkeypatch.setattr(dispatch, "_run", fake_run)

    result = dispatch._build_image("apple-container", tag)

    assert result["image"] == immutable_ref
    assert [
        "/usr/local/bin/container",
        "image",
        "tag",
        tag,
        immutable_ref,
    ] in calls
    assert [
        "/usr/local/bin/container",
        "image",
        "inspect",
        immutable_ref,
    ] in calls


def test_backend_probe_uses_explicit_not_applicable_values() -> None:
    docker = _probe("docker", strict=True)
    native = _probe(
        "native-linux",
        strict=False,
        reason="filesystem_isolation_unavailable",
    )

    assert docker.probe_results["outer_host_control"] is None
    assert native.probe_results["source_read_only"] is None
    assert docker.strict is True
    assert native.strict is False
    dispatch.validate_capability_artifact(native.to_artifact())


def test_gateway_is_discovered_from_runtime_metadata() -> None:
    payload = [{"status": {"ipv4Gateway": "192.168.64.1"}}]

    assert dispatch._find_gateway(payload) == "192.168.64.1"


def test_apple_runtime_subnets_use_persistent_default_network_as_exclusion_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(
            argv,
            0,
            json.dumps([{"status": {"ipv4Subnet": "192.168.64.0/24"}}]),
            "",
        )

    monkeypatch.setattr(dispatch, "_run", fake_run)

    subnets = dispatch._discover_apple_runtime_subnets("/usr/local/bin/container")

    assert [str(subnet) for subnet in subnets] == ["192.168.64.0/24"]
    assert calls == [["/usr/local/bin/container", "network", "inspect", "default"]]


def test_apple_runtime_subnet_deduplicates_identical_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = [
        {"status": {"ipv4Subnet": "192.168.64.0/24"}},
        {"configuration": {"ipv4Subnet": "192.168.64.0/24"}},
    ]
    monkeypatch.setattr(
        dispatch,
        "_run",
        lambda argv, **_kwargs: subprocess.CompletedProcess(
            argv,
            0,
            json.dumps(payload),
            "",
        ),
    )

    subnets = dispatch._discover_apple_runtime_subnets("/usr/local/bin/container")

    assert [str(subnet) for subnet in subnets] == ["192.168.64.0/24"]


@pytest.mark.parametrize(
    "payload",
    [
        "not-json",
        json.dumps([{"status": {"ipv4Subnet": "not-a-subnet"}}]),
        json.dumps([{"status": {"ipv4Subnet": "2001:db8::/64"}}]),
        json.dumps([{"status": {"ipv4Subnet": "192.168.64.1/24"}}]),
        json.dumps([{"status": {"ipv4Subnet": 123}}]),
        json.dumps(
            [
                {"status": {"ipv4Subnet": "192.168.64.0/24"}},
                {"status": {"ipv4Subnet": "192.168.65.0/24"}},
            ]
        ),
        json.dumps(
            [
                {"status": {"ipv4Subnet": "192.168.64.0/24"}},
                {"status": {"ipv4Subnet": "192.168.65.1/24"}},
            ]
        ),
        json.dumps([{"status": {}}]),
    ],
)
def test_apple_runtime_subnet_inspection_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    payload: str,
) -> None:
    monkeypatch.setattr(
        dispatch,
        "_run",
        lambda argv, **_kwargs: subprocess.CompletedProcess(
            argv,
            0,
            payload,
            "",
        ),
    )

    with pytest.raises(dispatch.DispatchError, match="network_gateway_unavailable"):
        dispatch._discover_apple_runtime_subnets("/usr/local/bin/container")


def test_apple_runtime_subnet_inspection_rejects_runtime_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dispatch,
        "_run",
        lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 1, "", "not retained"),
    )

    with pytest.raises(dispatch.DispatchError, match="network_gateway_unavailable"):
        dispatch._discover_apple_runtime_subnets("/usr/local/bin/container")


def test_apple_host_bind_address_filters_unsafe_runtime_and_unbindable_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dispatch.socket,
        "gethostname",
        lambda: "local-host",
    )
    monkeypatch.setattr(
        dispatch.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [
            (dispatch.socket.AF_INET, dispatch.socket.SOCK_STREAM, 6, "", ("0.0.0.0", 0)),
            (dispatch.socket.AF_INET, dispatch.socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0)),
            (
                dispatch.socket.AF_INET,
                dispatch.socket.SOCK_STREAM,
                6,
                "",
                ("169.254.10.20", 0),
            ),
            (
                dispatch.socket.AF_INET,
                dispatch.socket.SOCK_STREAM,
                6,
                "",
                ("192.168.64.22", 0),
            ),
            (
                dispatch.socket.AF_INET,
                dispatch.socket.SOCK_STREAM,
                6,
                "",
                ("10.0.0.10", 0),
            ),
            (
                dispatch.socket.AF_INET,
                dispatch.socket.SOCK_STREAM,
                6,
                "",
                ("10.0.0.20", 0),
            ),
            (
                dispatch.socket.AF_INET,
                dispatch.socket.SOCK_STREAM,
                6,
                "",
                ("10.0.0.20", 0),
            ),
            (
                dispatch.socket.AF_INET6,
                dispatch.socket.SOCK_STREAM,
                6,
                "",
                ("2001:db8::1", 0),
            ),
            (
                dispatch.socket.AF_INET,
                dispatch.socket.SOCK_DGRAM,
                17,
                "",
                ("10.0.0.30", 0),
            ),
            (
                dispatch.socket.AF_INET,
                dispatch.socket.SOCK_STREAM,
                6,
                "",
                ("not-an-address", 0),
            ),
        ],
    )
    bind_checks: list[str] = []

    def bindable(address: str) -> bool:
        bind_checks.append(address)
        return address == "10.0.0.20"

    monkeypatch.setattr(dispatch, "_address_is_bindable", bindable)

    selected = dispatch._discover_apple_host_bind_address(
        (dispatch.ipaddress.ip_network("192.168.64.0/24"),)
    )

    assert selected == "10.0.0.20"
    assert set(bind_checks) == {"10.0.0.10", "10.0.0.20"}
    assert bind_checks.count("10.0.0.20") == 1


def test_apple_host_bind_address_requires_one_candidate_without_order_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dispatch.socket, "gethostname", lambda: "local-host")
    monkeypatch.setattr(
        dispatch.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [
            (
                dispatch.socket.AF_INET,
                dispatch.socket.SOCK_STREAM,
                6,
                "",
                ("10.0.0.20", 0),
            ),
            (
                dispatch.socket.AF_INET,
                dispatch.socket.SOCK_STREAM,
                6,
                "",
                ("10.0.0.10", 0),
            ),
        ],
    )
    monkeypatch.setattr(dispatch, "_address_is_bindable", lambda _address: True)

    with pytest.raises(dispatch.DispatchError, match="host_listener_unavailable"):
        dispatch._discover_apple_host_bind_address(())


def test_apple_host_bind_address_rejects_unbindable_only_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dispatch.socket, "gethostname", lambda: "local-host")
    monkeypatch.setattr(
        dispatch.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [
            (
                dispatch.socket.AF_INET,
                dispatch.socket.SOCK_STREAM,
                6,
                "",
                ("10.0.0.20", 0),
            )
        ],
    )
    monkeypatch.setattr(dispatch, "_address_is_bindable", lambda _address: False)

    with pytest.raises(dispatch.DispatchError, match="host_listener_unavailable"):
        dispatch._discover_apple_host_bind_address(())


def test_apple_host_bind_address_normalizes_hostname_resolution_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dispatch.socket, "gethostname", lambda: "local-host")
    monkeypatch.setattr(
        dispatch.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("resolution failed")),
    )

    with pytest.raises(dispatch.DispatchError, match="host_listener_unavailable"):
        dispatch._discover_apple_host_bind_address(())


def test_docker_gateway_preserves_bridge_inspection_without_host_bind_requirement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(
            argv,
            0,
            json.dumps([{"IPAM": {"Config": [{"Gateway": "172.17.0.1"}]}}]),
            "",
        )

    monkeypatch.setattr(dispatch, "_run", fake_run)
    monkeypatch.setattr(
        dispatch,
        "_address_is_bindable",
        lambda _address: (_ for _ in ()).throw(AssertionError("Docker must not host-bind gateway")),
    )

    assert dispatch._discover_gateway("/usr/local/bin/docker", "docker", None) == "172.17.0.1"
    assert calls == [["/usr/local/bin/docker", "network", "inspect", "bridge"]]


def test_apple_canaries_share_exact_listener_address_on_unique_internal_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_subnets = (dispatch.ipaddress.ip_network("192.168.64.0/24"),)
    host_address = "10.0.0.20"
    call_order: list[str] = []
    listener_addresses: list[str | None] = []
    container_calls: list[dict[str, Any]] = []
    container_argvs: list[list[str]] = []
    build_container_argv = dispatch._container_run_argv
    outer_payload = {
        "guest_platform_supported": True,
        "host_reachable": True,
        "dns_blocked": True,
        "direct_ip_blocked": True,
        "source_read_only": True,
        "input_read_only": True,
        "root_read_only": True,
        "result_volume_writable": True,
        "private_tmpfs": True,
    }
    inner_payload = {**outer_payload, "host_reachable": False}
    payloads = iter((outer_payload, inner_payload))

    def discover_subnets(_cli: str) -> tuple[dispatch.ipaddress.IPv4Network, ...]:
        call_order.append("inspect-default-subnet")
        return runtime_subnets

    def discover_host(
        subnets: tuple[dispatch.ipaddress.IPv4Network, ...],
    ) -> str:
        assert subnets == runtime_subnets
        call_order.append("select-host-listener")
        return host_address

    def create_network(_cli: str) -> str:
        call_order.append("create-temporary-network")
        return "unique-internal"

    monkeypatch.setattr(dispatch, "_discover_apple_runtime_subnets", discover_subnets)
    monkeypatch.setattr(dispatch, "_discover_apple_host_bind_address", discover_host)
    monkeypatch.setattr(dispatch, "_create_apple_network", create_network)
    monkeypatch.setattr(dispatch, "_create_result_volume", lambda *_args: "result-volume")
    monkeypatch.setattr(dispatch, "_initialize_result_volume", lambda **_kwargs: True)

    def fake_listener(address: str | None = None) -> nullcontext[tuple[str, int, bool]]:
        listener_addresses.append(address)
        return nullcontext((str(address), 43123, True))

    def capture_container_argv(**kwargs: Any) -> list[str]:
        container_calls.append(dict(kwargs))
        argv = build_container_argv(**kwargs)
        container_argvs.append(argv)
        return argv

    monkeypatch.setattr(dispatch, "_host_listener", fake_listener)
    monkeypatch.setattr(dispatch, "_container_run_argv", capture_container_argv)
    monkeypatch.setattr(
        dispatch,
        "_run",
        lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 0, "", ""),
    )
    monkeypatch.setattr(dispatch, "_parse_canary", lambda _completed: next(payloads))
    monkeypatch.setattr(dispatch, "_cleanup_container", lambda *_args: True)
    monkeypatch.setattr(dispatch, "_cleanup_container_resources", lambda **_kwargs: True)

    results = dispatch._run_container_canary(
        "/usr/local/bin/container",
        "apple-container",
        _image(),
    )

    assert call_order == [
        "inspect-default-subnet",
        "select-host-listener",
        "create-temporary-network",
    ]
    assert listener_addresses == [host_address]
    assert len(container_calls) == 2
    assert all(call["apple_network"] == "unique-internal" for call in container_calls)
    assert all(argv[argv.index("--network") + 1] == "unique-internal" for argv in container_argvs)
    assert all("--no-dns" in argv for argv in container_argvs)
    assert all(f"host = {host_address!r}" in call["command"][-1] for call in container_calls)
    assert results["outer_host_control"] is True
    assert results["inner_host_blocked"] is True


def test_host_listener_normalizes_bind_race(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BindRaceSocket:
        def setsockopt(self, *_args: object) -> None:
            return None

        def bind(self, _address: tuple[str, int]) -> None:
            raise OSError("address changed after discovery")

        def close(self) -> None:
            return None

    monkeypatch.setattr(dispatch.socket, "socket", lambda *_args: BindRaceSocket())

    with pytest.raises(dispatch.DispatchError, match="host_listener_unavailable"):
        with dispatch._host_listener("10.0.0.20"):
            raise AssertionError("listener must not yield after bind race")


def test_explicit_host_listener_normalizes_self_connect_failure_and_cleans_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {"closed": False, "started": False, "joined": False}

    class ListenerSocket:
        def setsockopt(self, *_args: object) -> None:
            return None

        def bind(self, _address: tuple[str, int]) -> None:
            return None

        def listen(self, _backlog: int) -> None:
            return None

        def settimeout(self, _timeout: float) -> None:
            return None

        def getsockname(self) -> tuple[str, int]:
            return ("10.0.0.20", 43123)

        def accept(self) -> tuple[object, tuple[str, int]]:
            raise AssertionError("test thread must not execute listener loop")

        def close(self) -> None:
            state["closed"] = True

    class ListenerThread:
        def start(self) -> None:
            state["started"] = True

        def join(self, *, timeout: int) -> None:
            assert timeout == 1
            state["joined"] = True

    monkeypatch.setattr(dispatch.socket, "socket", lambda *_args: ListenerSocket())
    monkeypatch.setattr(
        dispatch.socket,
        "create_connection",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("self-connect failed")),
    )
    monkeypatch.setattr(
        dispatch.threading,
        "Thread",
        lambda **_kwargs: ListenerThread(),
    )

    with pytest.raises(dispatch.DispatchError, match="host_listener_unavailable"):
        with dispatch._host_listener("10.0.0.20"):
            raise AssertionError("listener must not yield after self-connect failure")

    assert state == {"closed": True, "started": True, "joined": True}


def test_default_listener_preserves_native_and_docker_bind_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BindFailureSocket:
        def setsockopt(self, *_args: object) -> None:
            return None

        def bind(self, _address: tuple[str, int]) -> None:
            raise OSError("legacy bind failure")

        def close(self) -> None:
            return None

    monkeypatch.setattr(dispatch, "_discover_host_bind_address", lambda: "10.0.0.20")
    monkeypatch.setattr(dispatch.socket, "socket", lambda *_args: BindFailureSocket())

    with pytest.raises(OSError, match="legacy bind failure"):
        with dispatch._host_listener():
            raise AssertionError("listener must not yield after bind failure")


def test_default_listener_preserves_native_and_docker_self_connect_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dispatch, "_discover_host_bind_address", lambda: "127.0.0.1")
    monkeypatch.setattr(
        dispatch.socket,
        "create_connection",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("legacy self-connect failure")),
    )

    with pytest.raises(OSError, match="legacy self-connect failure"):
        with dispatch._host_listener():
            raise AssertionError("listener must not yield after self-connect failure")


def test_host_listener_blocker_is_closed_and_address_is_not_persisted() -> None:
    probe = dispatch._failed_probe("apple-container", "host_listener_unavailable")
    artifact = probe.to_artifact()

    assert artifact["blocking_reasons"] == ["host_listener_unavailable"]
    assert "10.0.0.20" not in json.dumps(artifact, sort_keys=True)


def test_probe_preserves_host_listener_blocker_without_host_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dispatch.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(dispatch.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(dispatch, "_resolve_cli", lambda _name: "/usr/local/bin/container")
    monkeypatch.setattr(dispatch, "_runtime_version", lambda _cli: "1.1.0")
    monkeypatch.setattr(dispatch, "_runtime_readiness_reason", lambda *_args: None)
    monkeypatch.setattr(dispatch, "_inspect_image", lambda *_args: _DIGEST)
    monkeypatch.setattr(
        dispatch,
        "_run_container_canary",
        lambda *_args: (_ for _ in ()).throw(dispatch.DispatchError("host_listener_unavailable")),
    )

    artifact = dispatch.probe_backend("apple-container", _image()).to_artifact()
    serialized = json.dumps(artifact, sort_keys=True)

    assert artifact["blocking_reasons"] == ["host_listener_unavailable"]
    assert artifact["strict_isolation"] is False
    assert "10.0.0.20" not in serialized


def test_apple_volume_uses_supported_bounded_size_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(dispatch.uuid, "uuid4", lambda: type("U", (), {"hex": "a" * 32})())
    monkeypatch.setattr(dispatch, "_run", fake_run)

    dispatch._create_result_volume("/usr/local/bin/container", "apple-container")

    assert calls == [
        [
            "/usr/local/bin/container",
            "volume",
            "create",
            "-s",
            dispatch.RESULT_VOLUME_SIZE,
            "pp-er-result-aaaaaaaaaaaa",
        ]
    ]


def test_docker_volume_is_bounded_tmpfs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(dispatch.uuid, "uuid4", lambda: type("U", (), {"hex": "b" * 32})())
    monkeypatch.setattr(dispatch, "_run", fake_run)

    dispatch._create_result_volume("/usr/local/bin/docker", "docker")

    assert dispatch.RESULT_VOLUME_SIZE.lower() == f"{dispatch.MAX_RESULT_BYTES // (1024 * 1024)}m"
    assert calls == [
        [
            "/usr/local/bin/docker",
            "volume",
            "create",
            "--driver",
            "local",
            "--opt",
            "type=tmpfs",
            "--opt",
            "device=tmpfs",
            "--opt",
            f"o=size={dispatch.RESULT_VOLUME_SIZE.lower()},mode=0700",
            "pp-er-result-bbbbbbbbbbbb",
        ]
    ]


def test_capability_validator_matches_platform_and_isolation_schema() -> None:
    artifact = _probe("apple-container", strict=True).to_artifact()

    invalid_host = {**artifact, "host_platform": "windows_amd64"}
    with pytest.raises(ValueError, match="host_platform"):
        dispatch.validate_capability_artifact(invalid_host)

    invalid_isolation = {**artifact, "isolation_method": "linux_unshare"}
    with pytest.raises(ValueError, match="isolation_method"):
        dispatch.validate_capability_artifact(invalid_isolation)

    schema_path = (
        dispatch.REPO_ROOT
        / "docs/orchestration/contracts/experiment_runner_backend_capability.v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    mapped_backends = {
        rule["if"]["properties"]["backend"]["const"]: rule["then"]["properties"][
            "isolation_method"
        ]["const"]
        for rule in schema["allOf"]
    }
    assert mapped_backends == {
        "native-linux": "linux_unshare",
        "apple-container": "apple_internal_no_dns_plus_linux_unshare",
        "docker": "docker_network_none_plus_linux_unshare",
    }
    schema_blockers = set(schema["properties"]["blocking_reasons"]["items"]["enum"])
    assert schema_blockers == set(dispatch.BLOCKER_CODES)


def test_host_listener_marks_successful_positive_control_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dispatch, "_discover_host_bind_address", lambda: "127.0.0.1")
    monkeypatch.setattr(
        dispatch.socket, "create_connection", lambda *_args, **_kwargs: nullcontext()
    )

    with dispatch._host_listener() as (address, port, ready):
        assert address == "127.0.0.1"
        assert port > 0
        assert ready is True


def test_host_bind_address_is_exact_non_loopback_ipv4(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dispatch.socket, "gethostname", lambda: "local-host")
    monkeypatch.setattr(
        dispatch.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [
            (dispatch.socket.AF_INET, dispatch.socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0)),
            (
                dispatch.socket.AF_INET,
                dispatch.socket.SOCK_STREAM,
                6,
                "",
                ("192.168.100.100", 0),
            ),
        ],
    )
    monkeypatch.setattr(
        dispatch,
        "_address_is_bindable",
        lambda address: address == "192.168.100.100",
    )

    assert dispatch._discover_host_bind_address() == "192.168.100.100"


def test_probe_cli_requires_immutable_image() -> None:
    with pytest.raises(SystemExit):
        dispatch._parse_args(["probe", "--backend", "auto", "--output", "probe.json"])


def test_run_parser_attribution_defaults_remain_non_material() -> None:
    args = dispatch._parse_args(
        [
            "run",
            "--packet",
            "packet.json",
            "--image",
            f"pulseplate/experiment-runner:local@{_DIGEST}",
            "--output",
            "result.json",
        ]
    )

    assert args.contribution_kind == "none"
    assert args.coauthor_required is False
    assert args.coauthor_reason == ""


def test_run_help_describes_material_oracle_only_attribution_boundary(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as caught:
        dispatch._parse_args(["run", "--help"])

    assert caught.value.code == 0
    help_text = capsys.readouterr().out
    normalized_help = " ".join(help_text.split())
    assert "--contribution-kind" in help_text
    assert "--coauthor-required" in help_text
    assert "--coauthor-reason" in help_text
    assert "oracle-only governance evidence" in normalized_help
    assert "candidate-patch mode rejects material/non-default attribution" in normalized_help
    assert "accepted oracle-only result" in normalized_help
    assert "if it materially shapes the engineering decision" in normalized_help


def test_artifact_root_rejects_symlinked_components(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)

    with pytest.raises(ValueError, match="symlinked components"):
        dispatch._resolve_local_output("result.json", root=linked)


def test_recursive_result_redaction_removes_paths_and_secret_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_API_TOKEN", "aaaaaaaa")
    payload = {
        "nested": [
            f"failure at {dispatch.REPO_ROOT}/file.py",
            "fixture=aaaaaaaa",
        ]
    }

    redacted = dispatch._redact_result_value(payload)
    serialized = json.dumps(redacted)

    assert str(dispatch.REPO_ROOT) not in serialized
    assert "aaaaaaaa" not in serialized
    assert "<redacted>" in serialized


def test_sanitize_result_rejects_malformed_oracle_before_transform() -> None:
    result = _legacy_result()
    result["oracle_results"] = [None]

    with pytest.raises(dispatch.DispatchError, match="result_validation_failed"):
        dispatch._sanitize_result(result, _probe("apple-container", strict=True))


def test_sanitize_accepted_result_preserves_material_attribution() -> None:
    sanitized = dispatch._sanitize_result(
        _accepted_oracle_result(),
        _probe("apple-container", strict=True),
        requested_contribution_kind="oracle_review",
        requested_coauthor_required=True,
        requested_coauthor_reason=("Material oracle review shaped the commit decision."),
    )

    assert sanitized["contribution_kind"] == "oracle_review"
    assert sanitized["coauthor_required"] is True
    assert sanitized["coauthor_reason"] == ("Material oracle review shaped the commit decision.")


def test_sanitize_rejects_attributed_acceptance_for_default_request() -> None:
    with pytest.raises(dispatch.DispatchError, match="result_validation_failed"):
        dispatch._sanitize_result(
            _accepted_oracle_result(),
            _probe("apple-container", strict=True),
        )


def test_sanitize_rejects_altered_attribution_for_material_request() -> None:
    result = _accepted_oracle_result()
    result["contribution_kind"] = "commit_decision"
    result["coauthor_reason"] = "Altered contribution provenance."

    with pytest.raises(dispatch.DispatchError, match="result_validation_failed"):
        dispatch._sanitize_result(
            result,
            _probe("apple-container", strict=True),
            requested_contribution_kind="oracle_review",
            requested_coauthor_required=True,
            requested_coauthor_reason=("Material oracle review shaped the commit decision."),
        )


def test_sanitize_accepts_rejected_result_with_canonical_attribution_reset() -> None:
    result = _accepted_oracle_result()
    result.update(
        {
            "status": "rejected",
            "failure_class": "policy_violation",
            "contribution_kind": "none",
            "coauthor_required": False,
            "coauthor_reason": "",
        }
    )

    sanitized = dispatch._sanitize_result(
        result,
        _probe("apple-container", strict=True),
        requested_contribution_kind="oracle_review",
        requested_coauthor_required=True,
        requested_coauthor_reason=("Material oracle review shaped the commit decision."),
    )

    assert sanitized["status"] == "rejected"
    assert sanitized["contribution_kind"] == "none"
    assert sanitized["coauthor_required"] is False
    assert sanitized["coauthor_reason"] == ""


def test_collector_is_nofollow_regular_file_and_size_bounded() -> None:
    assert "O_NOFOLLOW" in dispatch._COLLECTOR_CODE
    assert "S_ISREG" in dispatch._COLLECTOR_CODE
    assert str(dispatch.MAX_RESULT_BYTES) in dispatch._COLLECTOR_CODE


def test_post_preflight_failure_is_validated_infra_flake() -> None:
    packet = experiment_contract.validate_experiment_packet(_packet())
    result = dispatch._infra_flake_result(
        packet,
        _image(),
        _probe("apple-container", strict=True),
        "runner_execution_failed",
    )

    assert result["failure_class"] == "infra_flake"
    assert result["budget_observations"]["runner_error"] == "runner_execution_failed"
    assert result["budget_observations"]["configured_budgets"]["network_budget"] == 0
    assert result["contribution_kind"] == "none"
    assert result["coauthor_required"] is False
    assert result["coauthor_reason"] == ""


def test_pre_run_image_drift_is_non_retryable_capability_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(_packet()), encoding="utf-8")
    output_path = tmp_path / "result.json"
    probe = _probe("apple-container", strict=True)
    written: dict[str, Any] = {}

    monkeypatch.setattr(
        dispatch,
        "_parse_args",
        lambda _argv: SimpleNamespace(
            command="run",
            backend="apple-container",
            packet="packet.json",
            candidate_patch=None,
            image=f"pulseplate/experiment-runner:local@{_DIGEST}",
            output="result.json",
        ),
    )
    monkeypatch.setattr(dispatch, "_require_repo_local_file", lambda *_args, **_kwargs: packet_path)
    monkeypatch.setattr(dispatch, "_resolve_local_output", lambda *_args, **_kwargs: output_path)
    monkeypatch.setattr(dispatch, "select_backend", lambda *_args: (probe, [probe]))

    def fail_before_start(**_kwargs: object) -> dict[str, Any]:
        raise dispatch.PreRunCapabilityError("image_digest_drift")

    monkeypatch.setattr(dispatch, "_invoke_container_runner", fail_before_start)
    monkeypatch.setattr(
        dispatch, "_atomic_write_json", lambda _path, payload: written.update(payload)
    )

    assert dispatch.main([]) == 1
    assert written["failure_class"] == "capability_mismatch"
    assert written["budget_observations"]["runner_error"] == "image_digest_drift"
    assert written["budget_observations"]["attempts"] == 0
    assert written["budget_observations"]["configured_budgets"]["network_budget"] == 0


def test_run_preserves_host_listener_blocker_and_resets_rejected_attribution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(_packet()), encoding="utf-8")
    output_path = tmp_path / "result.json"
    probe = dispatch._failed_probe("apple-container", "host_listener_unavailable")
    written: dict[str, Any] = {}

    monkeypatch.setattr(
        dispatch,
        "_parse_args",
        lambda _argv: SimpleNamespace(
            command="run",
            backend="apple-container",
            packet="packet.json",
            candidate_patch=None,
            image=f"pulseplate/experiment-runner:local@{_DIGEST}",
            output="result.json",
            contribution_kind="oracle_review",
            coauthor_required=True,
            coauthor_reason="Material oracle review would shape the commit decision.",
        ),
    )
    monkeypatch.setattr(dispatch, "_require_repo_local_file", lambda *_args, **_kwargs: packet_path)
    monkeypatch.setattr(dispatch, "_resolve_local_output", lambda *_args, **_kwargs: output_path)
    monkeypatch.setattr(dispatch, "select_backend", lambda *_args: (None, [probe]))
    monkeypatch.setattr(
        dispatch,
        "_atomic_write_json",
        lambda _path, payload: written.update(payload),
    )

    assert dispatch.main([]) == 1
    assert written["failure_class"] == "capability_mismatch"
    assert written["budget_observations"]["runner_error"] == "host_listener_unavailable"
    assert written["execution_backend"]["preflight_status"] == "failed"
    assert written["contribution_kind"] == "none"
    assert written["coauthor_required"] is False
    assert written["coauthor_reason"] == ""
    assert "10.0.0.20" not in json.dumps(written, sort_keys=True)


def test_main_normalizes_material_attribution_before_strict_dispatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(_packet()), encoding="utf-8")
    output_path = tmp_path / "result.json"
    probe = _probe("apple-container", strict=True)
    invocation: dict[str, Any] = {}
    reason = "Material oracle review shaped the commit decision."

    monkeypatch.setattr(
        dispatch,
        "_parse_args",
        lambda _argv: SimpleNamespace(
            command="run",
            backend="apple-container",
            packet="packet.json",
            candidate_patch=None,
            image=f"pulseplate/experiment-runner:local@{_DIGEST}",
            output="result.json",
            contribution_kind="oracle_review",
            coauthor_required=True,
            coauthor_reason=f"  {reason}  ",
        ),
    )
    monkeypatch.setattr(dispatch, "_require_repo_local_file", lambda *_args, **_kwargs: packet_path)
    monkeypatch.setattr(dispatch, "_resolve_local_output", lambda *_args, **_kwargs: output_path)
    monkeypatch.setattr(dispatch, "select_backend", lambda *_args: (probe, [probe]))

    def capture_invocation(**kwargs: Any) -> dict[str, Any]:
        invocation.update(kwargs)
        return _accepted_oracle_result()

    monkeypatch.setattr(dispatch, "_invoke_container_runner", capture_invocation)
    monkeypatch.setattr(dispatch, "_atomic_write_json", lambda *_args, **_kwargs: None)

    assert dispatch.main([]) == 0
    assert invocation["contribution_kind"] == "oracle_review"
    assert invocation["coauthor_required"] is True
    assert invocation["coauthor_reason"] == reason


@pytest.mark.parametrize("backend", ["apple-container", "docker"])
def test_container_runner_attribution_argv_has_backend_parity_and_default_omission(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    backend: str,
) -> None:
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(_packet()), encoding="utf-8")
    captured_commands: list[list[str]] = []

    monkeypatch.setattr(dispatch, "_resolve_cli", lambda _name: "/usr/local/bin/runtime")
    monkeypatch.setattr(
        dispatch,
        "_create_snapshot",
        lambda _root, destination: destination.mkdir() or "",
    )
    monkeypatch.setattr(dispatch, "_create_apple_network", lambda _cli: "run-network")
    monkeypatch.setattr(dispatch, "_inspect_image", lambda *_args: _DIGEST)
    monkeypatch.setattr(dispatch, "_create_result_volume", lambda *_args: "result-volume")
    monkeypatch.setattr(dispatch, "_initialize_result_volume", lambda **_kwargs: True)

    def capture_container_argv(**kwargs: Any) -> list[str]:
        captured_commands.append(list(kwargs["command"]))
        return ["/usr/local/bin/runtime", "run"]

    monkeypatch.setattr(dispatch, "_container_run_argv", capture_container_argv)
    monkeypatch.setattr(
        dispatch,
        "_run",
        lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 0, "", ""),
    )
    monkeypatch.setattr(dispatch, "_cleanup_container", lambda *_args: True)
    monkeypatch.setattr(dispatch, "_collect_result_volume", lambda **_kwargs: {})
    monkeypatch.setattr(dispatch, "_cleanup_container_resources", lambda **_kwargs: True)
    monkeypatch.setattr(
        dispatch,
        "_sanitize_result",
        lambda payload, _probe, **_kwargs: payload,
    )

    reason = "Material oracle review shaped the commit decision."
    dispatch._invoke_container_runner(
        probe=_probe(backend, strict=True),
        image=_image(),
        packet_path=packet_path,
        candidate_patch=None,
        output_name="result.json",
        contribution_kind="oracle_review",
        coauthor_required=True,
        coauthor_reason=reason,
    )

    assert captured_commands == [
        [
            dispatch.CONTAINER_PYTHON,
            f"{dispatch.CONTAINER_REPO}/scripts/orchestration/experiment_runner.py",
            "--packet",
            f"{dispatch.CONTAINER_INPUT}/packet.json",
            "--output",
            "result.json",
            "--contribution-kind",
            "oracle_review",
            "--coauthor-required",
            "--coauthor-reason",
            reason,
        ]
    ]

    captured_commands.clear()
    dispatch._invoke_container_runner(
        probe=_probe(backend, strict=True),
        image=_image(),
        packet_path=packet_path,
        candidate_patch=None,
        output_name="default-oracle-result.json",
    )
    default_oracle_command = captured_commands.pop()
    assert "--candidate-patch" not in default_oracle_command
    assert "--contribution-kind" not in default_oracle_command
    assert "--coauthor-required" not in default_oracle_command
    assert "--coauthor-reason" not in default_oracle_command

    candidate_packet = _packet()
    candidate_packet["runner_mode"] = "candidate_patch"
    candidate_packet["mutable_candidate_surface"] = ["core/rag/orchestration.py"]
    packet_path.write_text(json.dumps(candidate_packet), encoding="utf-8")
    candidate_patch = tmp_path / "candidate.patch"
    candidate_patch.write_text("", encoding="utf-8")
    dispatch._invoke_container_runner(
        probe=_probe(backend, strict=True),
        image=_image(),
        packet_path=packet_path,
        candidate_patch=candidate_patch,
        output_name="default-candidate-result.json",
    )
    default_candidate_command = captured_commands.pop()
    assert "--candidate-patch" in default_candidate_command
    assert "--contribution-kind" not in default_candidate_command
    assert "--coauthor-required" not in default_candidate_command
    assert "--coauthor-reason" not in default_candidate_command


@pytest.mark.parametrize("backend", ["apple-container", "docker"])
def test_container_cleanup_forces_delete_after_stop_error(
    monkeypatch: pytest.MonkeyPatch,
    backend: str,
) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        if argv[1] == "stop":
            raise dispatch.DispatchError("probe_execution_failed")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(dispatch, "_run", fake_run)

    assert dispatch._cleanup_container("/usr/local/bin/runtime", backend, "run-id")
    assert calls[0][1:4] == ["stop", "--time", "1"]
    expected_delete = "delete" if backend == "apple-container" else "rm"
    assert calls[1][1:3] == [expected_delete, "--force"]


def test_nonzero_network_budget_fails_before_backend_selection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(_packet(network_budget=1)), encoding="utf-8")
    output_path = tmp_path / "result.json"
    written: dict[str, Any] = {}
    monkeypatch.setattr(dispatch.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        dispatch,
        "_parse_args",
        lambda _argv: SimpleNamespace(
            command="run",
            backend="auto",
            packet="packet.json",
            candidate_patch=None,
            image=f"pulseplate/experiment-runner:local@{_DIGEST}",
            output="result.json",
        ),
    )
    monkeypatch.setattr(dispatch, "_require_repo_local_file", lambda *_args, **_kwargs: packet_path)
    monkeypatch.setattr(dispatch, "_resolve_local_output", lambda *_args, **_kwargs: output_path)
    monkeypatch.setattr(
        dispatch,
        "select_backend",
        lambda *_args: (_ for _ in ()).throw(AssertionError("backend probe must not run")),
    )
    monkeypatch.setattr(
        dispatch, "_atomic_write_json", lambda _path, payload: written.update(payload)
    )

    assert dispatch.main([]) == 1
    assert written["failure_class"] == "capability_mismatch"
    assert written["budget_observations"]["configured_budgets"]["network_budget"] == 1
    assert written["budget_observations"]["runner_error"] == ("strict_network_budget_required")
    assert written["execution_backend"]["preflight_status"] == "failed"


@pytest.mark.parametrize(
    ("packet_mode", "contribution_kind", "coauthor_required", "coauthor_reason", "message"),
    [
        (
            "oracle_only_governance_reviewer",
            "oracle_review",
            False,
            "",
            "material contribution_kind requires coauthor_required",
        ),
        (
            "candidate_patch",
            "oracle_review",
            True,
            "Material oracle review shaped the commit decision.",
            "supported only in oracle-only mode",
        ),
        (
            "oracle_only_governance_reviewer",
            "none",
            "true",
            "",
            "coauthor_required must be a boolean",
        ),
    ],
)
def test_invalid_or_candidate_attribution_rejects_before_backend_selection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    packet_mode: str,
    contribution_kind: str,
    coauthor_required: Any,
    coauthor_reason: str,
    message: str,
) -> None:
    packet = _packet()
    packet["runner_mode"] = packet_mode
    if packet_mode == "candidate_patch":
        packet["mutable_candidate_surface"] = ["core/rag/orchestration.py"]
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    candidate_patch = tmp_path / "candidate.patch"
    candidate_patch.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        dispatch,
        "_parse_args",
        lambda _argv: SimpleNamespace(
            command="run",
            backend="auto",
            packet="packet.json",
            candidate_patch="candidate.patch" if packet_mode == "candidate_patch" else None,
            image=f"pulseplate/experiment-runner:local@{_DIGEST}",
            output="result.json",
            contribution_kind=contribution_kind,
            coauthor_required=coauthor_required,
            coauthor_reason=coauthor_reason,
        ),
    )

    def resolve_input(raw: str, **_kwargs: object) -> Path:
        return candidate_patch if raw == "candidate.patch" else packet_path

    monkeypatch.setattr(dispatch, "_require_repo_local_file", resolve_input)
    monkeypatch.setattr(
        dispatch,
        "_resolve_local_output",
        lambda *_args, **_kwargs: tmp_path / "result.json",
    )
    monkeypatch.setattr(
        dispatch,
        "select_backend",
        lambda *_args: (_ for _ in ()).throw(AssertionError("backend probe must not run")),
    )

    assert dispatch.main([]) == 2
    assert message in capsys.readouterr().err


def test_probe_cleanup_failure_overrides_original_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dispatch,
        "_discover_apple_runtime_subnets",
        lambda _cli: (dispatch.ipaddress.ip_network("192.168.64.0/24"),),
    )
    monkeypatch.setattr(
        dispatch,
        "_discover_apple_host_bind_address",
        lambda _subnets: "10.0.0.20",
    )
    monkeypatch.setattr(dispatch, "_create_apple_network", lambda _cli: "probe-network")
    monkeypatch.setattr(
        dispatch,
        "_create_result_volume",
        lambda *_args: (_ for _ in ()).throw(dispatch.DispatchError("result_volume_failed")),
    )
    monkeypatch.setattr(dispatch, "_delete_apple_network", lambda *_args: False)

    with pytest.raises(dispatch.DispatchError, match="container_cleanup_failed") as caught:
        dispatch._run_container_canary("/usr/local/bin/container", "apple-container", _image())

    assert isinstance(caught.value.__cause__, dispatch.DispatchError)
    assert caught.value.__cause__.code == "result_volume_failed"


def test_pre_run_cleanup_failure_overrides_capability_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(_packet()), encoding="utf-8")
    monkeypatch.setattr(dispatch, "_resolve_cli", lambda _name: "/usr/local/bin/container")
    monkeypatch.setattr(
        dispatch,
        "_create_snapshot",
        lambda _root, destination: destination.mkdir() or "",
    )
    monkeypatch.setattr(dispatch, "_create_apple_network", lambda _cli: "run-network")
    monkeypatch.setattr(
        dispatch,
        "_inspect_image",
        lambda *_args: (_ for _ in ()).throw(dispatch.DispatchError("image_digest_drift")),
    )
    monkeypatch.setattr(dispatch, "_delete_apple_network", lambda *_args: False)

    with pytest.raises(dispatch.DispatchError, match="container_cleanup_failed") as caught:
        dispatch._invoke_container_runner(
            probe=_probe("apple-container", strict=True),
            image=_image(),
            packet_path=packet_path,
            candidate_patch=None,
            output_name="result.json",
        )

    assert isinstance(caught.value.__cause__, dispatch.PreRunCapabilityError)
    assert caught.value.__cause__.code == "image_digest_drift"


def test_missing_runtime_after_probe_is_pre_run_capability_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(dispatch, "_resolve_cli", lambda _name: None)

    with pytest.raises(dispatch.PreRunCapabilityError, match="runtime_cli_missing"):
        dispatch._invoke_container_runner(
            probe=_probe("apple-container", strict=True),
            image=_image(),
            packet_path=tmp_path / "packet.json",
            candidate_patch=None,
            output_name="result.json",
        )


def test_post_start_cleanup_failure_overrides_execution_exception(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(_packet()), encoding="utf-8")
    monkeypatch.setattr(dispatch, "_resolve_cli", lambda _name: "/usr/local/bin/container")
    monkeypatch.setattr(
        dispatch,
        "_create_snapshot",
        lambda _root, destination: destination.mkdir() or "",
    )
    monkeypatch.setattr(dispatch, "_create_apple_network", lambda _cli: "run-network")
    monkeypatch.setattr(dispatch, "_inspect_image", lambda *_args: _DIGEST)
    monkeypatch.setattr(dispatch, "_create_result_volume", lambda *_args: "result-volume")
    monkeypatch.setattr(dispatch, "_initialize_result_volume", lambda **_kwargs: True)
    monkeypatch.setattr(
        dispatch,
        "_run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            dispatch.DispatchError("runner_execution_failed")
        ),
    )
    monkeypatch.setattr(dispatch, "_cleanup_container", lambda *_args: True)
    monkeypatch.setattr(dispatch, "_delete_result_volume", lambda *_args: False)
    monkeypatch.setattr(dispatch, "_delete_apple_network", lambda *_args: True)

    with pytest.raises(dispatch.DispatchError, match="container_cleanup_failed") as caught:
        dispatch._invoke_container_runner(
            probe=_probe("apple-container", strict=True),
            image=_image(),
            packet_path=packet_path,
            candidate_patch=None,
            output_name="result.json",
        )

    assert isinstance(caught.value.__cause__, dispatch.DispatchError)
    assert caught.value.__cause__.code == "runner_execution_failed"
