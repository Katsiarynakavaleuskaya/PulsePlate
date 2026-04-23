"""Unit tests for the canonical AI runtime gate bundle launcher."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

import scripts.orchestration.ai_runtime_gate_bundle as gate_bundle


def test_build_pytest_args_uses_canonical_nodes_then_appends_extra_args() -> None:
    """Canonical node order must stay stable before optional pytest args."""

    result = gate_bundle.build_pytest_args(["-k", "privacy"])

    assert result[: 1 + len(gate_bundle.AI_RUNTIME_GATE_TEST_NODES)] == [
        "-q",
        *gate_bundle.AI_RUNTIME_GATE_TEST_NODES,
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


def test_main_forwards_option_like_pytest_args(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI must pass through pytest-style flags instead of rejecting them."""

    observed: dict[str, Sequence[str]] = {}

    def _fake_pytest_main(args: Sequence[str]) -> int:
        observed["args"] = args
        return 0

    monkeypatch.setattr("pytest.main", _fake_pytest_main)

    exit_code = gate_bundle.main(["-x", "-k", "privacy"])

    assert exit_code == 0
    assert observed["args"] == gate_bundle.build_pytest_args(["-x", "-k", "privacy"])
