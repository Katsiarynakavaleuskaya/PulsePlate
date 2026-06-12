"""Tests for MVP evidence snapshot — sanitized, aggregate-only, allowlist-first."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

import pytest

import scripts.orchestration.context_pack as context_pack
from scripts.orchestration import experiment_slack_socket_bridge as bridge
from scripts.orchestration import mvp_evidence_snapshot as snapshot
from scripts.orchestration.mvp_evidence_snapshot import (
    ALLOWED_EVENT_NAMES,
    ALLOWED_PAYLOAD_KEYS,
    MvpEvidenceSnapshotLine,
    _DENYLIST_KEY_FRAGMENTS,
    _repo_root,
    _snapshot_dir,
    build_snapshot_line,
    cleanup_expired_snapshots,
    read_latest_snapshot_line,
    write_snapshot_line,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _configure_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    monkeypatch.setattr(context_pack, "REPO_ROOT", repo)
    monkeypatch.setattr(bridge, "REPO_ROOT", repo)
    monkeypatch.setattr(snapshot, "_repo_root", lambda: repo)
    return repo


def _sample_events() -> list[dict[str, Any]]:
    return [
        {
            "name": "guided_planning_viewed",
            "payload": {"surface": "app", "routePath": "/app", "authState": "authenticated"},
        },
        {
            "name": "planning_save_clicked",
            "payload": {
                "surface": "app",
                "routePath": "/app",
                "authState": "authenticated",
                "optionId": "save",
            },
        },
        {
            "name": "guided_planning_viewed",
            "payload": {"surface": "app", "routePath": "/app", "authState": "unauthenticated"},
        },
    ]


def test_build_snapshot_line_determinism(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(snapshot, "_now_iso", lambda: "2026-05-30T00:00:00.000000+00:00")
    events = _sample_events()
    line_a = build_snapshot_line(events, producer_name="test", producer_version="1.0.0")
    line_b = build_snapshot_line(events, producer_name="test", producer_version="1.0.0")
    assert line_a.fingerprint == line_b.fingerprint
    assert line_a.idempotency_key == line_b.idempotency_key
    assert line_a.event_aggregates == line_b.event_aggregates
    assert line_a.route_buckets == line_b.route_buckets
    assert line_a.auth_state_buckets == line_b.auth_state_buckets
    assert line_a.coverage_flags == line_b.coverage_flags


def test_build_snapshot_line_aggregates_counts() -> None:
    events = _sample_events()
    line = build_snapshot_line(events, producer_name="test", producer_version="1.0.0")
    assert line.event_aggregates["guided_planning_viewed"] == 2
    assert line.event_aggregates["planning_save_clicked"] == 1
    assert line.event_aggregates["planning_continue_clicked"] == 0


def test_build_snapshot_line_route_and_auth_buckets() -> None:
    events = _sample_events()
    line = build_snapshot_line(events, producer_name="test", producer_version="1.0.0")
    assert line.route_buckets == ("/app",)
    assert line.auth_state_buckets == ("authenticated", "unauthenticated")


def test_sanitize_payload_allowlist_first() -> None:
    raw = {
        "surface": "app",
        "routePath": "/app",
        "authState": "authenticated",
        "weight": 70,
        "bmi": 22.5,
        "freeText": "user comment",
        "unknownField": "should be dropped",
    }
    sanitized = snapshot._sanitize_payload(raw)
    assert sanitized == {
        "surface": "app",
        "routePath": "/app",
        "authState": "authenticated",
    }


def test_sanitize_payload_denylist_defense_in_depth() -> None:
    raw = {
        "surface": "app",
        "apiKey": "secret123",  # pragma: allowlist secret
        "sessionToken": "tok",  # pragma: allowlist secret
        "email": "a@b.com",
        "passwordHash": "hash",  # pragma: allowlist secret
        "jwt": "eyJ0",
    }
    sanitized = snapshot._sanitize_payload(raw)
    assert "apiKey" not in sanitized
    assert "sessionToken" not in sanitized
    assert "email" not in sanitized
    assert "passwordHash" not in sanitized
    assert "jwt" not in sanitized
    assert sanitized == {"surface": "app"}


def test_build_snapshot_line_no_leak_of_sensitive_fields() -> None:
    events = [
        {
            "name": "guided_planning_viewed",
            "payload": {
                "surface": "app",
                "routePath": "/app",
                "weight": 70,
                "bmi": 22.5,
                "freeText": "secret",
            },
        },
    ]
    line = build_snapshot_line(events, producer_name="test", producer_version="1.0.0")
    assert "weight" not in line.event_aggregates
    assert "bmi" not in line.event_aggregates
    assert "freeText" not in line.event_aggregates
    dict_form = snapshot._snapshot_line_to_dict(line)
    # Ensure sensitive values do not appear in aggregate or bucket fields
    assert dict_form["event_aggregates"] == {
        "guided_planning_viewed": 1,
        "planning_intent_selected": 0,
        "planning_time_selected": 0,
        "planning_preview_seen": 0,
        "tier_value_viewed": 0,
        "primary_planning_cta_clicked": 0,
        "wellness_boundary_viewed": 0,
        "planning_save_prompt_viewed": 0,
        "planning_auth_prompt_viewed": 0,
        "planning_progress_state_viewed": 0,
        "planning_save_clicked": 0,
        "planning_continue_clicked": 0,
    }
    assert dict_form["route_buckets"] == ["/app"]
    assert dict_form["auth_state_buckets"] == []
    # Ensure raw sensitive values do not leak into any field string representation
    for bucket in dict_form["route_buckets"]:
        assert "70" not in bucket and "22.5" not in bucket and "secret" not in bucket
    for bucket in dict_form["auth_state_buckets"]:
        assert "70" not in bucket and "22.5" not in bucket and "secret" not in bucket
    for flag in dict_form["coverage_flags"]:
        assert "70" not in flag and "22.5" not in flag and "secret" not in flag


def test_write_and_read_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _configure_repo(monkeypatch, tmp_path)
    events = _sample_events()
    line = build_snapshot_line(events, producer_name="test", producer_version="1.0.0")
    written = write_snapshot_line(line)
    assert written.exists()
    read = read_latest_snapshot_line()
    assert read is not None
    assert read.fingerprint == line.fingerprint
    assert read.idempotency_key == line.idempotency_key
    assert read.event_aggregates == line.event_aggregates


def test_read_latest_returns_none_when_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    assert read_latest_snapshot_line() is None


def test_read_latest_returns_none_on_corrupt_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _configure_repo(monkeypatch, tmp_path)
    snap_dir = repo / "artifacts" / "orchestration" / "mvp_evidence_snapshots"
    snap_dir.mkdir(parents=True)
    corrupt = (
        snap_dir
        / "mvp_evidence_snapshot_2026-05-30T00-00-00.000000+00-00_000000000000000000000000.json"
    )
    corrupt.write_text("not json", encoding="utf-8")
    assert read_latest_snapshot_line() is None


def test_render_mvp_evidence_summary_with_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _configure_repo(monkeypatch, tmp_path)
    events = _sample_events()
    line = build_snapshot_line(events, producer_name="test", producer_version="1.0.0")
    write_snapshot_line(line)
    msg = bridge.render_mvp_evidence_summary()
    assert msg.message_type == "mvp_evidence_summary"
    assert msg.status_line == "snapshot_backed"
    text = msg.as_text()
    assert "present_event_count=2" in text
    assert "route_buckets=/app" in text
    assert "auth_state_buckets=authenticated,unauthenticated" in text
    assert "coverage_preview=guided_planning_viewed=present; planning_save_clicked=present" in text


def test_render_mvp_evidence_summary_fallback_without_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    msg = bridge.render_mvp_evidence_summary()
    assert msg.message_type == "mvp_evidence_summary"
    assert msg.status_line == "advisory_operator_summary"
    text = msg.as_text()
    assert "safe_event_count=12" in text
    assert "route_path=/app" in text


def test_cleanup_expired_snapshots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    repo = _configure_repo(monkeypatch, tmp_path)
    snap_dir = repo / "artifacts" / "orchestration" / "mvp_evidence_snapshots"
    snap_dir.mkdir(parents=True)
    old_file = (
        snap_dir
        / "mvp_evidence_snapshot_2020-01-01T00-00-00.000000+00-00_000000000000000000000000.json"
    )
    old_file.write_text("{}", encoding="utf-8")
    new_mtime = 1577836800.0  # 2020-01-01T00:00:00 UTC
    os.utime(str(old_file), (new_mtime, new_mtime))

    result = cleanup_expired_snapshots(retention_days=1)
    assert result["status"] == "pass"
    assert result["deleted_count"] == 1
    assert result["expired_count"] == 1
    assert not old_file.exists()


def test_cleanup_removes_stale_temp_files_with_pid_suffix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    repo = _configure_repo(monkeypatch, tmp_path)
    snap_dir = repo / "artifacts" / "orchestration" / "mvp_evidence_snapshots"
    snap_dir.mkdir(parents=True)
    temp_file = snap_dir / "snapshot_2020-01-01T00-00-00.000000+00-00_abc123.tmp.12345"
    temp_file.write_text("{}", encoding="utf-8")
    old_mtime = 1577836800.0  # 2020-01-01T00:00:00 UTC
    os.utime(str(temp_file), (old_mtime, old_mtime))

    result = cleanup_expired_snapshots(retention_days=1)
    assert result["status"] == "pass"
    assert result["deleted_count"] == 1
    assert result["expired_count"] == 1
    assert not temp_file.exists()


def test_path_traversal_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _configure_repo(monkeypatch, tmp_path)
    line = build_snapshot_line([], producer_name="test", producer_version="1.0.0")
    with pytest.raises(ValueError, match="must stay under"):
        write_snapshot_line(line, base_dir=tmp_path / "outside")


def test_symlink_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _configure_repo(monkeypatch, tmp_path)
    snap_dir = repo / "artifacts" / "orchestration" / "mvp_evidence_snapshots"
    snap_dir.mkdir(parents=True)
    symlink_dir = tmp_path / "symlink_attack"
    symlink_dir.symlink_to(snap_dir)
    line = build_snapshot_line([], producer_name="test", producer_version="1.0.0")
    with pytest.raises(ValueError, match="symlink"):
        write_snapshot_line(line, base_dir=symlink_dir)


def test_cross_language_denylist_drift_guard() -> None:
    frontend_source = (REPO_ROOT / "frontend" / "src" / "lib" / "mvpObservability.ts").read_text(
        encoding="utf-8"
    )
    match = re.search(
        r"export const guidedPlanningObservabilitySensitiveFields = \[(.*?)\] as const;",
        frontend_source,
        re.DOTALL,
    )
    assert match is not None, "Frontend denylist not found"
    frontend_fields = set(re.findall(r"'([^']+)'", match.group(1)))
    assert frontend_fields, "Frontend denylist is empty"

    python_denylist = set(_DENYLIST_KEY_FRAGMENTS)
    # Frontend uses camelCase; Python denylist uses lowercase substring matching.
    missing: set[str] = set()
    for field in frontend_fields:
        lowered = field.lower()
        if not any(fragment in lowered for fragment in python_denylist):
            missing.add(field)

    assert not missing, (
        f"Frontend sensitive fields missing in Python denylist: {sorted(missing)}. "
        f"Add them to _DENYLIST_KEY_FRAGMENTS in mvp_evidence_snapshot.py."
    )


def test_allowed_payload_keys_subset_of_frontend_payload() -> None:
    frontend_source = (REPO_ROOT / "frontend" / "src" / "lib" / "mvpObservability.ts").read_text(
        encoding="utf-8"
    )
    match = re.search(
        r"export interface GuidedPlanningEventPayload \{(.*?)\}",
        frontend_source,
        re.DOTALL,
    )
    assert match is not None, "Frontend payload interface not found"
    frontend_keys = set(re.findall(r"(\w+)\??:", match.group(1)))
    assert frontend_keys, "Frontend payload keys not found"
    # ALLOWED_PAYLOAD_KEYS must be a subset of frontend payload keys
    extra = ALLOWED_PAYLOAD_KEYS - frontend_keys
    assert not extra, f"ALLOWED_PAYLOAD_KEYS contains keys not in frontend payload: {sorted(extra)}"


def test_read_latest_rejects_symlinked_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _configure_repo(monkeypatch, tmp_path)
    snap_dir = repo / "artifacts" / "orchestration" / "mvp_evidence_snapshots"
    snap_dir.mkdir(parents=True)
    real_file = (
        snap_dir
        / "mvp_evidence_snapshot_2026-05-30T00-00-00.000000+00-00_000000000000000000000000.json"
    )
    real_file.write_text("{}", encoding="utf-8")
    symlink_file = (
        snap_dir
        / "mvp_evidence_snapshot_2026-05-30T00-00-00.000000+00-00_111111111111111111111111.json"
    )
    symlink_file.symlink_to(real_file)
    with pytest.raises(ValueError, match="symlink"):
        read_latest_snapshot_line()


def test_read_latest_rejects_path_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="must stay under"):
        read_latest_snapshot_line(base_dir=tmp_path / "outside")


def test_cleanup_rejects_path_traversal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_repo(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="must stay under"):
        cleanup_expired_snapshots(base_dir=tmp_path / "outside")


def test_render_mvp_evidence_summary_fallback_on_read_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_repo(monkeypatch, tmp_path)
    called = False

    def _raise() -> None:
        nonlocal called
        called = True
        raise OSError("simulated read failure")

    monkeypatch.setattr(bridge, "_read_latest_snapshot_line", _raise)
    msg = bridge.render_mvp_evidence_summary()
    assert called is True
    assert msg.status_line == "advisory_operator_summary"
    assert "safe_event_count=12" in msg.as_text()


def test_cleanup_missing_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_repo(monkeypatch, tmp_path)
    result = cleanup_expired_snapshots()
    assert result == {
        "deleted_count": 0,
        "expired_count": 0,
        "retention_days": 30,
        "status": "pass",
    }


def test_render_mvp_evidence_summary_empty_buckets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _configure_repo(monkeypatch, tmp_path)
    line = build_snapshot_line([], producer_name="test", producer_version="1.0.0")
    write_snapshot_line(line)
    msg = bridge.render_mvp_evidence_summary()
    assert msg.status_line == "snapshot_backed"
    text = msg.as_text()
    assert "route_buckets=none" in text
    assert "auth_state_buckets=none" in text


def test_render_mvp_evidence_summary_no_events_observed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _configure_repo(monkeypatch, tmp_path)
    line = build_snapshot_line([], producer_name="test", producer_version="1.0.0")
    write_snapshot_line(line)
    msg = bridge.render_mvp_evidence_summary()
    assert msg.status_line == "snapshot_backed"
    text = msg.as_text()
    assert "coverage_preview=no_events_observed" in text


def test_fingerprint_verification_on_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _configure_repo(monkeypatch, tmp_path)
    events = _sample_events()
    line = build_snapshot_line(events, producer_name="test", producer_version="1.0.0")
    write_snapshot_line(line)
    # Tamper with the file: change a count
    latest = read_latest_snapshot_line()
    assert latest is not None
    snap_dir = repo / "artifacts" / "orchestration" / "mvp_evidence_snapshots"
    files = list(snap_dir.iterdir())
    assert files
    with open(files[0], "r", encoding="utf-8") as f:
        data = json.load(f)
    data["event_aggregates"]["guided_planning_viewed"] = 999
    with open(files[0], "w", encoding="utf-8") as f:
        json.dump(data, f)
    assert read_latest_snapshot_line() is None


def test_zero_microsecond_filename_regex() -> None:
    # Regex must match filenames without fractional seconds
    filename = "mvp_evidence_snapshot_2026-05-30T00-00-00+00-00_000000000000000000000000.json"
    match = snapshot._SNAPSHOT_FILENAME_RE.match(filename)
    assert match is not None
    assert match.group("idempotency_key") == "000000000000000000000000"


def test_invalid_utf8_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _configure_repo(monkeypatch, tmp_path)
    snap_dir = repo / "artifacts" / "orchestration" / "mvp_evidence_snapshots"
    snap_dir.mkdir(parents=True)
    bad = (
        snap_dir
        / "mvp_evidence_snapshot_2026-05-30T00-00-00.000000+00-00_000000000000000000000000.json"
    )
    bad.write_bytes(b"\xff\xfe not utf8")
    assert read_latest_snapshot_line() is None


@pytest.mark.parametrize("payload", ["[]", "null", "true", "123", '"bad"'])
def test_non_object_snapshot_returns_none_and_render_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: str
) -> None:
    repo = _configure_repo(monkeypatch, tmp_path)
    snap_dir = repo / "artifacts" / "orchestration" / "mvp_evidence_snapshots"
    snap_dir.mkdir(parents=True)
    bad = (
        snap_dir
        / "mvp_evidence_snapshot_2026-05-30T00-00-00.000000+00-00_000000000000000000000000.json"
    )
    bad.write_text(payload, encoding="utf-8")

    assert read_latest_snapshot_line() is None
    msg = bridge.render_mvp_evidence_summary()
    assert msg.message_type == "mvp_evidence_summary"
    assert msg.status_line == "advisory_operator_summary"
    assert "safe_event_count=12" in msg.evidence_summary
    assert "forbidden_user_data=omitted" in msg.evidence_summary


def test_non_string_payload_values_ignored() -> None:
    events = [
        {
            "name": "guided_planning_viewed",
            "payload": {
                "surface": "app",
                "routePath": "/app",
                "authState": "authenticated",
                "optionId": 123,
                "componentId": ["nested"],
            },
        },
    ]
    line = build_snapshot_line(events, producer_name="test", producer_version="1.0.0")
    assert line.event_aggregates["guided_planning_viewed"] == 1
    assert line.route_buckets == ("/app",)
    assert line.auth_state_buckets == ("authenticated",)


def test_cleanup_expired_snapshots_rejects_non_positive_retention() -> None:
    with pytest.raises(ValueError, match="retention_days must be positive"):
        cleanup_expired_snapshots(retention_days=0)
    with pytest.raises(ValueError, match="retention_days must be positive"):
        cleanup_expired_snapshots(retention_days=-1)


def test_read_latest_rejects_unknown_policy_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _configure_repo(monkeypatch, tmp_path)
    snap_dir = repo / "artifacts" / "orchestration" / "mvp_evidence_snapshots"
    snap_dir.mkdir(parents=True)
    bad = (
        snap_dir
        / "mvp_evidence_snapshot_2026-05-30T00-00-00.000000+00-00_000000000000000000000000.json"
    )
    # Use a valid fingerprint so the rejection is proven to come from
    # policy_version validation, not fingerprint mismatch.
    from scripts.orchestration.mvp_evidence_snapshot import _fingerprint_payload

    fake_payload = {
        "event_aggregates": {},
        "route_buckets": [],
        "auth_state_buckets": [],
        "coverage_flags": [],
        "policy_version": "unknown-version",
        "producer_name": "test",
        "producer_version": "1.0.0",
        "produced_at": "2026-05-30T00:00:00.000000+00:00",
    }
    valid_fingerprint = _fingerprint_payload(fake_payload)
    bad.write_text(
        json.dumps(
            {
                "idempotency_key": "000000000000000000000000",
                "fingerprint": valid_fingerprint,
                "produced_at": "2026-05-30T00:00:00.000000+00:00",
                "producer_name": "test",
                "producer_version": "1.0.0",
                "policy_version": "unknown-version",
                "event_aggregates": {},
                "route_buckets": [],
                "auth_state_buckets": [],
                "coverage_flags": [],
            }
        ),
        encoding="utf-8",
    )
    assert read_latest_snapshot_line() is None
