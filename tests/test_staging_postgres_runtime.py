"""Adapter/ownership regressions for the separate real Linux runtime experiment."""

from __future__ import annotations

import json
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
    assert 'test ! -L "$DOCKER_CONFIG/config.json"' in cleanup
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
    images = [value for args in calls for value in args if value.startswith("ghcr.io/")]
    assert all(
        value == manifest["repository"] + "@" + manifest["platform_manifest_digest"]
        for value in images
    )


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
