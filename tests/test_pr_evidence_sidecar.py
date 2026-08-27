"""Focused contract and threat-model tests for PR evidence sidecar v1."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from scripts.orchestration import pr_evidence_sidecar as sidecar

SHA_A = "a" * 40
SHA_B = "b" * 40
REF = "sha256:" + "c" * 64


@pytest.fixture
def isolated_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Bind both repo-relative input resolution and storage to a private tree."""

    monkeypatch.setattr(sidecar, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        sidecar,
        "STORE_ROOT",
        tmp_path / "artifacts/orchestration/pr_evidence_sidecars",
    )
    return tmp_path


def _packet(root: Path, *, raw: bytes | None = None) -> Path:
    packet_root = root / "artifacts/orchestration/task_packets"
    packet_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = packet_root / f"{'1' * 12}.json"
    path.write_bytes(
        raw
        if raw is not None
        else json.dumps(
            {"schema_version": "3.1", "task_packet_id": "1" * 12, "extra": True},
            separators=(",", ":"),
        ).encode()
    )
    return path


def _prepare(root: Path, rails: list[str] | None = None) -> dict[str, object]:
    return sidecar.prepare(_packet(root), SHA_A, rails or ["experiment_runner"])


def _terminal(root: Path, prepared: dict[str, object]) -> Path:
    start = json.loads((root / str(prepared["sidecar_path"])).read_text())
    applicable = set(start["applicable_rails"])
    path = root / "terminal-input.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": sidecar.TERMINAL_INPUT_SCHEMA,
                "pr_number": 2342,
                "observed_pr_terminal_state": "merged",
                "material_head_sha": SHA_B,
                "merge_commit_sha": SHA_A,
                "rails": {
                    rail: (
                        {
                            "applicable": True,
                            "status": "referenced",
                            "reference_fingerprint": REF,
                        }
                        if rail in applicable
                        else {
                            "applicable": False,
                            "status": "not_applicable",
                            "reference_fingerprint": None,
                        }
                    )
                    for rail in sidecar.RAILS
                },
                "operator_observations": {
                    "operator_minutes": 12,
                    "review_cycles": 2,
                    "repair_cycles": 1,
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_self_fingerprinted_start(path: Path, value: dict[str, object]) -> None:
    unsigned = dict(value)
    unsigned.pop("receipt_fingerprint", None)
    unsigned["receipt_fingerprint"] = sidecar._fingerprint(unsigned)
    path.write_bytes(sidecar._canonical(unsigned))
    path.chmod(0o600)


def test_prepare_is_content_bound_private_and_replay_safe(isolated_store: Path) -> None:
    """Canonical replay is no-write and receipts are private/non-authoritative."""

    first = _prepare(isolated_store, ["teleology", "experiment_runner"])
    second = sidecar.prepare(
        isolated_store / f"artifacts/orchestration/task_packets/{'1' * 12}.json",
        SHA_A,
        ["experiment_runner", "teleology"],
    )

    assert first["created"] is True
    assert second == {**first, "created": False}
    assert set(first) == {"schema_version", "command", "sidecar_id", "sidecar_path", "created"}
    receipt_path = isolated_store / str(first["sidecar_path"])
    receipt = json.loads(receipt_path.read_text())
    assert receipt["authority"] == sidecar.AUTHORITY
    assert receipt["repository"] == sidecar.REPOSITORY
    assert all(value is False for value in receipt["authority"].values())
    assert set(receipt["authority"]) == {
        "implementation_authority",
        "routing_authority",
        "review_authority",
        "approval_authority",
        "promotion_authority",
        "merge_authority",
        "release_authority",
        "enrollment_authority",
        "causality_authority",
        "outcome_authority",
        "ci_authority",
    }
    assert "no review" in receipt["disclaimer"]
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(receipt_path.parent.stat().st_mode) == 0o700


@pytest.mark.parametrize(
    "raw",
    [
        b'\xef\xbb\xbf{"schema_version":"3.1","task_packet_id":"111111111111"}',
        b'{"schema_version":"3.1","task_packet_id":"111111111111","task_packet_id":"222222222222"}',
        b'{"schema_version":"3.1","task_packet_id":"111111111111"} trailing',
        b"\xff",
        b"[]",
        b'{"schema_version":"3.0","task_packet_id":"111111111111"}',
    ],
)
def test_prepare_rejects_noncanonical_or_wrong_packet(raw: bytes, isolated_store: Path) -> None:
    """Packet intake is bounded strict JSON with the minimal 3.1 contract."""

    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.prepare(_packet(isolated_store, raw=raw), SHA_A, ["experiment_runner"])


def test_prepare_rejects_links_and_duplicate_rails(isolated_store: Path) -> None:
    """Input aliases and ambiguous applicability are rejected."""

    packet = _packet(isolated_store)
    linked = isolated_store / "linked.json"
    os.link(packet, linked)
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.prepare(linked, SHA_A, ["experiment_runner"])
    packet.unlink()
    linked.unlink()
    _packet(isolated_store)
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.prepare(
            isolated_store / f"artifacts/orchestration/task_packets/{'1' * 12}.json",
            SHA_A,
            ["experiment_runner", "experiment_runner"],
        )


def test_prepare_rejects_oversize_without_unbounded_read(isolated_store: Path) -> None:
    """Descriptor intake stops after the configured bound plus one byte."""

    packet = _packet(isolated_store)
    packet.write_bytes(b"{" + (b" " * sidecar.MAX_PACKET_BYTES))
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.prepare(packet, SHA_A, ["experiment_runner"])


@pytest.mark.parametrize("dangling", [False, True])
def test_prepare_rejects_replaced_or_dangling_packet_symlink(
    dangling: bool,
    isolated_store: Path,
) -> None:
    """O_NOFOLLOW rejects live replacement aliases and dangling aliases."""

    packet = _packet(isolated_store)
    target = isolated_store / "target.json"
    packet.replace(target)
    packet.symlink_to(isolated_store / "missing.json" if dangling else target)
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.prepare(packet, SHA_A, ["experiment_runner"])


def test_prepare_rejects_symlinked_packet_ancestor(isolated_store: Path) -> None:
    """Canonical packet-root validation rejects a symlinked ancestor component."""

    artifacts = isolated_store / "artifacts"
    real_artifacts = isolated_store / "real-artifacts"
    real_artifacts.mkdir()
    artifacts.symlink_to(real_artifacts, target_is_directory=True)
    packet_root = real_artifacts / "orchestration/task_packets"
    packet_root.mkdir(parents=True)
    packet = packet_root / f"{'1' * 12}.json"
    packet.write_text(
        json.dumps({"schema_version": "3.1", "task_packet_id": "1" * 12}),
        encoding="utf-8",
    )
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.prepare(
            isolated_store / "artifacts/orchestration/task_packets" / packet.name,
            SHA_A,
            ["experiment_runner"],
        )


def test_prepare_requires_canonical_packet_root_and_matching_filename(
    isolated_store: Path,
) -> None:
    """Outside paths and packet-id filename drift are rejected."""

    outside = isolated_store / "outside.json"
    outside.write_text(
        json.dumps({"schema_version": "3.1", "task_packet_id": "1" * 12}),
        encoding="utf-8",
    )
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.prepare(outside, SHA_A, ["experiment_runner"])
    packet = _packet(isolated_store)
    mismatched = packet.with_name(f"{'2' * 12}.json")
    packet.replace(mismatched)
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.prepare(mismatched, SHA_A, ["experiment_runner"])


def test_prepare_rejects_nonfinite_packet_json(isolated_store: Path) -> None:
    """NaN and Infinity are outside the strict JSON contract."""

    for constant in ("NaN", "Infinity", "-Infinity"):
        packet = _packet(
            isolated_store,
            raw=(
                '{"schema_version":"3.1","task_packet_id":"111111111111",' f'"value":{constant}}}'
            ).encode(),
        )
        with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
            sidecar.prepare(packet, SHA_A, ["experiment_runner"])


def test_prepare_cli_maps_deep_json_recursion_to_category_only_error(
    isolated_store: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deep size-bounded JSON cannot escape the stable CLI error contract."""

    packet = _packet(isolated_store)

    def recurse(_decoder: json.JSONDecoder, _text: str) -> tuple[object, int]:
        raise RecursionError

    monkeypatch.setattr(
        sidecar.json.JSONDecoder,
        "raw_decode",
        recurse,
    )

    result = sidecar.main(
        [
            "prepare",
            "--packet",
            str(packet.relative_to(isolated_store)),
            "--base-sha",
            SHA_A,
            "--applicable-rail",
            "experiment_runner",
        ]
    )
    captured = capsys.readouterr()

    assert result == 1
    assert captured.out == ""
    assert captured.err == "INVALID_INPUT\n"


def test_finalize_binds_start_and_enforces_rail_truth(isolated_store: Path) -> None:
    """Terminal applicability mirrors start and referenced rails require full hashes."""

    prepared = _prepare(isolated_store, ["euler"])
    terminal_input = _terminal(isolated_store, prepared)
    result = sidecar.finalize(str(prepared["sidecar_id"]), terminal_input.name)

    assert result["created"] is True
    terminal = json.loads((isolated_store / str(result["sidecar_path"])).read_text())
    assert terminal["causal_status"] == "not_assessed"
    assert terminal["start_receipt_fingerprint"].startswith("sha256:")
    assert terminal["authority"] == sidecar.AUTHORITY
    assert sidecar.validate(str(prepared["sidecar_id"]))["receipt_state"] == "terminal_recorded"

    divergent = json.loads(terminal_input.read_text())
    divergent["rails"]["euler"] = {
        "applicable": False,
        "status": "not_applicable",
        "reference_fingerprint": None,
    }
    terminal_input.write_text(json.dumps(divergent), encoding="utf-8")
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.finalize(str(prepared["sidecar_id"]), terminal_input.name)


def test_finalize_replay_is_idempotent_and_divergence_conflicts(isolated_store: Path) -> None:
    """Terminal receipt creation is immutable under replay."""

    prepared = _prepare(isolated_store)
    terminal_input = _terminal(isolated_store, prepared)
    first = sidecar.finalize(str(prepared["sidecar_id"]), terminal_input.name)
    second = sidecar.finalize(str(prepared["sidecar_id"]), terminal_input.name)
    assert first["created"] is True
    assert second["created"] is False

    changed = json.loads(terminal_input.read_text())
    changed["operator_observations"]["repair_cycles"] = 4
    terminal_input.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(sidecar.SidecarError, match="CONFLICT"):
        sidecar.finalize(str(prepared["sidecar_id"]), terminal_input.name)


def test_finalize_rejects_path_traversal_unknown_keys_and_bad_observations(
    isolated_store: Path,
) -> None:
    """Terminal input stays repo-relative and exact-schema."""

    prepared = _prepare(isolated_store)
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.finalize(str(prepared["sidecar_id"]), "../terminal.json")
    terminal_input = _terminal(isolated_store, prepared)
    value = json.loads(terminal_input.read_text())
    value["unknown"] = True
    terminal_input.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.finalize(str(prepared["sidecar_id"]), terminal_input.name)
    value.pop("unknown")
    value["operator_observations"]["review_cycles"] = True
    terminal_input.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.finalize(str(prepared["sidecar_id"]), terminal_input.name)


def test_finalize_rejects_nonfinite_json_and_symlinked_parent(isolated_store: Path) -> None:
    """Terminal intake remains finite JSON under real repo directory components."""

    prepared = _prepare(isolated_store)
    terminal_input = _terminal(isolated_store, prepared)
    raw = terminal_input.read_text().replace('"operator_minutes": 12', '"operator_minutes": NaN')
    terminal_input.write_text(raw, encoding="utf-8")
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.finalize(str(prepared["sidecar_id"]), terminal_input.name)

    real_dir = isolated_store / "real-terminal"
    real_dir.mkdir()
    linked_dir = isolated_store / "linked-terminal"
    linked_dir.symlink_to(real_dir, target_is_directory=True)
    target = real_dir / "input.json"
    target.write_text("{}", encoding="utf-8")
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.finalize(str(prepared["sidecar_id"]), "linked-terminal/input.json")


def test_prepare_rejects_symlinked_store_component(isolated_store: Path) -> None:
    """Store creation never traverses a replacement fixed-root component."""

    packet = _packet(isolated_store)
    store = isolated_store / "artifacts/orchestration/pr_evidence_sidecars"
    replacement = isolated_store / "replacement-store"
    replacement.mkdir()
    store.symlink_to(replacement, target_is_directory=True)
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.prepare(packet, SHA_A, ["experiment_runner"])


@pytest.mark.parametrize(
    ("old_key", "replacement_key"),
    [
        ("observed_pr_terminal_state", "terminal_state"),
        ("observed_pr_terminal_state", "outcome"),
        ("operator_observations", "process_metrics"),
        ("operator_observations", "metrics"),
    ],
)
def test_finalize_rejects_old_or_generic_terminal_aliases(
    old_key: str,
    replacement_key: str,
    isolated_store: Path,
) -> None:
    """Legacy/generic terminal and process ontology aliases remain outside v1."""

    prepared = _prepare(isolated_store)
    terminal_input = _terminal(isolated_store, prepared)
    value = json.loads(terminal_input.read_text())
    value[replacement_key] = value.pop(old_key)
    terminal_input.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.finalize(str(prepared["sidecar_id"]), terminal_input.name)


@pytest.mark.parametrize(
    "generic_field",
    [
        "novel_findings_count",
        "false_positive_count",
        "main_regression_observed",
        "rollback_or_hotfix_required",
        "findings",
        "false_positives",
    ],
)
def test_finalize_rejects_outcome_or_quality_observation_fields(
    generic_field: str,
    isolated_store: Path,
) -> None:
    """Operator observations are mechanical effort only, not quality/outcome claims."""

    prepared = _prepare(isolated_store)
    terminal_input = _terminal(isolated_store, prepared)
    value = json.loads(terminal_input.read_text())
    value["operator_observations"][generic_field] = 0
    terminal_input.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.finalize(str(prepared["sidecar_id"]), terminal_input.name)


def test_report_prevalidates_whole_store_before_emitting_counts(isolated_store: Path) -> None:
    """Complete-store aggregation counts starts and integer-only terminal totals."""

    first = _prepare(isolated_store, ["teleology"])
    second_packet = isolated_store / "artifacts/orchestration/task_packets" / f"{'2' * 12}.json"
    second_packet.write_text(
        json.dumps({"schema_version": "3.1", "task_packet_id": "2" * 12}),
        encoding="utf-8",
    )
    second = sidecar.prepare(second_packet, SHA_B, ["euler"])
    sidecar.finalize(str(first["sidecar_id"]), _terminal(isolated_store, first).name)

    report = sidecar.report()
    assert report["counts"]["start_receipts"] == 2
    assert report["counts"]["terminal_receipts"] == 1
    assert report["counts"]["start_only_receipts"] == 1
    assert report["counts"]["observed_merged"] == 1
    assert report["totals"] == {
        "operator_minutes_known": 12,
        "review_cycles": 2,
        "repair_cycles": 1,
    }
    assert report["policy_version"] == sidecar.POLICY_VERSION
    assert report["repository"] == sidecar.REPOSITORY
    assert report["authority"] == sidecar.AUTHORITY
    assert "average" not in json.dumps(report).lower()
    assert sidecar.validate(str(second["sidecar_id"]))["receipt_state"] == "start_recorded"

    (sidecar.STORE_ROOT / "unknown.txt").write_text("bad", encoding="utf-8")
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.report()


def test_validate_rejects_unknown_sibling(isolated_store: Path) -> None:
    """Individual validation enforces the exact sidecar container grammar."""

    prepared = _prepare(isolated_store)
    receipt = isolated_store / str(prepared["sidecar_path"])
    (receipt.parent / ".receipt-poison").write_text("{}", encoding="utf-8")
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.validate(str(prepared["sidecar_id"]))


def test_finalize_rejects_unknown_sibling(isolated_store: Path) -> None:
    """Finalization cannot append to a container outside the exact grammar."""

    prepared = _prepare(isolated_store)
    receipt = isolated_store / str(prepared["sidecar_path"])
    (receipt.parent / "unknown.json").write_text("{}", encoding="utf-8")

    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.finalize(str(prepared["sidecar_id"]), _terminal(isolated_store, prepared).name)


def test_report_rejects_store_over_sidecar_limit(
    isolated_store: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Aggregation is bounded before any receipt counting begins."""

    _prepare(isolated_store)
    monkeypatch.setattr(sidecar, "MAX_SIDECARS", 0)
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.report()


def test_prepare_capacity_allows_replay_and_rejects_new_id_before_directory(
    isolated_store: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exact replay remains valid at capacity, while a new id is rejected."""

    monkeypatch.setattr(sidecar, "MAX_SIDECARS", 1)
    first = _prepare(isolated_store)
    replay = sidecar.prepare(
        isolated_store / f"artifacts/orchestration/task_packets/{'1' * 12}.json",
        SHA_A,
        ["experiment_runner"],
    )
    assert replay["created"] is False
    second_packet = isolated_store / "artifacts/orchestration/task_packets" / f"{'2' * 12}.json"
    second_packet.write_text(
        json.dumps({"schema_version": "3.1", "task_packet_id": "2" * 12}),
        encoding="utf-8",
    )
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.prepare(second_packet, SHA_B, ["euler"])
    assert [entry.name for entry in sidecar.STORE_ROOT.iterdir()] == [str(first["sidecar_id"])[7:]]
    assert sidecar.report()["counts"]["start_receipts"] == 1


def test_out_of_store_stage_residue_cannot_poison_receipt_publication(
    isolated_store: Path,
) -> None:
    """A crash-like sibling stage is ignored and never cleaned as arbitrary state."""

    packet = _packet(isolated_store)
    residue = sidecar.STORE_ROOT.parent / ".pr-evidence-receipt-crash-residue"
    residue.write_text("crash", encoding="utf-8")
    residue.chmod(0o600)
    prepared = sidecar.prepare(packet, SHA_A, ["experiment_runner"])
    terminal_input = _terminal(isolated_store, prepared)
    finalized = sidecar.finalize(str(prepared["sidecar_id"]), terminal_input.name)

    assert residue.read_text(encoding="utf-8") == "crash"
    start_path = isolated_store / str(prepared["sidecar_path"])
    terminal_path = isolated_store / str(finalized["sidecar_path"])
    assert start_path.stat().st_nlink == 1
    assert terminal_path.stat().st_nlink == 1
    assert {entry.name for entry in start_path.parent.iterdir()} == {
        "start.json",
        "terminal.json",
    }
    assert sidecar.validate(str(prepared["sidecar_id"]))["receipt_state"] == "terminal_recorded"
    assert sidecar.report()["counts"]["terminal_receipts"] == 1


def test_report_cli_emits_no_partial_stdout_on_malformed_store(
    isolated_store: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Report errors are category-only and never leak partial aggregates."""

    _prepare(isolated_store)
    (sidecar.STORE_ROOT / "bad").mkdir()
    result = sidecar.main(["report"])
    captured = capsys.readouterr()
    assert result == 1
    assert captured.out == ""
    assert captured.err == "INVALID_INPUT\n"


def test_kernel_rename_noreplace_fails_closed_without_platform_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing platform no-replace rename support never falls back to hardlinks."""

    class MissingLibc:
        pass

    def missing_libc(*_args: object, **_kwargs: object) -> MissingLibc:
        return MissingLibc()

    monkeypatch.setattr(sidecar.ctypes, "CDLL", missing_libc)

    with pytest.raises(sidecar.SidecarError, match="STORAGE_UNAVAILABLE"):
        sidecar._kernel_rename_noreplace(-1, "stage", -1, "start.json")


def test_concurrent_prepare_has_one_creator_and_identical_replays(isolated_store: Path) -> None:
    """No-replace publication has a single creator under a bounded race."""

    packet = _packet(isolated_store)
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(
            executor.map(
                lambda _: sidecar.prepare(packet, SHA_A, ["experiment_runner"]),
                range(16),
            )
        )
    assert sum(result["created"] is True for result in results) == 1
    assert len({str(result["sidecar_id"]) for result in results}) == 1


def test_publisher_lock_blocks_replay_validate_and_report_until_cleanup(
    isolated_store: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Readers and identical replay wait until canonical nlink returns to one."""

    packet = _packet(isolated_store)
    renamed = threading.Event()
    release = threading.Event()
    original_rename = sidecar._kernel_rename_noreplace

    def paused_rename(
        source_fd: int,
        source_name: str,
        destination_fd: int,
        destination_name: str,
    ) -> None:
        original_rename(source_fd, source_name, destination_fd, destination_name)
        renamed.set()
        assert release.wait(timeout=5)

    monkeypatch.setattr(sidecar, "_kernel_rename_noreplace", paused_rename)
    validate_started = threading.Event()
    report_started = threading.Event()

    def run_validate(sidecar_id: str) -> dict[str, object]:
        validate_started.set()
        return sidecar.validate(sidecar_id)

    def run_report() -> dict[str, object]:
        report_started.set()
        return sidecar.report()

    expected_id = sidecar._fingerprint(
        sidecar._start_identity(
            repository=sidecar.REPOSITORY,
            task_packet_id="1" * 12,
            task_packet_fingerprint="sha256:" + hashlib.sha256(packet.read_bytes()).hexdigest(),
            base_sha=SHA_A,
            applicable_rails=["experiment_runner"],
        )
    )
    with ThreadPoolExecutor(max_workers=4) as executor:
        creator = executor.submit(sidecar.prepare, packet, SHA_A, ["experiment_runner"])
        assert renamed.wait(timeout=5)
        replay = executor.submit(sidecar.prepare, packet, SHA_A, ["experiment_runner"])
        validation = executor.submit(run_validate, expected_id)
        reporting = executor.submit(run_report)
        assert validate_started.wait(timeout=5)
        assert report_started.wait(timeout=5)
        assert not replay.done()
        assert not validation.done()
        assert not reporting.done()
        release.set()
        assert creator.result(timeout=5)["created"] is True
        assert replay.result(timeout=5)["created"] is False
        assert validation.result(timeout=5)["receipt_state"] == "start_recorded"
        assert reporting.result(timeout=5)["counts"]["start_receipts"] == 1


def test_finalize_lock_serializes_identical_and_divergent_replays(
    isolated_store: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Terminal publication blocks both replay classes until receipt cleanup."""

    prepared = _prepare(isolated_store)
    terminal_input = _terminal(isolated_store, prepared)
    identical_input = isolated_store / "identical-terminal.json"
    identical_input.write_bytes(terminal_input.read_bytes())
    divergent_input = isolated_store / "divergent-terminal.json"
    divergent = json.loads(terminal_input.read_text())
    divergent["operator_observations"]["repair_cycles"] += 1
    divergent_input.write_text(json.dumps(divergent), encoding="utf-8")
    renamed = threading.Event()
    release = threading.Event()
    original_rename = sidecar._kernel_rename_noreplace

    def paused_rename(
        source_fd: int,
        source_name: str,
        destination_fd: int,
        destination_name: str,
    ) -> None:
        original_rename(source_fd, source_name, destination_fd, destination_name)
        renamed.set()
        assert release.wait(timeout=5)

    monkeypatch.setattr(sidecar, "_kernel_rename_noreplace", paused_rename)
    sidecar_id = str(prepared["sidecar_id"])
    with ThreadPoolExecutor(max_workers=3) as executor:
        creator = executor.submit(sidecar.finalize, sidecar_id, terminal_input.name)
        assert renamed.wait(timeout=5)
        identical = executor.submit(sidecar.finalize, sidecar_id, identical_input.name)
        divergent_future = executor.submit(sidecar.finalize, sidecar_id, divergent_input.name)
        assert not identical.done()
        assert not divergent_future.done()
        release.set()
        assert creator.result(timeout=5)["created"] is True
        assert identical.result(timeout=5)["created"] is False
        with pytest.raises(sidecar.SidecarError, match="CONFLICT"):
            divergent_future.result(timeout=5)


def test_store_lock_uses_directory_flock_modes(
    isolated_store: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Public lock protocol requests exclusive/shared file locks and unlocks."""

    calls: list[int] = []
    original_flock = sidecar.fcntl.flock

    def recording_flock(descriptor: int, operation: int) -> None:
        calls.append(operation)
        original_flock(descriptor, operation)

    monkeypatch.setattr(sidecar.fcntl, "flock", recording_flock)
    with sidecar._store_lock(exclusive=True, create_store=True):
        pass
    with sidecar._store_lock(exclusive=False, create_store=False):
        pass

    assert calls == [
        sidecar.fcntl.LOCK_EX,
        sidecar.fcntl.LOCK_UN,
        sidecar.fcntl.LOCK_SH,
        sidecar.fcntl.LOCK_UN,
    ]


def test_read_only_operations_do_not_create_missing_store(isolated_store: Path) -> None:
    """Empty reporting and failed validation remain filesystem read-only."""

    assert not sidecar.STORE_ROOT.exists()
    report = sidecar.report()
    assert report["counts"]["start_receipts"] == 0
    assert not sidecar.STORE_ROOT.exists()

    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.validate("sha256:" + ("d" * 64))
    assert not sidecar.STORE_ROOT.exists()


def test_validate_rejects_tampering_and_nonregular_receipts(isolated_store: Path) -> None:
    """Receipt fingerprint and file-shape checks fail closed."""

    prepared = _prepare(isolated_store)
    path = isolated_store / str(prepared["sidecar_path"])
    value = json.loads(path.read_text())
    value["base_sha"] = SHA_B
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.validate(str(prepared["sidecar_id"]))


def test_validate_and_report_reject_self_fingerprinted_identity_mismatch(
    isolated_store: Path,
) -> None:
    """A fresh receipt hash cannot conceal mutation of a start identity field."""

    prepared = _prepare(isolated_store)
    path = isolated_store / str(prepared["sidecar_path"])
    value = json.loads(path.read_text())
    value["base_sha"] = SHA_B
    _write_self_fingerprinted_start(path, value)

    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.validate(str(prepared["sidecar_id"]))
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.report()


def test_validate_and_report_reject_self_fingerprinted_directory_id_mismatch(
    isolated_store: Path,
) -> None:
    """Directory/id relabeling cannot substitute for canonical identity recomputation."""

    prepared = _prepare(isolated_store)
    original = isolated_store / str(prepared["sidecar_path"])
    fabricated_id = "sha256:" + ("e" * 64)
    fabricated_dir = sidecar.STORE_ROOT / ("e" * 64)
    fabricated_dir.mkdir(mode=0o700)
    value = json.loads(original.read_text())
    value["sidecar_id"] = fabricated_id
    _write_self_fingerprinted_start(fabricated_dir / "start.json", value)

    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.validate(fabricated_id)
    with pytest.raises(sidecar.SidecarError, match="INVALID_INPUT"):
        sidecar.report()
