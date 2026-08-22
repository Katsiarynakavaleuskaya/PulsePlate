"""Deterministic contract tests for the premium-alias telemetry verifier."""

from __future__ import annotations

import asyncio
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tarfile

import pytest

from scripts import verify_premium_alias_telemetry as verifier

_DIGEST_A = "sha256:" + "a" * 64
_DIGEST_B = "sha256:" + "b" * 64
_PROMETHEUS_REFERENCE = "prom/prometheus:v3.14.0-distroless@" + _DIGEST_B
_RELEASE_A = "1" * 40
_RELEASE_B = "2" * 40
_APP_CONTAINER_A = "a" * 64
_PROMETHEUS_CONTAINER_A = "b" * 64
_PROCESS_A = "sha256:" + "c" * 64
_T0 = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)


def _live_snapshot(
    *,
    release_id: str = _RELEASE_A,
    api_containers: int = 1,
    prometheus_containers: int = 1,
    uvicorn_processes: int = 1,
    retention_days: int = 45,
    app_container_id: str = _APP_CONTAINER_A,
    prometheus_container_id: str = _PROMETHEUS_CONTAINER_A,
    process_identity: str = _PROCESS_A,
) -> verifier.LiveRuntimeSnapshot:
    return verifier.LiveRuntimeSnapshot(
        app_container_id=app_container_id,
        prometheus_container_id=prometheus_container_id,
        release_id=release_id,
        app_image_id=_DIGEST_A,
        prometheus_image_id=_DIGEST_B,
        prometheus_image_reference=_PROMETHEUS_REFERENCE,
        config_sha256=_DIGEST_A,
        volume_id="prometheus-data-01",
        api_container_count=api_containers,
        prometheus_container_count=prometheus_containers,
        uvicorn_process_count=uvicorn_processes,
        uvicorn_process_identity=process_identity,
        retention_days=retention_days,
    )


class _FakePromtoolClient:
    def __init__(
        self,
        *,
        overrides: dict[str, float | verifier.VerificationError] | None = None,
        healthy: bool = True,
        ready: bool = True,
        snapshot: verifier.LiveRuntimeSnapshot | verifier.VerificationError | None = None,
        post_snapshot: verifier.LiveRuntimeSnapshot | verifier.VerificationError | None = None,
        anchor: datetime = _T0,
    ) -> None:
        self.overrides = overrides or {}
        self.healthy = healthy
        self.ready = ready
        self.snapshot = snapshot or _live_snapshot()
        self.post_snapshot = post_snapshot if post_snapshot is not None else self.snapshot
        self.anchor = anchor
        self.census_count = 0
        self.queries: list[tuple[str, str]] = []

    def collect_live_snapshot(self) -> verifier.LiveRuntimeSnapshot:
        selected = self.snapshot if self.census_count == 0 else self.post_snapshot
        self.census_count += 1
        if isinstance(selected, verifier.VerificationError):
            raise selected
        return selected

    def get_evaluation_anchor(self) -> datetime:
        return self.anchor

    def check_healthy(self) -> bool:
        return self.healthy

    def check_ready(self) -> bool:
        return self.ready

    def query_scalar(self, expression: str, *, evaluation_time: str) -> float:
        self.queries.append((expression, evaluation_time))
        for fragment, result in self.overrides.items():
            if fragment in expression:
                if isinstance(result, verifier.VerificationError):
                    raise result
                return result
        if expression.startswith("count(up"):
            return 1.0
        if expression.startswith("min(up") or expression.startswith("min_over_time"):
            return 1.0
        if expression.startswith("count_over_time"):
            return float(verifier.FINAL_MIN_SAMPLES)
        return 0.0


def _config(
    tmp_path: Path,
    *,
    mode: str,
    t0: datetime | None = None,
) -> verifier.VerificationConfig:
    return verifier.VerificationConfig(
        mode=mode,
        compose_file=tmp_path / "compose.yaml",
        evidence_dir=tmp_path,
        output_name=f"{mode}.json",
        baseline_evidence=None,
        t0=t0,
    )


def _passing_baseline(tmp_path: Path) -> dict[str, object]:
    return verifier.build_evidence(
        _config(tmp_path, mode="baseline"),
        _FakePromtoolClient(),
    )


def _cli_args(tmp_path: Path, mode: str) -> list[str]:
    arguments = [
        mode,
        "--compose-file",
        os.fspath(tmp_path / "compose.yaml"),
        "--evidence-dir",
        os.fspath(tmp_path),
        "--output-name",
        f"{mode}.json",
    ]
    if mode != "baseline":
        arguments.extend(("--baseline-evidence", os.fspath(tmp_path / "baseline.json")))
    if mode == "final":
        arguments.extend(("--t0", "2026-08-22T12:00:00Z"))
    return arguments


@pytest.mark.parametrize("mode", ["baseline", "checkpoint", "final"])
def test_parser_accepts_only_complete_mode_grammar(tmp_path: Path, mode: str) -> None:
    args = verifier._parse_args(_cli_args(tmp_path, mode))
    assert args.mode == mode


@pytest.mark.parametrize(
    "arguments",
    [
        ["unknown"],
    ],
)
def test_parser_rejects_invalid_mode(arguments: list[str]) -> None:
    with pytest.raises(SystemExit):
        verifier._parse_args(arguments)


def test_parser_rejects_stale_caller_truth_and_unsafe_output_name(tmp_path: Path) -> None:
    arguments = [*_cli_args(tmp_path, "baseline"), "--app-image-id", _DIGEST_A]
    with pytest.raises(SystemExit):
        verifier._parse_args(arguments)

    for spoofed_time in ("2099-01-01T00:00:00Z", "2000-01-01T00:00:00Z"):
        arguments = [*_cli_args(tmp_path, "baseline"), "--observed-at", spoofed_time]
        with pytest.raises(SystemExit):
            verifier._parse_args(arguments)

    arguments = [*_cli_args(tmp_path, "baseline"), "--expected-target-count", "2"]
    with pytest.raises(SystemExit):
        verifier._parse_args(arguments)

    arguments = _cli_args(tmp_path, "baseline")
    output_index = arguments.index("baseline.json")
    arguments[output_index] = "../baseline.json"
    with pytest.raises(SystemExit):
        verifier._parse_args(arguments)


def _promtool_payload(*, result_type: str = "vector", result: object = None) -> bytes:
    if result is None:
        result = [{"metric": {}, "value": [1_777_000_000.0, "0"]}]
    return json.dumps(
        {"status": "success", "data": {"resultType": result_type, "result": result}}
    ).encode()


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        (b"not-json", "promtool_result_invalid"),
        (_promtool_payload(result_type="matrix"), "promtool_result_invalid"),
        (_promtool_payload(result=[]), "promtool_vector_missing"),
        (_promtool_payload(result=[{"metric": {}, "value": [1.0, "NaN"]}]), "nonfinite"),
        (_promtool_payload(result=[{"metric": {}, "value": [1.0, "+Inf"]}]), "nonfinite"),
        (_promtool_payload(result=[{"metric": {}, "value": [1.0, 0]}]), "invalid"),
    ],
)
def test_promtool_parser_rejects_malformed_missing_and_nonfinite_vectors(
    payload: bytes,
    error: str,
) -> None:
    with pytest.raises(verifier.VerificationError, match=error):
        verifier._parse_promtool_vector(payload)


def test_bounded_baseline_and_final_pass_preserve_exact_zero_semantics(
    tmp_path: Path,
) -> None:
    baseline_client = _FakePromtoolClient()
    baseline = verifier.build_evidence(
        _config(tmp_path, mode="baseline"),
        baseline_client,
    )
    final_client = _FakePromtoolClient(anchor=_T0 + timedelta(days=30))
    final = verifier.build_evidence(
        _config(tmp_path, mode="final", t0=_T0),
        final_client,
        baseline=baseline,
    )

    assert baseline["decision"] == "PASS"
    assert final["decision"] == "PASS"
    assert final["authority"] == verifier.AUTHORITY
    assert baseline["asset_type"] == verifier.ASSET_TYPE
    assert baseline["policy_version"] == verifier.POLICY_VERSION
    assert baseline["replay"] == {
        "identical_same_idempotency": "verify_and_no_write",
        "divergent_existing": "fail_closed",
    }
    assert baseline["admission"] == {
        "behavior": "validate_schema_lineage_fingerprint_and_live_snapshot",
        "missing_or_invalid": "hold",
    }
    upstream_assets = baseline["upstream_assets"]
    assert isinstance(upstream_assets, list)
    assert [asset["role"] for asset in upstream_assets] == [
        "release",
        "app_container",
        "app_image",
        "prometheus_container",
        "prometheus_image",
        "prometheus_image_reference",
        "scrape_config",
        "tsdb",
        "uvicorn_process",
    ]
    assert all(
        isinstance(asset["fingerprint"], str)
        and verifier._DIGEST_RE.fullmatch(asset["fingerprint"])
        for asset in upstream_assets
    )
    final_upstreams = final["upstream_assets"]
    assert isinstance(final_upstreams, list)
    assert final_upstreams[-1] == {
        "asset_type": verifier.ASSET_TYPE,
        "role": "baseline_evidence",
        "fingerprint": baseline["fingerprint"],
    }
    verifier._validate_evidence_asset(baseline)
    verifier._validate_evidence_asset(final)
    replayed_baseline = verifier.build_evidence(
        _config(tmp_path, mode="baseline"),
        _FakePromtoolClient(),
    )
    assert replayed_baseline["idempotency_key"] == baseline["idempotency_key"]
    assert replayed_baseline["fingerprint"] == baseline["fingerprint"]
    assert final["window"] == {
        "started_at": "2026-08-22T12:00:00Z",
        "t0": "2026-08-22T12:00:00Z",
        "ended_at": "2026-09-21T12:00:00Z",
        "duration_seconds": 2_592_000,
        "complete": True,
    }
    aliases = final["aliases"]
    assert isinstance(aliases, list)
    assert [record["route"] for record in aliases] == list(verifier.ALIAS_ROUTES)
    assert all(record["observation"] == "observed_exact_zero" for record in aliases)
    assert all("or vector(0)" not in query for query, _time in baseline_client.queries)
    assert all("or vector(0)" not in query for query, _time in final_client.queries)
    assert all(
        "status=" not in query for query, _time in final_client.queries if "increase(" in query
    )
    assert {query_time for _query, query_time in baseline_client.queries} == {
        "2026-08-22T12:00:00Z"
    }
    assert {query_time for _query, query_time in final_client.queries} == {"2026-09-21T12:00:00Z"}
    serialized = json.dumps(final, sort_keys=True)
    assert os.fspath(tmp_path) not in serialized
    assert "docker compose" not in serialized


def test_final_idempotency_binds_human_t0_and_exact_replay_is_no_write(
    tmp_path: Path,
) -> None:
    baseline = _passing_baseline(tmp_path)
    observed_at = _T0 + timedelta(days=31)
    first = verifier.build_evidence(
        _config(tmp_path, mode="final", t0=_T0),
        _FakePromtoolClient(anchor=observed_at),
        baseline=baseline,
    )
    exact_replay = verifier.build_evidence(
        _config(tmp_path, mode="final", t0=_T0),
        _FakePromtoolClient(anchor=observed_at),
        baseline=baseline,
    )
    different_t0 = verifier.build_evidence(
        _config(
            tmp_path,
            mode="final",
            t0=_T0 + timedelta(days=1),
        ),
        _FakePromtoolClient(anchor=observed_at),
        baseline=baseline,
    )

    assert first["decision"] == exact_replay["decision"] == different_t0["decision"] == "PASS"
    assert first["idempotency_key"] == exact_replay["idempotency_key"]
    assert first["fingerprint"] == exact_replay["fingerprint"]
    assert first["idempotency_key"] != different_t0["idempotency_key"]
    assert first["fingerprint"] != different_t0["fingerprint"]

    output_name = "final.json"
    assert verifier.write_evidence_new_only(tmp_path, output_name, first) == "published"
    before = (tmp_path / output_name).read_bytes()
    assert (
        verifier.write_evidence_new_only(tmp_path, output_name, exact_replay) == "identical_replay"
    )
    assert (tmp_path / output_name).read_bytes() == before


def test_checkpoint_pass_cross_fields_are_admitted(tmp_path: Path) -> None:
    baseline = _passing_baseline(tmp_path)
    checkpoint = verifier.build_evidence(
        _config(tmp_path, mode="checkpoint"),
        _FakePromtoolClient(anchor=_T0 + timedelta(days=1)),
        baseline=baseline,
    )

    assert checkpoint["decision"] == "PASS"
    verifier._validate_evidence_asset(checkpoint)


def test_wrong_target_topology_and_retention_fail_closed(tmp_path: Path) -> None:
    evidence = verifier.build_evidence(
        _config(tmp_path, mode="baseline"),
        _FakePromtoolClient(
            overrides={"count(up": 2.0},
            snapshot=_live_snapshot(
                api_containers=2,
                prometheus_containers=2,
                uvicorn_processes=2,
                retention_days=44,
            ),
        ),
    )

    assert evidence["decision"] == "HOLD"
    assert set(evidence["reasons"]) >= {
        "target_count_mismatch",
        "topology_mismatch",
        "retention_too_short",
    }


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_evaluator_rejects_nonfinite_client_values(tmp_path: Path, value: float) -> None:
    evidence = verifier.build_evidence(
        _config(tmp_path, mode="baseline"),
        _FakePromtoolClient(overrides={"count(up": value}),
    )

    assert evidence["decision"] == "HOLD"
    assert "promtool_value_nonfinite" in evidence["reasons"]
    target = evidence["target"]
    assert isinstance(target, dict)
    assert target["observed_count"] is None


def test_identity_drift_invalidates_checkpoint_baseline(tmp_path: Path) -> None:
    evidence = verifier.build_evidence(
        _config(tmp_path, mode="checkpoint"),
        _FakePromtoolClient(
            snapshot=_live_snapshot(release_id=_RELEASE_B),
            anchor=_T0 + timedelta(days=1),
        ),
        baseline=_passing_baseline(tmp_path),
    )

    assert evidence["decision"] == "HOLD"
    assert "baseline_evidence_invalid_or_drifted" in evidence["reasons"]


def test_runtime_replacement_between_censuses_forces_hold(tmp_path: Path) -> None:
    replacement = _live_snapshot(
        app_container_id="d" * 64,
        prometheus_container_id="e" * 64,
        process_identity="sha256:" + "f" * 64,
    )
    evidence = verifier.build_evidence(
        _config(tmp_path, mode="baseline"),
        _FakePromtoolClient(post_snapshot=replacement),
    )

    assert evidence["decision"] == "HOLD"
    assert "runtime_identity_drift" in evidence["reasons"]
    window = evidence["window"]
    assert isinstance(window, dict)
    assert window["complete"] is False


def test_missing_live_release_identity_forces_hold(tmp_path: Path) -> None:
    evidence = verifier.build_evidence(
        _config(tmp_path, mode="baseline"),
        _FakePromtoolClient(snapshot=verifier.VerificationError("release_identity_unavailable")),
    )

    assert evidence["decision"] == "HOLD"
    assert set(evidence["reasons"]) >= {
        "live_snapshot_unavailable",
        "release_identity_unavailable",
    }
    identities = evidence["identities"]
    assert isinstance(identities, dict)
    assert identities["release"] is None


@pytest.mark.parametrize(
    ("fragment", "value", "reason_fragment"),
    [
        ('route="/api/v1/premium/bmr"}', 1.0, "alias_bmr_current_positive"),
        ("increase(http_requests_total", 1.0, "increase_positive"),
        ("increase(http_requests_total", -1.0, "increase_negative"),
        (
            'route="/api/v1/premium/bmr"}',
            verifier.VerificationError("promtool_vector_missing"),
            "alias_bmr_current_missing",
        ),
    ],
)
def test_alias_missing_positive_and_negative_values_hold(
    tmp_path: Path,
    fragment: str,
    value: float | verifier.VerificationError,
    reason_fragment: str,
) -> None:
    evidence = verifier.build_evidence(
        _config(tmp_path, mode="final", t0=_T0),
        _FakePromtoolClient(
            overrides={fragment: value},
            anchor=_T0 + timedelta(days=30),
        ),
        baseline=_passing_baseline(tmp_path),
    )

    assert evidence["decision"] == "HOLD"
    assert any(reason_fragment in reason for reason in evidence["reasons"])


def test_gap_reset_restart_and_short_window_each_force_hold(tmp_path: Path) -> None:
    evidence = verifier.build_evidence(
        _config(tmp_path, mode="final", t0=_T0),
        _FakePromtoolClient(
            overrides={
                "min_over_time": 0.0,
                "count_over_time": 80_000.0,
                "changes(process_start_time": 1.0,
                "resets(http_requests_total": 1.0,
            },
            anchor=_T0 + timedelta(days=29),
        ),
        baseline=_passing_baseline(tmp_path),
    )

    assert evidence["decision"] == "HOLD"
    reasons = set(evidence["reasons"])
    assert "final_window_too_short" in reasons
    assert "scrape_gap_detected" in reasons
    assert "sample_count_too_low" in reasons
    assert "process_restart_positive" in reasons
    assert any(reason.endswith("_reset_positive") for reason in reasons)


def test_malformed_baseline_file_is_rejected_without_coercion(tmp_path: Path) -> None:
    baseline_file = tmp_path / "baseline.json"
    baseline_file.write_text('{"schema": NaN}', encoding="utf-8")

    with pytest.raises(verifier.VerificationError, match="baseline_evidence_invalid"):
        verifier._read_bounded_regular_json(baseline_file)


def test_deeply_nested_promtool_and_inspect_json_fail_closed() -> None:
    deeply_nested = ("[" * 2_000 + "0" + "]" * 2_000).encode()

    with pytest.raises(verifier.VerificationError, match="promtool_result_invalid"):
        verifier._parse_promtool_vector(deeply_nested)
    with pytest.raises(verifier.VerificationError, match="container_inspect_invalid"):
        verifier._parse_container_inspect(deeply_nested)


def _tar_payload(
    members: list[tuple[str, bytes, bytes, str]],
) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, data, member_type, link_name in members:
            member = tarfile.TarInfo(name)
            member.type = member_type
            member.linkname = link_name
            member.size = len(data) if member_type == tarfile.REGTYPE else 0
            archive.addfile(member, io.BytesIO(data) if member_type == tarfile.REGTYPE else None)
    return buffer.getvalue()


def test_container_config_tar_hashes_exact_safe_member() -> None:
    config_bytes = b"global:\n  scrape_interval: 30s\n"
    payload = _tar_payload([("prometheus.yml", config_bytes, tarfile.REGTYPE, "")])

    assert verifier._hash_container_config_tar(payload) == (
        "sha256:" + hashlib.sha256(config_bytes).hexdigest()
    )


@pytest.mark.parametrize(
    "suffix",
    [
        _tar_payload([("prometheus.yml", b"second", tarfile.REGTYPE, "")]),
        b"trailing-garbage",
    ],
)
def test_container_config_tar_rejects_concatenated_or_trailing_data(suffix: bytes) -> None:
    valid = _tar_payload([("prometheus.yml", b"first", tarfile.REGTYPE, "")])

    with pytest.raises(verifier.VerificationError, match="prometheus_config_tar_invalid"):
        verifier._hash_container_config_tar(valid + suffix)


@pytest.mark.parametrize(
    "members",
    [
        [("../prometheus.yml", b"x", tarfile.REGTYPE, "")],
        [("prometheus.yml", b"", tarfile.SYMTYPE, "target")],
        [("prometheus.yml", b"", tarfile.CHRTYPE, "")],
        [("other.yml", b"x", tarfile.REGTYPE, "")],
        [
            ("prometheus.yml", b"first", tarfile.REGTYPE, ""),
            ("prometheus.yml", b"second", tarfile.REGTYPE, ""),
        ],
    ],
)
def test_container_config_tar_rejects_unsafe_members(
    tmp_path: Path,
    members: list[tuple[str, bytes, bytes, str]],
) -> None:
    with pytest.raises(verifier.VerificationError, match="prometheus_config_tar_invalid"):
        verifier._hash_container_config_tar(_tar_payload(members))
    evidence = verifier.build_evidence(
        _config(tmp_path, mode="baseline"),
        _FakePromtoolClient(snapshot=verifier.VerificationError("prometheus_config_tar_invalid")),
    )
    assert evidence["decision"] == "HOLD"
    assert "prometheus_config_tar_invalid" in evidence["reasons"]


def test_container_config_tar_rejects_oversized_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verifier, "MAX_JSON_BYTES", 128)
    payload = _tar_payload([("prometheus.yml", b"x" * 256, tarfile.REGTYPE, "")])

    with pytest.raises(verifier.VerificationError, match="prometheus_config_tar_invalid"):
        verifier._hash_container_config_tar(payload)
    evidence = verifier.build_evidence(
        _config(tmp_path, mode="baseline"),
        _FakePromtoolClient(snapshot=verifier.VerificationError("prometheus_config_tar_invalid")),
    )
    assert evidence["decision"] == "HOLD"


@pytest.mark.parametrize(
    "image_reference",
    [
        "prom/prometheus:v3.14.0-distroless",
        "https://registry.example/prometheus@" + _DIGEST_B,
        "user:password@registry.example/prometheus@" + _DIGEST_B,
        "prom/prometheus@sha256:" + "A" * 64,
    ],
)
def test_tag_only_or_malformed_prometheus_image_reference_forces_hold(
    tmp_path: Path,
    image_reference: str,
) -> None:
    with pytest.raises(
        verifier.VerificationError,
        match="prometheus_image_reference_invalid",
    ):
        verifier._parse_pinned_image_reference(image_reference)

    evidence = verifier.build_evidence(
        _config(tmp_path, mode="baseline"),
        _FakePromtoolClient(
            snapshot=verifier.VerificationError("prometheus_image_reference_invalid")
        ),
    )
    assert evidence["decision"] == "HOLD"
    assert "prometheus_image_reference_invalid" in evidence["reasons"]


@pytest.mark.parametrize(
    "program",
    [
        "import sys; sys.stdout.write('x' * 4096)",
        "import sys; sys.stderr.write('x' * 4096)",
    ],
)
def test_docker_streaming_collection_rejects_oversized_stdout_and_stderr(
    monkeypatch: pytest.MonkeyPatch,
    program: str,
) -> None:
    monkeypatch.setattr(verifier, "MAX_JSON_BYTES", 128)
    client = verifier.DockerPromtoolClient(
        docker=sys.executable,
        compose_file=Path("deploy/compose.yaml"),
    )

    with pytest.raises(verifier.VerificationError, match="docker_output_limit"):
        client._run_docker(["-c", program], error_code="synthetic_execution_failed")


def test_docker_streaming_collection_times_out_and_cleans_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verifier, "COMMAND_TIMEOUT_SECONDS", 0.05)
    client = verifier.DockerPromtoolClient(
        docker=sys.executable,
        compose_file=Path("deploy/compose.yaml"),
    )

    with pytest.raises(verifier.VerificationError, match="docker_timeout"):
        client._run_docker(
            ["-c", "import time; time.sleep(5)"],
            error_code="synthetic_execution_failed",
        )


def test_async_docker_cancellation_cleans_readers_and_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = verifier.DockerPromtoolClient(
        docker="/absolute/docker",
        compose_file=Path("deploy/compose.yaml"),
    )
    monkeypatch.setattr(verifier, "PROCESS_CLEANUP_TIMEOUT_SECONDS", 0.01)
    reader_state = {"started": 0, "finished": 0}

    class _FakeProcess:
        def __init__(self) -> None:
            self.stdout = asyncio.StreamReader()
            self.stderr = asyncio.StreamReader()
            self.returncode: int | None = None
            self.terminate_calls = 0
            self.kill_calls = 0
            self.wait_calls = 0
            self._never_finishes = asyncio.Event()

        def terminate(self) -> None:
            self.terminate_calls += 1

        def kill(self) -> None:
            self.kill_calls += 1
            self.returncode = -9

        async def wait(self) -> int:
            self.wait_calls += 1
            if self.returncode is None:
                await self._never_finishes.wait()
            assert self.returncode is not None
            return self.returncode

    async def _scenario() -> _FakeProcess:
        process = _FakeProcess()
        spawned = asyncio.Event()
        both_readers_started = asyncio.Event()

        async def _create_process(
            *argv: str,
            stdout: object,
            stderr: object,
        ) -> _FakeProcess:
            assert argv == ("/absolute/docker", "version")
            assert stdout is asyncio.subprocess.PIPE
            assert stderr is asyncio.subprocess.PIPE
            spawned.set()
            return process

        original_reader = client._read_bounded_stream

        async def _tracked_reader(
            stream: asyncio.StreamReader,
            target: bytearray,
            aggregate_size: list[int],
        ) -> None:
            reader_state["started"] += 1
            if reader_state["started"] == 2:
                both_readers_started.set()
            try:
                await original_reader(stream, target, aggregate_size)
            finally:
                reader_state["finished"] += 1

        monkeypatch.setattr(verifier.asyncio, "create_subprocess_exec", _create_process)
        monkeypatch.setattr(client, "_read_bounded_stream", _tracked_reader)
        task = asyncio.create_task(
            client._run_docker_async(["version"], error_code="synthetic_failed")
        )
        await spawned.wait()
        await both_readers_started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return process

    process = asyncio.run(_scenario())

    assert reader_state == {"started": 2, "finished": 2}
    assert process.terminate_calls == 1
    assert process.kill_calls == 1
    assert process.wait_calls >= 2
    assert process.returncode == -9


def test_sync_docker_runner_rejects_active_event_loop_before_spawn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = verifier.DockerPromtoolClient(
        docker="/absolute/docker",
        compose_file=Path("deploy/compose.yaml"),
    )
    spawn_calls = 0

    async def _scenario() -> None:
        async def _unexpected_spawn(*_argv: str, **_kwargs: object) -> None:
            nonlocal spawn_calls
            spawn_calls += 1

        monkeypatch.setattr(verifier.asyncio, "create_subprocess_exec", _unexpected_spawn)
        with pytest.raises(verifier.VerificationError, match="docker_sync_context_invalid"):
            client._run_docker(["version"], error_code="synthetic_failed")

    asyncio.run(_scenario())

    assert spawn_calls == 0


def test_docker_promtool_uses_absolute_argv_without_shell(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "prometheus.yml"
    host_config_bytes = b"global:\n  scrape_interval: 99s\n"
    container_config_bytes = b"global:\n  scrape_interval: 30s\n"
    config_file.write_bytes(host_config_bytes)
    config_tar = tmp_path / "container-config.tar"
    with tarfile.open(config_tar, mode="w") as archive:
        member = tarfile.TarInfo("prometheus.yml")
        member.size = len(container_config_bytes)
        archive.addfile(member, io.BytesIO(container_config_bytes))
    app_id = _APP_CONTAINER_A
    prometheus_id = _PROMETHEUS_CONTAINER_A
    call_log = tmp_path / "docker-calls.jsonl"
    inspect_payload = [
        [
            {
                "Id": app_id,
                "Image": _DIGEST_A,
                "Config": {"Labels": {"org.opencontainers.image.revision": _RELEASE_A}},
            },
            {
                "Id": prometheus_id,
                "Image": _DIGEST_B,
                "Config": {"Image": _PROMETHEUS_REFERENCE},
                "Args": [
                    "--config.file=/etc/prometheus/prometheus.yml",
                    "--storage.tsdb.retention.time=45d",
                ],
                "Mounts": [
                    {
                        "Type": "bind",
                        "Source": os.fspath(config_file),
                        "Destination": "/etc/prometheus/prometheus.yml",
                    },
                    {
                        "Type": "volume",
                        "Name": "prometheus-data-01",
                        "Destination": "/prometheus",
                    },
                ],
            },
        ]
    ][0]
    fake_docker = tmp_path / "docker"
    fake_docker.write_text(
        f"""#!{sys.executable}
import json
import sys

args = sys.argv[1:]
with open({os.fspath(call_log)!r}, "a", encoding="utf-8") as stream:
    stream.write(json.dumps(args, separators=(",", ":")) + "\\n")
if args[-3:] == ["ps", "-q", "app"]:
    print({app_id!r})
elif args[-3:] == ["ps", "-q", "prometheus"]:
    print({prometheus_id!r})
elif args[:3] == ["inspect", {app_id!r}, {prometheus_id!r}]:
    print(json.dumps({inspect_payload!r}, separators=(",", ":")))
elif args == ["cp", {f'{prometheus_id}:/etc/prometheus/prometheus.yml'!r}, "-"]:
    with open({os.fspath(config_tar)!r}, "rb") as stream:
        sys.stdout.buffer.write(stream.read())
elif args[:2] == ["top", {app_id!r}]:
    print("PID STARTED COMMAND")
    print("101 Fri Aug 22 12:00:00 2026 /usr/local/bin/python -m uvicorn app.main:app")
elif "/bin/promtool" in args and "query" in args:
    expression = args[-1]
    timestamp = {_T0.timestamp()!r}
    if expression == "time()":
        value = timestamp
    elif expression.startswith("count(up") or expression.startswith("min(up"):
        value = 1.0
    elif expression.startswith("count_over_time"):
        value = {float(verifier.FINAL_MIN_SAMPLES)!r}
    else:
        value = 0.0
    print(json.dumps({{"status": "success", "data": {{"resultType": "vector", "result": [{{"metric": {{}}, "value": [timestamp, str(value)]}}]}}}}, separators=(",", ":")))
elif "/bin/promtool" in args:
    print("Prometheus is Healthy.")
else:
    raise SystemExit(9)
""",
        encoding="utf-8",
    )
    fake_docker.chmod(0o700)
    client = verifier.DockerPromtoolClient(
        docker=os.fspath(fake_docker),
        compose_file=Path("deploy/compose.yaml"),
    )

    snapshot = client.collect_live_snapshot()
    assert client.check_healthy() is True
    assert client.check_ready() is True
    anchor = client.get_evaluation_anchor()
    assert anchor == _T0
    assert client.query_scalar("sum(up)", evaluation_time="2026-08-22T12:00:00Z") == 0.0
    process_identity = verifier._sha256_fingerprint(
        b"101 Fri Aug 22 12:00:00 2026 /usr/local/bin/python -m uvicorn app.main:app"
    )
    assert snapshot == verifier.LiveRuntimeSnapshot(
        app_container_id=app_id,
        prometheus_container_id=prometheus_id,
        release_id=_RELEASE_A,
        app_image_id=_DIGEST_A,
        prometheus_image_id=_DIGEST_B,
        prometheus_image_reference=_PROMETHEUS_REFERENCE,
        config_sha256="sha256:" + hashlib.sha256(container_config_bytes).hexdigest(),
        volume_id="prometheus-data-01",
        api_container_count=1,
        prometheus_container_count=1,
        uvicorn_process_count=1,
        uvicorn_process_identity=process_identity,
        retention_days=45,
    )
    assert os.fspath(config_file) not in repr(snapshot)
    assert snapshot.config_sha256 != "sha256:" + hashlib.sha256(host_config_bytes).hexdigest()

    calls = [json.loads(line) for line in call_log.read_text(encoding="utf-8").splitlines()]
    assert len(calls) == 9
    assert [call[-3:] for call in calls[:2]] == [
        ["ps", "-q", "app"],
        ["ps", "-q", "prometheus"],
    ]
    assert calls[2] == ["inspect", app_id, prometheus_id]
    assert calls[3] == ["cp", f"{prometheus_id}:/etc/prometheus/prometheus.yml", "-"]
    assert calls[4] == ["top", app_id, "-eo", "pid,lstart,args"]
    assert all(call[:3] == ["exec", prometheus_id, "/bin/promtool"] for call in calls[5:])
    assert "--time=2026-08-22T12:00:00Z" not in calls[7]
    assert "--time=2026-08-22T12:00:00Z" in calls[8]


def test_evidence_writer_is_private_and_identical_replay_is_no_write(tmp_path: Path) -> None:
    evidence = _passing_baseline(tmp_path)
    output_name = "baseline.json"

    assert verifier.write_evidence_new_only(tmp_path, output_name, evidence) == "published"

    output_file = tmp_path / output_name
    assert stat.S_IMODE(output_file.stat().st_mode) == 0o600
    assert json.loads(output_file.read_text(encoding="utf-8"))["decision"] == "PASS"
    before = output_file.stat()
    before_bytes = output_file.read_bytes()

    assert verifier.write_evidence_new_only(tmp_path, output_name, evidence) == "identical_replay"

    after = output_file.stat()
    assert (after.st_ino, after.st_mtime_ns, output_file.read_bytes()) == (
        before.st_ino,
        before.st_mtime_ns,
        before_bytes,
    )


def test_evidence_writer_rejects_divergent_and_different_idempotency(
    tmp_path: Path,
) -> None:
    evidence = _passing_baseline(tmp_path)
    verifier.write_evidence_new_only(tmp_path, "baseline.json", evidence)

    divergent = copy.deepcopy(evidence)
    divergent["decision"] = "HOLD"
    divergent["reasons"] = ["synthetic_divergence"]
    divergent["fingerprint"] = verifier._sha256_fingerprint(
        verifier._canonical_object_bytes(verifier._fingerprint_projection(divergent))
    )
    verifier._validate_evidence_asset(divergent)
    with pytest.raises(verifier.VerificationError, match="evidence_replay_divergent"):
        verifier.write_evidence_new_only(tmp_path, "baseline.json", divergent)

    different_identity = verifier.build_evidence(
        _config(tmp_path, mode="baseline"),
        _FakePromtoolClient(anchor=_T0 + timedelta(seconds=1)),
    )
    with pytest.raises(verifier.VerificationError, match="evidence_idempotency_collision"):
        verifier.write_evidence_new_only(tmp_path, "baseline.json", different_identity)


def test_evidence_writer_rejects_malformed_existing_and_symlink(tmp_path: Path) -> None:
    evidence = _passing_baseline(tmp_path)
    malformed = tmp_path / "malformed.json"
    malformed.write_text("not-json", encoding="utf-8")
    malformed.chmod(0o600)
    with pytest.raises(verifier.VerificationError, match="evidence_existing_malformed"):
        verifier.write_evidence_new_only(tmp_path, "malformed.json", evidence)

    target = tmp_path / "target.json"
    target.write_text("preserve", encoding="utf-8")
    symlink = tmp_path / "symlink.json"
    symlink.symlink_to(target)
    with pytest.raises(verifier.VerificationError, match="evidence_existing_malformed"):
        verifier.write_evidence_new_only(tmp_path, "symlink.json", evidence)
    assert target.read_text(encoding="utf-8") == "preserve"


def _recompute_self_metadata(evidence: dict[str, object]) -> None:
    evidence["idempotency_key"] = verifier._sha256_fingerprint(
        verifier._canonical_object_bytes(verifier._idempotency_projection(evidence))
    )
    evidence["fingerprint"] = verifier._sha256_fingerprint(
        verifier._canonical_object_bytes(verifier._fingerprint_projection(evidence))
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "authority_true",
        "unknown_schema",
        "unknown_mode",
        "unknown_decision",
        "missing_top_level",
        "extra_top_level",
    ],
)
def test_writer_rejects_recomputed_fingerprint_invalid_evidence_shapes(
    tmp_path: Path,
    mutation: str,
) -> None:
    evidence = copy.deepcopy(_passing_baseline(tmp_path))
    if mutation == "authority_true":
        evidence["authority"] = {
            "sets_t0": True,
            "authorizes_deploy": False,
            "authorizes_alias_removal": False,
        }
    elif mutation == "unknown_schema":
        evidence["schema"] = "pulseplate.unknown.v1"
    elif mutation == "unknown_mode":
        evidence["mode"] = "preview"
    elif mutation == "unknown_decision":
        evidence["decision"] = "ALLOW"
    elif mutation == "missing_top_level":
        evidence.pop("aliases")
    elif mutation == "extra_top_level":
        evidence["unexpected"] = False
    else:
        raise AssertionError(f"unhandled mutation: {mutation}")
    _recompute_self_metadata(evidence)

    output_name = f"invalid-{mutation}.json"
    with pytest.raises(verifier.VerificationError, match="evidence_asset_invalid"):
        verifier.write_evidence_new_only(tmp_path, output_name, evidence)
    assert not (tmp_path / output_name).exists()


def test_writer_rejects_scheme_image_identity_after_lineage_and_hash_recompute(
    tmp_path: Path,
) -> None:
    evidence = copy.deepcopy(_passing_baseline(tmp_path))
    scheme_reference = "https://registry.example/prometheus@" + _DIGEST_B
    identities = evidence["identities"]
    upstream_assets = evidence["upstream_assets"]
    assert isinstance(identities, dict)
    assert isinstance(upstream_assets, list)
    identities["prometheus_image_reference"] = scheme_reference
    for upstream in upstream_assets:
        if isinstance(upstream, dict) and upstream.get("role") == "prometheus_image_reference":
            upstream["fingerprint"] = verifier._source_fingerprint(
                "prometheus_image_reference",
                scheme_reference,
            )
    _recompute_self_metadata(evidence)

    with pytest.raises(verifier.VerificationError, match="evidence_asset_invalid"):
        verifier.write_evidence_new_only(tmp_path, "scheme-reference.json", evidence)


@pytest.mark.parametrize(
    "mutation",
    [
        "minimum_up_zero",
        "restart_one",
        "alias_increase_nine",
        "t0_none",
        "expected_count_bool",
        "mode_list",
        "alias_observation_list",
    ],
)
def test_writer_rejects_recomputed_invalid_pass_cross_fields(
    tmp_path: Path,
    mutation: str,
) -> None:
    baseline = _passing_baseline(tmp_path)
    evidence = verifier.build_evidence(
        _config(tmp_path, mode="final", t0=_T0),
        _FakePromtoolClient(anchor=_T0 + timedelta(days=30)),
        baseline=baseline,
    )
    assert evidence["decision"] == "PASS"
    target = evidence["target"]
    aliases = evidence["aliases"]
    window = evidence["window"]
    assert isinstance(target, dict)
    assert isinstance(aliases, list)
    assert isinstance(window, dict)
    if mutation == "minimum_up_zero":
        target["minimum_up"] = 0.0
    elif mutation == "restart_one":
        target["restart_changes"] = 1.0
    elif mutation == "alias_increase_nine":
        first_alias = aliases[0]
        assert isinstance(first_alias, dict)
        first_alias["increase"] = 9.0
        first_alias["observation"] = "observed_exact_zero"
    elif mutation == "t0_none":
        window["t0"] = None
    elif mutation == "expected_count_bool":
        target["expected_count"] = True
    elif mutation == "mode_list":
        evidence["mode"] = []
    elif mutation == "alias_observation_list":
        first_alias = aliases[0]
        assert isinstance(first_alias, dict)
        first_alias["observation"] = []
    else:
        raise AssertionError(f"unhandled mutation: {mutation}")
    _recompute_self_metadata(evidence)

    with pytest.raises(verifier.VerificationError, match="evidence_asset_invalid"):
        verifier.write_evidence_new_only(tmp_path, f"invalid-pass-{mutation}.json", evidence)
