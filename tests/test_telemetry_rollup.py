"""Tests for telemetry_rollup script (agent run summary aggregation)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.orchestration.telemetry_rollup import (
    _aggregate,
    _extract_signal,
    _score_run,
    build_rollup,
    main,
)
from scripts.orchestration.telemetry_rollup import RunSignal


def test_extract_signal_valid_payload() -> None:
    payload = {
        "agent": "agent-coordinator",
        "domain": "docs",
        "task_type": "Documentation",
        "decision": {"action": "PASS", "max_severity": "LOW"},
        "philosophy_validator": {"ok": True, "issues": []},
        "static_scans": {},
    }
    sig = _extract_signal(payload)
    assert sig is not None
    assert sig.agent == "agent-coordinator"
    assert sig.domain == "docs"
    assert sig.decision == "PASS"
    assert sig.max_severity == "LOW"
    assert sig.static_fail is False


def test_extract_signal_rewrite_required() -> None:
    payload = {
        "agent": "philosophy-agent",
        "domain": "safety",
        "task_type": "Safety",
        "decision": {"action": "REWRITE_REQUIRED", "max_severity": "BLOCKER"},
        "philosophy_validator": {
            "ok": False,
            "issues": [{"severity": "BLOCKER", "code": "MEDICAL_CLAIM"}],
        },
        "static_scans": {},
    }
    sig = _extract_signal(payload)
    assert sig is not None
    assert sig.decision == "REWRITE_REQUIRED"
    assert sig.max_severity == "BLOCKER"
    assert sig.blocker_count == 1


def test_extract_signal_invalid_returns_none() -> None:
    assert _extract_signal({}) is None
    assert _extract_signal({"agent": "x", "domain": "y"}) is None  # missing task_type, decision
    assert _extract_signal({"agent": "x", "domain": "y", "task_type": "z", "decision": {}}) is None


def test_score_run_pass_low() -> None:
    sig = RunSignal(
        agent="a",
        domain="d",
        task_type="t",
        decision="PASS",
        max_severity="LOW",
        blocker_count=0,
        issues_count=0,
        static_fail=False,
    )
    assert _score_run(sig) > 0.9


def test_score_run_rewrite_blocker() -> None:
    sig = RunSignal(
        agent="a",
        domain="d",
        task_type="t",
        decision="REWRITE_REQUIRED",
        max_severity="BLOCKER",
        blocker_count=1,
        issues_count=1,
        static_fail=False,
    )
    assert _score_run(sig) < 0.6


def test_aggregate_empty_signals() -> None:
    out = _aggregate([])
    assert out["signals_count"] == 0
    assert out["agents"] == {}
    assert out["domains"] == {}


def test_aggregate_single_signal() -> None:
    sig = RunSignal(
        agent="agent-coordinator",
        domain="docs",
        task_type="Documentation",
        decision="PASS",
        max_severity="LOW",
        blocker_count=0,
        issues_count=0,
        static_fail=False,
    )
    out = _aggregate([sig])
    assert out["signals_count"] == 1
    assert "agent-coordinator" in out["agents"]
    assert out["agents"]["agent-coordinator"]["stability"] == "LOW_DATA"
    assert "docs" in out["domains"]
    assert out["domains"]["docs"]["primary_suggested"] == "agent-coordinator"


def test_build_rollup_empty_dir(tmp_path: Path) -> None:
    out = build_rollup(tmp_path)
    assert out["signals_count"] == 0
    assert "runs_dir" in out


def test_build_rollup_with_json(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs"
    run_dir.mkdir()
    (run_dir / "abc123__agent-coordinator__docs.json").write_text(
        json.dumps(
            {
                "run_id": "abc123",
                "agent": "agent-coordinator",
                "domain": "docs",
                "task_type": "Documentation",
                "decision": {"action": "PASS", "max_severity": "LOW"},
                "philosophy_validator": {"ok": True, "issues": []},
                "static_scans": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = build_rollup(run_dir)
    assert out["signals_count"] == 1
    assert "agent-coordinator" in out["agents"]


def test_main_writes_output(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    out_path = tmp_path / "rollup.json"
    exit_code = main(["--runs-dir", str(runs_dir), "--output", str(out_path)])
    assert exit_code == 0
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "signals_count" in data
    assert "agents" in data
