"""Adapter/ownership regressions for the separate real Linux runtime experiment."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any

import pytest
import yaml

from scripts.ci import check_staging_postgres_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]


def selected_fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = json.loads((ROOT / "deploy/postgres-pgvector/image-manifest.json").read_text())
    # This is a renderer adapter fixture, not native integration success evidence.
    source = yaml.safe_load((ROOT / "deploy/docker-compose.staging.yaml").read_text())["services"][
        "postgres"
    ]
    rendered = {
        "services": {
            "postgres": {
                "image": source["image"],
                "platform": source["platform"],
                "command": source["command"],
                "environment": {"PGDATA": manifest["compose_pgdata"]},
                "volumes": [
                    {"type": "volume", "target": manifest["compose_volume_target"]},
                    {
                        "type": "bind",
                        "read_only": True,
                        "target": "/etc/postgresql/pg_hba.conf",
                        "source": str(ROOT / "deploy/postgres-pgvector/pg_hba.conf"),
                    },
                ],
            }
        }
    }
    return rendered, manifest


def test_native_adapter_retains_real_command_image_hba_and_pgdata() -> None:
    rendered, manifest = selected_fixture()
    selected = runtime.selected_contract(rendered, manifest)
    assert selected["command"] == rendered["services"]["postgres"]["command"]
    # The selected image's native entrypoint owns exec postgres "$@".
    assert selected["command"][0] == "-c" and "postgres" not in selected["command"]
    assert selected["image"] == manifest["repository"] + "@" + manifest["platform_manifest_digest"]
    assert selected["compose_runtime_ref"] == manifest["runtime_ref"]
    assert selected["hba"] == str(ROOT / "deploy/postgres-pgvector/pg_hba.conf")
    assert selected["pgdata"] == rendered["services"]["postgres"]["environment"]["PGDATA"]


def test_digest_execution_does_not_relax_the_rendered_canonical_reference_contract() -> None:
    rendered, manifest = selected_fixture()
    digest_only = manifest["repository"] + "@" + manifest["platform_manifest_digest"]
    assert runtime.selected_contract(rendered, manifest)["image"] == digest_only
    rendered["services"]["postgres"]["image"] = digest_only
    with pytest.raises(runtime.ProbeError, match="selected immutable manifest"):
        runtime.selected_contract(rendered, manifest)


def test_native_entrypoint_rejects_a_second_postgres_executable() -> None:
    rendered, manifest = selected_fixture()
    rendered["services"]["postgres"]["command"].insert(0, "postgres")
    with pytest.raises(runtime.ProbeError, match="admitted TLS arguments"):
        runtime.selected_contract(rendered, manifest)


@pytest.mark.parametrize(
    "field,value",
    [
        ("image", "postgres:15-alpine"),
        ("platform", "linux/arm64"),
        ("command", []),
        ("command", ["postgres", 1]),
        ("volumes", []),
        ("volumes", None),
    ],
)
def test_native_adapter_rejects_unbound_or_malformed_source(field: str, value: object) -> None:
    rendered, manifest = selected_fixture()
    rendered["services"]["postgres"][field] = value
    with pytest.raises(ValueError):
        runtime.selected_contract(rendered, manifest)


@pytest.mark.parametrize("fault", ["data_mount", "pgdata"])
def test_native_adapter_denies_divergent_runtime_storage_contract(fault: str) -> None:
    rendered, manifest = selected_fixture()
    postgres = rendered["services"]["postgres"]
    if fault == "data_mount":
        postgres["volumes"][0]["target"] = "/wrong/data"
    else:
        postgres["environment"]["PGDATA"] = "/wrong/data"
    with pytest.raises(runtime.ProbeError):
        runtime.selected_contract(rendered, manifest)


def test_crash_waits_on_observed_transaction_before_kill_and_restart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    observations = iter(("0", "1"))

    def native(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, b"", b"")

    def query(container: str, sql: str, conn: str) -> subprocess.CompletedProcess[bytes]:
        assert "pg_stat_activity" in sql and "wait_event='PgSleep'" in sql
        assert "application_name=pulseplate_crash_" in conn
        return subprocess.CompletedProcess([], 0, next(observations).encode(), b"")

    monkeypatch.setattr(runtime, "native", native)
    monkeypatch.setattr(runtime, "query", query)
    monkeypatch.setattr(runtime.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(runtime, "wait_database", lambda container: calls.append(["ready"]))
    runtime.crash_at_transaction_barrier("owned-db", "a" * 32)
    assert "BEGIN; INSERT" in calls[0][-1] and "pg_sleep(120); COMMIT" in calls[0][-1]
    assert calls[1] == ["docker", "kill", "--signal", "KILL", "owned-db"]
    assert calls[2] == ["docker", "start", "owned-db"]


def test_cleanup_includes_stopped_owned_containers_and_rejects_unknown_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def native(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        output = b"unknown-container\n" if args[1:3] == ["container", "ls"] else b""
        return subprocess.CompletedProcess(args, 0, output, b"")

    monkeypatch.setattr(runtime, "native", native)
    with pytest.raises(ValueError, match="ownership"):
        runtime.cleanup({"container": ["owned-db"], "volume": [], "network": []}, "owner")
    assert "--all" in calls[0] and "{{.Names}}" in calls[0]
    assert not any("rm" in args for args in calls)


def test_primary_failure_is_preserved_when_cleanup_also_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failure = runtime.ProbeError("primary native experiment")

    def pki(root: Path) -> Path:
        raise failure

    def cleanup(resources: dict, owner: str) -> None:
        raise runtime.ProbeError("secondary cleanup")

    monkeypatch.setattr(runtime, "create_pki", pki)
    monkeypatch.setattr(runtime, "cleanup", cleanup)
    with pytest.raises(runtime.ProbeError, match="primary native experiment") as observed:
        runtime.experiment(ROOT, {}, {})
    assert observed.value is failure


def test_real_integration_job_is_unprivileged_pr_capable_and_not_configure_only() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/cd.yml").read_text())
    job = workflow["jobs"]["staging-postgres-native-integration"]
    assert "pull_request" in job["if"] and "refs/heads/main" in job["if"]
    assert job["permissions"] == {"contents": "read", "packages": "read"}
    assert "environment" not in job and "needs" not in job
    text = json.dumps(job)
    for forbidden in (
        "DHI_",
        "SSH_",
        "--configure-only",
        "continue-on-error",
        "--publish",
    ):
        assert forbidden not in text
    assert "scripts.ci.check_pgvector_attestations changes" in text
    assert "scripts.ci.check_staging_postgres_runtime" in text
    artifact = next(step for step in job["steps"] if "with" in step and "path" in step["with"])
    assert artifact["with"]["path"] == "staging-postgres-native-result.json"
    login = next(
        step
        for step in job["steps"]
        if step.get("name") == "Authenticate public package read with ephemeral repository token"
    )
    assert login["env"]["GHCR_EPHEMERAL_TOKEN"] == "${{ secrets.GITHUB_TOKEN }}"
    assert login["env"]["GHCR_OWNER"] == "${{ github.repository_owner }}"
    assert text.count("secrets.") == 1 and "GHCR_READ_TOKEN" not in text
    assert "--password-stdin" in login["run"] and "DOCKER_CONFIG=" in login["run"]


def test_external_current_incomplete_tuple_control_precedes_spdx_and_complete_probe() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/cd.yml").read_text())
    steps = workflow["jobs"]["postgres-synthetic-attestation-probe"]["steps"]
    names = [step["name"] for step in steps]
    incomplete = names.index(
        "Reject the exact current incomplete native and materials tuple before SPDX"
    )
    assert (
        names.index("Attest synthetic exact materials")
        < incomplete
        < names.index("Attest synthetic SPDX")
    )
    assert names.index("Attest synthetic SPDX") < names.index(
        "Fresh-process external pullback repeat and source-rejection probe"
    )
    control = steps[incomplete]["run"]
    assert "--run-invocation-uri" in control and "if python3" in control and "exit 1" in control
    assert "continue-on-error" not in steps[incomplete]
    build = next(
        step["run"] for step in steps if step.get("name") == "Build and push tiny synthetic image"
    )
    assert 'export DOCKER_CONFIG="$config_dir"' in build
    assert 'printf \'DOCKER_CONFIG=%s\\n\' "$config_dir" >> "$GITHUB_ENV"' in build
    cleanup = steps[-1]["run"]
    assert 'docker --config "$DOCKER_CONFIG" logout ghcr.io' in cleanup
    assert 'scripts.ci.ghcr_attestation_credentials cleanup --directory "$DOCKER_CONFIG"' in cleanup
    assert 'success) exit "$cleanup_failed"' in cleanup
    assert "continue-on-error" not in steps[-1]


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "accept_corrupt",
        "accept_plaintext",
        "lose_committed",
        "wrong_version",
        "missing_archive_table",
        "bad_tls",
        "bad_cast",
        "bad_vector_version",
        "source_missing",
        "restart_missing",
        "restore_missing",
        "bad_dump_size",
        "negative_healthy_lost",
        "expired_accepted",
        "inspect_malformed",
        "inspect_wrong_config",
        "cleanup_pki",
        "wrapper_failure",
    ],
)
def test_driver_protocol_rejects_bad_outcomes_and_cleans_owned_resources(
    monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    rendered, manifest = selected_fixture()
    contract = runtime.selected_contract(rendered, manifest)
    state: dict[str, Any] = {
        "container": None,
        "volume": None,
        "network": None,
        "sentinel": None,
        "expired": False,
        "crashed": False,
        "restarts": 0,
        "selects": 0,
        "negative_seen": False,
        "dump": b"PGDMP-disposable-native-oracle-archive",
    }
    calls = []
    if fault == "bad_dump_size":
        state["dump"] = b""

    def native(
        args: list[str], data: bytes | None = None, **kwargs: Any
    ) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        output, code = b"", 0
        if args[0] == "openssl":
            for flag in ("-keyout", "-out"):
                if flag in args:
                    Path(args[args.index(flag) + 1]).write_text("disposable-crypto-oracle")
            if "-fingerprint" in args:
                output = b"SHA256 Fingerprint=disposable-public-oracle"
        elif args[1:3] == ["image", "inspect"]:
            output = json.dumps(
                []
                if fault == "inspect_malformed"
                else [
                    {
                        "Id": (
                            "wrong"
                            if fault == "inspect_wrong_config"
                            else manifest["config_digest"]
                        )
                    }
                ]
            ).encode()
        elif args[1] in ("network", "volume") and args[2] == "create":
            state[args[1]] = args[-1]
        elif args[1] == "compose":
            assert args[-5:] == ["up", "--detach", "--pull", "never", "postgres"]
            state["compose"] = json.loads(Path(args[args.index("-f") + 1]).read_text())
            state["container"] = state["compose"]["services"]["postgres"]["container_name"]
        elif args[1] == "run":
            if fault == "cleanup_pki" and any("-ownership-restore" in value for value in args):
                raise runtime.ProbeError("Native private PKI cleanup denied")
            if "--detach" in args:
                state["container"] = args[args.index("--name") + 1]
            if "-ec" in args and "expired_server_crt /k/postgres_server_crt" in args[-1]:
                state["expired"] = True
        elif args[1] in ("container", "volume", "network") and args[2] == "ls":
            output = ((state[args[1]] + "\n") if state[args[1]] else "").encode()
        elif args[1] in ("container", "volume", "network") and args[2] == "rm":
            assert args[-1] == state[args[1]]
            state[args[1]] = None
        elif args[1] == "kill":
            state["crashed"] = True
        elif args[1] == "restart":
            state["restarts"] += 1
        elif args[1] == "exec" and "pg_dump" in args:
            output = state["dump"]
        elif args[1] == "exec" and "pg_restore" in args:
            if "--list" in args:
                output = (
                    b"214; 1259 16387 TABLE public staging_probe pulseplate_probe\n"
                    if fault != "missing_archive_table"
                    else b""
                )
            elif "--file=/dev/null" in args and data != state["dump"]:
                code = 0 if fault == "accept_corrupt" else 1
        elif args[1] == "exec" and "psql" in args:
            if "--command" in args:
                output = b""  # Detached open transaction starts; SQL barrier is observed below.
            else:
                sql = (data or b"").decode()
                conn = args[args.index("--dbname") + 1]
                if "sslmode=disable" in conn:
                    code = 0 if fault == "accept_plaintext" else 1
                    state["negative_seen"] = True
                elif "wrong_ca" in conn or "host=wrong.invalid" in conn or state["expired"]:
                    code = 0 if state["expired"] and fault == "expired_accepted" else 1
                elif "pg_stat_activity" in sql:
                    output = b"1\n"
                elif "pg_stat_ssl" in sql:
                    output = b"false:TLSv1.0" if fault == "bad_tls" else b"true:TLSv1.3\n"
                elif "SHOW server_version" in sql:
                    output = (
                        b"99.0\n"
                        if fault == "wrong_version"
                        else manifest["postgres_version"].encode()
                    )
                elif "SELECT extversion" in sql:
                    output = (
                        b"99.0"
                        if fault == "bad_vector_version"
                        else manifest["pgvector_version"].encode()
                    )
                elif "CREATE EXTENSION" in sql:
                    output = b"bad cast" if fault == "bad_cast" else b"[1,2,3]\n"
                elif "CREATE TABLE staging_probe" in sql:
                    value = args[args.index("--set") + 1]
                    assert value.startswith("sentinel=") and ":'sentinel'" in sql
                    state["sentinel"] = value.split("=", 1)[1]
                elif "FROM staging_probe" in sql:
                    state["selects"] += 1
                    output = (
                        "0:lost"
                        if (
                            (state["crashed"] and fault == "lose_committed")
                            or (fault == "source_missing" and state["selects"] == 1)
                            or (fault == "restart_missing" and state["restarts"] == 1)
                            or (
                                fault == "restore_missing"
                                and "dbname=pulseplate_restore_check_" in conn
                            )
                        )
                        else "1:" + state["sentinel"]
                    ).encode()
                else:
                    output = (
                        b"0"
                        if fault == "negative_healthy_lost" and state["negative_seen"]
                        else b"1\n"
                    )
        return subprocess.CompletedProcess(args, code, output, b"")

    def wrapper_checks(*args: Any) -> dict[str, bool]:
        calls.append(["wrapper-checks"])
        if fault == "wrapper_failure":
            raise runtime.ProbeError("Native wrapper controls rejected")
        return {"adapter_only": True}

    monkeypatch.setattr(runtime, "wrapper_restore_checks", wrapper_checks)
    monkeypatch.setattr(runtime, "native", native)
    if fault is None:
        result = runtime.experiment(ROOT, contract, manifest)
        assert result["live_deployment_sessions_and_do_encryption_claim"] is False
        assert result["process_crash_committed_survives_uncommitted_rolls_back"] is True
        assert result["isolated_restore_sentinel_count_equal"] is True
        assert len(result["fingerprint"]) == 64
    else:
        with pytest.raises(runtime.ProbeError):
            runtime.experiment(ROOT, contract, manifest)
    assert not state["container"] and not state["volume"] and not state["network"]
    assert not any("--publish" in args or "--privileged" in args for args in calls)
    expected_image = manifest["repository"] + "@" + manifest["platform_manifest_digest"]
    for args in calls:
        if args[:2] == ["docker", "pull"] or args[:3] == ["docker", "image", "inspect"]:
            assert args[-1] == expected_image
        if args[:2] == ["docker", "run"]:
            assert args[args.index("-ec") - 1] == expected_image
    if "compose" in state:
        service = state["compose"]["services"]["postgres"]
        assert service["image"] == expected_image
        assert service["command"] == contract["command"]
        assert "ports" not in service and "entrypoint" not in service
        assert "PGHOST" not in service["environment"]  # Native init uses its socket-only server.
        assert runtime.USER != runtime.DATABASE
        if fault is not None and fault != "cleanup_pki":
            diagnostics = next(
                i for i, args in enumerate(calls) if args[1:3] == ["container", "inspect"]
            )
            removal = next(i for i, args in enumerate(calls) if args[1:3] == ["container", "ls"])
            assert diagnostics < removal


def test_native_command_adapter_requires_resolved_binary_and_preserves_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime.shutil, "which", lambda name: None)
    with pytest.raises(runtime.ProbeError, match="unavailable"):
        runtime.native(["docker", "info"])
    monkeypatch.setattr(runtime.shutil, "which", lambda name: "/resolved/docker")

    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        assert args[0] == "/resolved/docker" and kwargs["timeout"] == 60
        return subprocess.CompletedProcess(args, 23, b"", b"private output not logged")

    monkeypatch.setattr(runtime.subprocess, "run", run)
    assert runtime.native(["docker", "info"], required=False).returncode == 23
    with pytest.raises(runtime.ProbeError, match="exit 23"):
        runtime.native(["docker", "info"])


def test_render_uses_native_compose_with_synthetic_variables_and_real_source_asset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rendered, manifest = selected_fixture()

    def native(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        assert "compose" in args and "--no-env-resolution" in args
        assert kwargs["environment"]["POSTGRES_USER"] == runtime.USER
        assert kwargs["environment"]["STAGING_ENV_FILE"] == "/dev/null"
        return subprocess.CompletedProcess(args, 0, json.dumps(rendered).encode(), b"")

    monkeypatch.setattr(runtime, "native", native)
    assert (
        runtime.render_contract(ROOT, manifest)["command"]
        == rendered["services"]["postgres"]["command"]
    )
    rendered["services"]["postgres"]["volumes"][1]["source"] = "/untrusted/hba"
    with pytest.raises(runtime.ProbeError, match="real regular"):
        runtime.render_contract(ROOT, manifest)


@pytest.mark.parametrize("barrier", [False, True])
def test_readiness_and_transaction_barrier_expire_without_faulting_unobserved_state(
    monkeypatch: pytest.MonkeyPatch, barrier: bool
) -> None:
    clock = iter((0.0, 1.0, 100.0))
    calls = []
    monkeypatch.setattr(runtime.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(runtime.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        runtime, "query", lambda *args, **kwargs: subprocess.CompletedProcess([], 1, b"0", b"")
    )
    monkeypatch.setattr(runtime, "native", lambda args, **kwargs: calls.append(args))
    with pytest.raises(runtime.ProbeError):
        if barrier:
            runtime.crash_at_transaction_barrier("owned", "a" * 32)
        else:
            runtime.wait_database("owned")
    assert not any("kill" in args for args in calls)


@pytest.mark.parametrize("fault", ["census", "remove"])
def test_native_cleanup_failures_are_blocking(monkeypatch: pytest.MonkeyPatch, fault: str) -> None:
    def native(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        output = b"owned\n" if args[1:3] == ["container", "ls"] and fault == "remove" else b""
        code = 1 if (args[2] == "ls" and fault == "census") or args[2] == "rm" else 0
        return subprocess.CompletedProcess(args, code, output, b"")

    monkeypatch.setattr(runtime, "native", native)
    with pytest.raises(runtime.ProbeError):
        runtime.cleanup({"container": ["owned"], "volume": [], "network": []}, "owner")


@pytest.mark.parametrize("mode", ["configure", "linux", "nonlinux", "error"])
def test_cli_keeps_configuration_and_native_execution_claims_separate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    rendered, manifest = selected_fixture()
    monkeypatch.setattr(
        runtime,
        "render_contract",
        lambda root, selected: runtime.selected_contract(rendered, selected),
    )
    output = tmp_path / "result.json"
    arguments = ["probe", "--repo-root", str(ROOT), "--json-out", str(output)] + (
        ["--configure-only"] if mode == "configure" else []
    )
    monkeypatch.setattr(runtime.sys, "argv", arguments)
    monkeypatch.setattr(
        runtime.sys, "platform", "linux" if mode in ("linux", "error") else "darwin"
    )

    def experiment(root: Path, contract: dict, selected: dict) -> dict:
        if mode == "error":
            raise runtime.ProbeError("native rejected")
        return {"native_execution": True}

    monkeypatch.setattr(runtime, "experiment", experiment)
    assert runtime.main() == (1 if mode in ("nonlinux", "error") else 0)
    if mode in ("nonlinux", "error"):
        assert not output.exists()
    else:
        record = json.loads(output.read_text())
        assert record.get("configure_only", False) is (mode == "configure")


def test_native_diagnostics_are_bounded_redacted_and_omit_stdout_argv_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime.shutil, "which", lambda name: "/resolved/docker")
    secret = "opaque" + "_native" + "_diagnostic"
    stderr = (
        "TLS certificate verification failed GH_TOKEN="
        + secret
        + " https://user:"
        + secret
        + "@registry.invalid Bearer "
        + secret
        + " -----BEGIN PRIVATE KEY-----\n"
        + secret
        + "\n-----END PRIVATE KEY----- "
        + "x" * 1000
    )
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            [], 7, b"binary-stdout-private-data", stderr.encode()
        ),
    )
    with pytest.raises(runtime.ProbeError) as failure:
        runtime.native(["docker", "exec", "private-container-identifier", "private-argument"])
    message = str(failure.value)
    assert "Native docker exec" in message and "TLS certificate verification failed" in message
    assert len(message) < 600
    for value in (
        secret,
        "binary-stdout-private-data",
        "private-container-identifier",
        "private-argument",
    ):
        assert value not in message


@pytest.mark.parametrize("owned", [True, False])
def test_failure_diagnostics_read_only_owned_state_and_bounded_redacted_logs(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], owned: bool
) -> None:
    calls = []
    probe_value = "ephemeral-diagnostic-control"

    def native(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        assert kwargs == {"required": False, "timeout": 10}
        if "--format" in args and ".Config.Labels" in args[-2]:
            output = json.dumps("owner" if owned else "someone-else").encode()
        elif "--format" in args:
            assert all(
                field in args[-2]
                for field in (".State.Status", ".State.OOMKilled", ".State.ExitCode")
            )
            assert ".Config.Env" not in args[-2] and ".State.Health" not in args[-2]
            output = b'{"status":"exited","oom_killed":false,"exit_code":1}'
        else:
            assert args == ["docker", "logs", "--tail", "64", "owned-db"]
            output = (
                "ENTRYPOINT startup failed "
                + probe_value
                + " GH_TOKEN="
                + probe_value
                + "\n-----BEGIN PRIVATE KEY-----\nprivate-key-data\n-----END PRIVATE KEY-----\n"
                + "x" * 20_000
            ).encode()
        return subprocess.CompletedProcess(args, 0, output, b"")

    monkeypatch.setattr(runtime, "native", native)
    runtime.diagnose_container("owned-db", "owner", (probe_value,))
    captured = capsys.readouterr().err
    assert len(captured) < 10_000
    assert probe_value not in captured and "private-key-data" not in captured
    if owned:
        assert len(calls) == 3 and "ENTRYPOINT startup failed" in captured
        assert '"exit_code":1' in captured.replace('\\"', '"')
    else:
        assert len(calls) == 1 and "ownership unconfirmed" in captured


def test_readiness_failure_retains_last_query_exit_and_redacted_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = iter((0.0, 1.0, 100.0))
    monkeypatch.setattr(runtime.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(runtime.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        runtime,
        "query",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            [], 7, b"do-not-publish-query-data", b"could not connect GH_TOKEN=opaque-test-token"
        ),
    )
    with pytest.raises(runtime.ProbeError) as failed:
        runtime.wait_database("owned-db")
    assert "exit=7" in str(failed.value) and "could not connect" in str(failed.value)
    assert "opaque-test-token" not in str(failed.value)
    assert "do-not-publish-query-data" not in str(failed.value)


@pytest.fixture
def wrapper_adapter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Finite command outputs test helper decisions, never native DB execution."""
    compose_file = tmp_path / "compose.native.json"
    compose_file.write_text("{}")
    state: dict[str, Any] = {
        "fault": None,
        "cleanup_fault": None,
        "owner": "a" * 32,
        "source_owner": "default",
        "bad_sql": False,
        "private_source": False,
        "targets": {},
        "calls": [],
        "backups": 0,
        "decoded": [],
        "primary": runtime.ProbeError("Original wrapper command error"),
    }
    monkeypatch.setattr(runtime.shutil, "which", lambda name: "/resolved/" + name)

    def completed(
        args: list[str], output: bytes = b"", code: int = 0, error: bytes = b""
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(args, code, output, error)

    def native(
        args: list[str], data: bytes | None = None, **kwargs: Any
    ) -> subprocess.CompletedProcess[bytes]:
        state["calls"].append((args, kwargs))
        fault = state["fault"]
        if args[0] == "bash":
            env = kwargs["environment"]
            assert Path(args[1]).is_absolute()
            assert env["PROJECT_DIR"] == str(tmp_path) and env["COMPOSE_FILE"] == str(compose_file)
            assert env["POSTGRES_USER"] == runtime.USER and env["POSTGRES_DB"] == runtime.DATABASE
            assert env["ENV_FILE"] == "/dev/null" and env["DOCKER_BIN"] == "/resolved/docker"
            assert kwargs["timeout"] == 120
            assert not any(key.startswith("PG") for key in env)
            assert "COMPOSE_PROJECT_NAME" not in env
            if args[1].endswith("postgres_backup.sh"):
                if fault == "backup-error":
                    raise state["primary"]
                state["backups"] += 1
                tag = (
                    "nonpublic"
                    if state["private_source"]
                    else "failing" if state["bad_sql"] else state["source_owner"]
                )
                backup_dir = Path(env["BACKUP_DIR"])
                path = backup_dir / f"pulseplate_{state['backups']}.dump"
                if fault != "backup-absent":
                    path.write_bytes(tag.encode())
                    path.chmod(0o600)
                if fault == "backup-multiple":
                    (backup_dir / "pulseplate_extra.dump").write_bytes(b"default")
                elif fault == "backup-mode":
                    path.chmod(0o644)
                elif fault == "backup-empty":
                    path.write_bytes(b"")
                elif fault == "backup-large":
                    with path.open("r+b") as stream:
                        stream.truncate(64 * 1024**2 + 1)
                elif fault == "backup-link":
                    os.link(path, backup_dir / "extra-link")
                elif fault == "backup-symlink":
                    real = backup_dir / "real-dump"
                    path.rename(real)
                    path.symlink_to(real)
                elif fault == "backup-residue":
                    (backup_dir / ".pulseplate-backup.residue").mkdir()
                output = "Backup created: " + str(path)
                if fault == "backup-receipt":
                    output += " extra output"
                return completed(args, (output + "\n").encode())
            assert args[1].endswith("postgres_restore.sh")
            mode, target, archive = args[2], args[3], Path(args[4]).read_bytes()
            if mode == "--verify-into":
                if target in state["targets"]:
                    if fault == "verify-accepts-existing":
                        return completed(args)
                    if fault == "verify-mutates-existing":
                        state["targets"][target]["mutated"] = True
                    return completed(args, code=1, error=b"database already exists")
                state["targets"][target] = {"old": False, "private": False, "mutated": False}
                return completed(args)
            assert mode == "--replace-existing"
            database = state["targets"][target]
            if archive == b"failing":
                if fault == "rollback-mutates":
                    database["mutated"] = True
                if fault == "rollback-residue":
                    (Path(env["BACKUP_DIR"]) / ".pulseplate-restore.residue").mkdir()
                return completed(
                    args,
                    b"Restore completed" if fault == "rollback-success-output" else b"",
                    0 if fault == "rollback-accepts" else 3,
                    (
                        b"authentication failed"
                        if fault == "rollback-other-rejection"
                        else b"synthetic restore index failure"
                    ),
                )
            if archive == b"nonpublic" or database["private"]:
                rail = "source" if archive == b"nonpublic" else "target"
                if fault == rail + "-hold-mutates":
                    database["mutated"] = True
                if fault == "target-private-lost" and rail == "target":
                    database["private"] = False
                reason = (
                    b"archive contains unsupported"
                    if rail == "source"
                    else b"target contains unsupported"
                )
                return completed(
                    args,
                    code=0 if fault == rail + "-hold-accepts" else 1,
                    error=(
                        b"unrelated network error"
                        if fault == rail + "-hold-other-rejection"
                        else reason
                    ),
                )
            database["old"] = False
            if fault == "replacement-retains-extra":
                database["extra"] = True
            return completed(args)
        assert args[:2] == ["docker", "exec"]
        if "createdb" in args:
            assert args[args.index("--maintenance-db") + 1] == runtime.DATABASE
            assert args[args.index("-U") + 1] == runtime.USER
            state["targets"][args[-1]] = {"old": True, "private": False, "mutated": False}
            return completed(args)
        if "pg_dump" in args:
            assert "--schema=public" in args
            return completed(args, b"definition")
        assert "pg_restore" in args
        if "--file=/dev/null" in args:
            if fault == "backup-decode":
                raise runtime.ProbeError("Native archive decoder rejected")
            state["decoded"].append(data)
            return completed(args)
        tag = (data or b"").decode()
        has_record = tag != "default"
        if fault == "shape-omitted" and tag == "default":
            has_record = True
        if fault == "shape-metadata-only" and tag == "metadata":
            has_record = False
        if "--list" in args:
            output = "214; 1259 16387 TABLE public staging_probe pulseplate_probe\n"
            if has_record:
                output = "5; 2615 2200 SCHEMA - public pulseplate_probe\n" + output
            return completed(args, output.encode())
        assert "--clean" in args and "--if-exists" in args and "--file=-" in args
        sql = (
            "CREATE SCHEMA public;\n"
            if tag == "definition" and fault != "shape-definition"
            else "-- no schema CREATE\n"
        )
        return completed(args, sql.encode())

    def query(
        container: str, sql: str, conn: str | None = None, **kwargs: Any
    ) -> subprocess.CompletedProcess[bytes]:
        state["calls"].append((["query", sql, conn or "source"], kwargs))
        fault = state["fault"]
        database_name = (
            runtime.DATABASE
            if conn is None
            else next(
                token.removeprefix("dbname=")
                for token in conn.split()
                if token.startswith("dbname=")
            )
        )
        if sql.startswith("DROP INDEX IF EXISTS"):
            state["cleaned"] = True
            if state["cleanup_fault"] == "exception":
                raise runtime.ProbeError("Cleanup adapter raised")
            return completed([], code=7 if state["cleanup_fault"] == "exit" else 0)
        if database_name == runtime.DATABASE:
            if "FROM public.staging_probe" in sql:
                return completed([], b"1:source-sentinel")
            if "FROM pg_database" in sql:
                assert "datname=:'role'" in sql
                assert kwargs["variables"] == {"role": runtime.USER}
                return completed([], b"1" if fault == "role-database-exists" else b"0")
            if sql == "ALTER SCHEMA public OWNER TO " + runtime.USER + ";":
                state["source_owner"] = "metadata"
            elif sql == "ALTER SCHEMA public OWNER TO pg_database_owner;":
                state["source_owner"] = "default"
            elif sql.startswith("CREATE FUNCTION public.wrapper_restore_key"):
                state["bad_sql"] = True
            elif sql.startswith("DROP INDEX public.wrapper_restore_failure_idx"):
                state["bad_sql"] = False
            elif sql.startswith("CREATE SCHEMA private_wrapper"):
                state["private_source"] = True
            elif sql.startswith("DROP SCHEMA private_wrapper"):
                state["private_source"] = False
            return completed([])
        database = state["targets"][database_name]
        if sql.startswith("CREATE TABLE public.wrapper_original"):
            assert "VALUES(1,:'old_payload')" in sql
            assert kwargs["variables"] == {"old_payload": "old_" + "a" * 16}
            return completed([])
        if sql.startswith("CREATE SCHEMA private_wrapper"):
            database["private"] = True
            return completed([])
        if "SELECT id FROM private_wrapper.hidden" in sql:
            return completed([], b"9" if database["private"] else b"lost")
        if "FROM public.wrapper_original" in sql:
            return completed(
                [], b"original-data-and-objects" if not database["mutated"] else b"mutated-data"
            )
        if "FROM public.staging_probe" in sql:
            if (
                database["mutated"]
                or fault == "verification-missing"
                and database_name.startswith("pulseplate_restore_check")
            ):
                return completed([], b"0:missing")
            return completed([], b"1:source-sentinel")
        assert "SELECT tablename" in sql
        return completed(
            [],
            (
                b"t|t|t|t\nstaging_probe"
                if not database["mutated"] and not database.get("extra", False)
                else b"f|t|t|t\nstaging_probe\nextra"
            ),
        )

    monkeypatch.setattr(runtime, "native", native)
    monkeypatch.setattr(runtime, "query", query)
    state["run"] = lambda: runtime.wrapper_restore_checks(
        ROOT, tmp_path, "owned-db", state["owner"], compose_file
    )
    return state


def test_wrapper_helper_adapter_accepts_only_complete_observed_controls(
    wrapper_adapter: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PGHOST", "unrelated-host")
    monkeypatch.setenv("COMPOSE_PROJECT_NAME", "unrelated-project")
    results = wrapper_adapter["run"]()
    assert len(results) == 9 and all(value is True for value in results.values())
    assert all(
        results["wrapper_replacement_schema_" + shape]
        for shape in ("omitted", "metadata_only", "definition")
    )
    assert b"failing" in wrapper_adapter["decoded"]
    assert wrapper_adapter["cleaned"]
    restores = [
        args
        for args, _ in wrapper_adapter["calls"]
        if args[0] == "bash" and args[1].endswith("postgres_restore.sh")
    ]
    assert sum(args[2] == "--replace-existing" for args in restores) == 6
    assert runtime.USER != runtime.DATABASE


@pytest.mark.parametrize(
    "fault",
    [
        "backup-absent",
        "backup-multiple",
        "backup-mode",
        "backup-empty",
        "backup-large",
        "backup-link",
        "backup-symlink",
        "backup-residue",
        "backup-receipt",
        "backup-decode",
    ],
)
def test_wrapper_helper_rejects_invalid_actual_wrapper_publication_outputs(
    wrapper_adapter: dict[str, Any], fault: str
) -> None:
    wrapper_adapter["fault"] = fault
    with pytest.raises(runtime.ProbeError, match="backup|decoder"):
        wrapper_adapter["run"]()
    assert wrapper_adapter["cleaned"]
    assert not any(
        args[0] == "bash" and args[1].endswith("postgres_restore.sh")
        for args, _ in wrapper_adapter["calls"]
    )


@pytest.mark.parametrize("shape", ["omitted", "metadata-only", "definition"])
def test_wrapper_helper_rejects_misclassified_native_schema_shapes(
    wrapper_adapter: dict[str, Any], shape: str
) -> None:
    wrapper_adapter["fault"] = "shape-" + shape
    with pytest.raises(runtime.ProbeError, match="schema shape"):
        wrapper_adapter["run"]()
    assert wrapper_adapter["cleaned"]


@pytest.mark.parametrize(
    "fault",
    [
        "rollback-accepts",
        "rollback-other-rejection",
        "rollback-mutates",
        "rollback-success-output",
        "rollback-residue",
    ],
)
def test_wrapper_helper_requires_expected_late_sql_failure_and_exact_retention(
    wrapper_adapter: dict[str, Any], fault: str
) -> None:
    wrapper_adapter["fault"] = fault
    with pytest.raises(runtime.ProbeError, match="late SQL failure"):
        wrapper_adapter["run"]()
    assert b"failing" in wrapper_adapter["decoded"]
    assert wrapper_adapter["cleaned"]


@pytest.mark.parametrize(
    "fault",
    [
        "source-hold-accepts",
        "source-hold-other-rejection",
        "source-hold-mutates",
        "target-hold-accepts",
        "target-hold-other-rejection",
        "target-hold-mutates",
        "target-private-lost",
    ],
)
def test_wrapper_helper_requires_correct_layout_hold_with_all_original_data_retained(
    wrapper_adapter: dict[str, Any], fault: str
) -> None:
    wrapper_adapter["fault"] = fault
    with pytest.raises(runtime.ProbeError, match="non-public"):
        wrapper_adapter["run"]()
    assert wrapper_adapter["cleaned"]


@pytest.mark.parametrize(
    "fault",
    [
        "role-database-exists",
        "verify-accepts-existing",
        "verify-mutates-existing",
        "verification-missing",
        "replacement-retains-extra",
    ],
)
def test_wrapper_helper_rejects_missing_maintenance_or_replacement_evidence(
    wrapper_adapter: dict[str, Any], fault: str
) -> None:
    wrapper_adapter["fault"] = fault
    with pytest.raises(runtime.ProbeError):
        wrapper_adapter["run"]()
    assert wrapper_adapter["cleaned"]


@pytest.mark.parametrize("cleanup_fault", ["exit", "exception"])
def test_wrapper_helper_cleanup_failure_preserves_original_command_error(
    wrapper_adapter: dict[str, Any], capsys: pytest.CaptureFixture[str], cleanup_fault: str
) -> None:
    wrapper_adapter["fault"], wrapper_adapter["cleanup_fault"] = "backup-error", cleanup_fault
    with pytest.raises(runtime.ProbeError) as failed:
        wrapper_adapter["run"]()
    assert failed.value is wrapper_adapter["primary"]
    assert "cleanup also failed; primary failure preserved" in capsys.readouterr().err


@pytest.mark.parametrize("cleanup_fault", ["exit", "exception"])
def test_wrapper_helper_cleanup_failure_without_prior_error_remains_blocking(
    wrapper_adapter: dict[str, Any], cleanup_fault: str
) -> None:
    wrapper_adapter["cleanup_fault"] = cleanup_fault
    with pytest.raises(runtime.ProbeError, match="cleanup|Cleanup"):
        wrapper_adapter["run"]()


@pytest.mark.parametrize("fault", ["same-role-database", "invalid-owner", "missing-docker"])
def test_wrapper_helper_start_boundaries_precede_native_operations(
    wrapper_adapter: dict[str, Any], monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    if fault == "same-role-database":
        monkeypatch.setattr(runtime, "DATABASE", runtime.USER)
    elif fault == "invalid-owner":
        wrapper_adapter["owner"] = "untrusted-owner"
    else:
        monkeypatch.setattr(runtime.shutil, "which", lambda name: None)
    with pytest.raises(runtime.ProbeError):
        wrapper_adapter["run"]()
    assert wrapper_adapter["calls"] == []
