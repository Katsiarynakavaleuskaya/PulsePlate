"""Metric config tests for the offline RAGAS bootstrap lane."""

from __future__ import annotations

from evals.ragas import metrics_config


def test_metrics_config_matches_bootstrap_contract() -> None:
    """The bootstrap metric tuple must stay exact."""

    assert metrics_config.DEFAULT_RAGAS_METRICS == (
        "faithfulness",
        "answer_relevancy",
        "context_precision",
    )


def test_bootstrap_runner_stays_report_only() -> None:
    """The bootstrap lane must remain report-only and threshold-free."""

    assert metrics_config.REPORT_ONLY_MODE is True
    assert not hasattr(metrics_config, "FAIL_THRESHOLDS")
    assert not hasattr(metrics_config, "GATE_THRESHOLDS")
