"""Unit tests for the canonical AI runtime gate bundle launcher."""

from __future__ import annotations

from collections.abc import Sequence

import scripts.orchestration.ai_runtime_gate_bundle as gate_bundle


def test_build_pytest_args_uses_canonical_nodes_then_appends_extra_args() -> None:
    """Canonical node order must stay stable before optional pytest args."""

    result = gate_bundle.build_pytest_args(["-k", "privacy"])

    assert result[:7] == [
        "-q",
        "tests/test_logic_philosophy_replay_eval.py",
        "tests/test_agent_run_summary_artifact.py",
        "tests/test_philosophy_validator.py",
        "tests/test_recursive_rag.py",
        "tests/test_rag_orchestration.py",
        "tests/test_vector_rag.py",
    ]
    assert result[-2:] == ["-k", "privacy"]


def test_run_gate_bundle_passes_built_args_to_pytest_runner() -> None:
    """Launcher must delegate through the canonical pytest arg builder."""

    observed: dict[str, Sequence[str]] = {}

    def _fake_pytest_runner(args: Sequence[str]) -> int:
        observed["args"] = args
        return 0

    exit_code = gate_bundle.run_gate_bundle(
        pytest_runner=_fake_pytest_runner,
        extra_args=["-x"],
    )

    assert exit_code == 0
    assert observed["args"] == gate_bundle.build_pytest_args(["-x"])
