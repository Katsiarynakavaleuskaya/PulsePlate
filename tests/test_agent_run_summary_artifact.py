"""Tests for agent run summary artifact (JSON contract, determinism)."""

from __future__ import annotations

import json

from scripts.orchestration.agent_run_summary import build_summary, compute_run_id


def test_run_id_is_deterministic() -> None:
    text = "Мы не ставим диагнозы. Это wellness-поддержка."
    rid1 = compute_run_id(agent="philosophy-agent", domain="safety", task_type="Safety", text=text)
    rid2 = compute_run_id(agent="philosophy-agent", domain="safety", task_type="Safety", text=text)
    assert rid1 == rid2
    assert len(rid1) == 12


def test_run_id_changes_with_inputs() -> None:
    """run_id must change when agent, domain, task_type, or text changes."""
    base = {
        "agent": "philosophy-agent",
        "domain": "safety",
        "task_type": "Safety",
        "text": "Wellness-only advice.",
    }
    rid_base = compute_run_id(**base)
    assert rid_base != compute_run_id(**{**base, "agent": "logic-agent"})
    assert rid_base != compute_run_id(**{**base, "domain": "docs"})
    assert rid_base != compute_run_id(**{**base, "task_type": "Documentation"})
    assert rid_base != compute_run_id(**{**base, "text": "Different text."})


def test_summary_contains_philosophy_validator_blocker() -> None:
    # RU medical claim (вылечит) should be BLOCKER via philosophy_validator
    text = "Это вылечит вашу тревожность за 2 недели."
    summary = build_summary(
        agent="philosophy-agent",
        domain="safety",
        task_type="Safety / Philosophy / Logic",
        text=text,
        run_id="fixed_run_id",
        static_scan_docs=False,
        run_phase="execute",
        cluster="safety",
        agents_used=["agent-coordinator", "philosophy-agent"],
        handoff_count=1,
        sync_points=1,
        duration_ms=240,
        gate_status="pass",
        retries=0,
        outcome="pass",
    )

    assert summary["schema_version"] == "2.0"
    assert summary["run_id"] == "fixed_run_id"
    assert summary["cluster"] == "safety"
    assert summary["agents_used"] == ["agent-coordinator", "philosophy-agent"]
    assert summary["philosophy_validator"]["ok"] is False
    issues = summary["philosophy_validator"]["issues"]
    assert any(i.get("severity") == "BLOCKER" for i in issues)
    assert summary["decision"]["action"] == "REWRITE_REQUIRED"


def test_summary_json_is_serializable() -> None:
    text = "В wellness мы избегаем мед-обещаний и даём проверяемые рекомендации."
    summary = build_summary(
        agent="agent-coordinator",
        domain="docs",
        task_type="Documentation",
        text=text,
        run_id=None,
        static_scan_docs=False,
        run_phase="analyze",
        cluster="ops",
        agents_used=["agent-coordinator"],
        handoff_count=0,
        sync_points=0,
        duration_ms=15,
        gate_status="pass",
        retries=0,
        outcome="pass",
    )
    payload = json.dumps(summary, ensure_ascii=False, sort_keys=True)
    assert isinstance(payload, str)
    assert "philosophy_validator" in summary
    assert summary["gate_status"] == "pass"


def test_summary_includes_optional_experiment_context() -> None:
    summary = build_summary(
        agent="agent-coordinator",
        domain="ml",
        task_type="Experimentation",
        text="Bounded experiment summary.",
        run_id="run-experiment",
        static_scan_docs=False,
        experiment_context={
            "experiment_id": "exp-123",
            "failure_class": "guard_failure",
            "promotion_target": "backlog_entry",
            "oracle_name": "pytest -q tests/test_philosophical_runtime.py",
            "benchmark_delta": "-0.02",
        },
    )

    assert summary["experiment_context"]["experiment_id"] == "exp-123"
    assert summary["experiment_context"]["promotion_target"] == "backlog_entry"


def test_summary_omits_empty_experiment_context() -> None:
    summary = build_summary(
        agent="agent-coordinator",
        domain="ml",
        task_type="Experimentation",
        text="No experiment context.",
        run_id="run-no-experiment",
        static_scan_docs=False,
        experiment_context={},
    )

    assert "experiment_context" not in summary


def test_summary_accepts_unhashable_benchmark_delta() -> None:
    summary = build_summary(
        agent="agent-coordinator",
        domain="ml",
        task_type="Experimentation",
        text="Nested experiment context.",
        run_id="run-nested-experiment",
        static_scan_docs=False,
        experiment_context={
            "experiment_id": "exp-nested",
            "benchmark_delta": {"before": 1.0, "after": 0.9},
        },
    )

    assert summary["experiment_context"]["benchmark_delta"] == {"before": 1.0, "after": 0.9}
