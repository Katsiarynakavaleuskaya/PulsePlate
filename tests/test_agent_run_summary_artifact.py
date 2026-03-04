"""Tests for agent run summary artifact (JSON contract, determinism)."""

from __future__ import annotations

import json

import pytest

from scripts.orchestration.agent_run_summary import build_summary, compute_run_id


def test_run_id_is_deterministic() -> None:
    text = "Мы не ставим диагнозы. Это wellness-поддержка."
    rid1 = compute_run_id(agent="philosophy-agent", domain="safety", task_type="Safety", text=text)
    rid2 = compute_run_id(agent="philosophy-agent", domain="safety", task_type="Safety", text=text)
    assert rid1 == rid2
    assert len(rid1) == 12


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
    )

    assert summary["run_id"] == "fixed_run_id"
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
    )
    payload = json.dumps(summary, ensure_ascii=False, sort_keys=True)
    assert isinstance(payload, str)
    assert "philosophy_validator" in summary
